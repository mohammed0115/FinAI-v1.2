from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.viewsets import ReadOnlyModelViewSet
from django.core.files.storage import default_storage
from django.utils import timezone
from django.db.models import Sum, Count, Q
from .models import (
    Document, ExtractedData, Transaction, Account,
    JournalEntry, JournalEntryLine, ComplianceCheck, AuditFlag,
    InvoiceAuditReport
)
from .serializers import (
    DocumentSerializer, ExtractedDataSerializer, TransactionSerializer,
    AccountSerializer, JournalEntrySerializer, JournalEntryLineSerializer,
    ComplianceCheckSerializer, AuditFlagSerializer
)
from core.api.base import OrganizationScopedModelViewSet, OrganizationScopedReadOnlyModelViewSet
from core.ai_service import ai_service
from documents.services.audit_workflow_service import invoice_audit_workflow_service
from decimal import Decimal
import uuid
import base64
import hashlib
import os
import logging
import tempfile
from urllib.parse import urlparse
import requests

logger = logging.getLogger(__name__)


class DocumentViewSet(OrganizationScopedModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    actor_save_field = 'uploaded_by'
    
    @staticmethod
    def _build_checks_list(raw_checks):
        """Transform compliance_checks dict → list for template rendering."""
        if isinstance(raw_checks, list):
            return raw_checks  # already correct shape
        checks = []
        for key, val in (raw_checks.items() if isinstance(raw_checks, dict) else []):
            passed = val.get('passed', False)
            findings = val.get('findings', [])
            checks.append({
                'check_name': val.get('check_name', key.replace('_', ' ').title()),
                'status': 'pass' if passed else 'fail',
                'passed': passed,
                'message': '; '.join(str(f) for f in findings) if findings else '',
                'severity': 'INFO' if passed else 'ERROR',
                'risk_score': val.get('risk_score', 0),
            })
        return checks

    @staticmethod
    def _build_audit_summary(phase3):
        """Build audit_summary dict matching pipeline_result.html expectations."""
        risk_score = phase3.get('risk_score', 0) or 0
        return {
            'executive_summary': phase3.get('executive_summary', ''),
            'key_risks': phase3.get('key_findings', []) or [],
            'recommended_actions': phase3.get('recommended_actions', []) or [],
            'final_status': 'approved' if risk_score < 40 else 'review',
        }

    @staticmethod
    def _compute_content_hash(file_obj):
        position = file_obj.tell() if hasattr(file_obj, 'tell') else 0
        payload = file_obj.read()
        if hasattr(file_obj, 'seek'):
            file_obj.seek(position)
        return hashlib.md5(payload).hexdigest()

    def _extract_invoice_data(self, document, file_path, audit_session=None, source='api_upload'):
        """
        Complete 5-phase invoice processing pipeline:
        1. Extraction: OpenAI Vision API
        2. Normalization: Data normalization and validation
        3. Compliance: Compliance checks and findings
        4. Cross-Document: Duplicate detection and anomalies
        5. Financial: Cash flow and spend intelligence
        
        Saves all phase results to ExtractedData model.
        
        Args:
            document: Document instance
            file_path: Full file path to the document
        """
        result = invoice_audit_workflow_service.process_document(
            document=document,
            file_path=file_path,
            actor=document.uploaded_by,
            language=document.language or 'mixed',
            is_handwritten=document.is_handwritten,
            source=source,
            audit_session=audit_session,
        )
        return result.extracted_data

        from core.invoice_processing_pipeline import get_pipeline_manager
        from dateutil import parser as date_parser
        import json
        
        try:
            # Get file extension
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # Accept images and PDFs
            if file_ext not in ['.jpg', '.jpeg', '.png', '.pdf']:
                logger.info(f"Invoice extraction skipped for {file_ext}: unsupported format")
                return None
            
            logger.info(f"Starting complete 5-phase pipeline for document {document.id}")
            
            # Get historical invoices from same organization for cross-document analysis
            historical_invoices = []
            try:
                historical_data = ExtractedData.objects.filter(
                    organization=document.organization,
                    extraction_status='extracted',
                    is_valid=True
                ).values_list('normalized_json', flat=True)[:30]  # Last 30 invoices
                
                for data_json in historical_data:
                    if data_json:
                        historical_invoices.append(data_json)
            except Exception as e:
                logger.warning(f"Could not load historical invoices: {str(e)}")
            
            # Run complete pipeline
            pipeline_manager = get_pipeline_manager()
            result = pipeline_manager.process_and_store(
                file_path=file_path,
                document_id=str(document.id),
                organization_id=str(document.organization.id),
                historical_invoices=historical_invoices
            )
            
            if result['status'] != 'success':
                logger.warning(
                    f"Pipeline processing failed for {document.id}: {result.get('error')}"
                )
                document.status = 'failed'
                document.save()
                return None
            
            # Extract fields from processing result
            extracted_fields = result.get('extracted_fields', {})
            processing_result = result.get('processing_result', {})
            phases = processing_result.get('phases', {})
            
            # Parse dates from extraction
            invoice_date = None
            due_date = None
            extracted_data_dict = extracted_fields.get('extracted_data', {})
            
            try:
                if extracted_data_dict.get('issue_date'):
                    invoice_date = date_parser.parse(extracted_data_dict['issue_date'])
            except:
                pass
            
            try:
                if extracted_data_dict.get('due_date'):
                    due_date = date_parser.parse(extracted_data_dict['due_date'])
            except:
                pass
            
            # Parse total amount
            total_amount = extracted_data_dict.get('total_amount')
            if total_amount and isinstance(total_amount, str):
                try:
                    total_amount = Decimal(total_amount.replace(',', '').strip())
                except (ValueError, TypeError):
                    total_amount = None
            
            # Create ExtractedData record with all phase results
            extracted_data = ExtractedData.objects.create(
                document=document,
                organization=document.organization,
                
                # Phase 1: Extraction
                vendor_name=extracted_data_dict.get('vendor_name', ''),
                customer_name=extracted_data_dict.get('customer_name', ''),
                invoice_number=extracted_data_dict.get('invoice_number', ''),
                invoice_date=invoice_date,
                due_date=due_date,
                total_amount=total_amount,
                tax_amount=extracted_data_dict.get('tax_amount'),
                currency=extracted_data_dict.get('currency', 'SAR'),
                items_json=extracted_data_dict.get('items', []),
                confidence=phases.get('phase_1_extraction', {}).get('extracted_data', {}).get('confidence', 0),
                extraction_status='extracted',
                extraction_completed_at=timezone.now(),
                # Provenance flags — DRY: single write, consumed by pipeline_result.html & audit reports
                is_fallback=phases.get('phase_1_extraction', {}).get('is_fallback', False),
                extraction_provider=phases.get('phase_1_extraction', {}).get('extraction_method', 'unknown'),
                
                # Phase 2: Normalization & Validation
                normalized_json=extracted_fields.get('normalized_json'),
                validation_errors=phases.get('phase_2_normalization', {}).get('validation_errors', []),
                validation_warnings=phases.get('phase_2_normalization', {}).get('validation_warnings', []),
                is_valid=phases.get('phase_2_normalization', {}).get('is_valid', False),
                validation_completed_at=timezone.now() if phases.get('phase_2_normalization') else None,
                
                # Phase 3: Compliance — transform to list/dict shapes the template expects
                compliance_checks=self._build_checks_list(phases.get('phase_3_compliance', {}).get('compliance_checks', {})),
                risk_score=phases.get('phase_3_compliance', {}).get('risk_score', 0),
                risk_level=phases.get('phase_3_compliance', {}).get('risk_level', 'unknown'),
                audit_summary=self._build_audit_summary(phases.get('phase_3_compliance', {})),
                audit_completed_at=timezone.now() if phases.get('phase_3_compliance', {}).get('status') == 'completed' else None,

                # Phase 4: Cross-Document Intelligence
                duplicate_score=phases.get('phase_4_cross_document', {}).get('duplicate_detection', {}).get('duplicate_risk_score', 0),
                anomaly_flags=phases.get('phase_4_cross_document', {}).get('anomaly_detection', {}).get('anomaly_flags', []) or [],
                anomaly_score=phases.get('phase_4_cross_document', {}).get('anomaly_detection', {}).get('anomaly_risk_score', 0),
                vendor_risk_score=phases.get('phase_4_cross_document', {}).get('vendor_risk', {}).get('vendor_risk_score', 0),
                vendor_risk_level=phases.get('phase_4_cross_document', {}).get('vendor_risk', {}).get('risk_level', 'unknown'),
                phase4_completed_at=timezone.now() if phases.get('phase_4_cross_document', {}).get('status') == 'completed' else None,
                
                validation_status='validated',
            )
            
            logger.info(
                f"Successfully processed invoice {extracted_data.id} through complete 5-phase pipeline. "
                f"Risk score: {extracted_data.risk_score}, Validation: {extracted_data.is_valid}"
            )
            
            return extracted_data
            
        except Exception as e:
            # Log the error but don't fail the upload
            logger.error(
                f"Unexpected error during pipeline processing for {document.id}: {str(e)}",
                exc_info=True
            )
            return None
    
    @action(detail=False, methods=['post'])
    def upload(self, request):
        """Upload document with file handling and optional invoice extraction"""
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Use logged-in user's organization instead of request data for security
        user_organization = request.user.organization
        if not user_organization:
            return Response(
                {'error': 'User does not belong to any organization'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        document_type = request.data.get('document_type', 'other')
        content_hash = self._compute_content_hash(file)
        audit_session = None
        if document_type == 'invoice':
            audit_session = invoice_audit_workflow_service.start_session(
                organization=user_organization,
                actor=request.user,
                file_name=file.name,
                content_hash=content_hash,
                source='api_upload',
            )
        
        # Save file
        file_name = file.name
        doc_id = str(uuid.uuid4())
        storage_key = f"documents/{user_organization.id}/{doc_id}/{file_name}"
        storage_path = default_storage.save(storage_key, file)
        storage_url = default_storage.url(storage_path)
        
        # Create document record
        document = Document.objects.create(
            id=doc_id,
            organization=user_organization,
            uploaded_by=request.user,
            file_name=file_name,
            file_type=file.content_type,
            file_size=file.size,
            storage_key=storage_key,
            storage_url=storage_url,
            content_hash=content_hash,
            document_type=document_type,
            status='pending'
        )
        
        # Try to get local file path for extraction
        extracted_data = None
        try:
            # If using local storage, get the actual file path
            if hasattr(default_storage, 'path'):
                try:
                    file_path = default_storage.path(storage_path)
                    # Extract invoice if document type is invoice
                    if document_type == 'invoice':
                        extracted_data = self._extract_invoice_data(
                            document,
                            file_path,
                            audit_session=audit_session,
                            source='api_upload',
                        )
                except Exception as path_error:
                    logger.warning(f"Could not get local file path: {path_error}")
                    if audit_session is not None:
                        audit_session.status = 'failed'
                        audit_session.last_error = str(path_error)
                        audit_session.completed_at = timezone.now()
                        audit_session.save(update_fields=['status', 'last_error', 'completed_at'])
        except Exception as e:
            # Don't crash the upload if extraction fails
            logger.error(f"Error during post-upload processing: {e}", exc_info=True)
        
        serializer = self.get_serializer(document)
        response_data = serializer.data
        
        # Add extraction info if successful
        if extracted_data:
            response_data['extracted_data'] = {
                'id': str(extracted_data.id),
                'invoice_number': extracted_data.invoice_number,
                'total_amount': float(extracted_data.total_amount) if extracted_data.total_amount else None,
                'confidence': extracted_data.confidence
            }
        if audit_session is not None:
            response_data['audit_session'] = {
                'id': str(audit_session.id),
                'status': audit_session.status,
                'current_stage': audit_session.current_stage,
            }
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def batch_upload(self, request):
        """Batch upload multiple documents"""

        files = request.FILES.getlist('files')
        if not files:
            return Response({'error': 'No files provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Use logged-in user's organization instead of request data for security
        user_organization = request.user.organization
        if not user_organization:
            return Response(
                {'error': 'User does not belong to any organization'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        document_type = request.data.get('document_type', 'other')
        
        uploaded_docs = []
        for file in files:
            content_hash = self._compute_content_hash(file)
            file_name = file.name
            doc_id = str(uuid.uuid4())
            storage_key = f"documents/{user_organization.id}/{doc_id}/{file_name}"
            storage_path = default_storage.save(storage_key, file)
            storage_url = default_storage.url(storage_path)
            audit_session = None
            if document_type == 'invoice':
                audit_session = invoice_audit_workflow_service.start_session(
                    organization=user_organization,
                    actor=request.user,
                    file_name=file_name,
                    content_hash=content_hash,
                    source='api_upload',
                )
            
            document = Document.objects.create(
                id=doc_id,
                organization=user_organization,
                uploaded_by=request.user,
                file_name=file_name,
                file_type=file.content_type,
                file_size=file.size,
                storage_key=storage_key,
                storage_url=storage_url,
                content_hash=content_hash,
                document_type=document_type,
                status='pending'
            )
            
            # Try invoice extraction for invoices
            if document_type == 'invoice':
                try:
                    if hasattr(default_storage, 'path'):
                        try:
                            file_path = default_storage.path(storage_path)
                            self._extract_invoice_data(
                                document,
                                file_path,
                                audit_session=audit_session,
                                source='api_upload',
                            )
                        except Exception as e:
                            logger.warning(f"Could not extract invoice for batch upload: {e}")
                except Exception as e:
                    logger.error(f"Error during batch invoice extraction: {e}", exc_info=True)
            
            uploaded_docs.append(document)
        
        serializer = self.get_serializer(uploaded_docs, many=True)
        return Response({
            'count': len(uploaded_docs),
            'documents': serializer.data
        }, status=status.HTTP_201_CREATED)

    
    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Process document with AI"""
        document = self.get_object()

        try:
            file_path = invoice_audit_workflow_service.resolve_document_file_path(document)
            workflow_result = invoice_audit_workflow_service.process_document(
                document=document,
                file_path=file_path,
                actor=request.user,
                language=document.language or 'mixed',
                is_handwritten=document.is_handwritten,
                source='api_upload',
            )
            return Response({
                'success': True,
                'audit_session_id': str(workflow_result.audit_session.id),
                'extracted_data_id': str(workflow_result.extracted_data.id) if workflow_result.extracted_data else None,
                'invoice_id': str(workflow_result.invoice.id) if workflow_result.invoice else None,
                'risk_score': workflow_result.extracted_data.risk_score if workflow_result.extracted_data else None,
                'risk_level': workflow_result.extracted_data.risk_level if workflow_result.extracted_data else None,
            })

            # Get full URL for the image
            image_url = request.build_absolute_uri(document.storage_url)
            
            # Process with AI
            result = ai_service.process_document_with_vision(
                image_url=image_url,
                document_type=document.document_type
            )
            
            if not result.get('success'):
                document.status = 'failed'
                document.save()
                return Response({
                    'success': False,
                    'error': result.get('error', 'Processing failed')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Save extracted data
            structured_data = result.get('structured_data', {})
            extracted_text = result.get('extracted_text', {})
            
            extracted_data = ExtractedData.objects.create(
                document=document,
                organization=document.organization,
                vendor_name=structured_data.get('vendorName'),
                customer_name=structured_data.get('customerName'),
                invoice_number=structured_data.get('invoiceNumber'),
                invoice_date=structured_data.get('invoiceDate'),
                due_date=structured_data.get('dueDate'),
                total_amount=Decimal(str(structured_data.get('totalAmount', 0))) if structured_data.get('totalAmount') else None,
                tax_amount=Decimal(str(structured_data.get('taxAmount', 0))) if structured_data.get('taxAmount') else None,
                currency=structured_data.get('currency'),
                items_json=structured_data.get('items'),
                raw_text_ar=extracted_text.get('arabic'),
                raw_text_en=extracted_text.get('english'),
                confidence=result.get('confidence', 0)
            )
            
            # Update document
            document.status = 'completed'
            document.language = result.get('language', 'en')
            document.is_handwritten = result.get('is_handwritten', False)
            document.processed_at = timezone.now()
            document.save()
            
            return Response({
                'success': True,
                'extracted_data_id': str(extracted_data.id),
                'confidence': result.get('confidence'),
                'language': result.get('language'),
                'is_handwritten': result.get('is_handwritten')
            })
            
        except Exception as e:
            document.status = 'failed'
            document.save()
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def re_audit(self, request, pk=None):
        """Re-run the audit workflow using saved invoice/vendor/customer data."""
        document = self.get_object()

        try:
            workflow_result = invoice_audit_workflow_service.rerun_saved_audit(
                document=document,
                actor=request.user,
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'status': workflow_result.audit_session.status,
            'audit_session_id': str(workflow_result.audit_session.id),
            'document_id': str(document.id),
            'invoice_id': str(workflow_result.invoice.id) if workflow_result.invoice else None,
            'vendor_id': str(workflow_result.invoice.vendor_id) if workflow_result.invoice else None,
            'customer_name': workflow_result.invoice.customer_name if workflow_result.invoice else None,
            'customer_tax_id': workflow_result.invoice.customer_vat_number if workflow_result.invoice else None,
            'risk_score': workflow_result.extracted_data.risk_score if workflow_result.extracted_data else None,
            'risk_level': workflow_result.extracted_data.risk_level if workflow_result.extracted_data else None,
            'findings_count': workflow_result.extracted_data.audit_findings.count() if workflow_result.extracted_data else 0,
        })


class ExtractedDataViewSet(OrganizationScopedModelViewSet):
    queryset = ExtractedData.objects.all()
    serializer_class = ExtractedDataSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=True, methods=['get'])
    def review(self, request, pk=None):
        """
        Phase 2 & 3: Review extracted invoice data with compliance and risk assessment
        
        Returns:
        - Original document image
        - Extracted JSON
        - Normalized fields
        - Validation errors/warnings
        - Audit findings
        - Compliance checks (Phase 3)
        - Risk score and level (Phase 3)
        - Audit summary (Phase 3)
        - Audit trail (Phase 3)
        """
        extracted = self.get_object()
        document = extracted.document
        
        try:
            # Get document image URL
            image_url = request.build_absolute_uri(document.storage_url) if document.storage_url else None
            
            # Get audit findings
            audit_findings = extracted.audit_findings.all()
            
            # Get audit trail
            audit_trail = extracted.audit_trails.all()
            
            review_data = {
                'id': str(extracted.id),
                'document': {
                    'id': str(document.id),
                    'file_name': document.file_name,
                    'image_url': image_url,
                    'uploaded_at': document.uploaded_at.isoformat() if document.uploaded_at else None,
                },
                'extracted_invoice': {
                    'invoice_number': extracted.invoice_number,
                    'vendor_name': extracted.vendor_name,
                    'customer_name': extracted.customer_name,
                    'invoice_date': extracted.invoice_date.isoformat() if extracted.invoice_date else None,
                    'due_date': extracted.due_date.isoformat() if extracted.due_date else None,
                    'total_amount': float(extracted.total_amount) if extracted.total_amount else None,
                    'currency': extracted.currency,
                    'items': extracted.items_json,
                    'confidence': extracted.confidence,
                },
                'normalized_invoice': extracted.normalized_json,
                'validation': {
                    'is_valid': extracted.is_valid,
                    'completed_at': extracted.validation_completed_at.isoformat() if extracted.validation_completed_at else None,
                    'errors': extracted.validation_errors or [],
                    'warnings': extracted.validation_warnings or [],
                },
                'audit_findings': [
                    {
                        'id': str(f.id),
                        'finding_type': f.finding_type,
                        'severity': f.severity,
                        'description': f.description,
                        'field': f.field,
                        'expected_value': f.expected_value,
                        'actual_value': f.actual_value,
                        'is_resolved': f.is_resolved,
                    }
                    for f in audit_findings
                ],
                # Phase 3: Compliance and Risk Assessment
                'compliance': {
                    'checks': extracted.compliance_checks or [],
                    'risk_score': extracted.risk_score or 0,
                    'risk_level': extracted.risk_level or 'Low',
                    'completed_at': extracted.audit_completed_at.isoformat() if extracted.audit_completed_at else None,
                },
                'audit_summary': extracted.audit_summary or {},
                'audit_trail': [
                    {
                        'id': str(t.id),
                        'event_type': t.event_type,
                        'title': t.title,
                        'description': t.description,
                        'severity': t.severity,
                        'event_time': t.event_time.isoformat() if t.event_time else None,
                        'success': t.success,
                        'phase': t.phase,
                    }
                    for t in audit_trail
                ],
                'status': extracted.validation_status,
                'extraction_status': extracted.extraction_status,
                'extracted_at': extracted.extracted_at.isoformat() if extracted.extracted_at else None,
            }
            
            return Response(review_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in review endpoint: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """
        Accept the extracted invoice data
        
        Request body:
        {
            'note': 'optional acceptance note'
        }
        """
        extracted = self.get_object()
        
        note = request.data.get('note', '')
        
        extracted.validation_status = 'validated'
        extracted.validated_by = request.user
        extracted.validated_at = timezone.now()
        extracted.save()
        
        logger.info(
            f"User {request.user.id} accepted invoice {extracted.id}. Note: {note}"
        )
        
        serializer = self.get_serializer(extracted)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Reject the extracted invoice data
        
        Request body:
        {
            'reason': 'reason for rejection'
        }
        """
        extracted = self.get_object()
        
        reason = request.data.get('reason', 'No reason provided')
        
        extracted.validation_status = 'rejected'
        extracted.validated_by = request.user
        extracted.validated_at = timezone.now()
        extracted.save()
        
        logger.warning(
            f"User {request.user.id} rejected invoice {extracted.id}. Reason: {reason}"
        )
        
        serializer = self.get_serializer(extracted)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def correct(self, request, pk=None):
        """
        Correct extracted invoice data
        
        Request body:
        {
            'corrections': {
                'invoice_number': 'new value',
                'vendor_name': 'new value',
                'total_amount': 'new value',
                ...
            },
            'note': 'reason for correction'
        }
        """
        extracted = self.get_object()
        
        corrections = request.data.get('corrections', {})
        note = request.data.get('note', '')
        
        if not corrections:
            return Response(
                {'error': 'No corrections provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Update fields
            if 'invoice_number' in corrections:
                extracted.invoice_number = corrections['invoice_number']
            
            if 'vendor_name' in corrections:
                extracted.vendor_name = corrections['vendor_name']
            
            if 'customer_name' in corrections:
                extracted.customer_name = corrections['customer_name']
            
            if 'total_amount' in corrections:
                try:
                    extracted.total_amount = Decimal(str(corrections['total_amount']))
                except (ValueError, TypeError):
                    return Response(
                        {'error': f"Invalid total_amount: {corrections['total_amount']}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            if 'currency' in corrections:
                extracted.currency = corrections['currency']
            
            # Mark as corrected
            extracted.validation_status = 'corrected'
            extracted.validated_by = request.user
            extracted.validated_at = timezone.now()
            extracted.save()
            
            logger.info(
                f"User {request.user.id} corrected invoice {extracted.id}. "
                f"Corrections: {corrections}. Note: {note}"
            )
            
            serializer = self.get_serializer(extracted)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error correcting invoice: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def validate_data(self, request, pk=None):
        """Validate extracted data"""
        extracted = self.get_object()
        validation_status = request.data.get('status', 'validated')
        
        extracted.validation_status = validation_status
        extracted.validated_by = request.user
        extracted.validated_at = timezone.now()
        extracted.save()
        
        serializer = self.get_serializer(extracted)
        return Response(serializer.data)



class AccountViewSet(OrganizationScopedModelViewSet):
    """Chart of Accounts management"""
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get accounts grouped by type"""
        organization_id = request.query_params.get('organization_id')
        queryset = self.get_queryset()
        
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        
        grouped = {}
        for account in queryset:
            if account.account_type not in grouped:
                grouped[account.account_type] = []
            grouped[account.account_type].append(AccountSerializer(account).data)
        
        return Response(grouped)
    
    @action(detail=False, methods=['get'])
    def trial_balance(self, request):
        """Generate trial balance"""
        organization_id = request.query_params.get('organization_id')
        queryset = self.get_queryset()
        
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        
        total_debit = Decimal('0')
        total_credit = Decimal('0')
        accounts_data = []
        
        for account in queryset:
            balance = account.current_balance
            if account.account_type in ['asset', 'expense']:
                debit = balance
                credit = Decimal('0')
                total_debit += balance
            else:
                debit = Decimal('0')
                credit = balance
                total_credit += balance
            
            accounts_data.append({
                'account_code': account.account_code,
                'account_name': account.account_name,
                'debit': float(debit),
                'credit': float(credit),
            })
        
        return Response({
            'accounts': accounts_data,
            'total_debit': float(total_debit),
            'total_credit': float(total_credit),
            'is_balanced': abs(total_debit - total_credit) < Decimal('0.01'),
        })


class TransactionViewSet(OrganizationScopedModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    actor_save_field = 'created_by'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(transaction_date__range=[start_date, end_date])
        
        # Filter by type
        transaction_type = self.request.query_params.get('type')
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
        
        # Filter anomalies
        anomalies_only = self.request.query_params.get('anomalies_only')
        if anomalies_only == 'true':
            queryset = queryset.filter(is_anomaly=True)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def reconcile(self, request, pk=None):
        """Mark transaction as reconciled"""
        transaction = self.get_object()
        transaction.is_reconciled = True
        transaction.reconciled_at = timezone.now()
        transaction.save()
        
        serializer = self.get_serializer(transaction)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get transaction summary statistics"""
        organization_id = request.query_params.get('organization_id')
        queryset = self.get_queryset()
        
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        
        income = queryset.filter(transaction_type='income').aggregate(
            total=Sum('amount'), count=Count('id')
        )
        expenses = queryset.filter(transaction_type='expense').aggregate(
            total=Sum('amount'), count=Count('id')
        )
        anomalies = queryset.filter(is_anomaly=True).count()
        unreconciled = queryset.filter(is_reconciled=False).count()
        
        return Response({
            'total_income': float(income['total'] or 0),
            'income_count': income['count'],
            'total_expenses': float(expenses['total'] or 0),
            'expenses_count': expenses['count'],
            'net_income': float((income['total'] or 0) - (expenses['total'] or 0)),
            'anomaly_count': anomalies,
            'unreconciled_count': unreconciled,
        })


class JournalEntryViewSet(OrganizationScopedModelViewSet):
    """Journal entry management for double-entry bookkeeping"""
    queryset = JournalEntry.objects.all()
    serializer_class = JournalEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    actor_save_field = 'created_by'
    
    @action(detail=True, methods=['post'])
    def post_entry(self, request, pk=None):
        """Post a draft journal entry"""
        entry = self.get_object()
        
        if entry.status != 'draft':
            return Response(
                {'error': 'Only draft entries can be posted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify balance
        if not entry.is_balanced:
            return Response(
                {'error': 'Entry is not balanced'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        entry.status = 'posted'
        entry.posted_by = request.user
        entry.posted_at = timezone.now()
        entry.save()
        
        # Update account balances
        for line in entry.lines.all():
            account = line.account
            if account.account_type in ['asset', 'expense']:
                account.current_balance += line.debit_amount - line.credit_amount
            else:
                account.current_balance += line.credit_amount - line.debit_amount
            account.save()
        
        serializer = self.get_serializer(entry)
        return Response(serializer.data)


class ComplianceCheckViewSet(OrganizationScopedModelViewSet):
    """Compliance checking and scoring"""
    queryset = ComplianceCheck.objects.all()
    serializer_class = ComplianceCheckSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status
        check_status = self.request.query_params.get('status')
        if check_status:
            queryset = queryset.filter(status=check_status)
        
        # Filter by type
        check_type = self.request.query_params.get('check_type')
        if check_type:
            queryset = queryset.filter(check_type=check_type)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Mark compliance check as resolved"""
        check = self.get_object()
        
        check.is_resolved = True
        check.resolved_by = request.user
        check.resolved_at = timezone.now()
        check.resolution_notes = request.data.get('notes', '')
        check.save()
        
        serializer = self.get_serializer(check)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def score_summary(self, request):
        """Get compliance score summary"""
        organization_id = request.query_params.get('organization_id')
        queryset = self.get_queryset()
        
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        
        total_checks = queryset.count()
        passed = queryset.filter(status='passed').count()
        failed = queryset.filter(status='failed').count()
        warnings = queryset.filter(status='warning').count()
        
        avg_score = queryset.aggregate(avg=Sum('compliance_score'))['avg'] or 0
        if total_checks > 0:
            avg_score = avg_score / total_checks
        
        return Response({
            'total_checks': total_checks,
            'passed': passed,
            'failed': failed,
            'warnings': warnings,
            'average_score': round(avg_score, 2),
            'pass_rate': round(passed / total_checks * 100, 2) if total_checks > 0 else 0,
        })


class AuditFlagViewSet(OrganizationScopedModelViewSet):
    """Audit flags for transaction review"""
    queryset = AuditFlag.objects.all()
    serializer_class = AuditFlagSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by resolution status
        include_resolved = self.request.query_params.get('include_resolved', 'false').lower() == 'true'
        if not include_resolved:
            queryset = queryset.filter(is_resolved=False)
        
        # Filter by priority
        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        # Filter by flag type
        flag_type = self.request.query_params.get('flag_type')
        if flag_type:
            queryset = queryset.filter(flag_type=flag_type)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve audit flag"""
        flag = self.get_object()
        
        flag.is_resolved = True
        flag.resolution_action = request.data.get('action', 'reviewed')
        flag.resolved_by = request.user
        flag.resolved_at = timezone.now()
        flag.resolution_notes = request.data.get('notes', '')
        flag.save()
        
        serializer = self.get_serializer(flag)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get audit flags dashboard summary"""
        organization_id = request.query_params.get('organization_id')
        queryset = self.get_queryset()
        
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        
        by_priority = {
            'critical': queryset.filter(priority='critical', is_resolved=False).count(),
            'high': queryset.filter(priority='high', is_resolved=False).count(),
            'medium': queryset.filter(priority='medium', is_resolved=False).count(),
            'low': queryset.filter(priority='low', is_resolved=False).count(),
        }
        
        by_type = queryset.filter(is_resolved=False).values('flag_type').annotate(count=Count('id'))
        
        return Response({
            'total_unresolved': queryset.filter(is_resolved=False).count(),
            'total_resolved': queryset.filter(is_resolved=True).count(),
            'by_priority': by_priority,
            'by_type': list(by_type),
        })


# Audit Report Views
class InvoiceAuditReportViewSet(OrganizationScopedReadOnlyModelViewSet):
    """
    API ViewSet for Audit Reports
    
    Provides endpoints to retrieve and view comprehensive invoice audit reports.
    """
    queryset = InvoiceAuditReport.objects.all()
    serializer_class = None  # We'll use custom serialization
    permission_classes = [permissions.IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        """List all audit reports with summary information"""
        queryset = self.get_queryset()
        
        # Filtering
        status = request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        risk_level = request.query_params.get('risk_level')
        if risk_level:
            queryset = queryset.filter(risk_level=risk_level)
        
        recommendation = request.query_params.get('recommendation')
        if recommendation:
            queryset = queryset.filter(recommendation=recommendation)
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        start = (page - 1) * page_size
        end = start + page_size
        
        reports = queryset.order_by('-generated_at')[start:end]
        
        data = []
        for report in reports:
            data.append({
                'id': str(report.id),
                'report_number': report.report_number,
                'invoice_number': report.extracted_invoice_number,
                'vendor': report.extracted_vendor_name,
                'amount': str(report.total_amount),
                'currency': report.currency,
                'risk_level': report.risk_level,
                'risk_score': report.risk_score,
                'recommendation': report.recommendation,
                'status': report.status,
                'generated_at': report.generated_at.isoformat(),
                'duplicate_score': report.duplicate_score,
                'anomaly_score': report.anomaly_score,
            })
        
        return Response({
            'count': queryset.count(),
            'page': page,
            'page_size': page_size,
            'results': data
        })
    
    def retrieve(self, request, pk=None):
        """Retrieve complete audit report"""
        try:
            report = self.get_queryset().get(id=pk)
        except InvoiceAuditReport.DoesNotExist:
            return Response(
                {'error': 'Report not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Return full report or JSON
        if request.query_params.get('format') == 'json':
            return Response(report.full_report_json or {})
        
        # Return formatted report data
        data = {
            # Report metadata
            'id': str(report.id),
            'report_number': report.report_number,
            'status': report.status,
            'generated_at': report.generated_at.isoformat(),
            'generated_by': report.generated_by.email if report.generated_by else 'System',
            
            # Document info
            'document': {
                'id': str(report.document.id),
                'file_name': report.document.file_name,
                'upload_date': report.upload_date.isoformat() if report.upload_date else None,
                'ocr_engine': report.ocr_engine,
                'ocr_confidence': report.ocr_confidence_score,
                'processing_status': report.processing_status,
            },
            
            # Invoice data
            'invoice_data': {
                'invoice_number': report.extracted_invoice_number,
                'issue_date': report.extracted_issue_date.isoformat() if report.extracted_issue_date else None,
                'due_date': report.extracted_due_date.isoformat() if report.extracted_due_date else None,
                'vendor': {
                    'name': report.extracted_vendor_name,
                    'address': report.extracted_vendor_address,
                    'tin': report.extracted_vendor_tin,
                },
                'customer': {
                    'name': report.extracted_customer_name,
                    'address': report.extracted_customer_address,
                    'tin': report.extracted_customer_tin,
                },
            },
            
            # Line items
            'line_items': report.line_items_json or [],
            
            # Totals
            'totals': {
                'subtotal': str(report.subtotal_amount) if report.subtotal_amount else None,
                'vat': str(report.vat_amount) if report.vat_amount else None,
                'total': str(report.total_amount) if report.total_amount else None,
                'currency': report.currency,
            },
            
            # Validation
            'validation_results': report.validation_results_json or {},
            
            # Duplicate detection
            'duplicate_detection': {
                'score': report.duplicate_score,
                'status': report.duplicate_status,
                'matched_documents': report.duplicate_matched_documents_json or [],
            },
            
            # Anomaly detection
            'anomaly_detection': {
                'score': report.anomaly_score,
                'status': report.anomaly_status,
                'explanation': report.anomaly_explanation,
                'reasons': report.anomaly_reasons_json or [],
            },
            
            # Risk assessment
            'risk_assessment': {
                'score': report.risk_score,
                'level': report.risk_level,
                'factors': report.risk_factors_json or [],
            },
            
            # AI Analysis
            'ai_analysis': {
                'summary': report.ai_summary,
                'findings': report.ai_findings,
                'review_required': report.ai_review_required,
            },
            
            # Recommendation
            'recommendation': {
                'action': report.recommendation,
                'reason': report.recommendation_reason,
            },
            
            # Audit trail
            'audit_trail': report.audit_trail_json or [],
        }
        
        return Response(data)
    
    @action(detail=True, methods=['get'])
    def export_pdf(self, request, pk=None):
        """Export audit report as PDF (placeholder)"""
        try:
            report = self.get_queryset().get(id=pk)
            return Response({
                'message': 'PDF export functionality coming soon',
                'report_number': report.report_number
            })
        except InvoiceAuditReport.DoesNotExist:
            return Response(
                {'error': 'Report not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get audit report statistics"""
        queryset = self.get_queryset()
        
        stats = {
            'total_reports': queryset.count(),
            'by_status': dict(queryset.values('status').annotate(count=Count('id')).values_list('status', 'count')),
            'by_risk_level': dict(queryset.values('risk_level').annotate(count=Count('id')).values_list('risk_level', 'count')),
            'by_recommendation': dict(queryset.values('recommendation').annotate(count=Count('id')).values_list('recommendation', 'count')),
            'average_risk_score': queryset.aggregate(avg=Sum('risk_score') / Count('id') if queryset.count() > 0 else 0)['avg'] or 0,
            'approved_count': queryset.filter(recommendation='approve').count(),
            'rejected_count': queryset.filter(recommendation='reject').count(),
            'pending_review_count': queryset.filter(recommendation='manual_review').count(),
        }
        
        return Response(stats)
