import hashlib
import os
import uuid
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from core.models import Organization
from documents.models import AuditSession, Document, InvoiceRecord, Vendor
from documents.services.audit_workflow_service import invoice_audit_workflow_service

User = get_user_model()


class _FakeOpenAIExtractionService:
    client = object()

    def __init__(self, payload):
        self.payload = payload

    def extract_invoice(self, file_path):
        return self.payload


class AuditWorkflowTests(TestCase):
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
            email='workflow@finai.test',
            password='StrongPass!123',
            name='Workflow Owner',
            role='admin',
            organization=cls.organization,
            organization_member_role='admin',
        )

    def setUp(self):
        self.api_client = APIClient()
        self.api_client.force_authenticate(self.user)
        self.created_paths = []

    def tearDown(self):
        for path in self.created_paths:
            if os.path.exists(path):
                os.remove(path)

    def _make_document(self, name='invoice.pdf', content=b'pdf-content'):
        org_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', str(self.organization.id))
        os.makedirs(org_dir, exist_ok=True)
        stored_name = f'{uuid.uuid4()}.pdf'
        file_path = os.path.join(org_dir, stored_name)
        with open(file_path, 'wb') as handle:
            handle.write(content)
        self.created_paths.append(file_path)

        storage_key = f'uploads/{self.organization.id}/{stored_name}'
        storage_url = f'/media/{storage_key}'
        content_hash = hashlib.md5(content).hexdigest()
        document = Document.objects.create(
            organization=self.organization,
            uploaded_by=self.user,
            file_name=name,
            file_type='application/pdf',
            file_size=len(content),
            storage_key=storage_key,
            storage_url=storage_url,
            content_hash=content_hash,
            document_type='invoice',
            status='pending',
        )
        return document, file_path, content_hash

    def _extraction_payload(self, invoice_number='INV-200'):
        return {
            'extraction_success': True,
            'invoice_number': invoice_number,
            'issue_date': '2026-03-10',
            'due_date': '2026-03-20',
            'vendor_name': 'Acme Supplies',
            'vendor_tax_id': '300123456700003',
            'customer_name': self.organization.name,
            'customer_tax_id': self.organization.vat_number,
            'subtotal': '100.00',
            'tax_amount': '15.00',
            'tax_rate': '15',
            'total_amount': '115.00',
            'currency': 'SAR',
            'language_detected': 'mixed',
            'is_mathematically_correct': True,
            'confidence': 93,
            'items': [
                {
                    'description': 'Consulting services',
                    'quantity': '2',
                    'unit_price': '50.00',
                    'line_total': '100.00',
                }
            ],
        }

    @patch('documents.services.audit_workflow_service.get_openai_extraction_service')
    def test_process_document_runs_canonical_order_and_persists_entities(self, mock_get_service):
        document, file_path, content_hash = self._make_document()
        mock_get_service.return_value = _FakeOpenAIExtractionService(self._extraction_payload())

        session = invoice_audit_workflow_service.start_session(
            organization=self.organization,
            actor=self.user,
            file_name=document.file_name,
            content_hash=content_hash,
            source='web_upload',
        )
        result = invoice_audit_workflow_service.process_document(
            document=document,
            file_path=file_path,
            actor=self.user,
            language='mixed',
            is_handwritten=False,
            source='web_upload',
            audit_session=session,
        )

        result.audit_session.refresh_from_db()
        result.document.refresh_from_db()

        self.assertEqual(result.audit_session.status, 'published')
        self.assertEqual(result.audit_session.current_stage, 'publish_to_dashboard')
        self.assertEqual(result.document.status, 'completed')
        for stage in (
            'upload_file',
            'create_audit_session',
            'save_document',
            'ai_extraction',
            'normalization',
            'validation',
            'compliance_engine',
            'risk_score',
            'findings',
            'ai_executive_summary',
            'publish_to_dashboard',
        ):
            self.assertIn(stage, result.audit_session.stages_json)
            self.assertEqual(result.audit_session.stages_json[stage]['status'], 'completed')

        self.assertEqual(Vendor.objects.filter(organization=self.organization).count(), 1)
        self.assertEqual(InvoiceRecord.objects.filter(document=document).count(), 1)
        self.assertEqual(result.invoice.customer_name, self.organization.name)
        self.assertEqual(result.invoice.customer_vat_number, self.organization.vat_number)
        self.assertEqual(result.audit_session.invoice_record_id, result.invoice.id)
        self.assertEqual(result.audit_session.vendor_id, result.invoice.vendor_id)
        self.assertEqual(result.audit_session.dashboard_payload['invoice_id'], str(result.invoice.id))

    @patch('documents.services.audit_workflow_service.get_openai_extraction_service')
    def test_rerun_saved_audit_works_without_document_file(self, mock_get_service):
        document, file_path, content_hash = self._make_document(name='reaudit.pdf')
        mock_get_service.return_value = _FakeOpenAIExtractionService(self._extraction_payload(invoice_number='INV-RE-1'))

        initial = invoice_audit_workflow_service.process_document(
            document=document,
            file_path=file_path,
            actor=self.user,
            language='mixed',
            is_handwritten=False,
            source='web_upload',
            audit_session=invoice_audit_workflow_service.start_session(
                organization=self.organization,
                actor=self.user,
                file_name=document.file_name,
                content_hash=content_hash,
                source='web_upload',
            ),
        )

        os.remove(file_path)
        self.created_paths.remove(file_path)

        rerun = invoice_audit_workflow_service.rerun_saved_audit(document=document, actor=self.user)
        rerun.audit_session.refresh_from_db()

        self.assertEqual(rerun.audit_session.source, 're_audit')
        self.assertEqual(rerun.audit_session.status, 'published')
        self.assertEqual(rerun.audit_session.stages_json['ai_extraction']['status'], 'reused')
        self.assertEqual(InvoiceRecord.objects.filter(document=document).count(), 1)
        self.assertEqual(Vendor.objects.filter(organization=self.organization).count(), 1)
        self.assertEqual(rerun.invoice.customer_name, self.organization.name)
        self.assertEqual(rerun.invoice.customer_vat_number, self.organization.vat_number)
        self.assertEqual(initial.extracted_data.raw_json, rerun.extracted_data.raw_json)

    @patch('documents.services.audit_workflow_service.get_openai_extraction_service')
    def test_reaudit_endpoint_returns_saved_invoice_vendor_customer(self, mock_get_service):
        document, file_path, content_hash = self._make_document(name='endpoint.pdf')
        mock_get_service.return_value = _FakeOpenAIExtractionService(self._extraction_payload(invoice_number='INV-ENDPOINT'))

        invoice_audit_workflow_service.process_document(
            document=document,
            file_path=file_path,
            actor=self.user,
            language='mixed',
            is_handwritten=False,
            source='web_upload',
            audit_session=invoice_audit_workflow_service.start_session(
                organization=self.organization,
                actor=self.user,
                file_name=document.file_name,
                content_hash=content_hash,
                source='web_upload',
            ),
        )

        response = self.api_client.post(reverse('document-re-audit', args=[document.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['document_id'], str(document.id))
        self.assertEqual(response.data['customer_name'], self.organization.name)
        self.assertEqual(response.data['customer_tax_id'], self.organization.vat_number)
        self.assertIsNotNone(response.data['invoice_id'])
        self.assertIsNotNone(response.data['vendor_id'])
        self.assertEqual(AuditSession.objects.filter(document=document, source='re_audit').count(), 1)
