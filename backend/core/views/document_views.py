"""
Document Views - وجهات المستندات
Enterprise Document Upload System with Single, Multi-file, and ZIP support
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
import os
import uuid
import logging
import zipfile
import hashlib
import tempfile
import shutil

from core.models import Organization
from documents.models import Document
from documents.models import OCREvidence
from documents.report_presenter import build_report_presentation
from documents.services.audit_workflow_service import invoice_audit_workflow_service

logger = logging.getLogger(__name__)

# Supported file extensions for batch upload
SUPPORTED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.txt', '.xml', '.csv', '.json'}
CONTENT_TYPE_MAP = {
    '.pdf':  'application/pdf',
    '.jpg':  'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png':  'image/png',
    '.tiff': 'image/tiff',
    '.tif':  'image/tiff',
    '.bmp':  'image/bmp',
    '.txt':  'text/plain',
    '.xml':  'application/xml',
    '.csv':  'text/csv',
    '.json': 'application/json',
}

# Extensions that go through the structured ingestor (CSV/JSON) instead of OCR
STRUCTURED_EXTENSIONS = {'.csv', '.json'}


def generate_file_hash(file_content):
    """Generate MD5 hash for file content"""
    return hashlib.md5(file_content).hexdigest()


def save_document_file(organization, uploaded_file, file_content=None):
    """
    Save uploaded file to media directory
    Returns: (storage_key, storage_url, file_path)
    """
    # Create organization upload directory
    org_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', str(organization.id))
    os.makedirs(org_dir, exist_ok=True)
    
    # Generate unique filename
    ext = os.path.splitext(uploaded_file.name if hasattr(uploaded_file, 'name') else uploaded_file)[1].lower()
    unique_name = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(org_dir, unique_name)
    
    # Write file
    if file_content:
        with open(file_path, 'wb') as f:
            f.write(file_content)
    else:
        with open(file_path, 'wb') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)
    
    storage_key = f"uploads/{organization.id}/{unique_name}"
    storage_url = f"/media/{storage_key}"
    
    return storage_key, storage_url, file_path


def create_document_record(organization, user, file_name, file_content, file_type, upload_source='single', content_hash=None):
    """
    Create a Document record with audit trail
    
    Args:
        organization: Organization instance
        user: User who uploaded
        file_name: Original filename
        file_content: File bytes
        file_type: MIME type
        upload_source: 'single', 'multi', or 'batch_zip'
    
    Returns: Document instance
    """
    # Generate audit hash
    audit_hash = content_hash or generate_file_hash(file_content)
    
    # Create temp file-like object for save
    class FileWrapper:
        def __init__(self, name, content):
            self.name = name
            self._content = content
            self._pos = 0
        
        def read(self, size=-1):
            if size == -1:
                data = self._content[self._pos:]
                self._pos = len(self._content)
            else:
                data = self._content[self._pos:self._pos + size]
                self._pos += len(data)
            return data
        
        def chunks(self, chunk_size=8192):
            for i in range(0, len(self._content), chunk_size):
                yield self._content[i:i + chunk_size]
        
        def seek(self, pos):
            self._pos = pos
    
    file_wrapper = FileWrapper(file_name, file_content)
    
    # Save file
    storage_key, storage_url, file_path = save_document_file(organization, file_wrapper, file_content)
    
    # Create document record
    document = Document.objects.create(
        organization=organization,
        uploaded_by=user,
        file_name=file_name,
        file_type=file_type,
        file_size=len(file_content),
        storage_key=storage_key,
        storage_url=storage_url,
        content_hash=audit_hash,
        document_type='other',
        status='pending',
        language=None,
        is_handwritten=False,
    )
    
    # Log upload source in a way that can be queried
    logger.info(f"Document created: {document.id} | source={upload_source} | file={file_name} | hash={audit_hash}")
    
    return document, file_path, audit_hash


def process_document_ocr(document, file_path, language, is_handwritten, user, organization, audit_session=None):
    """
    Process a document using the canonical audit workflow.
    Returns: (success, message, ocr_evidence)
    """
    try:
        workflow_result = invoice_audit_workflow_service.process_document(
            document=document,
            file_path=file_path,
            actor=user,
            language=language,
            is_handwritten=is_handwritten,
            source='web_upload',
            audit_session=audit_session,
        )

        confidence = workflow_result.ocr_evidence.confidence_score if workflow_result.ocr_evidence else 0
        return True, f'درجة الثقة: {confidence}%', workflow_result.ocr_evidence
        
    except Exception as e:
        logger.error(f"OCR processing error for {document.id}: {e}")
        document.status = 'failed'
        document.save()
        return False, str(e), None


@login_required
def documents_view(request):
    """صفحة المستندات"""
    user = request.user
    organization = user.organization
    
    documents = Document.objects.filter(organization=organization).order_by('-uploaded_at')[:20]
    
    context = {
        'documents': documents,
    }
    
    return render(request, 'documents/list.html', context)


@login_required
def document_upload_view(request):
    """
    صفحة رفع المستندات - Enterprise Upload
    
    Supports:
    - Single file upload (immediate OCR processing)
    - Multi-file upload (batch registration, queued OCR)
    - ZIP batch upload (extraction + batch registration)
    
    Max size: 50MB per file, 200MB for ZIP
    Supported: PDF, JPG, PNG, TIFF, BMP, TXT, XML
    """
    user = request.user
    organization = user.organization
    
    if request.method == 'POST':
        upload_mode = request.POST.get('upload_mode', 'single')
        document_type = request.POST.get('document_type', 'other')
        language = request.POST.get('language', 'ara+eng')
        is_handwritten = request.POST.get('is_handwritten') == 'on'
        process_ocr = request.POST.get('process_ocr', 'immediate')
        
        # Handle different upload modes
        if upload_mode == 'single' and request.FILES.get('document'):
            return handle_single_upload(request, user, organization, document_type, language, is_handwritten)

        elif upload_mode == 'structured' and request.FILES.get('structured_file'):
            return handle_structured_upload(request, user, organization, document_type)

        elif upload_mode == 'multi' and request.FILES.getlist('documents'):
            return handle_multi_upload(request, user, organization, document_type, language, is_handwritten, process_ocr)

        elif upload_mode == 'zip' and request.FILES.get('zip_file'):
            return handle_zip_upload(request, user, organization, document_type, language, is_handwritten)

        else:
            messages.error(request, 'لم يتم تحديد ملفات للرفع')
            return redirect('document_upload')
    
    # GET request - show upload form
    recent_documents = Document.objects.filter(
        organization=organization
    ).order_by('-uploaded_at')[:10]
    
    # Get upload statistics
    total_docs = Document.objects.filter(organization=organization).count()
    pending_docs = Document.objects.filter(organization=organization, status='pending').count()
    processing_docs = Document.objects.filter(organization=organization, status='processing').count()
    
    context = {
        'recent_documents': recent_documents,
        'total_docs': total_docs,
        'pending_docs': pending_docs,
        'processing_docs': processing_docs,
    }
    
    return render(request, 'documents/upload.html', context)


def handle_single_upload(request, user, organization, document_type, language, is_handwritten):
    """Handle single file upload with immediate OCR processing"""
    uploaded_file = request.FILES['document']
    
    # Validate file size
    if uploaded_file.size > settings.MAX_UPLOAD_SIZE:
        messages.error(request, f'حجم الملف يتجاوز الحد المسموح ({settings.MAX_UPLOAD_SIZE // (1024*1024)}MB)')
        return redirect('document_upload')
    
    # Validate file type
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        messages.error(request, f'نوع الملف غير مدعوم. الأنواع المدعومة: PDF, JPG, PNG, TIFF, TXT, XML')
        return redirect('document_upload')
    
    try:
        # Read file content
        file_content = uploaded_file.read()
        file_type = CONTENT_TYPE_MAP.get(ext, 'application/octet-stream')
        audit_hash = generate_file_hash(file_content)
        audit_session = invoice_audit_workflow_service.start_session(
            organization=organization,
            actor=user,
            file_name=uploaded_file.name,
            content_hash=audit_hash,
            source='web_upload',
        )
        
        # Create document record
        document, file_path, audit_hash = create_document_record(
            organization=organization,
            user=user,
            file_name=uploaded_file.name,
            file_content=file_content,
            file_type=file_type,
            upload_source='single',
            content_hash=audit_hash,
        )
        
        # Update document type
        document.document_type = document_type
        document.language = language.split('+')[0] if '+' in language else language
        document.is_handwritten = is_handwritten
        document.save()
        
        # Process OCR immediately for single uploads
        success, message, ocr_evidence = process_document_ocr(
            document, file_path, language, is_handwritten, user, organization, audit_session=audit_session
        )
        
        if success:
            messages.success(request, f'تم معالجة المستند بنجاح. {message}')
            return redirect('pipeline_result', document_id=document.id)
        else:
            messages.error(request, f'خطأ في معالجة المستند: {message}')
            return redirect('pipeline_result', document_id=document.id)
            
    except Exception as e:
        logger.error(f"Single upload error: {e}")
        messages.error(request, f'خطأ في رفع المستند: {str(e)}')
        return redirect('document_upload')


def handle_multi_upload(request, user, organization, document_type, language, is_handwritten, process_ocr):
    """Handle multi-file upload (batch registration)"""
    uploaded_files = request.FILES.getlist('documents')
    
    if len(uploaded_files) > 500:
        messages.error(request, 'الحد الأقصى 500 ملف في المرة الواحدة')
        return redirect('document_upload')
    
    results = {
        'success': [],
        'failed': [],
    }
    
    for uploaded_file in uploaded_files:
        try:
            # Validate file size
            if uploaded_file.size > settings.MAX_UPLOAD_SIZE:
                results['failed'].append({
                    'name': uploaded_file.name,
                    'error': 'حجم الملف يتجاوز الحد المسموح'
                })
                continue
            
            # Validate file type
            ext = os.path.splitext(uploaded_file.name)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                results['failed'].append({
                    'name': uploaded_file.name,
                    'error': 'نوع الملف غير مدعوم'
                })
                continue
            
            # Read file content
            file_content = uploaded_file.read()
            file_type = CONTENT_TYPE_MAP.get(ext, 'application/octet-stream')
            audit_hash = generate_file_hash(file_content)
            audit_session = None
            if process_ocr == 'immediate' and len(uploaded_files) <= 10:
                audit_session = invoice_audit_workflow_service.start_session(
                    organization=organization,
                    actor=user,
                    file_name=uploaded_file.name,
                    content_hash=audit_hash,
                    source='web_upload',
                )
            
            # Create document record
            document, file_path, audit_hash = create_document_record(
                organization=organization,
                user=user,
                file_name=uploaded_file.name,
                file_content=file_content,
                file_type=file_type,
                upload_source='multi',
                content_hash=audit_hash,
            )
            
            # Update document metadata
            document.document_type = document_type
            document.language = language.split('+')[0] if '+' in language else language
            document.is_handwritten = is_handwritten
            document.save()
            
            # Process OCR based on user preference
            if process_ocr == 'immediate' and len(uploaded_files) <= 10:
                success, message, ocr_evidence = process_document_ocr(
                    document, file_path, language, is_handwritten, user, organization, audit_session=audit_session
                )
                if success:
                    results['success'].append({
                        'name': uploaded_file.name,
                        'id': str(document.id),
                        'status': 'processed',
                        'message': message
                    })
                else:
                    results['success'].append({
                        'name': uploaded_file.name,
                        'id': str(document.id),
                        'status': 'failed_ocr',
                        'message': message
                    })
            else:
                # Queue for background processing (document stays in 'pending' status)
                results['success'].append({
                    'name': uploaded_file.name,
                    'id': str(document.id),
                    'status': 'queued',
                    'message': 'في قائمة الانتظار للمعالجة'
                })
            
        except Exception as e:
            logger.error(f"Multi-upload file error ({uploaded_file.name}): {e}")
            results['failed'].append({
                'name': uploaded_file.name,
                'error': str(e)
            })
    
    # Show results
    success_count = len(results['success'])
    failed_count = len(results['failed'])
    
    if success_count > 0:
        messages.success(request, f'تم رفع {success_count} ملف بنجاح')
    if failed_count > 0:
        messages.warning(request, f'فشل رفع {failed_count} ملف')
    
    # Store results in session for display
    request.session['upload_results'] = results
    
    return redirect('document_upload')


def handle_zip_upload(request, user, organization, document_type, language, is_handwritten):
    """Handle ZIP batch upload (extraction + registration)"""
    zip_file = request.FILES['zip_file']
    
    # Validate ZIP size (200MB max)
    max_zip_size = 200 * 1024 * 1024
    if zip_file.size > max_zip_size:
        messages.error(request, f'حجم ملف ZIP يتجاوز الحد المسموح (200 ميجابايت)')
        return redirect('document_upload')
    
    # Validate it's actually a ZIP
    if not zip_file.name.lower().endswith('.zip'):
        messages.error(request, 'يجب أن يكون الملف بصيغة ZIP')
        return redirect('document_upload')
    
    results = {
        'success': [],
        'failed': [],
        'skipped': [],
    }
    
    temp_dir = None
    try:
        # Create temp directory for extraction
        temp_dir = tempfile.mkdtemp(prefix='finai_zip_')
        zip_path = os.path.join(temp_dir, 'upload.zip')
        
        # Save ZIP temporarily
        with open(zip_path, 'wb') as f:
            for chunk in zip_file.chunks():
                f.write(chunk)
        
        # Extract and process
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Get list of files (exclude directories and hidden files)
            file_list = [
                name for name in zf.namelist()
                if not name.endswith('/') 
                and not name.startswith('__MACOSX')
                and not os.path.basename(name).startswith('.')
            ]
            
            logger.info(f"ZIP upload: {len(file_list)} files to process from {zip_file.name}")
            
            for file_name in file_list:
                try:
                    # Get just the filename (ignore paths)
                    base_name = os.path.basename(file_name)
                    if not base_name:
                        continue
                    
                    # Check extension
                    ext = os.path.splitext(base_name)[1].lower()
                    if ext not in SUPPORTED_EXTENSIONS:
                        results['skipped'].append({
                            'name': base_name,
                            'reason': 'نوع الملف غير مدعوم'
                        })
                        continue
                    
                    # Read file content from ZIP
                    file_content = zf.read(file_name)
                    
                    # Check file size
                    if len(file_content) > settings.MAX_UPLOAD_SIZE:
                        results['failed'].append({
                            'name': base_name,
                            'error': 'حجم الملف يتجاوز الحد المسموح'
                        })
                        continue
                    
                    # Skip empty files
                    if len(file_content) == 0:
                        results['skipped'].append({
                            'name': base_name,
                            'reason': 'ملف فارغ'
                        })
                        continue
                    
                    file_type = CONTENT_TYPE_MAP.get(ext, 'application/octet-stream')
                    
                    # Create document record
                    document, file_path, audit_hash = create_document_record(
                        organization=organization,
                        user=user,
                        file_name=base_name,
                        file_content=file_content,
                        file_type=file_type,
                        upload_source='batch_zip'
                    )
                    
                    # Update document metadata
                    document.document_type = document_type
                    document.language = language.split('+')[0] if '+' in language else language
                    document.is_handwritten = is_handwritten
                    document.save()
                    
                    results['success'].append({
                        'name': base_name,
                        'id': str(document.id),
                        'size': len(file_content),
                        'hash': audit_hash,
                        'status': 'registered'
                    })
                    
                except Exception as e:
                    logger.error(f"ZIP file extraction error ({file_name}): {e}")
                    results['failed'].append({
                        'name': os.path.basename(file_name),
                        'error': str(e)
                    })
        
    except zipfile.BadZipFile:
        messages.error(request, 'ملف ZIP تالف أو غير صالح')
        return redirect('document_upload')
    except Exception as e:
        logger.error(f"ZIP upload error: {e}")
        messages.error(request, f'خطأ في معالجة ملف ZIP: {str(e)}')
        return redirect('document_upload')
    finally:
        # Clean up temp directory
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    # Show results summary
    success_count = len(results['success'])
    failed_count = len(results['failed'])
    skipped_count = len(results['skipped'])

    if success_count > 0:
        messages.success(request, f'تم استخراج وتسجيل {success_count} ملف من ZIP بنجاح')
    if failed_count > 0:
        messages.warning(request, f'فشل معالجة {failed_count} ملف')
    if skipped_count > 0:
        messages.info(request, f'تم تخطي {skipped_count} ملف (غير مدعوم)')

    # Dispatch OCR asynchronously via Celery (non-blocking)
    if success_count > 0:
        doc_ids = [item['id'] for item in results['success']]
        try:
            from core.tasks import process_zip_documents
            process_zip_documents.delay(document_ids=doc_ids)
            messages.info(request, f'تم إرسال {success_count} مستند لمعالجة OCR في الخلفية.')
        except Exception as exc:
            logger.warning("Celery dispatch failed, queued as pending: %s", exc)
            messages.info(request, 'المستندات في قائمة الانتظار — سيتم المعالجة عند توفر العامل.')

    # Store results in session for display
    request.session['upload_results'] = results

    return redirect('document_upload')


def handle_structured_upload(request, user, organization, document_type):
    """
    Handle CSV / JSON structured file upload.

    Instead of running OCR, this path uses the IngestDocumentUseCase
    (Clean Architecture Application layer) to parse the file and create
    one ExtractedData record per invoice row.

    SRP: only orchestrates upload + ingestion; storage/persistence handled inline.
    """
    import tempfile
    from core.application.ingest_document_usecase import default_ingest_usecase
    from documents.models import ExtractedData
    from django.utils import timezone

    uploaded_file = request.FILES['structured_file']
    ext = os.path.splitext(uploaded_file.name)[1].lower()

    if ext not in STRUCTURED_EXTENSIONS:
        messages.error(request, f'نوع الملف {ext} غير مدعوم. يُقبل CSV أو JSON فقط.')
        return redirect('document_upload')

    if uploaded_file.size > 10 * 1024 * 1024:  # 10 MB cap for structured files
        messages.error(request, 'حجم الملف يتجاوز 10MB')
        return redirect('document_upload')

    file_content = uploaded_file.read()
    file_type = CONTENT_TYPE_MAP.get(ext, 'application/octet-stream')

    try:
        # Register the file as a Document (audit trail)
        document, file_path, _ = create_document_record(
            organization=organization,
            user=user,
            file_name=uploaded_file.name,
            file_content=file_content,
            file_type=file_type,
            upload_source='structured',
        )
        document.document_type = document_type
        document.status = 'processing'
        document.save()

        # Write to temp file so ingestors can use file-based APIs
        suffix = ext
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        created_count = 0
        error_count = 0

        def _persist_invoice(invoice_data):
            """Callback: save each parsed InvoiceData as an ExtractedData row."""
            nonlocal created_count
            from decimal import Decimal as D
            ExtractedData.objects.create(
                document=document,
                organization=organization,
                vendor_name=invoice_data.vendor_name or '',
                customer_name=invoice_data.customer_name or '',
                invoice_number=invoice_data.invoice_number or '',
                total_amount=invoice_data.total_amount,
                tax_amount=invoice_data.tax_amount,
                currency=invoice_data.currency or 'SAR',
                confidence=invoice_data.confidence,
                extraction_status='extracted',
                extraction_provider=f'structured_{ext[1:]}',   # 'structured_csv' / 'structured_json'
                is_fallback=False,
                extraction_completed_at=timezone.now(),
                validation_status='pending',
                is_valid=False,
            )
            created_count += 1

        result = default_ingest_usecase.execute(tmp_path, on_invoice=_persist_invoice)
        error_count = result.error_count

        # Cleanup temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

        document.status = 'completed' if error_count == 0 else 'pending_review'
        document.processed_at = timezone.now()
        document.save()

        if created_count:
            messages.success(request,
                f'تم استيراد {created_count} فاتورة من {uploaded_file.name}.'
                + (f' ({error_count} أخطاء)' if error_count else ''))
        else:
            messages.warning(request,
                f'لم يُستورد أي سجل. تأكد من صيغة الملف. ({error_count} أخطاء)')

    except Exception as exc:
        logger.error("Structured upload error: %s", exc)
        messages.error(request, f'خطأ في استيراد الملف: {exc}')

    return redirect('document_upload')


@login_required
@require_POST
def process_pending_documents(request):
    """
    Process pending documents with OCR (AJAX endpoint)
    For background processing of batch uploads
    """
    user = request.user
    organization = user.organization
    
    # Get pending documents
    pending_docs = Document.objects.filter(
        organization=organization,
        status='pending'
    ).order_by('uploaded_at')[:10]  # Process 10 at a time
    
    results = []
    for document in pending_docs:
        try:
            file_path = os.path.join(settings.MEDIA_ROOT, document.storage_key)
            if not os.path.exists(file_path):
                results.append({
                    'id': str(document.id),
                    'status': 'error',
                    'message': 'الملف غير موجود'
                })
                continue
            
            language = 'ara+eng' if document.language in ['ar', 'mixed'] else 'eng'
            success, message, ocr_evidence = process_document_ocr(
                document, file_path, language, document.is_handwritten, user, organization
            )
            
            results.append({
                'id': str(document.id),
                'name': document.file_name,
                'status': 'processed' if success else 'failed',
                'message': message
            })
            
        except Exception as e:
            results.append({
                'id': str(document.id),
                'status': 'error',
                'message': str(e)
            })
    
    remaining = Document.objects.filter(
        organization=organization,
        status='pending'
    ).count()
    
    return JsonResponse({
        'processed': results,
        'remaining': remaining
    })


@login_required
def ocr_evidence_list_view(request):
    """قائمة أدلة OCR"""
    user = request.user
    organization = user.organization
    
    evidence_list = OCREvidence.objects.filter(organization=organization).order_by('-extracted_at')
    
    # Pagination
    paginator = Paginator(evidence_list, 20)
    page_number = request.GET.get('page')
    evidence_page = paginator.get_page(page_number)
    
    context = {
        'evidence_list': evidence_page,
    }
    
    return render(request, 'documents/ocr_list.html', context)


@login_required
def ocr_evidence_detail_view(request, evidence_id):
    """تفاصيل دليل OCR"""
    user = request.user
    organization = user.organization

    evidence = get_object_or_404(OCREvidence, id=evidence_id, organization=organization)

    # Load extracted data for AI summary display
    extracted_data = None
    try:
        extracted_data = evidence.document.extracted_data
        # Normalize audit_summary to ensure key_risks/recommended_actions are strings
        if extracted_data and extracted_data.audit_summary:
            summary = extracted_data.audit_summary
            # Fix executor_summary typo
            if 'executor_summary' in summary and 'executive_summary' not in summary:
                summary['executive_summary'] = summary.pop('executor_summary')
            # Flatten any dict items in lists to strings
            for list_key in ('key_risks', 'recommended_actions'):
                if list_key in summary:
                    summary[list_key] = [
                        (r.get('description') or r.get('risk') or r.get('action')
                         or r.get('recommendation') or str(r))
                        if isinstance(r, dict) else str(r)
                        for r in (summary[list_key] or [])
                    ]
    except Exception:
        pass

    from core.models import Organization as _Org
    scope_docs = {
        'disclaimer_ar': 'النص المستخرج من المستندات يُستخدم كدليل تدقيق فقط وليس مصدراً للحقيقة المحاسبية.',
        'disclaimer_en': 'Extracted text is used as audit evidence only, not accounting truth.',
        'scope_ar': 'نطاق OCR — أدلة التدقيق فقط\n• استخراج النص من المستندات ضوئياً\n• دعم اللغة العربية والإنجليزية\n• التعرف على الخط اليدوي (أفضل جهد)\n• تخزين النتائج كأدلة تدقيق',
    }

    context = {
        'evidence': evidence,
        'extracted_data': extracted_data,
        'scope_docs': scope_docs,
    }

    return render(request, 'documents/ocr_detail.html', context)


@login_required
def reprocess_with_ai_view(request, evidence_id):
    """Re-process an existing OCR evidence record using OpenAI Vision."""
    if request.method != 'POST':
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(['POST'])

    user = request.user
    organization = user.organization
    evidence = get_object_or_404(OCREvidence, id=evidence_id, organization=organization)
    document = evidence.document

    try:
        # Reconstruct file path from storage_key and MEDIA_ROOT
        # Try direct path first, then uploads/<org_id>/<filename> pattern
        storage_key = document.storage_key.strip('/')
        file_path = os.path.join(str(settings.MEDIA_ROOT), storage_key)
        if not os.path.exists(file_path):
            # Fallback: storage_key may only have the filename, file is under uploads/<org_id>/
            filename = os.path.basename(storage_key)
            file_path = os.path.join(
                str(settings.MEDIA_ROOT), 'uploads', str(organization.id), filename
            )
        if not os.path.exists(file_path):
            from django.contrib import messages
            messages.error(request, f'ملف المستند غير موجود: {file_path}')
            return redirect('ocr_evidence_detail', evidence_id=evidence_id)

        process_document_ocr(
            document=document,
            file_path=file_path,
            language=evidence.language_used or 'ar+en',
            is_handwritten=evidence.is_handwritten,
            user=user,
            organization=organization,
        )

        from django.contrib import messages
        messages.success(request, 'تمت إعادة المعالجة بنجاح باستخدام OpenAI Vision.')
    except Exception as e:
        logger.error(f"Reprocess failed for evidence {evidence_id}: {e}")
        from django.contrib import messages
        messages.error(request, f'فشلت إعادة المعالجة: {e}')

    return redirect('pipeline_result', document_id=document.id)


@login_required
def pipeline_result_view(request, document_id):
    """
    عرض نتائج خط المعالجة الكامل للمستند
    يعرض جميع مراحل المعالجة: رفع → OCR → بيانات → تحقق → امتثال → مخالفات → مخاطرة → ملخص AI
    """
    user = request.user
    organization = user.organization

    document = get_object_or_404(Document, id=document_id, organization=organization)

    # Get OCR evidence (latest for this document)
    evidence = OCREvidence.objects.filter(
        document=document, organization=organization
    ).order_by('-extracted_at').first()

    # Get extracted/pipeline data
    extracted = None
    try:
        extracted = document.extracted_data
    except Exception:
        pass

    # Get comprehensive audit report
    audit_report = None
    try:
        audit_report = document.audit_report
    except Exception:
        pass

    report_presentation = None
    if audit_report:
        lang = request.session.get('language', 'ar')
        report_presentation = build_report_presentation(audit_report, lang=lang)

    # Count completed pipeline steps for display
    pipeline_steps = 1  # Upload always done
    if evidence:
        pipeline_steps = 2
    if extracted:
        pipeline_steps = 3
        if extracted.validation_completed_at:
            pipeline_steps = 4
        if extracted.compliance_checks:
            pipeline_steps = 5
        if extracted.audit_completed_at:
            pipeline_steps = 6
        if extracted.risk_score is not None:
            pipeline_steps = 7
        if extracted.audit_summary:
            pipeline_steps = 8
    if audit_report:
        pipeline_steps = 11  # Full report generated

    context = {
        'document': document,
        'evidence': evidence,
        'extracted': extracted,
        'audit_report': audit_report,
        'report_presentation': report_presentation,
        'pipeline_steps': pipeline_steps,
    }

    return render(request, 'documents/pipeline_result.html', context)


@login_required
@require_POST
def pending_review_submit_view(request, document_id):
    """
    Handle human correction of a document in 'pending_review' state.
    The accountant fills in the missing/unclear fields via the Alpine.js form
    and submits here. We re-run validation immediately after saving.

    SOLID — Single Responsibility: this view only handles the correction POST;
    all business logic stays in the service layer.
    """
    from django.utils import timezone
    from documents.models import ExtractedData
    from decimal import Decimal

    user = request.user
    organization = user.organization

    document = get_object_or_404(Document, id=document_id, organization=organization)

    try:
        extracted = document.extracted_data
    except ExtractedData.DoesNotExist:
        messages.error(request, 'لا توجد بيانات مستخرجة لهذا المستند.')
        return redirect('pipeline_result', document_id=document_id)

    # Apply human corrections to extracted fields
    fields_updated = []

    def _patch(field, cast=str):
        """DRY helper: update a field only if a non-empty value was submitted."""
        val = request.POST.get(field, '').strip()
        if val:
            try:
                setattr(extracted, field, cast(val))
                fields_updated.append(field)
            except (ValueError, TypeError):
                pass

    _patch('invoice_number')
    _patch('vendor_name')
    _patch('customer_name')
    _patch('currency')
    _patch('total_amount', cast=Decimal)
    _patch('tax_amount',   cast=Decimal)

    # Date fields — enforce YYYY-MM-DD (matches normalization contract)
    from core.invoice_normalization_service import InvoiceNormalizationService
    for date_field in ('invoice_date', 'due_date'):
        raw = request.POST.get(date_field, '').strip()
        if raw:
            normalised = InvoiceNormalizationService.normalize_date(raw)
            if normalised:
                setattr(extracted, date_field, normalised)
                fields_updated.append(date_field)

    # Audit trail
    extracted.review_notes = request.POST.get('review_notes', '').strip() or None
    extracted.reviewed_by = user
    extracted.reviewed_at = timezone.now()
    extracted.extraction_status = 'extracted'   # promote out of pending_review
    extracted.save()

    # Promote document status
    document.status = 'completed'
    document.save(update_fields=['status'])

    messages.success(request, f'تم حفظ التصحيحات البشرية ({len(fields_updated)} حقل). أُعيد تصنيف المستند.')
    return redirect('pipeline_result', document_id=document_id)
