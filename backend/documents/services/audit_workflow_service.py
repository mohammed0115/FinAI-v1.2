from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.utils import timezone

from core.openai_invoice_extraction_service import get_openai_extraction_service
from documents.models import (
    AuditSession,
    AuditTrail,
    Document,
    ExtractedData,
    InvoiceAuditFinding,
    InvoiceRecord,
    OCREvidence,
)
from documents.services.audit_report_service import (
    AnomalyDetectionService,
    DataValidationService,
    DuplicateDetectionService,
    InvoiceAuditReportService,
    RecommendationService,
    RiskScoringService,
)
from documents.services.ingestion_persistence_service import invoice_ingestion_persistence_service
from documents.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)


@dataclass
class AuditWorkflowResult:
    audit_session: AuditSession
    document: Document
    extracted_data: Optional[ExtractedData]
    invoice: Optional[InvoiceRecord]
    ocr_evidence: Optional[OCREvidence]


class InvoiceAuditWorkflowService:
    """Canonical workflow for upload, audit, and publish."""

    STAGE_SEQUENCE = [
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
    ]

    def __init__(self):
        self.openai_service = OpenAIService()

    def start_session(
        self,
        *,
        organization,
        actor,
        file_name: str,
        content_hash: Optional[str] = None,
        source: str = 'web_upload',
        document: Optional[Document] = None,
    ) -> AuditSession:
        now = timezone.now().isoformat()
        stages = {
            'upload_file': {'status': 'completed', 'at': now},
            'create_audit_session': {'status': 'completed', 'at': now},
        }
        for stage in self.STAGE_SEQUENCE[2:]:
            stages[stage] = {'status': 'pending'}

        return AuditSession.objects.create(
            organization=organization,
            started_by=actor,
            source=source,
            file_name=file_name,
            content_hash=content_hash,
            document=document,
            status='processing',
            current_stage='create_audit_session',
            stages_json=stages,
        )

    def resolve_document_file_path(self, document: Document) -> str:
        storage_key = (document.storage_key or '').lstrip('/\\')
        if storage_key:
            return os.path.join(settings.MEDIA_ROOT, storage_key)

        storage_url = (document.storage_url or '').replace('\\', '/')
        if storage_url.startswith('/media/'):
            relative_path = storage_url[len('/media/'):]
            return os.path.join(settings.MEDIA_ROOT, relative_path)
        if storage_url.startswith('media/'):
            relative_path = storage_url[len('media/'):]
            return os.path.join(settings.MEDIA_ROOT, relative_path)
        return storage_url

    def process_document(
        self,
        *,
        document: Document,
        file_path: str,
        actor,
        language: str = 'mixed',
        is_handwritten: bool = False,
        source: str = 'web_upload',
        audit_session: Optional[AuditSession] = None,
    ) -> AuditWorkflowResult:
        session = audit_session or self.start_session(
            organization=document.organization,
            actor=actor,
            file_name=document.file_name,
            content_hash=document.content_hash,
            source=source,
            document=document,
        )
        if session.document_id != document.id:
            session.document = document
            session.save(update_fields=['document'])
        self._mark_stage(
            session,
            'save_document',
            'completed',
            {'document_id': str(document.id), 'storage_key': document.storage_key},
        )

        try:
            document.status = 'processing'
            document.save(update_fields=['status'])

            extraction = self._extract_with_ai(
                document=document,
                file_path=file_path,
                actor=actor,
                language=language,
                is_handwritten=is_handwritten,
            )

            self._mark_stage(
                session,
                'ai_extraction',
                'completed',
                {
                    'ocr_evidence_id': str(extraction['ocr_evidence'].id),
                    'confidence': extraction['confidence'],
                    'provider': extraction['provider'],
                },
            )
            return self._continue_from_payload(
                session=session,
                document=document,
                actor=actor,
                raw_payload=extraction['structured_json'],
                ocr_evidence=extraction['ocr_evidence'],
                extraction_provider=extraction['provider'],
                confidence=extraction['confidence'],
            )
        except Exception as exc:
            logger.error('Audit workflow failed for document %s: %s', document.id, exc, exc_info=True)
            document.status = 'failed'
            document.save(update_fields=['status'])
            self._fail_session(session, 'ai_extraction', str(exc))
            raise

    def process_existing_ocr_evidence(
        self,
        *,
        ocr_evidence: OCREvidence,
        actor=None,
        source: str = 'ocr_signal',
    ) -> Optional[ExtractedData]:
        document = ocr_evidence.document
        actor = actor or document.uploaded_by
        raw_payload = ocr_evidence.structured_data_json or {}
        if not raw_payload:
            logger.warning('OCR evidence %s has no structured payload to process', ocr_evidence.id)
            return None

        session = self.start_session(
            organization=document.organization,
            actor=actor,
            file_name=document.file_name,
            content_hash=document.content_hash,
            source=source,
            document=document,
        )
        self._mark_stage(
            session,
            'save_document',
            'completed',
            {'document_id': str(document.id), 'reused_saved_document': True},
        )
        self._mark_stage(
            session,
            'ai_extraction',
            'reused',
            {'ocr_evidence_id': str(ocr_evidence.id), 'reused_saved_extraction': True},
        )

        result = self._continue_from_payload(
            session=session,
            document=document,
            actor=actor,
            raw_payload=raw_payload,
            ocr_evidence=ocr_evidence,
            extraction_provider='saved_ocr_evidence',
            confidence=ocr_evidence.confidence_score,
        )
        return result.extracted_data

    def rerun_saved_audit(self, *, document: Document, actor) -> AuditWorkflowResult:
        extracted_data = getattr(document, 'extracted_data', None)
        raw_payload = None
        extraction_provider = 'saved_invoice_state'
        confidence = 0
        ocr_evidence = document.ocr_evidence_records.order_by('-extracted_at').first()

        if extracted_data and extracted_data.raw_json:
            raw_payload = extracted_data.raw_json
            extraction_provider = extracted_data.extraction_provider or extraction_provider
            confidence = extracted_data.confidence or 0
        elif document.invoice_records.exists() and document.invoice_records.first().raw_json:
            raw_payload = document.invoice_records.first().raw_json
        elif ocr_evidence and ocr_evidence.structured_data_json:
            raw_payload = ocr_evidence.structured_data_json
            extraction_provider = 'saved_ocr_evidence'
            confidence = ocr_evidence.confidence_score

        if not raw_payload:
            raise ValueError('No saved invoice data is available to re-audit this document.')

        session = self.start_session(
            organization=document.organization,
            actor=actor,
            file_name=document.file_name,
            content_hash=document.content_hash,
            source='re_audit',
            document=document,
        )
        self._mark_stage(
            session,
            'save_document',
            'reused',
            {'document_id': str(document.id), 'reused_saved_document': True},
        )
        self._mark_stage(
            session,
            'ai_extraction',
            'reused',
            {'reused_saved_extraction': True},
        )

        return self._continue_from_payload(
            session=session,
            document=document,
            actor=actor,
            raw_payload=raw_payload,
            ocr_evidence=ocr_evidence,
            extraction_provider=extraction_provider,
            confidence=confidence,
            existing_extracted_data=extracted_data,
        )

    def _continue_from_payload(
        self,
        *,
        session: AuditSession,
        document: Document,
        actor,
        raw_payload: Dict[str, Any],
        ocr_evidence: Optional[OCREvidence],
        extraction_provider: str,
        confidence: int,
        existing_extracted_data: Optional[ExtractedData] = None,
    ) -> AuditWorkflowResult:
        try:
            normalized = invoice_ingestion_persistence_service.normalize_payload(raw_payload)
            self._mark_stage(
                session,
                'normalization',
                'completed',
                {
                    'invoice_number': normalized.get('invoice_number'),
                    'currency': normalized.get('currency'),
                    'vendor_name': normalized.get('vendor_name'),
                    'customer_name': normalized.get('customer_name'),
                },
            )

            if existing_extracted_data is None:
                try:
                    existing_extracted_data = document.extracted_data
                except ExtractedData.DoesNotExist:
                    existing_extracted_data = None

            persistence_result = invoice_ingestion_persistence_service.persist(
                document=document,
                raw_payload=raw_payload,
                actor=actor,
                extraction_provider=extraction_provider,
                confidence=confidence,
                extracted_data=existing_extracted_data,
                normalized_payload=normalized,
            )
            extracted_data = persistence_result.extracted_data
            invoice = persistence_result.invoice

            self._sync_ocr_snapshot(extracted_data=extracted_data, ocr_evidence=ocr_evidence)

            self._attach_session_entities(session, persistence_result)
            self._mark_stage(
                session,
                'validation',
                'completed',
                {
                    'errors_count': (persistence_result.audit_result or {}).get('errors_count', len(extracted_data.validation_errors or [])),
                    'warnings_count': (persistence_result.audit_result or {}).get('warnings_count', len(extracted_data.validation_warnings or [])),
                    'is_valid': extracted_data.is_valid,
                },
            )
            self._mark_stage(
                session,
                'compliance_engine',
                'completed',
                {
                    'checks_run': (persistence_result.audit_result or {}).get('checks_run', len(extracted_data.compliance_checks or [])),
                    'finding_count': (persistence_result.audit_result or {}).get(
                        'finding_count',
                        InvoiceAuditFinding.objects.filter(extracted_data=extracted_data).count(),
                    ),
                },
            )

            validation_results = DataValidationService.validate_all(extracted_data)
            duplicate_score, matched_docs, duplicate_status = DuplicateDetectionService.calculate_duplicate_score(
                extracted_data,
                document.organization,
            )
            anomaly_score, anomalies, anomaly_status = AnomalyDetectionService.calculate_anomaly_score(
                extracted_data,
                document.organization,
                ocr_evidence,
            )
            risk_score, risk_level, risk_factors = RiskScoringService.calculate_risk_score(
                validation_results,
                duplicate_score,
                anomaly_score,
                extracted_data,
            )

            extracted_data.duplicate_score = max(extracted_data.duplicate_score or 0, duplicate_score)
            extracted_data.anomaly_score = anomaly_score
            extracted_data.anomaly_flags = anomalies
            extracted_data.risk_score = risk_score
            extracted_data.risk_level = risk_level
            extracted_data.phase4_completed_at = timezone.now()
            extracted_data.save(
                update_fields=[
                    'duplicate_score',
                    'anomaly_score',
                    'anomaly_flags',
                    'risk_score',
                    'risk_level',
                    'phase4_completed_at',
                ]
            )

            self._mark_stage(
                session,
                'risk_score',
                'completed',
                {
                    'risk_score': risk_score,
                    'risk_level': risk_level,
                    'duplicate_status': duplicate_status,
                    'anomaly_status': anomaly_status,
                    'matched_documents': matched_docs,
                },
            )

            findings_qs = InvoiceAuditFinding.objects.filter(extracted_data=extracted_data)
            self._mark_stage(
                session,
                'findings',
                'completed',
                {
                    'count': findings_qs.count(),
                    'critical': findings_qs.filter(severity='critical').count(),
                    'high': findings_qs.filter(severity='high').count(),
                },
            )

            recommendation, recommendation_reason = RecommendationService.generate_recommendation(
                risk_score,
                risk_level,
                validation_results,
                duplicate_score,
                extracted_data,
            )
            ai_summary = self.openai_service.generate_invoice_summary(extracted_data, risk_level, anomalies)
            ai_findings = self.openai_service.generate_audit_findings(extracted_data, validation_results, anomalies)
            extracted_data.audit_summary = {
                'executive_summary': ai_summary,
                'key_risks': risk_factors,
                'recommended_actions': [recommendation_reason] if recommendation_reason else [],
                'final_status': recommendation,
                'ai_findings': ai_findings,
            }
            extracted_data.audit_completed_at = timezone.now()
            extracted_data.save(update_fields=['audit_summary', 'audit_completed_at'])

            report = InvoiceAuditReportService(user=actor).generate_comprehensive_report(
                extracted_data=extracted_data,
                document=document,
                organization=document.organization,
                ocr_evidence=ocr_evidence,
            )
            self._mark_stage(
                session,
                'ai_executive_summary',
                'completed',
                {
                    'recommendation': recommendation,
                    'report_id': str(report.id),
                },
            )

            final_status = 'pending_review' if risk_level in {'high', 'critical'} or not extracted_data.is_valid else 'completed'
            document.status = final_status
            document.processed_at = timezone.now()
            document.save(update_fields=['status', 'processed_at'])

            session.dashboard_payload = {
                'document_id': str(document.id),
                'invoice_id': str(invoice.id),
                'vendor_id': str(persistence_result.vendor.id),
                'customer_name': invoice.customer_name,
                'customer_tax_id': invoice.customer_vat_number,
                'risk_score': risk_score,
                'risk_level': risk_level,
                'findings_count': findings_qs.count(),
                'document_status': final_status,
            }
            session.status = 'published'
            session.current_stage = 'publish_to_dashboard'
            session.completed_at = timezone.now()
            session.published_at = timezone.now()
            session.save(update_fields=['dashboard_payload', 'status', 'current_stage', 'completed_at', 'published_at'])
            self._mark_stage(
                session,
                'publish_to_dashboard',
                'completed',
                {'document_status': final_status, 'published': True},
            )

            AuditTrail.objects.create(
                extracted_data=extracted_data,
                organization=document.organization,
                event_type='dashboard_publish',
                severity='info',
                title='Audit session published to dashboard',
                description='The canonical audit workflow completed and was published to the dashboard view.',
                performed_by=actor,
                details={
                    'audit_session_id': str(session.id),
                    'invoice_id': str(invoice.id),
                    'risk_score': risk_score,
                    'risk_level': risk_level,
                },
                success=True,
                result_summary=f'Published with {findings_qs.count()} findings and risk {risk_level}.',
                phase='phase3',
            )

            return AuditWorkflowResult(
                audit_session=session,
                document=document,
                extracted_data=extracted_data,
                invoice=invoice,
                ocr_evidence=ocr_evidence,
            )
        except Exception as exc:
            logger.error('Audit workflow continuation failed for document %s: %s', document.id, exc, exc_info=True)
            document.status = 'failed'
            document.save(update_fields=['status'])
            self._fail_session(session, session.current_stage or 'normalization', str(exc))
            raise

    def _sync_ocr_snapshot(self, *, extracted_data: ExtractedData, ocr_evidence: Optional[OCREvidence]) -> None:
        if ocr_evidence is None:
            return

        update_fields: List[str] = []
        if extracted_data.raw_text_ar != ocr_evidence.text_ar:
            extracted_data.raw_text_ar = ocr_evidence.text_ar
            update_fields.append('raw_text_ar')
        if extracted_data.raw_text_en != ocr_evidence.text_en:
            extracted_data.raw_text_en = ocr_evidence.text_en
            update_fields.append('raw_text_en')

        if update_fields:
            extracted_data.save(update_fields=update_fields)

    def _extract_with_ai(self, *, document: Document, file_path: str, actor, language: str, is_handwritten: bool) -> Dict[str, Any]:
        openai_svc = get_openai_extraction_service()
        if not openai_svc.client:
            raise RuntimeError('OpenAI API key not configured. Cannot process without AI extraction.')

        result = openai_svc.extract_invoice(file_path)
        if not result.get('extraction_success'):
            raise RuntimeError(result.get('error', 'AI extraction failed'))

        items = []
        for item in result.get('items', []) or []:
            items.append({
                'description': item.get('description') or item.get('product') or '',
                'quantity': item.get('quantity', 0),
                'unit_price': item.get('unit_price', 0),
                'discount': item.get('discount', 0),
                'line_total': item.get('line_total') or item.get('total') or 0,
            })

        structured_json = {
            'invoice_number': result.get('invoice_number'),
            'issue_date': result.get('issue_date'),
            'due_date': result.get('due_date'),
            'vendor_name': result.get('vendor_name'),
            'vendor_tax_id': result.get('vendor_tax_id'),
            'customer_name': result.get('customer_name'),
            'customer_tax_id': result.get('customer_tax_id'),
            'vendor': {
                'name': result.get('vendor_name'),
                'tax_id': result.get('vendor_tax_id'),
                'address': result.get('vendor_address'),
            },
            'customer': {
                'name': result.get('customer_name'),
                'tax_id': result.get('customer_tax_id'),
                'address': result.get('customer_address'),
            },
            'items': items,
            'subtotal': result.get('subtotal'),
            'tax_amount': result.get('tax_amount'),
            'tax_rate': result.get('tax_rate'),
            'discount_amount': result.get('discount_amount'),
            'total_amount': result.get('total_amount'),
            'currency': result.get('currency', 'SAR'),
            'language_detected': result.get('language_detected'),
            'is_mathematically_correct': result.get('is_mathematically_correct'),
        }
        confidence = result.get('confidence') or 85
        raw_text = json.dumps(structured_json, ensure_ascii=False)
        confidence_level = self._confidence_level(confidence)

        ocr_evidence = OCREvidence.objects.create(
            document=document,
            organization=document.organization,
            raw_text=raw_text,
            text_ar='',
            text_en='',
            confidence_score=confidence,
            confidence_level=confidence_level,
            page_count=1,
            word_count=len(raw_text.split()),
            ocr_engine='openai_vision',
            ocr_version='gpt-4o-mini',
            language_used=language,
            is_handwritten=is_handwritten,
            processing_time_ms=0,
            extracted_invoice_number=structured_json.get('invoice_number'),
            extracted_vat_number=structured_json.get('vendor_tax_id'),
            extracted_total=structured_json.get('total_amount') or 0,
            extracted_tax=structured_json.get('tax_amount') or 0,
            extracted_vendor_name=structured_json.get('vendor_name'),
            extracted_vendor_address=structured_json.get('vendor', {}).get('address') or '',
            extracted_customer_name=structured_json.get('customer_name'),
            extracted_customer_address=structured_json.get('customer', {}).get('address') or '',
            extracted_currency=structured_json.get('currency', 'SAR'),
            extracted_items=structured_json.get('items', []),
            structured_data_json=structured_json,
            evidence_hash=self._make_hash(raw_text),
            extracted_by=actor,
        )
        return {
            'structured_json': structured_json,
            'confidence': confidence,
            'provider': 'openai_vision',
            'ocr_evidence': ocr_evidence,
        }

    def _attach_session_entities(self, session: AuditSession, persistence_result) -> None:
        session.document = persistence_result.invoice.document
        session.extracted_data = persistence_result.extracted_data
        session.invoice_record = persistence_result.invoice
        session.vendor = persistence_result.vendor
        session.customer_name = persistence_result.invoice.customer_name
        session.customer_tax_id = persistence_result.invoice.customer_vat_number
        session.save(
            update_fields=[
                'document',
                'extracted_data',
                'invoice_record',
                'vendor',
                'customer_name',
                'customer_tax_id',
            ]
        )

    def _mark_stage(self, session: AuditSession, stage: str, status: str, details: Optional[Dict[str, Any]] = None) -> None:
        stages = dict(session.stages_json or {})
        payload = {'status': status, 'at': timezone.now().isoformat()}
        if details:
            payload['details'] = details
        stages[stage] = payload
        session.stages_json = stages
        session.current_stage = stage
        session.save(update_fields=['stages_json', 'current_stage'])

    def _fail_session(self, session: AuditSession, stage: str, error: str) -> None:
        self._mark_stage(session, stage, 'failed', {'error': error})
        session.status = 'failed'
        session.last_error = error
        session.completed_at = timezone.now()
        session.save(update_fields=['status', 'last_error', 'completed_at'])

    @staticmethod
    def _confidence_level(confidence: int) -> str:
        if confidence >= 80:
            return 'high'
        if confidence >= 50:
            return 'medium'
        if confidence >= 25:
            return 'low'
        return 'very_low'

    @staticmethod
    def _make_hash(value: str) -> str:
        return hashlib.sha256(value.encode('utf-8')).hexdigest()


invoice_audit_workflow_service = InvoiceAuditWorkflowService()
