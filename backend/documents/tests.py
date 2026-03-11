from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Organization
from documents.models import Document, ExtractedData, InvoiceAuditReport


User = get_user_model()


class AuditReportPresentationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organization = Organization.objects.create(
            name='Hasaballah Hamadain Organization',
            country='SA',
            vat_number='300123456700003',
            vat_applicable=True,
            vat_validation_status='valid',
        )
        cls.user = User.objects.create_user(
            email='audit-report@finai.test',
            password='StrongPass!123',
            name='Audit Report User',
            role='admin',
            organization=cls.organization,
        )

        cls.document = Document.objects.create(
            organization=cls.organization,
            uploaded_by=cls.user,
            file_name='invoice-ar.pdf',
            file_type='application/pdf',
            file_size=2048,
            storage_key='uploads/test/invoice-ar.pdf',
            storage_url='/media/uploads/test/invoice-ar.pdf',
            content_hash='abc123hash',
            document_type='invoice',
            status='completed',
            language='ar',
        )

        cls.extracted_data = ExtractedData.objects.create(
            document=cls.document,
            organization=cls.organization,
            vendor_name='شركة المثال',
            vendor_tax_id='300123456700003',
            customer_name='عميل تجريبي',
            customer_tax_id='300987654300003',
            invoice_number='INV-AR-100',
            invoice_date=timezone.now(),
            due_date=timezone.now(),
            total_amount=Decimal('115.00'),
            tax_amount=Decimal('15.00'),
            subtotal_amount=Decimal('100.00'),
            currency='SAR',
            items_json=[
                {
                    'description': 'خدمة استشارية',
                    'quantity': '2',
                    'unit_price': '50.00',
                    'discount': '0.00',
                    'total': '100.00',
                }
            ],
        )

        cls.report, _ = InvoiceAuditReport.objects.update_or_create(
            extracted_data=cls.extracted_data,
            defaults={
                'document': cls.document,
                'organization': cls.organization,
                'report_number': 'AR-20260311-TEST01',
                'status': 'generated',
                'upload_date': timezone.now(),
                'ocr_engine': 'tesseract',
                'ocr_confidence_score': 92,
                'processing_status': 'completed',
                'extracted_invoice_number': 'INV-AR-100',
                'extracted_issue_date': timezone.now(),
                'extracted_due_date': timezone.now(),
                'extracted_vendor_name': 'شركة المثال',
                'extracted_vendor_address': 'الرياض',
                'extracted_vendor_tin': '300123456700003',
                'extracted_customer_name': 'عميل تجريبي',
                'extracted_customer_address': 'جدة',
                'extracted_customer_tin': '300987654300003',
                'line_items_json': [
                    {
                        'description': 'خدمة استشارية',
                        'quantity': '2',
                        'unit_price': '50.00',
                        'discount': '0.00',
                        'total': '100.00',
                    }
                ],
                'subtotal_amount': Decimal('100.00'),
                'vat_amount': Decimal('15.00'),
                'total_amount': Decimal('115.00'),
                'currency': 'SAR',
                'validation_results_json': {
                    'invoice_number': {'status': 'fail', 'issues': ['Invoice number is missing']},
                    'vendor': {'status': 'pass', 'issues': []},
                    'customer': {'status': 'warning', 'issues': ['Customer TIN is missing']},
                    'items': {'status': 'pass', 'issues': []},
                    'total_match': {'status': 'pass', 'issues': []},
                    'vat': {'status': 'warning', 'issues': ['VAT amount is missing or zero']},
                },
                'duplicate_score': 84,
                'duplicate_status': 'confirmed_duplicate',
                'anomaly_score': 65,
                'anomaly_status': 'warning',
                'anomaly_explanation': 'Potential duplicate detected',
                'anomaly_reasons_json': [
                    {'reason': 'Due date is before invoice date', 'type': 'detected'}
                ],
                'risk_score': 90,
                'risk_level': 'critical',
                'risk_factors_json': ['Potential duplicate detected (score: 84)'],
                'ai_summary': 'English AI summary that should not appear on Arabic UI.',
                'ai_findings': 'English AI findings that should not appear on Arabic UI.',
                'ai_review_required': True,
                'recommendation': 'reject',
                'recommendation_reason': 'Critical risk detected (90/100); invoice_number validation failed',
                'audit_trail_json': [
                    {
                        'timestamp': timezone.now().isoformat(),
                        'event': 'audit_summary',
                        'status': 'success',
                        'title': 'Audit Report Generated',
                        'description': 'Comprehensive audit report generated: AR-20260311-TEST01',
                    }
                ],
                'generated_by': cls.user,
            },
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def _set_session_language(self, lang: str) -> None:
        session = self.client.session
        session['language'] = lang
        session.save()

    def test_audit_report_detail_uses_arabic_labels_and_fallback_content(self):
        self._set_session_language('ar')

        response = self.client.get(reverse('audit-report-detail', args=[self.report.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'تقرير التدقيق الشامل')
        self.assertContains(response, 'جدول التحقق')
        self.assertContains(response, 'تنزيل PDF')
        self.assertContains(response, 'الفاتورة رقم INV-AR-100')
        self.assertContains(response, 'رقم الفاتورة مفقود')
        self.assertNotContains(response, 'English AI summary that should not appear on Arabic UI.')

    def test_audit_report_pdf_download_returns_pdf_file(self):
        self._set_session_language('ar')

        response = self.client.get(reverse('audit-report-download-pdf', args=[self.report.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_pipeline_result_uses_arabic_report_presentation_and_pdf_action(self):
        self._set_session_language('ar')

        response = self.client.get(reverse('pipeline_result', args=[self.document.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'تنزيل PDF')
        self.assertContains(response, 'رقم الفاتورة مفقود')
        self.assertContains(response, reverse('web_audit_report_download_pdf', args=[self.report.id]))
        self.assertNotContains(response, 'English AI summary that should not appear on Arabic UI.')
