from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.test import TestCase

from core.models import Organization
from core.post_ocr_pipeline import process_ocr_evidence
from documents.models import (
    Account,
    Document,
    ExtractedData,
    FinancialBudget,
    InvoiceAuditFinding,
    InvoiceRecord,
    OCREvidence,
    Vendor,
)
from documents.services.ingestion_persistence_service import invoice_ingestion_persistence_service
from documents.signals import auto_generate_audit_report, trigger_post_ocr_pipeline

User = get_user_model()


class InvoiceIngestionLayerTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        post_save.disconnect(auto_generate_audit_report, sender=ExtractedData)
        post_save.disconnect(trigger_post_ocr_pipeline, sender=OCREvidence)

    @classmethod
    def tearDownClass(cls):
        post_save.connect(auto_generate_audit_report, sender=ExtractedData)
        post_save.connect(trigger_post_ocr_pipeline, sender=OCREvidence)
        super().tearDownClass()

    @classmethod
    def setUpTestData(cls):
        cls.organization = Organization.objects.create(
            name='FinAI Saudi Org',
            country='SA',
            vat_number='300000000000003',
            vat_applicable=True,
            vat_validation_status='valid',
            currency='SAR',
        )
        cls.user = User.objects.create_user(
            email='auditor@finai.test',
            password='StrongPass!123',
            name='Audit Owner',
            role='admin',
            organization=cls.organization,
            organization_member_role='admin',
        )
        cls.account = Account.objects.create(
            organization=cls.organization,
            account_code='5000',
            account_name='Operations Expense',
            account_type='expense',
            account_subtype='other_expense',
            currency='SAR',
        )
        cls.budget = FinancialBudget.objects.create(
            organization=cls.organization,
            category='Operations',
            period_start=date(2026, 1, 1),
            period_end=date(2026, 12, 31),
            currency='SAR',
            budget_amount=Decimal('10000.00'),
            actual_spend=Decimal('1000.00'),
        )

    def _make_document(self, name='invoice.pdf', content_hash='hash-1'):
        return Document.objects.create(
            organization=self.organization,
            uploaded_by=self.user,
            file_name=name,
            file_type='application/pdf',
            file_size=2048,
            storage_key=f'uploads/{name}',
            storage_url=f'/media/uploads/{name}',
            content_hash=content_hash,
            document_type='invoice',
            status='completed',
        )

    def _payload(self, **overrides):
        payload = {
            'invoice_number': 'INV-100',
            'issue_date': '2026-03-10',
            'due_date': '2026-03-20',
            'vendor_name': 'Acme Supplies',
            'vendor_tax_id': '300123456700003',
            'customer_name': self.organization.name,
            'customer_tax_id': self.organization.vat_number,
            'currency': 'SAR',
            'subtotal': '100.00',
            'tax_amount': '15.00',
            'total_amount': '115.00',
            'cost_center': 'Operations',
            'budget_category': 'Operations',
            'account_code': '5000',
            'qr_code': 'zatca-qr',
            'items': [
                {
                    'description': 'Consulting services',
                    'quantity': '2',
                    'unit_price': '50.00',
                    'line_total': '100.00',
                }
            ],
        }
        payload.update(overrides)
        return payload

    def test_persist_creates_vendor_invoice_and_line_items(self):
        document = self._make_document()

        result = invoice_ingestion_persistence_service.persist(
            document=document,
            raw_payload=self._payload(),
            actor=self.user,
            confidence=92,
        )

        self.assertEqual(Vendor.objects.count(), 1)
        self.assertEqual(InvoiceRecord.objects.count(), 1)
        self.assertEqual(result.invoice.line_items.count(), 1)
        self.assertEqual(result.invoice.customer_organization, self.organization)
        self.assertEqual(result.invoice.accounting_account, self.account)
        self.assertEqual(result.invoice.budget, self.budget)
        self.assertEqual(result.extracted_data.raw_json['invoice_number'], 'INV-100')
        self.assertTrue(result.extracted_data.compliance_checks)
        self.assertTrue(result.extracted_data.is_valid)
        self.assertEqual(result.audit_result['procedures_run'], 10)
        self.assertEqual(result.to_dict()['vendor_id'], str(result.vendor.id))

    def test_persist_reuses_vendor_by_vat_and_flags_duplicate_invoice(self):
        first_document = self._make_document(name='first.pdf', content_hash='hash-first')
        second_document = self._make_document(name='second.pdf', content_hash='hash-second')

        first = invoice_ingestion_persistence_service.persist(
            document=first_document,
            raw_payload=self._payload(invoice_number='INV-DUP-1'),
            actor=self.user,
        )
        second = invoice_ingestion_persistence_service.persist(
            document=second_document,
            raw_payload=self._payload(invoice_number='INV-DUP-1'),
            actor=self.user,
        )

        self.assertEqual(first.vendor.id, second.vendor.id)
        self.assertGreaterEqual(second.extracted_data.duplicate_score, 95)
        self.assertFalse(second.extracted_data.is_valid)
        self.assertTrue(
            any('same vendor and same invoice number' in msg.lower() for msg in second.extracted_data.validation_errors)
        )
        self.assertTrue(
            InvoiceAuditFinding.objects.filter(
                extracted_data=second.extracted_data,
                field__startswith='rule:duplicate_vendor_invoice_number',
            ).exists()
        )

    def test_duplicate_document_hash_is_detected(self):
        first_document = self._make_document(name='hash-a.pdf', content_hash='same-hash')
        second_document = self._make_document(name='hash-b.pdf', content_hash='same-hash')

        invoice_ingestion_persistence_service.persist(
            document=first_document,
            raw_payload=self._payload(invoice_number='INV-HASH-A'),
            actor=self.user,
        )
        second = invoice_ingestion_persistence_service.persist(
            document=second_document,
            raw_payload=self._payload(invoice_number='INV-HASH-B'),
            actor=self.user,
        )

        self.assertEqual(second.extracted_data.duplicate_score, 100)
        self.assertTrue(
            any('content hash' in msg.lower() for msg in second.extracted_data.validation_errors)
        )

    def test_approved_invoice_cannot_be_modified(self):
        document = self._make_document(name='approved.pdf', content_hash='hash-approved')
        result = invoice_ingestion_persistence_service.persist(
            document=document,
            raw_payload=self._payload(invoice_number='INV-APPROVED'),
            actor=self.user,
        )

        invoice = result.invoice
        invoice.approval_status = 'approved'
        invoice.approved_by = self.user
        invoice.save()

        invoice.total_amount = Decimal('999.00')
        with self.assertRaisesMessage(ValidationError, 'Approved invoices cannot be modified.'):
            invoice.save()

    @patch('core.post_ocr_pipeline.generate_audit_report')
    @patch('core.post_ocr_pipeline.generate_ai_summary')
    @patch('core.post_ocr_pipeline.calculate_risk_score')
    @patch('core.post_ocr_pipeline.create_compliance_findings')
    def test_process_ocr_evidence_persists_relational_records(self, _mock_findings, _mock_risk, _mock_summary, _mock_report):
        document = self._make_document(name='ocr.pdf', content_hash='hash-ocr')
        ocr_evidence = OCREvidence.objects.create(
            document=document,
            organization=self.organization,
            raw_text='raw invoice text',
            text_ar='نص عربي',
            text_en='english text',
            confidence_score=90,
            confidence_level='high',
            page_count=1,
            word_count=5,
            ocr_engine='openai_vision',
            language_used='mixed',
            evidence_hash='hash-evidence',
            extracted_by=self.user,
            structured_data_json=self._payload(invoice_number='INV-OCR-1'),
        )

        extracted = process_ocr_evidence(ocr_evidence)
        again = process_ocr_evidence(ocr_evidence)

        self.assertIsNotNone(extracted)
        self.assertEqual(extracted.id, again.id)
        self.assertEqual(InvoiceRecord.objects.filter(document=document).count(), 1)
        self.assertEqual(document.invoice_records.count(), 1)
        self.assertEqual(document.invoice_records.first().vendor.vat_number, '300123456700003')
        self.assertEqual(extracted.raw_text_en, 'english text')
