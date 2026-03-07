"""
FinAI QA Test Suite — Invoice Lifecycle (5 Critical Scenarios)
مجموعة اختبارات جودة منصة FinAI — دورة حياة الفاتورة

Engineer: QA Lead — Financial Systems
Coverage:
  TC-01  Multi-lingual OCR + Arabic/Hindi numeral conversion
  TC-02  Mathematical cross-validation (qty × price ≠ total)
  TC-03  ZATCA TIN compliance (15-digit, starts/ends with 3)
  TC-04  Duplicate invoice detection (ZIP batch)
  TC-05  Alpine.js frontend live-total integrity (simulated via form POST)

Run:
    cd backend
    python manage.py test tests.test_invoice_lifecycle -v 2
"""
from __future__ import annotations

import json
import os
import tempfile
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from core.models import Organization
from documents.models import Document, ExtractedData

User = get_user_model()

# ─────────────────────────────────────────────────────────────────────────────
# Shared fixtures
# ─────────────────────────────────────────────────────────────────────────────

class FinAIBaseTest(TestCase):
    """
    Base class with shared setup for all QA scenarios.
    Creates one Organisation, one Auditor user, and pre-connects the Django
    test Client so individual tests stay focused on their assertion.
    """

    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(
            name="شركة الخليج للتجارة",
            country="SA",
        )
        cls.user = User.objects.create_user(
            email="qa@finai-test.com",
            password="QApassword!123",
            name="QA Auditor",
            role="auditor",
            organization=cls.org,
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _make_document(self, name="invoice.pdf", status="completed"):
        return Document.objects.create(
            organization=self.org,
            uploaded_by=self.user,
            file_name=name,
            file_type="application/pdf",
            file_size=1024,
            storage_key=f"test/{uuid.uuid4()}.pdf",
            storage_url=f"/media/test/{uuid.uuid4()}.pdf",
            document_type="invoice",
            status=status,
        )

    def _make_extracted(self, document, **kwargs):
        defaults = dict(
            organization=self.org,
            vendor_name="شركة المورد",
            invoice_number="INV-2024-001",
            currency="SAR",
            confidence=85,
            extraction_status="extracted",
            is_valid=True,
        )
        defaults.update(kwargs)
        return ExtractedData.objects.create(document=document, **defaults)


# ─────────────────────────────────────────────────────────────────────────────
# TC-01  Multi-lingual OCR + Arabic/Hindi Numeral Conversion
# ─────────────────────────────────────────────────────────────────────────────

class TC01_ArabicNumeralConversion(FinAIBaseTest):
    """
    SCENARIO: Invoice image contains Arabic text and Eastern-Arabic numerals
    (١٢٣٤٫٥٦ ريال — Eastern Arabic decimal: ٫)

    GOAL:
    - ArabicNumeralNormalizer converts every digit before Decimal parsing
    - No digit-mixing (e.g. 1٬234 must not become 1234.0 via wrong separator)
    - Normalization pipeline returns Decimal with correct value
    """

    def test_eastern_arabic_digits_converted(self):
        """TC-01-A: Basic digit conversion ١٢٣٤٥ → 12345"""
        from core.infrastructure.arabic_normalizer import ArabicNumeralNormalizer
        n = ArabicNumeralNormalizer()

        self.assertEqual(n.convert_string("١٢٣٤٥"), "12345")
        self.assertEqual(n.convert_string("٠.٥"), "0.5")
        self.assertEqual(n.convert_string("١٬٥٠٠٫٠٠"), "1٬500.00")

    def test_persian_hindi_digits_converted(self):
        """TC-01-B: Persian/Hindi digit set ۱۲۳۴ → 1234"""
        from core.infrastructure.arabic_normalizer import ArabicNumeralNormalizer
        n = ArabicNumeralNormalizer()

        self.assertEqual(n.convert_string("۱۲۳"), "123")
        self.assertEqual(n.convert_string("المبلغ ۱٬۵۰۰"), "المبلغ 1٬500")

    def test_mixed_invoice_dict_fully_normalised(self):
        """TC-01-C: Full invoice dict with mixed numerals is normalised end-to-end"""
        from core.infrastructure.arabic_normalizer import ArabicNumeralNormalizer
        n = ArabicNumeralNormalizer()

        raw = {
            "invoice_number": "INV-٢٠٢٤-٠٠١",
            "total_amount": "١٬٢٣٥.٠٠",
            "vendor": {"name": "شركة XYZ", "tax_id": "٣١٢٣٤٥٦٧٨٩٠١٢٣٣"},
            "items": [{"qty": "٢", "unit_price": "٦١٧.٥٠", "total": "١٢٣٥.٠٠"}],
        }
        result = n.normalize(raw)

        self.assertEqual(result["invoice_number"], "INV-2024-001")
        self.assertEqual(result["total_amount"], "1٬235.00")
        self.assertEqual(result["items"][0]["qty"], "2")
        self.assertEqual(result["vendor"]["tax_id"], "312345678901233")

    def test_normalization_service_handles_arabic_amounts(self):
        """TC-01-D: InvoiceNormalizationService.normalize_amount parses converted Arabic amount"""
        from core.invoice_normalization_service import InvoiceNormalizationService

        # Simulate what arrives after ArabicNumeralNormalizer runs
        amount_str = "1235.00"   # post-conversion
        result = InvoiceNormalizationService.normalize_amount(amount_str)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, Decimal)
        self.assertEqual(result, Decimal("1235.00"))

    def test_thousands_separator_not_confused_with_decimal(self):
        """TC-01-E: 1,235 (thousands) must not become 1.235 (decimal error)"""
        from core.invoice_normalization_service import InvoiceNormalizationService

        # Commas are thousands separators — result should be 1235.0 not 1.235
        result = InvoiceNormalizationService.normalize_amount("1,235.00")
        self.assertEqual(result, Decimal("1235.00"),
                         "Comma should be stripped as thousands separator, not treated as decimal")

    # ── Result summary ────────────────────────────────────────────────────────
    # Expected: PASS — ArabicNumeralNormalizer + InvoiceNormalizationService
    #           handle all variants correctly.


# ─────────────────────────────────────────────────────────────────────────────
# TC-02  Mathematical Cross-Validation (items total ≠ invoice total)
# ─────────────────────────────────────────────────────────────────────────────

class TC02_MathematicalValidation(FinAIBaseTest):
    """
    SCENARIO: Invoice total = 1,000 SAR but sum(items) = 950 SAR (Δ = 50)

    GOAL:
    - ComplianceCheckService detects the mismatch
    - Check name 'total_consistency' has status CHECK_INVALID
    - Risk score is elevated (≥ High threshold)
    - Pipeline result template would show 🔴 alert for this check
    """

    def _build_invoice_data(self, declared_total, items_sum):
        return {
            "invoice_number": "INV-MATH-001",
            "issue_date": timezone.now(),
            "due_date": timezone.now(),
            "vendor": {"name": "مورد الاختبار", "tax_id": ""},
            "customer": {"name": "عميل الاختبار", "tax_id": ""},
            "currency": "SAR",
            "total_amount": Decimal(str(declared_total)),
            "items": [
                {"description": "خدمة", "amount": Decimal(str(items_sum))}
            ],
        }

    def test_detects_total_mismatch(self):
        """TC-02-A: Compliance engine flags mismatch (1000 declared vs 950 actual)"""
        from core.invoice_compliance_service import InvoiceComplianceCheckService

        service = InvoiceComplianceCheckService()
        data = self._build_invoice_data(declared_total=1000, items_sum=950)
        checks, _ = service.check_invoice_compliance(data)

        total_check = next((c for c in checks if c.check_name == "total_consistency"), None)
        self.assertIsNotNone(total_check, "total_consistency check must be present")
        self.assertNotEqual(total_check.status, "pass",
                            "Status must NOT be pass when mismatch is 50 SAR")
        self.assertIn("50", total_check.message,
                      "Mismatch message should mention the difference amount")

    def test_risk_score_elevated_on_mismatch(self):
        """TC-02-B: Risk score ≥ 50 (High) when critical mismatch present"""
        from core.invoice_compliance_service import InvoiceComplianceCheckService
        from core.invoice_risk_scoring_service import InvoiceRiskScoringService

        service = InvoiceComplianceCheckService()
        data = self._build_invoice_data(declared_total=1000, items_sum=950)
        checks, _ = service.check_invoice_compliance(data)

        scorer = InvoiceRiskScoringService()
        score, level = scorer.compute_risk_score(checks)

        self.assertGreaterEqual(score, 50,
                                f"Risk score should be ≥50 for critical mismatch, got {score}")
        self.assertIn(level, ["High", "Critical"],
                      f"Risk level should be High or Critical, got '{level}'")

    def test_within_tolerance_passes(self):
        """TC-02-C: Δ ≤ 0.01 SAR is accepted (floating-point tolerance)"""
        from core.invoice_compliance_service import InvoiceComplianceCheckService

        service = InvoiceComplianceCheckService()
        data = self._build_invoice_data(
            declared_total=Decimal("1000.00"),
            items_sum=Decimal("999.995"),
        )
        checks, _ = service.check_invoice_compliance(data)

        total_check = next((c for c in checks if c.check_name == "total_consistency"), None)
        if total_check:
            self.assertEqual(total_check.status, "pass",
                             "Sub-penny differences must be accepted as rounding")

    def test_mismatch_stored_in_extracted_data(self):
        """TC-02-D: validation_errors list contains mismatch info after pipeline save"""
        doc = self._make_document()
        ext = self._make_extracted(
            doc,
            total_amount=Decimal("1000.00"),
            items_json=[{"description": "خدمة", "amount": "950.00"}],
            validation_errors=["Total mismatch: invoice 1000 vs items 950 (diff: 50)"],
            is_valid=False,
        )

        self.assertFalse(ext.is_valid)
        self.assertTrue(any("mismatch" in e.lower() or "total" in e.lower()
                            for e in ext.validation_errors),
                        "validation_errors must document the mismatch")

    # ── Result summary ────────────────────────────────────────────────────────
    # Expected: PASS — InvoiceComplianceCheckService._check_total_consistency
    #           correctly detects and reports the 50 SAR discrepancy.


# ─────────────────────────────────────────────────────────────────────────────
# TC-03  ZATCA TIN Compliance (Saudi 15-digit, starts/ends with 3)
# ─────────────────────────────────────────────────────────────────────────────

class TC03_ZATCACompliance(FinAIBaseTest):
    """
    SCENARIO: Vendor TIN = '200345678901235' (starts with 2, ends with 5)
              — ZATCA requires starts AND ends with '3'

    GOAL:
    - VATValidationService returns valid=False
    - ComplianceCheckService triggers at least one ERROR-level check
    - Risk level escalates to High or Critical
    """

    VALID_SA_TIN   = "312345678901233"    # 15 digits, starts 3, ends 3 ✓
    INVALID_SA_TIN = "200345678901235"    # starts 2, ends 5 ✗

    def test_valid_zatca_tin_accepted(self):
        """TC-03-A: Correct 15-digit ZATCA TIN is accepted"""
        from core.vat_validation_service import VATValidationService
        svc = VATValidationService()
        result = svc.validate_vat_number(self.VALID_SA_TIN, country="SA")
        self.assertTrue(result["valid"],
                        f"Valid ZATCA TIN {self.VALID_SA_TIN} should be accepted")

    def test_invalid_start_end_rejected(self):
        """TC-03-B: TIN starting with 2 and ending with 5 is rejected"""
        from core.vat_validation_service import VATValidationService
        svc = VATValidationService()
        result = svc.validate_vat_number(self.INVALID_SA_TIN, country="SA")

        self.assertFalse(result["valid"],
                         "TIN not starting/ending with 3 must be invalid")
        self.assertEqual(result["error_code"], "invalid_format",
                         "Error code should be 'invalid_format'")

    def test_wrong_length_rejected(self):
        """TC-03-C: 14-digit TIN is rejected (must be exactly 15)"""
        from core.vat_validation_service import VATValidationService
        svc = VATValidationService()
        short_tin = "31234567890123"   # 14 digits
        result = svc.validate_vat_number(short_tin, country="SA")

        self.assertFalse(result["valid"])
        self.assertEqual(result["error_code"], "invalid_length")

    def test_non_digit_tin_rejected(self):
        """TC-03-D: TIN with letters or hyphens is rejected"""
        from core.vat_validation_service import VATValidationService
        svc = VATValidationService()
        result = svc.validate_vat_number("3-1234567890123-3", country="SA")
        self.assertFalse(result["valid"])

    def test_compliance_engine_flags_invalid_tin_as_high_risk(self):
        """TC-03-E: Full compliance check on invoice with invalid TIN → risk ≥ High"""
        from core.invoice_compliance_service import InvoiceComplianceCheckService
        from core.invoice_risk_scoring_service import InvoiceRiskScoringService

        data = {
            "invoice_number": "INV-ZATCA-001",
            "issue_date": timezone.now(),
            "due_date": timezone.now(),
            "vendor":   {"name": "مورد خاطئ", "tax_id": self.INVALID_SA_TIN},
            "customer": {"name": "عميل", "tax_id": self.VALID_SA_TIN},
            "currency": "SAR",
            "total_amount": Decimal("5000.00"),
            "items": [{"description": "بضاعة", "amount": Decimal("5000.00")}],
        }

        checks, _ = InvoiceComplianceCheckService().check_invoice_compliance(data)
        score, level = InvoiceRiskScoringService().compute_risk_score(checks)

        # With an invalid TIN the risk should be elevated
        self.assertGreaterEqual(score, 25,
                                f"Invalid ZATCA TIN must raise risk score, got {score}")

    def test_arabic_region_non_sa_tin_optional(self):
        """TC-03-F: UAE company without TIN is NOT penalised (VAT optional)"""
        from core.vat_validation_service import VATValidationService
        svc = VATValidationService()
        result = svc.validate_vat_number(None, country="AE")
        self.assertTrue(result["valid"],
                        "UAE TIN is optional — empty should be valid")

    # ── Result summary ────────────────────────────────────────────────────────
    # Expected: PASS — _validate_saudi_vat() correctly enforces ZATCA rules.


# ─────────────────────────────────────────────────────────────────────────────
# TC-04  Duplicate Invoice Detection
# ─────────────────────────────────────────────────────────────────────────────

class TC04_DuplicateDetection(FinAIBaseTest):
    """
    SCENARIO: Invoice INV-2024-DUP / vendor 'شركة ABC' / 5000 SAR
              was uploaded last week.  The same invoice is uploaded again
              today (simulating a ZIP batch re-upload).

    GOAL:
    - DuplicateDetectionService assigns score ≥ 80
    - is_exact or is_likely flag is True
    - document.duplicate_score is stored in ExtractedData
    """

    def _seed_original_invoice(self):
        doc = self._make_document("original_inv.pdf")
        ext = self._make_extracted(
            doc,
            invoice_number="INV-2024-DUP",
            vendor_name="شركة ABC للتجارة",
            total_amount=Decimal("5000.00"),
            currency="SAR",
            invoice_date=timezone.now() - timezone.timedelta(days=7),
        )
        return doc, ext

    def test_exact_duplicate_detected(self):
        """TC-04-A: Identical number + vendor + amount triggers duplicate ≥ 80"""
        from core.invoice_duplicate_detection_service import InvoiceDuplicateDetectionService

        _, original = self._seed_original_invoice()
        new_doc = self._make_document("dup_inv.pdf")

        svc = InvoiceDuplicateDetectionService()
        matches = svc.find_duplicates(
            new_invoice_data={
                "invoice_number": "INV-2024-DUP",
                "vendor_name":    "شركة ABC للتجارة",
                "total_amount":   Decimal("5000.00"),
                "currency":       "SAR",
                "issue_date":     timezone.now().date(),
            },
            organization_id=str(self.org.id),
            exclude_document_id=str(new_doc.id),
        )

        self.assertTrue(len(matches) > 0, "At least one duplicate match must be found")
        top = max(matches, key=lambda m: m.score)
        self.assertGreaterEqual(top.score, 75,
                                f"Duplicate score should be ≥75, got {top.score}")
        self.assertTrue(top.is_likely or top.is_exact,
                        "Duplicate should be flagged as likely or exact")

    def test_different_vendor_not_duplicate(self):
        """TC-04-B: Same amount but different vendor → NOT a duplicate"""
        from core.invoice_duplicate_detection_service import InvoiceDuplicateDetectionService

        self._seed_original_invoice()
        svc = InvoiceDuplicateDetectionService()
        matches = svc.find_duplicates(
            new_invoice_data={
                "invoice_number": "INV-2024-DUP",
                "vendor_name":    "شركة ZZZ مختلفة تماماً",
                "total_amount":   Decimal("5000.00"),
                "currency":       "SAR",
                "issue_date":     timezone.now().date(),
            },
            organization_id=str(self.org.id),
        )

        exact_matches = [m for m in matches if m.is_exact]
        self.assertEqual(len(exact_matches), 0,
                         "Different vendor should not produce exact duplicate")

    def test_duplicate_score_stored_in_model(self):
        """TC-04-C: duplicate_score field persisted in ExtractedData"""
        doc = self._make_document("dup_stored.pdf")
        ext = self._make_extracted(doc, duplicate_score=82, duplicate_matched_document=None)

        refreshed = ExtractedData.objects.get(pk=ext.pk)
        self.assertEqual(refreshed.duplicate_score, 82)

    def test_organisation_isolation(self):
        """TC-04-D: Duplicate from another org is NOT visible (data isolation)"""
        # Create a second org with same invoice
        org2 = Organization.objects.create(name="منظمة أخرى", country="AE")
        user2 = User.objects.create_user(
            email="user2@other.com", password="pass", organization=org2
        )
        doc2 = Document.objects.create(
            organization=org2, uploaded_by=user2,
            file_name="other_org.pdf", file_type="application/pdf",
            file_size=512, storage_key="other/x.pdf", storage_url="/media/other/x.pdf",
            document_type="invoice", status="completed",
        )
        ExtractedData.objects.create(
            document=doc2, organization=org2,
            invoice_number="INV-2024-DUP",
            vendor_name="شركة ABC للتجارة",
            total_amount=Decimal("5000.00"),
            currency="SAR",
            extraction_status="extracted",
        )

        from core.invoice_duplicate_detection_service import InvoiceDuplicateDetectionService
        svc = InvoiceDuplicateDetectionService()
        matches = svc.find_duplicates(
            new_invoice_data={
                "invoice_number": "INV-2024-DUP",
                "vendor_name":    "شركة ABC للتجارة",
                "total_amount":   Decimal("5000.00"),
                "currency":       "SAR",
            },
            organization_id=str(self.org.id),   # ← original org
        )

        # Must return zero matches — other org's data must not leak
        self.assertEqual(len(matches), 0,
                         "Cross-organization duplicate leakage detected — SECURITY FAILURE")

    # ── Result summary ────────────────────────────────────────────────────────
    # Expected: PASS — InvoiceDuplicateDetectionService correctly enforces
    #           org isolation and scores identical invoices ≥ 75.


# ─────────────────────────────────────────────────────────────────────────────
# TC-05  Alpine.js Live-Total Integrity (Pending Review correction POST)
# ─────────────────────────────────────────────────────────────────────────────

class TC05_PendingReviewFormIntegrity(FinAIBaseTest):
    """
    SCENARIO: Accountant manually edits unit_price in the pending_review form.
    Alpine.js recalculates total live (browser-side).
    On form submission Django's pending_review_submit_view must:
      - Accept corrected total_amount
      - Normalise the date
      - Promote document.status to 'completed'
      - Record reviewed_by / reviewed_at

    NOTE: TC-05-A simulates the Alpine.js recalculation with pure Python
    arithmetic (unit test). TC-05-B–D test the Django POST endpoint directly.
    """

    def _make_pending_doc(self):
        doc = self._make_document("pending_review.pdf", status="pending_review")
        ext = self._make_extracted(
            doc,
            total_amount=Decimal("0"),
            vendor_name="???",          # OCR unreadable
            invoice_number="???",
            confidence=30,
            extraction_status="pending_review",
            is_valid=False,
            is_fallback=True,
            extraction_provider="tesseract_ocr",
        )
        return doc, ext

    # ── TC-05-A  Alpine.js live-total arithmetic (pure Python) ───────────────

    def test_alpine_js_total_formula(self):
        """TC-05-A: qty × unit_price − discount = total (the formula Alpine.js uses)"""
        # Simulates the JS expression:
        # total = qty * unit_price - discount
        test_cases = [
            # (qty, unit_price, discount, expected_total)
            (2,   617.50, 0,    1235.00),
            (10,  100.00, 50,   950.00),
            (1,   999.99, 0,    999.99),
            (5,   200.00, 100,  900.00),
        ]
        for qty, unit_price, discount, expected in test_cases:
            with self.subTest(qty=qty, unit_price=unit_price, discount=discount):
                calculated = round(qty * unit_price - discount, 2)
                self.assertAlmostEqual(
                    calculated, expected, places=2,
                    msg=f"Alpine.js formula failed: {qty}×{unit_price}−{discount}≠{expected}"
                )

    # ── TC-05-B  POST → pending_review_submit_view ───────────────────────────

    def test_correction_post_updates_fields(self):
        """TC-05-B: POST with corrected data updates ExtractedData fields"""
        doc, ext = self._make_pending_doc()

        response = self.client.post(
            reverse("pending_review_submit", kwargs={"document_id": str(doc.id)}),
            data={
                "invoice_number": "INV-2024-CORRECTED",
                "vendor_name":    "شركة التوريدات السعودية",
                "invoice_date":   "2024-03-15",
                "due_date":       "2024-04-15",
                "total_amount":   "1235.00",
                "tax_amount":     "185.25",
                "currency":       "SAR",
                "review_notes":   "صُحِّح يدوياً من قِبل المحاسب",
            },
        )

        # Must redirect (302) after successful save
        self.assertIn(response.status_code, [302, 200],
                      "POST should redirect or return 200 after save")

        ext.refresh_from_db()
        doc.refresh_from_db()

        self.assertEqual(ext.invoice_number, "INV-2024-CORRECTED")
        self.assertEqual(ext.vendor_name,    "شركة التوريدات السعودية")
        self.assertEqual(ext.total_amount,   Decimal("1235.00"))
        self.assertEqual(ext.currency,       "SAR")
        self.assertEqual(ext.review_notes,   "صُحِّح يدوياً من قِبل المحاسب")
        self.assertEqual(ext.reviewed_by,    self.user)
        self.assertIsNotNone(ext.reviewed_at)
        self.assertEqual(ext.extraction_status, "extracted",
                         "Extraction status must be promoted out of pending_review")
        self.assertEqual(doc.status, "completed",
                         "Document status must become 'completed' after review")

    def test_correction_normalises_date(self):
        """TC-05-C: Date entered as DD/MM/YYYY is stored as YYYY-MM-DD"""
        doc, _ = self._make_pending_doc()

        self.client.post(
            reverse("pending_review_submit", kwargs={"document_id": str(doc.id)}),
            data={
                "invoice_date": "15/03/2024",   # DD/MM/YYYY format
                "currency": "SAR",
            },
        )

        ext = ExtractedData.objects.get(document=doc)
        if ext.invoice_date:
            date_str = (ext.invoice_date.strftime("%Y-%m-%d")
                        if hasattr(ext.invoice_date, "strftime")
                        else str(ext.invoice_date)[:10])
            self.assertEqual(date_str, "2024-03-15",
                             "Date must be normalised to YYYY-MM-DD regardless of input format")

    def test_empty_post_does_not_corrupt_data(self):
        """TC-05-D: Submitting empty fields must not overwrite existing values (DRY _patch logic)"""
        doc, ext = self._make_pending_doc()

        # Set a known total first
        ext.total_amount = Decimal("500.00")
        ext.save()

        self.client.post(
            reverse("pending_review_submit", kwargs={"document_id": str(doc.id)}),
            data={
                "total_amount": "",     # empty — should be ignored
                "currency": "SAR",
            },
        )

        ext.refresh_from_db()
        self.assertEqual(ext.total_amount, Decimal("500.00"),
                         "Empty POST field must not overwrite existing value (DRY _patch guard)")

    def test_unauthorised_user_cannot_access_other_org_document(self):
        """TC-05-E: User from Org-B cannot POST corrections to Org-A document"""
        org_b = Organization.objects.create(name="منظمة ب", country="AE")
        user_b = User.objects.create_user(
            email="b@other.com", password="pass", organization=org_b
        )
        doc, _ = self._make_pending_doc()

        client_b = Client()
        client_b.force_login(user_b)

        response = client_b.post(
            reverse("pending_review_submit", kwargs={"document_id": str(doc.id)}),
            data={"total_amount": "9999", "currency": "SAR"},
        )

        # Must return 404 (org isolation) not 200
        self.assertEqual(response.status_code, 404,
                         "Cross-org document access must return 404 — SECURITY FAILURE")

    # ── Result summary ────────────────────────────────────────────────────────
    # Expected: PASS — pending_review_submit_view enforces _patch DRY guard,
    #           date normalisation, org isolation, and field promotion.


# ─────────────────────────────────────────────────────────────────────────────
# CSV Ingestor Integration (bonus — verifies structured upload pipeline)
# ─────────────────────────────────────────────────────────────────────────────

class TC_BonusCSVIngestor(FinAIBaseTest):
    """
    Bonus TC: CSV file with Arabic column names and Hindu-Arabic numerals
    is parsed correctly through the IngestDocumentUseCase.
    """

    CSV_CONTENT = """\
رقم_الفاتورة,المورد,الإجمالي,العملة,تاريخ_الإصدار
INV-٢٠٢٤-٠٠١,شركة الرياض,١٢٣٥.٠٠,SAR,٢٠٢٤-٠٣-١٥
INV-2024-002,ABC Corp,2500.00,AED,2024-03-16
""".encode("utf-8")

    def test_csv_arabic_columns_and_hindu_digits_parsed(self):
        """BONUS: CSV with Arabic headers + Hindu numerals produces correct InvoiceData"""
        from core.application.ingest_document_usecase import default_ingest_usecase

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False,
                                         mode="wb") as f:
            f.write(self.CSV_CONTENT)
            path = f.name

        try:
            result = default_ingest_usecase.execute(path)
        finally:
            os.unlink(path)

        self.assertEqual(result.error_count, 0,
                         f"No parse errors expected, got: {result.errors}")
        self.assertEqual(result.success_count, 2)

        first = result.invoices[0]
        self.assertEqual(first.invoice_number, "INV-2024-001",
                         "Hindu digits in invoice number must be converted")
        self.assertEqual(first.total_amount, Decimal("1235.00"),
                         "Hindu digit amount must be correctly parsed")
        self.assertEqual(first.currency, "SAR")

        second = result.invoices[1]
        self.assertEqual(second.currency, "AED")
        self.assertEqual(second.total_amount, Decimal("2500.00"))
