from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.storage import default_storage
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.core.files.utils import validate_file_name
import logging

from .models import (
    Document, ExtractedData, Transaction, Account,
    JournalEntry, JournalEntryLine, ComplianceCheck, AuditFlag
)
from .serializers import (
    DocumentSerializer, ExtractedDataSerializer, TransactionSerializer,
    AccountSerializer, JournalEntrySerializer, JournalEntryLineSerializer,
    ComplianceCheckSerializer, AuditFlagSerializer
)
from core.ai import OCRProcessor, StructuredExtractor
from core.ai.errors import FileProcessingError, AIAPIError
from decimal import Decimal
import uuid
import os

logger = logging.getLogger(__name__)


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Document.objects.all()
        elif user.organization:
            return Document.objects.filter(organization=user.organization)
        return Document.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)
    
    @action(detail=False, methods=['post'])
    def upload(self, request):
        """Upload document with file handling"""
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        organization_id = request.data.get('organization_id')
        document_type = request.data.get('document_type', 'other')
        
        # Save file
        file_name = file.name
        doc_id = str(uuid.uuid4())
        storage_key = f"documents/{organization_id}/{doc_id}/{file_name}"
        storage_path = default_storage.save(storage_key, file)
        storage_url = default_storage.url(storage_path)
        
        # Create document record
        document = Document.objects.create(
            id=doc_id,
            organization_id=organization_id,
            uploaded_by=request.user,
            file_name=file_name,
            file_type=file.content_type,
            file_size=file.size,
            storage_key=storage_key,
            storage_url=storage_url,
            document_type=document_type,
            status='pending'
        )
        
        serializer = self.get_serializer(document)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def batch_upload(self, request):
        """Batch upload multiple documents"""
        files = request.FILES.getlist('files')
        if not files:
            return Response({'error': 'No files provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        organization_id = request.data.get('organization_id')
        document_type = request.data.get('document_type', 'other')
        
        uploaded_docs = []
        for file in files:
            file_name = file.name
            doc_id = str(uuid.uuid4())
            storage_key = f"documents/{organization_id}/{doc_id}/{file_name}"
            storage_path = default_storage.save(storage_key, file)
            storage_url = default_storage.url(storage_path)
            
            document = Document.objects.create(
                id=doc_id,
                organization_id=organization_id,
                uploaded_by=request.user,
                file_name=file_name,
                file_type=file.content_type,
                file_size=file.size,
                storage_key=storage_key,
                storage_url=storage_url,
                document_type=document_type,
                status='pending'
            )
            uploaded_docs.append(document)
        
        serializer = self.get_serializer(uploaded_docs, many=True)
        return Response({
            'count': len(uploaded_docs),
            'documents': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """
        Process document with AI OCR and extraction.
        
        Security:
        - Reads file from disk (no URL-based fetching, prevents SSRF)
        - Validates organization ownership
        - Returns proper error codes (400/403/413/429/500)
        
        Returns:
        - extracted_data_id: ID of ExtractedData for access
        - ocr_confidence: Confidence of OCR (0-1)
        - extraction_confidence: Confidence of data extraction (0-1)
        - language: Detected language (ar/en)
        - method: OCR method used (vision/tesseract)
        - processing_time_ms: Time taken
        """
        document = self.get_object()
        
        # Security: Validate organization ownership
        user_org = getattr(request.user, 'organization', None)
        if not user_org and request.user.role != 'admin':
            logger.warning(f"Unauthorized document access attempt: user={request.user.id}, doc={pk}")
            return Response(
                {'error': 'You do not have access to this document'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not request.user.is_staff and document.organization_id != user_org.id:
            logger.warning(f"Organization mismatch: user_org={user_org.id}, doc_org={document.organization_id}")
            return Response(
                {'error': 'You do not have access to this document'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if already processing or completed
        if document.status in ['processing', 'completed']:
            return Response({
                'error': 'Document already processed or processing',
                'current_status': document.status
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Security: Construct full file path from disk (not from URL)
        file_path = os.path.join(settings.MEDIA_ROOT, document.storage_key)
        
        # Security: Validate file path is within MEDIA_ROOT (prevent directory traversal)
        try:
            file_path = os.path.abspath(file_path)
            if not file_path.startswith(os.path.abspath(settings.MEDIA_ROOT)):
                logger.error(f"Path traversal attempt: {file_path}")
                return Response(
                    {'error': 'Invalid file path'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            logger.error(f"Path validation error: {e}")
            return Response(
                {'error': 'Invalid file path'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check file exists
        if not os.path.isfile(file_path):
            logger.error(f"Document file not found: {file_path}")
            document.status = 'failed'
            document.save(update_fields=['status'])
            return Response(
                {'error': 'Document file not found on disk'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Update status
        document.status = 'processing'
        document.save(update_fields=['status'])
        
        try:
            # Phase 1: OCR (Extract text)
            logger.info(f"Starting OCR for document {document.id}: {file_path}")
            ocr_processor = OCRProcessor()
            
            try:
                ocr_result = ocr_processor.process(
                    file_path=file_path,
                    language_hint='ar'  # Default to Arabic
                )
            except FileProcessingError as e:
                logger.error(f"File validation failed: {e.message}")
                document.status = 'failed'
                document.save(update_fields=['status'])
                return Response(
                    {'error': e.message},
                    status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE  # For file size errors
                )
            except AIAPIError as e:
                logger.error(f"OCR API error: {e.message}")
                document.status = 'failed'
                document.save(update_fields=['status'])
                return Response(
                    {'error': 'OCR processing failed. Please try again.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            except Exception as e:
                logger.error(f"Unexpected OCR error: {e}")
                document.status = 'failed'
                document.save(update_fields=['status'])
                return Response(
                    {'error': 'OCR processing failed'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            extracted_text = ocr_result.get('extracted_text', '')
            if not extracted_text or len(extracted_text.strip()) < 10:
                logger.warning(f"OCR extracted very little text: {len(extracted_text)} chars")
                document.status = 'completed'
                document.language = ocr_result.get('language', 'ar')
                document.processed_at = timezone.now()
                document.save()
                
                return Response({
                    'warning': 'Document OCR succeeded but extracted text is very short',
                    'extracted_text_length': len(extracted_text),
                    'ocr_confidence': ocr_result.get('confidence', 0),
                    'language': ocr_result.get('language'),
                    'method': ocr_result.get('method'),
                })
            
            # Phase 2: Structured Data Extraction (Parse invoice details)
            logger.info(f"Starting extraction for document {document.id}")
            extractor = StructuredExtractor()
            
            try:
                extraction_result = extractor.extract_invoice_data(
                    ocr_text=extracted_text,
                    language=ocr_result.get('language', 'ar')
                )
            except AIAPIError as e:
                logger.error(f"Extraction API error: {e.message}")
                # Fall back to creating ExtractedData with OCR text only
                extraction_result = {
                    'extracted_data': {},
                    'confidence': 0.3,
                    'warnings': ['Could not extract structured data'],
                }
            except Exception as e:
                logger.error(f"Extraction error: {e}")
                extraction_result = {
                    'extracted_data': {},
                    'confidence': 0.3,
                    'warnings': ['Extraction processing failed'],
                }
            
            # Phase 3: Save Results
            extracted_invoice = extraction_result.get('extracted_data', {})
            
            extracted_data = ExtractedData.objects.create(
                document=document,
                organization=document.organization,
                # Extracted fields
                vendor_name=extracted_invoice.get('vendor_name'),
                customer_name=extracted_invoice.get('customer_name'),
                invoice_number=extracted_invoice.get('invoice_number'),
                invoice_date=extracted_invoice.get('invoice_date'),
                due_date=extracted_invoice.get('due_date'),
                # Amounts
                total_amount=Decimal(str(extracted_invoice.get('total', 0))) if extracted_invoice.get('total') else None,
                tax_amount=Decimal(str(extracted_invoice.get('tax_amount', 0))) if extracted_invoice.get('tax_amount') else None,
                currency=extracted_invoice.get('currency'),
                # Items
                items_json=extracted_invoice.get('line_items'),
                # OCR text
                raw_text_ar=extracted_text if ocr_result.get('language') in ['ar', 'mixed'] else None,
                raw_text_en=extracted_text if ocr_result.get('language') in ['en', 'mixed'] else None,
                # Confidence scores
                confidence=round(extraction_result.get('confidence', 0.5), 2),
            )
            
            # Update document
            document.status = 'completed'
            document.language = ocr_result.get('language', 'ar')
            document.is_handwritten = False  # Vision API doesn't detect this
            document.processed_at = timezone.now()
            document.save()
            
            logger.info(f"Document {document.id} processed successfully. "
                       f"Extraction confidence: {extraction_result.get('confidence')}")
            
            return Response({
                'success': True,
                'extracted_data_id': str(extracted_data.id),
                'ocr_confidence': ocr_result.get('confidence', 0),
                'extraction_confidence': extraction_result.get('confidence', 0),
                'language': ocr_result.get('language', 'ar'),
                'method': ocr_result.get('method', 'vision'),
                'processing_time_ms': ocr_result.get('processing_time_ms', 0),
                'warnings': extraction_result.get('warnings', []),
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Unexpected error processing document {document.id}: {e}", exc_info=True)
            document.status = 'failed'
            document.save(update_fields=['status'])
            return Response(
                {'error': 'Internal server error during processing'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ExtractedDataViewSet(viewsets.ModelViewSet):
    queryset = ExtractedData.objects.all()
    serializer_class = ExtractedDataSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return ExtractedData.objects.all()
        elif user.organization:
            return ExtractedData.objects.filter(organization=user.organization)
        return ExtractedData.objects.none()
    
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


class AccountViewSet(viewsets.ModelViewSet):
    """Chart of Accounts management"""
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Account.objects.all()
        elif user.organization:
            return Account.objects.filter(organization=user.organization)
        return Account.objects.none()
    
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


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = Transaction.objects.all() if user.role == 'admin' else Transaction.objects.filter(organization=user.organization)
        
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
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
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


class JournalEntryViewSet(viewsets.ModelViewSet):
    """Journal entry management for double-entry bookkeeping"""
    queryset = JournalEntry.objects.all()
    serializer_class = JournalEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return JournalEntry.objects.all()
        elif user.organization:
            return JournalEntry.objects.filter(organization=user.organization)
        return JournalEntry.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
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


class ComplianceCheckViewSet(viewsets.ModelViewSet):
    """Compliance checking and scoring"""
    queryset = ComplianceCheck.objects.all()
    serializer_class = ComplianceCheckSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = ComplianceCheck.objects.all() if user.role == 'admin' else ComplianceCheck.objects.filter(organization=user.organization)
        
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


class AuditFlagViewSet(viewsets.ModelViewSet):
    """Audit flags for transaction review"""
    queryset = AuditFlag.objects.all()
    serializer_class = AuditFlagSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = AuditFlag.objects.all() if user.role == 'admin' else AuditFlag.objects.filter(organization=user.organization)
        
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
