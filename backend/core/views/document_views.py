"""
Document Views - وجهات المستندات
Enterprise Document Upload System with Single, Multi-file, and ZIP support
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.conf import settings
from django.http import HttpResponse, JsonResponse
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
from core.views.base import build_shell_stats, get_interface_language
from documents.models import AuditTrail, Document, InvoiceAuditFinding, OCREvidence
from documents.report_presenter import build_report_presentation

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


def get_invoice_audit_pdf_service():
    from documents.services.invoice_audit_pdf_service import invoice_audit_pdf_service

    return invoice_audit_pdf_service


def get_invoice_audit_workflow_service():
    from documents.services.audit_workflow_service import invoice_audit_workflow_service

    return invoice_audit_workflow_service


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
        workflow_service = get_invoice_audit_workflow_service()
        workflow_result = workflow_service.process_document(
            document=document,
            file_path=file_path,
            actor=user,
            language=language,
            is_handwritten=is_handwritten,
            source='web_upload',
            audit_session=audit_session,
        )

        if workflow_result.document.status == 'pending_review':
            return True, 'تعذر الاستخراج الآلي محلياً، وتم حفظ المستند وتحويله إلى المراجعة اليدوية.', workflow_result.ocr_evidence

        confidence = workflow_result.ocr_evidence.confidence_score if workflow_result.ocr_evidence else 0
        return True, f'درجة الثقة: {confidence}%', workflow_result.ocr_evidence
        
    except Exception as e:
        logger.error(f"OCR processing error for {document.id}: {e}")
        document.status = 'failed'
        document.save()
        return False, str(e), None


def build_shell_context(organization):
    return {'stats': build_shell_stats(organization)}


def request_expects_json(request):
    accept = request.headers.get('Accept', '')
    return (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or 'application/json' in accept
    )


def _localized_value(ui_language, arabic_value, english_value):
    return arabic_value if ui_language == 'ar' else english_value


def _localize_checklist_title(title, ui_language):
    if ui_language != 'ar' or not title:
        return title
    labels = {
        'Invoice Number': 'رقم الفاتورة',
        'Vendor': 'بيانات المورد',
        'Customer': 'بيانات العميل',
        'Items': 'بنود الفاتورة',
        'Total Match': 'مطابقة الإجماليات',
        'Vat': 'فحص الضريبة',
        'Validation Error': 'خطأ تحقق',
        'Validation Warning': 'تنبيه تحقق',
    }
    return labels.get(str(title), title)


def _localize_checklist_message(message, ui_language):
    if ui_language != 'ar' or not message:
        return message
    text = str(message)
    replacements = {
        'Invoice number is missing': 'رقم الفاتورة مفقود',
        'Invoice number is unusually short': 'رقم الفاتورة قصير على نحو غير معتاد',
        'Vendor name is missing': 'اسم المورد مفقود',
        'Vendor TIN is missing': 'الرقم الضريبي للمورد مفقود',
        'Vendor TIN appears to be invalid format': 'صيغة الرقم الضريبي للمورد تبدو غير صحيحة',
        'Customer name is missing': 'اسم العميل مفقود',
        'Customer TIN is missing': 'الرقم الضريبي للعميل مفقود',
        'Customer TIN appears to be invalid format': 'صيغة الرقم الضريبي للعميل تبدو غير صحيحة',
        'No line items found on invoice': 'لم يتم العثور على بنود داخل الفاتورة',
        'Cannot verify totals without line items': 'لا يمكن التحقق من الإجماليات دون بنود الفاتورة',
        'VAT amount is missing or zero': 'مبلغ الضريبة مفقود أو يساوي صفراً',
        'No anomalies detected': 'لم يتم رصد شذوذات',
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = text.replace('Subtotal mismatch', 'عدم تطابق في الإجمالي قبل الضريبة')
    text = text.replace('Total mismatch', 'عدم تطابق في الإجمالي النهائي')
    text = text.replace('Calculated total', 'الإجمالي المحتسب')
    text = text.replace('does not match stated total', 'لا يطابق الإجمالي المدرج')
    return text


def _build_audit_checklist_rows(validation_rows, compliance_rows, duplicate_entry, anomaly_entry, ui_language):
    rows = []
    done_yes = _localized_value(ui_language, 'تم', 'Yes')
    done_no = _localized_value(ui_language, 'لا', 'No')

    for row in validation_rows:
        rows.append({
            'group': _localized_value(ui_language, 'التحقق', 'Validation'),
            'title': _localize_checklist_title(row.get('title'), ui_language),
            'done_label': done_yes if row.get('tone') == 'success' else done_no,
            'status_label': row.get('status_label'),
            'message': _localize_checklist_message(row.get('message'), ui_language),
            'tone': row.get('tone'),
        })

    for row in compliance_rows:
        rows.append({
            'group': _localized_value(ui_language, 'الامتثال', 'Compliance'),
            'title': _localize_checklist_title(row.get('title'), ui_language),
            'done_label': done_yes if row.get('tone') == 'success' else done_no,
            'status_label': row.get('status_label'),
            'message': _localize_checklist_message(row.get('message'), ui_language),
            'tone': row.get('tone'),
        })

    if duplicate_entry:
        rows.append({
            'group': _localized_value(ui_language, 'التكرار', 'Duplicate'),
            'title': _localized_value(ui_language, 'كشف التكرار', 'Duplicate detection'),
            'done_label': done_yes if duplicate_entry.get('tone') == 'success' else done_no,
            'status_label': duplicate_entry.get('status_label'),
            'message': duplicate_entry.get('message'),
            'tone': duplicate_entry.get('tone'),
        })

    if anomaly_entry:
        rows.append({
            'group': _localized_value(ui_language, 'الشذوذ', 'Anomaly'),
            'title': _localized_value(ui_language, 'كشف الشذوذ', 'Anomaly detection'),
            'done_label': done_yes if anomaly_entry.get('tone') == 'success' else done_no,
            'status_label': anomaly_entry.get('status_label'),
            'message': anomaly_entry.get('message'),
            'tone': anomaly_entry.get('tone'),
        })

    return rows


@login_required
def documents_view(request):
    """صفحة المستندات"""
    user = request.user
    organization = user.organization
    
    documents = Document.objects.filter(organization=organization).order_by('-uploaded_at')[:20]
    
    context = {
        'documents': documents,
        **build_shell_context(organization),
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
    
    if request.GET.get('clear_results') == '1':
        request.session.pop('upload_results', None)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'cleared': True})
        return redirect('document_upload')

    # GET request - show upload form
    recent_documents = Document.objects.filter(
        organization=organization
    ).order_by('-uploaded_at')[:10]
    
    # Get upload statistics
    total_docs = Document.objects.filter(organization=organization).count()
    pending_docs = Document.objects.filter(organization=organization, status='pending').count()
    processing_docs = Document.objects.filter(organization=organization, status='processing').count()
    pending_review_docs = Document.objects.filter(organization=organization, status='pending_review').count()
    completed_docs = Document.objects.filter(
        organization=organization,
        status__in=['completed', 'validated'],
    ).count()
    upload_results = request.session.get('upload_results') or {}
    upload_results_summary = {
        'success_count': len(upload_results.get('success') or []),
        'failed_count': len(upload_results.get('failed') or []),
        'skipped_count': len(upload_results.get('skipped') or []),
    }
    upload_results_summary['total'] = (
        upload_results_summary['success_count']
        + upload_results_summary['failed_count']
        + upload_results_summary['skipped_count']
    )
    
    context = {
        'recent_documents': recent_documents,
        'total_docs': total_docs,
        'pending_docs': pending_docs,
        'processing_docs': processing_docs,
        'pending_review_docs': pending_review_docs,
        'completed_docs': completed_docs,
        'upload_results_summary': upload_results_summary,
        **build_shell_context(organization),
    }
    
    return render(request, 'documents/upload.html', context)


def handle_single_upload(request, user, organization, document_type, language, is_handwritten):
    """Handle single file upload with immediate OCR processing"""
    uploaded_file = request.FILES['document']
    expects_json = request_expects_json(request)
    
    # Validate file size
    if uploaded_file.size > settings.MAX_UPLOAD_SIZE:
        error_message = f'حجم الملف يتجاوز الحد المسموح ({settings.MAX_UPLOAD_SIZE // (1024*1024)}MB)'
        if expects_json:
            return JsonResponse({'success': False, 'message': error_message}, status=400)
        messages.error(request, error_message)
        return redirect('document_upload')
    
    # Validate file type
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        error_message = 'نوع الملف غير مدعوم. الأنواع المدعومة: PDF, JPG, PNG, TIFF, TXT, XML'
        if expects_json:
            return JsonResponse({'success': False, 'message': error_message}, status=400)
        messages.error(request, error_message)
        return redirect('document_upload')
    
    try:
        # Read file content
        file_content = uploaded_file.read()
        file_type = CONTENT_TYPE_MAP.get(ext, 'application/octet-stream')
        audit_hash = generate_file_hash(file_content)
        workflow_service = get_invoice_audit_workflow_service()
        audit_session = workflow_service.start_session(
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
            success_message = f'تم معالجة المستند بنجاح. {message}'
            if expects_json:
                return JsonResponse({
                    'success': True,
                    'message': success_message,
                    'document_id': str(document.id),
                    'document_name': document.file_name,
                    'status': document.status,
                    'redirect_url': reverse('pipeline_result', kwargs={'document_id': document.id}),
                    'manual_review_required': document.status == 'pending_review',
                })
            messages.success(request, success_message)
            return redirect('pipeline_result', document_id=document.id)
        else:
            error_message = f'خطأ في معالجة المستند: {message}'
            if expects_json:
                return JsonResponse({
                    'success': False,
                    'message': error_message,
                    'document_id': str(document.id),
                    'document_name': document.file_name,
                    'status': document.status,
                    'redirect_url': reverse('pipeline_result', kwargs={'document_id': document.id}),
                }, status=422)
            messages.error(request, error_message)
            return redirect('pipeline_result', document_id=document.id)
            
    except Exception as e:
        logger.error(f"Single upload error: {e}")
        error_message = f'خطأ في رفع المستند: {str(e)}'
        if expects_json:
            return JsonResponse({'success': False, 'message': error_message}, status=500)
        messages.error(request, error_message)
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
                workflow_service = get_invoice_audit_workflow_service()
                audit_session = workflow_service.start_session(
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
        **build_shell_context(organization),
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
        **build_shell_context(organization),
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
    ui_language = get_interface_language(request)

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

    latest_session = document.audit_sessions.select_related('started_by').first()
    invoice_record = document.invoice_records.select_related('vendor').first()

    pipeline_steps = 1
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
        if extracted.risk_score:
            pipeline_steps = 7
        if extracted.audit_summary:
            pipeline_steps = 8
    if audit_report:
        pipeline_steps = 11

    def first_value(*values):
        for value in values:
            if value is not None and value != '':
                return value
        return None

    def normalize_engine_label(raw_value):
        if not raw_value:
            return 'OCR'
        value = str(raw_value).lower()
        if 'openai' in value:
            return 'OpenAI Vision'
        if 'tesseract' in value:
            return 'Tesseract OCR'
        if 'structured_csv' in value:
            return 'CSV Import'
        if 'structured_json' in value:
            return 'JSON Import'
        return str(raw_value).replace('_', ' ').title()

    def prettify_label(value):
        return str(value).replace('_', ' ').replace('-', ' ').title()

    def tone_for_status(status):
        value = str(status or '').lower()
        if value in {'pass', 'completed', 'approved', 'success', 'reused', 'published'}:
            return 'success'
        if value in {'warning', 'pending', 'manual_review', 'medium'}:
            return 'warning'
        if value in {'fail', 'failed', 'error', 'critical', 'reject', 'high'}:
            return 'danger'
        return 'neutral'

    def arabic_status_label(status):
        labels = {
            'pass': 'مطابق',
            'completed': 'مكتمل',
            'approved': 'معتمد',
            'success': 'ناجح',
            'reused': 'معاد الاستخدام',
            'published': 'منشور',
            'warning': 'تنبيه',
            'pending': 'قيد التنفيذ',
            'manual_review': 'مراجعة يدوية',
            'fail': 'فشل',
            'failed': 'فشل',
            'error': 'خطأ',
            'critical': 'حرج',
            'high': 'مرتفع',
            'medium': 'متوسط',
            'low': 'منخفض',
        }
        return labels.get(str(status or '').lower(), prettify_label(status or 'unknown'))

    def display_timestamp(value):
        if not value:
            return None
        if hasattr(value, 'strftime'):
            try:
                return timezone.localtime(value).strftime('%Y/%m/%d %H:%M')
            except Exception:
                return value.strftime('%Y/%m/%d %H:%M')
        return str(value)[:16]

    def summarize_stage_payload(payload):
        if not isinstance(payload, dict):
            return None
        details = []
        for key, label in (
            ('provider', 'المحرك'),
            ('confidence', 'الثقة'),
            ('invoice_number', 'الفاتورة'),
            ('errors_count', 'الأخطاء'),
            ('warnings_count', 'التحذيرات'),
            ('checks_run', 'فحوص الامتثال'),
            ('finding_count', 'المخالفات'),
        ):
            value = payload.get(key)
            if value not in (None, '', [], {}, False):
                if key == 'confidence':
                    details.append(f'{label}: {value}%')
                else:
                    details.append(f'{label}: {value}')
        return ' • '.join(details) if details else None

    def normalize_line_items(raw_items):
        normalized = []
        if not raw_items and invoice_record:
            raw_items = list(
                invoice_record.line_items.all().values(
                    'line_number',
                    'description',
                    'quantity',
                    'unit_price',
                    'line_total',
                )
            )
        if not isinstance(raw_items, list):
            return normalized
        for index, item in enumerate(raw_items, start=1):
            if not isinstance(item, dict):
                continue
            normalized.append({
                'line_number': item.get('line_number') or index,
                'description': first_value(
                    item.get('description'),
                    item.get('product'),
                    item.get('name'),
                    item.get('item'),
                    f'Line {index}',
                ),
                'quantity': first_value(item.get('quantity'), item.get('qty'), 1),
                'unit_price': first_value(item.get('unit_price'), item.get('price')),
                'discount': first_value(item.get('discount'), item.get('discount_amount')),
                'total': first_value(item.get('total'), item.get('line_total'), item.get('amount')),
            })
        return normalized

    def normalize_detail_rows(value):
        rows = []
        if isinstance(value, dict):
            for key, entry in value.items():
                if isinstance(entry, dict):
                    rows.append({
                        'title': entry.get('title') or prettify_label(key),
                        'status': entry.get('status') or entry.get('severity') or 'info',
                        'status_label': arabic_status_label(entry.get('status') or entry.get('severity') or 'info'),
                        'tone': tone_for_status(entry.get('status') or entry.get('severity')),
                        'message': entry.get('message') or entry.get('description') or entry.get('details') or entry.get('value'),
                    })
                else:
                    rows.append({
                        'title': prettify_label(key),
                        'status': 'info',
                        'status_label': arabic_status_label(entry),
                        'tone': tone_for_status(entry),
                        'message': str(entry),
                    })
        elif isinstance(value, list):
            for index, entry in enumerate(value, start=1):
                if isinstance(entry, dict):
                    status = entry.get('status') or entry.get('severity') or 'info'
                    rows.append({
                        'title': first_value(
                            entry.get('title'),
                            entry.get('rule_key'),
                            entry.get('procedure'),
                            entry.get('check'),
                            prettify_label(f'item_{index}'),
                        ),
                        'status': status,
                        'status_label': arabic_status_label(status),
                        'tone': tone_for_status(status),
                        'message': first_value(
                            entry.get('message'),
                            entry.get('description'),
                            entry.get('reason'),
                            entry.get('result'),
                        ),
                    })
                else:
                    rows.append({
                        'title': prettify_label(f'item_{index}'),
                        'status': 'info',
                        'status_label': 'معلومة',
                        'tone': 'neutral',
                        'message': str(entry),
                    })
        return rows

    def normalize_string_list(value):
        rows = []
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    rows.append(first_value(item.get('reason'), item.get('message'), item.get('title'), item.get('description')))
                elif item not in (None, ''):
                    rows.append(str(item))
        return [row for row in rows if row]

    risk_level = first_value(
        getattr(audit_report, 'risk_level', None),
        getattr(extracted, 'risk_level', None),
    )
    risk_labels = {
        'critical': 'حرجة',
        'high': 'عالية',
        'medium': 'متوسطة',
        'low': 'منخفضة',
    }
    recommendation = getattr(audit_report, 'recommendation', None)
    recommendation_labels = {
        'approve': 'يوصى بالموافقة',
        'reject': 'يوصى بالرفض',
        'manual_review': 'مراجعة يدوية',
    }
    duplicate_status_labels = {
        'confirmed_duplicate': 'تكرار مؤكد',
        'high_risk': 'خطر تكرار عال',
        'medium_risk': 'خطر تكرار متوسط',
        'low_risk': 'خطر تكرار منخفض',
        'no_duplicate': 'لا يوجد تكرار',
    }
    anomaly_status_labels = {
        'critical_anomaly': 'شذوذ حرج',
        'high_anomaly': 'شذوذ مرتفع',
        'medium_anomaly': 'شذوذ متوسط',
        'low_anomaly': 'شذوذ منخفض',
        'no_anomaly': 'لا يوجد شذوذ',
    }

    document_status_labels = {
        'pending': 'تم الرفع',
        'processing': 'قيد المعالجة',
        'completed': 'اكتمل الاستخراج',
        'validated': 'تم الاعتماد',
        'pending_review': 'تحتاج مراجعة',
        'failed': 'فشلت المعالجة',
    }
    extraction_status_labels = {
        'pending': 'بانتظار الاستخراج',
        'extracted': 'تم الاستخراج',
        'failed': 'فشل الاستخراج',
        'pending_review': 'استخراج غير مكتمل',
    }
    validation_status_labels = {
        'pending': 'بانتظار التحقق',
        'validated': 'تم التحقق',
        'rejected': 'مرفوض',
        'corrected': 'تم التصحيح',
    }
    review_state_labels = {
        'required': 'مراجعة بشرية مطلوبة',
        'reviewed': 'تمت المراجعة',
        'not_required': 'لا تحتاج مراجعة',
    }
    decision_labels = {
        'approve': 'جاهزة للاعتماد',
        'reject': 'موصى بالرفض',
        'manual_review': 'قيد المراجعة اليدوية',
        'pending': 'قيد التحليل',
    }

    def tone_for_invoice_state(state):
        if state in {'validated', 'completed', 'extracted', 'reviewed', 'not_required', 'approve'}:
            return 'success'
        if state in {'pending_review', 'manual_review', 'processing', 'pending', 'required'}:
            return 'warning'
        if state in {'failed', 'rejected', 'reject'}:
            return 'danger'
        return 'neutral'

    stage_label = 'تقرير تدقيق كامل'
    if not audit_report and extracted:
        stage_label = 'استخراج وتحليل أولي'
    elif not extracted and evidence:
        stage_label = 'نتيجة OCR'
    elif not evidence:
        stage_label = 'تم رفع المستند'

    document_status = getattr(document, 'status', None) or 'pending'
    extraction_status = (
        getattr(extracted, 'extraction_status', None)
        or ('extracted' if extracted else 'failed' if document_status == 'failed' else 'pending')
    )
    validation_status = (
        getattr(extracted, 'validation_status', None)
        or ('validated' if extracted and getattr(extracted, 'is_valid', False) else 'pending')
    )
    decision_state = recommendation or (
        'manual_review'
        if document_status == 'pending_review'
        else 'approve'
        if document_status in {'validated', 'completed'} and extracted
        else 'pending'
    )
    review_state = (
        'required'
        if document_status == 'pending_review'
        else 'reviewed'
        if getattr(extracted, 'reviewed_at', None)
        else 'not_required'
    )
    invoice_states = [
        {
            'key': 'document',
            'label': document_status_labels.get(document_status, 'حالة غير معروفة'),
            'tone': tone_for_invoice_state(document_status),
        },
        {
            'key': 'extraction',
            'label': extraction_status_labels.get(extraction_status, 'حالة استخراج غير معروفة'),
            'tone': tone_for_invoice_state(extraction_status),
        },
        {
            'key': 'validation',
            'label': validation_status_labels.get(validation_status, 'حالة تحقق غير معروفة'),
            'tone': tone_for_invoice_state(validation_status),
        },
        {
            'key': 'review',
            'label': review_state_labels.get(review_state, 'حالة مراجعة غير معروفة'),
            'tone': tone_for_invoice_state(review_state),
        },
        {
            'key': 'decision',
            'label': decision_labels.get(decision_state, 'قرار غير محسوم'),
            'tone': tone_for_invoice_state(decision_state),
        },
    ]

    result_card = {
        'invoice_number': first_value(
            getattr(audit_report, 'extracted_invoice_number', None),
            getattr(extracted, 'invoice_number', None),
        ),
        'vendor_name': first_value(
            getattr(audit_report, 'extracted_vendor_name', None),
            getattr(extracted, 'vendor_name', None),
            getattr(invoice_record.vendor, 'name', None) if invoice_record else None,
        ),
        'customer_name': first_value(
            getattr(audit_report, 'extracted_customer_name', None),
            getattr(extracted, 'customer_name', None),
            getattr(invoice_record, 'customer_name', None) if invoice_record else None,
            getattr(organization, 'name', None),
        ),
        'vendor_tax_id': first_value(
            getattr(audit_report, 'extracted_vendor_tin', None),
            getattr(extracted, 'vendor_tax_id', None),
        ),
        'customer_tax_id': first_value(
            getattr(audit_report, 'extracted_customer_tin', None),
            getattr(extracted, 'customer_tax_id', None),
        ),
        'vendor_address': first_value(
            getattr(audit_report, 'extracted_vendor_address', None),
        ),
        'issue_date': first_value(
            getattr(audit_report, 'extracted_issue_date', None),
            getattr(extracted, 'invoice_date', None),
            getattr(invoice_record, 'issue_date', None) if invoice_record else None,
        ),
        'due_date': first_value(
            getattr(audit_report, 'extracted_due_date', None),
            getattr(extracted, 'due_date', None),
            getattr(invoice_record, 'due_date', None) if invoice_record else None,
        ),
        'currency': first_value(
            getattr(audit_report, 'currency', None),
            getattr(extracted, 'currency', None),
            getattr(invoice_record, 'currency', None) if invoice_record else None,
            getattr(organization, 'currency', None),
            'SAR',
        ),
        'total_amount': first_value(
            getattr(audit_report, 'total_amount', None),
            getattr(extracted, 'total_amount', None),
            getattr(invoice_record, 'total_amount', None) if invoice_record else None,
        ),
        'subtotal_amount': first_value(
            getattr(audit_report, 'subtotal_amount', None),
            getattr(extracted, 'subtotal_amount', None),
            getattr(invoice_record, 'subtotal_amount', None) if invoice_record else None,
        ),
        'tax_amount': first_value(
            getattr(audit_report, 'vat_amount', None),
            getattr(extracted, 'tax_amount', None),
            getattr(invoice_record, 'vat_amount', None) if invoice_record else None,
        ),
        'confidence_score': first_value(
            getattr(audit_report, 'ocr_confidence_score', None),
            getattr(evidence, 'confidence_score', None),
            getattr(extracted, 'confidence', None),
        ),
        'ocr_engine': first_value(
            getattr(audit_report, 'ocr_engine', None),
            getattr(evidence, 'ocr_engine', None),
            getattr(extracted, 'extraction_provider', None),
            'OCR',
        ),
        'engine_label': normalize_engine_label(
            first_value(
                getattr(audit_report, 'ocr_engine', None),
                getattr(evidence, 'ocr_engine', None),
                getattr(extracted, 'extraction_provider', None),
                'OCR',
            )
        ),
        'risk_score': first_value(
            getattr(audit_report, 'risk_score', None),
            getattr(extracted, 'risk_score', None),
        ),
        'risk_level': risk_level,
        'risk_label': risk_labels.get(risk_level, 'غير مقيم'),
        'duplicate_score': getattr(audit_report, 'duplicate_score', None),
        'duplicate_status_label': duplicate_status_labels.get(
            getattr(audit_report, 'duplicate_status', None),
            'غير محدد',
        ),
        'anomaly_score': getattr(audit_report, 'anomaly_score', None),
        'anomaly_status_label': anomaly_status_labels.get(
            getattr(audit_report, 'anomaly_status', None),
            'غير محدد',
        ),
        'recommendation': recommendation,
        'recommendation_label': recommendation_labels.get(recommendation, 'لم تصدر توصية بعد'),
        'has_recommendation': bool(recommendation),
        'stage_label': stage_label,
        'report_number': getattr(audit_report, 'report_number', None),
        'document_status': document_status,
        'document_status_label': document_status_labels.get(document_status, 'حالة غير معروفة'),
        'extraction_status': extraction_status,
        'extraction_status_label': extraction_status_labels.get(extraction_status, 'حالة استخراج غير معروفة'),
        'validation_status': validation_status,
        'validation_status_label': validation_status_labels.get(validation_status, 'حالة تحقق غير معروفة'),
        'review_state': review_state,
        'review_state_label': review_state_labels.get(review_state, 'حالة مراجعة غير معروفة'),
        'decision_state': decision_state,
        'decision_label': decision_labels.get(decision_state, 'قرار غير محسوم'),
    }

    raw_line_items = first_value(
        getattr(audit_report, 'line_items_json', None),
        getattr(extracted, 'items_json', None),
    )
    line_items = normalize_line_items(raw_line_items)

    validation_rows = normalize_detail_rows(getattr(audit_report, 'validation_results_json', None))
    if not validation_rows and extracted:
        validation_rows.extend([
            {
                'title': 'Validation Error',
                'status': 'fail',
                'status_label': 'فشل',
                'tone': 'danger',
                'message': message,
            }
            for message in (extracted.validation_errors or [])
        ])
        validation_rows.extend([
            {
                'title': 'Validation Warning',
                'status': 'warning',
                'status_label': 'تنبيه',
                'tone': 'warning',
                'message': message,
            }
            for message in (extracted.validation_warnings or [])
        ])

    for row in validation_rows:
        row['title'] = _localize_checklist_title(row.get('title'), ui_language)
        row['message'] = _localize_checklist_message(row.get('message'), ui_language)

    compliance_rows = normalize_detail_rows(
        first_value(
            getattr(audit_report, 'compliance_checks_json', None),
            getattr(extracted, 'compliance_checks', None),
        )
    )
    for row in compliance_rows:
        row['title'] = _localize_checklist_title(row.get('title'), ui_language)
        row['message'] = _localize_checklist_message(row.get('message'), ui_language)
    duplicate_rows = normalize_detail_rows(getattr(audit_report, 'duplicate_matched_documents_json', None))
    anomaly_rows = normalize_string_list(
        first_value(
            getattr(audit_report, 'anomaly_reasons_json', None),
            getattr(extracted, 'anomaly_flags', None),
        )
    )
    risk_factors = normalize_string_list(
        first_value(
            getattr(audit_report, 'risk_factors_json', None),
            getattr(extracted, 'audit_summary', {}).get('key_risks') if getattr(extracted, 'audit_summary', None) else None,
        )
    )
    recommended_actions = normalize_string_list(
        (
            getattr(extracted, 'audit_summary', {}) or {}
        ).get('recommended_actions') if extracted else None
    )
    if ui_language == 'ar' and getattr(audit_report, 'recommendation_reason_ar', None):
        recommended_actions.insert(0, audit_report.recommendation_reason_ar)
    elif getattr(audit_report, 'recommendation_reason', None):
        recommended_actions.insert(0, audit_report.recommendation_reason)
    elif getattr(audit_report, 'recommendation_reason_ar', None):
        recommended_actions.insert(0, audit_report.recommendation_reason_ar)

    audit_findings = []
    if extracted:
        audit_findings = list(
            InvoiceAuditFinding.objects.filter(extracted_data=extracted).order_by('-created_at')[:6]
        )

    extracted_audit_summary = getattr(extracted, 'audit_summary', {}) or {}
    if ui_language == 'ar':
        executive_summary = first_value(
            getattr(audit_report, 'ai_summary_ar', None),
            extracted_audit_summary.get('executive_summary_ar'),
            extracted_audit_summary.get('executive_summary'),
            getattr(audit_report, 'ai_summary', None),
            extracted_audit_summary.get('executive_summary_en'),
        )
        findings_summary = first_value(
            getattr(audit_report, 'ai_findings_ar', None),
            extracted_audit_summary.get('ai_findings_ar'),
            getattr(audit_report, 'ai_findings', None),
            extracted_audit_summary.get('ai_findings_en'),
        )
    else:
        executive_summary = first_value(
            getattr(audit_report, 'ai_summary', None),
            extracted_audit_summary.get('executive_summary_en'),
            getattr(audit_report, 'ai_summary_ar', None),
            extracted_audit_summary.get('executive_summary'),
            extracted_audit_summary.get('executive_summary_ar'),
        )
        findings_summary = first_value(
            getattr(audit_report, 'ai_findings', None),
            extracted_audit_summary.get('ai_findings_en'),
            getattr(audit_report, 'ai_findings_ar', None),
            extracted_audit_summary.get('ai_findings_ar'),
        )

    duplicate_entry = {
        'status_label': result_card['duplicate_status_label'],
        'message': duplicate_rows[0]['message'] if duplicate_rows else _localized_value(ui_language, 'لم يتم العثور على تطابقات مؤكدة.', 'No confirmed duplicate matches were found.'),
        'tone': 'success' if result_card['duplicate_status_label'] in {'لا يوجد تكرار', 'No Duplicate Detected'} else 'warning',
    }
    anomaly_entry = {
        'status_label': result_card['anomaly_status_label'],
        'message': anomaly_rows[0] if anomaly_rows else _localized_value(ui_language, 'لم يتم رصد شذوذات مالية جوهرية.', 'No material anomalies were detected.'),
        'tone': 'success' if result_card['anomaly_status_label'] in {'لا يوجد شذوذ', 'No Anomaly Detected'} else 'warning',
    }
    audit_checklist_rows = _build_audit_checklist_rows(
        validation_rows,
        compliance_rows,
        duplicate_entry,
        anomaly_entry,
        ui_language,
    )

    stage_titles = {
        'upload_document': 'رفع المستند',
        'ocr_vision_ai': 'OCR / Vision AI',
        'structured_extraction': 'الاستخراج المنظم',
        'save_invoice_vendor_customer': 'حفظ الفاتورة والمورد والعميل',
        'audit_rules_engine': 'محرك قواعد التدقيق',
        'risk_engine_score': 'محرك المخاطر والدرجة',
        'findings_cross_document_intelligence': 'الملاحظات والذكاء بين المستندات',
        'ai_summary_recommendations': 'الملخص والتوصيات',
        'reviewer_decision': 'قرار المراجع',
        'dashboard_reports': 'اللوحة والتقارير',
        'upload_file': 'رفع الملف',
        'create_audit_session': 'فتح جلسة التدقيق',
        'save_document': 'حفظ المستند',
        'ai_extraction': 'الاستخراج الذكي',
        'normalization': 'توحيد البيانات',
        'validation': 'التحقق المحاسبي',
        'compliance_engine': 'فحص الامتثال',
        'risk_score': 'احتساب المخاطر',
        'findings': 'تجميع المخالفات',
        'ai_executive_summary': 'الملخص التنفيذي',
        'publish_to_dashboard': 'النشر إلى اللوحة',
    }
    processing_journey = []
    if latest_session:
        workflow_service = get_invoice_audit_workflow_service()
        for stage_key in workflow_service.get_stage_sequence_for_session(latest_session):
            payload = (latest_session.stages_json or {}).get(stage_key, {})
            status = payload.get('status', 'pending') if isinstance(payload, dict) else 'pending'
            processing_journey.append({
                'title': stage_titles.get(stage_key, prettify_label(stage_key)),
                'status': status,
                'status_label': arabic_status_label(status),
                'tone': tone_for_status(status),
                'details': summarize_stage_payload(payload),
                'timestamp_display': display_timestamp(payload.get('at') if isinstance(payload, dict) else None),
            })
    else:
        processing_journey = [
            {'title': 'رفع الملف', 'status': 'completed', 'status_label': 'مكتمل', 'tone': 'success', 'details': document.file_name, 'timestamp_display': display_timestamp(document.uploaded_at)},
            {'title': 'نتيجة OCR', 'status': 'completed' if evidence else 'pending', 'status_label': 'مكتمل' if evidence else 'قيد التنفيذ', 'tone': 'success' if evidence else 'warning', 'details': result_card['engine_label'] if evidence else None, 'timestamp_display': display_timestamp(getattr(evidence, 'extracted_at', None))},
            {'title': 'التحليل المالي', 'status': 'completed' if extracted else 'pending', 'status_label': 'مكتمل' if extracted else 'قيد التنفيذ', 'tone': 'success' if extracted else 'warning', 'details': result_card['recommendation_label'] if extracted else None, 'timestamp_display': display_timestamp(getattr(extracted, 'audit_completed_at', None) if extracted else None)},
        ]

    timeline_rows = []
    if audit_report and isinstance(audit_report.audit_trail_json, list):
        for entry in audit_report.audit_trail_json:
            if not isinstance(entry, dict):
                continue
            status = entry.get('status', 'success' if entry.get('success', True) else 'failed')
            timeline_rows.append({
                'title': first_value(entry.get('title'), entry.get('event'), 'Audit Event'),
                'description': first_value(entry.get('description'), entry.get('message')),
                'status_label': arabic_status_label(status),
                'tone': tone_for_status(status),
                'timestamp_display': display_timestamp(entry.get('timestamp')),
            })
    elif extracted:
        for trail in AuditTrail.objects.filter(extracted_data=extracted).order_by('event_time')[:12]:
            status = 'success' if trail.success else trail.severity
            timeline_rows.append({
                'title': trail.title,
                'description': trail.description or trail.result_summary,
                'status_label': arabic_status_label(status),
                'tone': tone_for_status(status),
                'timestamp_display': display_timestamp(trail.event_time),
            })
    else:
        timeline_rows = [
            {
                'title': 'تم إنشاء المستند',
                'description': document.file_name,
                'status_label': 'مكتمل',
                'tone': 'success',
                'timestamp_display': display_timestamp(document.uploaded_at),
            }
        ]

    context = {
        'document': document,
        'evidence': evidence,
        'extracted': extracted,
        'audit_report': audit_report,
        'report_presentation': report_presentation,
        'invoice_record': invoice_record,
        'latest_session': latest_session,
        'pipeline_steps': pipeline_steps,
        'result_card': result_card,
        'invoice_states': invoice_states,
        'line_items': line_items,
        'validation_rows': validation_rows,
        'compliance_rows': compliance_rows,
        'audit_checklist_rows': audit_checklist_rows,
        'duplicate_rows': duplicate_rows,
        'anomaly_rows': anomaly_rows,
        'risk_factors': risk_factors,
        'recommended_actions': recommended_actions,
        'processing_journey': processing_journey,
        'timeline_rows': timeline_rows,
        'audit_findings': audit_findings,
        'executive_summary': executive_summary,
        'findings_summary': findings_summary,
        'pdf_download_url': reverse('pipeline_result_pdf', kwargs={'document_id': document.id}) if extracted else None,
        'manual_review_required': document.status == 'pending_review' or getattr(audit_report, 'ai_review_required', False),
        'now': timezone.now(),
        'ui_language': ui_language,
        'is_arabic': ui_language == 'ar',
        'html_lang': ui_language,
        'direction': 'rtl' if ui_language == 'ar' else 'ltr',
        **build_shell_context(organization),
    }

    return render(request, 'documents/pipeline_result.html', context)


@login_required
def download_invoice_audit_pdf_view(request, document_id):
    user = request.user
    organization = user.organization
    ui_language = get_interface_language(request)

    document = get_object_or_404(Document, id=document_id, organization=organization)
    try:
        extracted = document.extracted_data
    except Exception:
        extracted = None
    try:
        audit_report = document.audit_report
    except Exception:
        audit_report = None

    if extracted is None:
        messages.error(request, _localized_value(ui_language, 'لا توجد بيانات مستخرجة لهذا المستند.', 'No extracted data is available for this document.'))
        return redirect('pipeline_result', document_id=document_id)

    validation_results = getattr(audit_report, 'validation_results_json', None) or {}
    compliance_checks = getattr(audit_report, 'compliance_checks_json', None) or getattr(extracted, 'compliance_checks', None) or []
    checklist_rows = []

    if isinstance(validation_results, dict):
        for key, result in validation_results.items():
            if not isinstance(result, dict):
                continue
            status = str(result.get('status') or 'pending')
            tone = 'success' if status in {'pass', 'completed', 'approved'} else 'warning' if status in {'warning', 'pending'} else 'danger'
            checklist_rows.append({
                'group': _localized_value(ui_language, 'التحقق', 'Validation'),
                'title': _localize_checklist_title(str(key).replace('_', ' ').title(), ui_language),
                'done_label': _localized_value(ui_language, 'تم', 'Yes') if tone == 'success' else _localized_value(ui_language, 'لا', 'No'),
                'status_label': status,
                'message': _localize_checklist_message('; '.join(result.get('issues') or []), ui_language) or '-',
            })

    if isinstance(compliance_checks, list):
        for item in compliance_checks:
            if not isinstance(item, dict):
                continue
            status = str(item.get('status') or item.get('severity') or 'pending')
            tone = 'success' if status in {'pass', 'completed', 'approved'} else 'warning' if status in {'warning', 'pending'} else 'danger'
            checklist_rows.append({
                'group': _localized_value(ui_language, 'الامتثال', 'Compliance'),
                'title': _localize_checklist_title(item.get('title') or item.get('rule_key') or item.get('check') or 'Compliance check', ui_language),
                'done_label': _localized_value(ui_language, 'تم', 'Yes') if tone == 'success' else _localized_value(ui_language, 'لا', 'No'),
                'status_label': status,
                'message': _localize_checklist_message(item.get('message') or item.get('description') or '-', ui_language),
            })

    line_items = extracted.items_json or []
    normalized_items = []
    for index, item in enumerate(line_items, start=1):
        if not isinstance(item, dict):
            continue
        normalized_items.append({
            'line_number': item.get('line_number') or index,
            'description': item.get('description') or item.get('product') or item.get('name') or f'Line {index}',
            'quantity': item.get('quantity') or item.get('qty') or 1,
            'unit_price': item.get('unit_price') or item.get('price') or '-',
            'total': item.get('total') or item.get('line_total') or item.get('amount') or '-',
        })

    executive_summary = (
        getattr(audit_report, 'ai_summary_ar', None) if ui_language == 'ar' else getattr(audit_report, 'ai_summary', None)
    ) or (
        getattr(audit_report, 'ai_summary', None) if ui_language != 'ar' else getattr(audit_report, 'ai_summary_ar', None)
    ) or ''
    findings_summary = (
        getattr(audit_report, 'ai_findings_ar', None) if ui_language == 'ar' else getattr(audit_report, 'ai_findings', None)
    ) or (
        getattr(audit_report, 'ai_findings', None) if ui_language != 'ar' else getattr(audit_report, 'ai_findings_ar', None)
    ) or ''

    recommendation_reason = (
        getattr(audit_report, 'recommendation_reason_ar', None) if ui_language == 'ar' else getattr(audit_report, 'recommendation_reason', None)
    ) or getattr(audit_report, 'recommendation_reason', None) or getattr(audit_report, 'recommendation_reason_ar', None) or ''
    recommended_actions = [recommendation_reason] if recommendation_reason else []

    payload = {
        'language': ui_language,
        'title': _localized_value(ui_language, 'تقرير تدقيق الفاتورة', 'Invoice Audit Report'),
        'subtitle': document.file_name,
        'overview_heading': _localized_value(ui_language, 'ملخص المستند', 'Document Overview'),
        'overview_rows': [
            {'label': _localized_value(ui_language, 'رقم الفاتورة', 'Invoice Number'), 'value': extracted.invoice_number or '-'},
            {'label': _localized_value(ui_language, 'المورد', 'Vendor'), 'value': extracted.vendor_name or '-'},
            {'label': _localized_value(ui_language, 'العميل', 'Customer'), 'value': extracted.customer_name or organization.name},
            {'label': _localized_value(ui_language, 'الإجمالي', 'Total Amount'), 'value': f"{extracted.total_amount or 0} {extracted.currency or 'SAR'}"},
            {'label': _localized_value(ui_language, 'مستوى المخاطر', 'Risk Level'), 'value': getattr(audit_report, 'risk_level', None) or extracted.risk_level or '-'},
            {'label': _localized_value(ui_language, 'حالة المستند', 'Document Status'), 'value': document.status},
        ],
        'checklist_heading': _localized_value(ui_language, 'قائمة التحقق', 'Audit Checklist'),
        'checklist_rows': checklist_rows,
        'items_heading': _localized_value(ui_language, 'بنود الفاتورة', 'Line Items'),
        'line_items': normalized_items,
        'summary_heading': _localized_value(ui_language, 'الملخص التنفيذي', 'Executive Summary'),
        'executive_summary': executive_summary,
        'findings_heading': _localized_value(ui_language, 'تفسير الذكاء الاصطناعي', 'AI Findings'),
        'findings_summary': findings_summary,
        'actions_heading': _localized_value(ui_language, 'الإجراءات المقترحة', 'Recommended Actions'),
        'recommended_actions': recommended_actions,
    }
    invoice_audit_pdf_service = get_invoice_audit_pdf_service()
    pdf_bytes = invoice_audit_pdf_service.generate_report(payload)

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_audit_{document.id}.pdf"'
    return response


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
    from datetime import date, datetime

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

    def _iso_date(value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        return str(value)

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
    _patch('vendor_tax_id')
    _patch('customer_name')
    _patch('customer_tax_id')
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
    update_fields = ['review_notes', 'reviewed_by', 'reviewed_at', 'extraction_status']

    if document.document_type == 'invoice':
        raw_payload = {
            'invoice_number': extracted.invoice_number,
            'issue_date': _iso_date(getattr(extracted, 'invoice_date', None)),
            'due_date': _iso_date(getattr(extracted, 'due_date', None)),
            'vendor_name': extracted.vendor_name,
            'vendor_tax_id': extracted.vendor_tax_id,
            'customer_name': extracted.customer_name or organization.name,
            'customer_tax_id': extracted.customer_tax_id or organization.vat_number,
            'vendor': {
                'name': extracted.vendor_name,
                'tax_id': extracted.vendor_tax_id,
            },
            'customer': {
                'name': extracted.customer_name or organization.name,
                'tax_id': extracted.customer_tax_id or organization.vat_number,
            },
            'currency': extracted.currency or organization.currency or 'SAR',
            'subtotal': str(extracted.subtotal_amount) if extracted.subtotal_amount is not None else None,
            'tax_amount': str(extracted.tax_amount) if extracted.tax_amount is not None else None,
            'total_amount': str(extracted.total_amount) if extracted.total_amount is not None else None,
            'items': extracted.items_json or [],
        }
        extracted.raw_json = raw_payload
        update_fields.append('raw_json')
        extracted.save(update_fields=update_fields)
        workflow_service = get_invoice_audit_workflow_service()
        workflow_result = workflow_service.resume_after_reviewer_correction(
            document=document,
            actor=user,
            raw_payload=raw_payload,
            review_notes=extracted.review_notes,
        )
        document = workflow_result.document

    # Promote document status
    if document.document_type != 'invoice':
        extracted.save(update_fields=update_fields)
        document.status = 'completed'
        document.save(update_fields=['status'])

    if document.status == 'pending_review':
        messages.warning(request, 'تم حفظ التصحيحات، لكن المستند ما زال يحتاج مراجعة إضافية قبل الاعتماد.')
        return redirect('pipeline_result', document_id=document_id)

    messages.success(request, f'تم حفظ التصحيحات البشرية ({len(fields_updated)} حقل). أُعيد تصنيف المستند.')
    return redirect('pipeline_result', document_id=document_id)

    messages.success(request, f'تم حفظ التصحيحات البشرية ({len(fields_updated)} حقل). أُعيد تصنيف المستند.')
    return redirect('pipeline_result', document_id=document_id)
