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
from documents.ocr_service import document_ocr_service
from documents.models import OCREvidence

logger = logging.getLogger(__name__)

# Supported file extensions for batch upload
SUPPORTED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.txt', '.xml'}
CONTENT_TYPE_MAP = {
    '.pdf': 'application/pdf',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.tiff': 'image/tiff',
    '.tif': 'image/tiff',
    '.bmp': 'image/bmp',
    '.txt': 'text/plain',
    '.xml': 'application/xml',
}


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


def create_document_record(organization, user, file_name, file_content, file_type, upload_source='single'):
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
    audit_hash = generate_file_hash(file_content)
    
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
        document_type='other',
        status='pending',
        language=None,
        is_handwritten=False,
    )
    
    # Log upload source in a way that can be queried
    logger.info(f"Document created: {document.id} | source={upload_source} | file={file_name} | hash={audit_hash}")
    
    return document, file_path, audit_hash


def process_document_ocr(document, file_path, language, is_handwritten, user, organization):
    """
    Process a document with OCR
    Returns: (success, message, ocr_evidence)
    """
    try:
        # Update status to processing
        document.status = 'processing'
        document.save()
        
        # Get file extension for OCR service
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Process with OCR
        ocr_result = document_ocr_service.process_document(
            file_path=file_path,
            file_type=file_ext,
            language=language,
            is_handwritten=is_handwritten,
        )
        
        # Calculate confidence level
        confidence = ocr_result.get('confidence', 0)
        if confidence >= 80:
            confidence_level = 'high'
        elif confidence >= 50:
            confidence_level = 'medium'
        else:
            confidence_level = 'low'
        
        # Extract structured data
        structured = document_ocr_service.extract_structured_data(
            ocr_result.get('text', ''),
            document.document_type
        )
        
        # Get JSON-serializable version
        structured_json = document_ocr_service.get_json_serializable_data(structured)
        
        # Create OCR evidence record
        ocr_evidence = OCREvidence.objects.create(
            document=document,
            organization=organization,
            raw_text=ocr_result.get('text', ''),
            text_ar=ocr_result.get('text_ar', ''),
            text_en=ocr_result.get('text_en', ''),
            confidence_score=confidence,
            confidence_level=confidence_level,
            page_count=ocr_result.get('page_count', 1),
            word_count=len(ocr_result.get('text', '').split()),
            ocr_engine=ocr_result.get('ocr_engine', 'tesseract'),
            ocr_version=ocr_result.get('ocr_version', ''),
            language_used=language,
            is_handwritten=is_handwritten,
            processing_time_ms=ocr_result.get('processing_time_ms', 0),
            extracted_invoice_number=structured.get('invoice_number'),
            extracted_vat_number=structured.get('vat_number'),
            extracted_total=structured.get('total_amount'),
            extracted_tax=structured.get('tax_amount'),
            structured_data_json=structured_json,
            evidence_hash=ocr_result.get('evidence_hash', ''),
            extracted_by=user,
        )
        
        # Update document status
        document.status = 'completed'
        document.processed_at = timezone.now()
        document.save()
        
        return True, f'درجة الثقة: {confidence}%', ocr_evidence
        
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
        
        # Create document record
        document, file_path, audit_hash = create_document_record(
            organization=organization,
            user=user,
            file_name=uploaded_file.name,
            file_content=file_content,
            file_type=file_type,
            upload_source='single'
        )
        
        # Update document type
        document.document_type = document_type
        document.language = language.split('+')[0] if '+' in language else language
        document.is_handwritten = is_handwritten
        document.save()
        
        # Process OCR immediately for single uploads
        success, message, ocr_evidence = process_document_ocr(
            document, file_path, language, is_handwritten, user, organization
        )
        
        if success:
            messages.success(request, f'تم معالجة المستند بنجاح. {message}')
            return redirect('ocr_evidence_detail', evidence_id=ocr_evidence.id)
        else:
            messages.error(request, f'خطأ في معالجة المستند: {message}')
            return redirect('document_upload')
            
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
            
            # Create document record
            document, file_path, audit_hash = create_document_record(
                organization=organization,
                user=user,
                file_name=uploaded_file.name,
                file_content=file_content,
                file_type=file_type,
                upload_source='multi'
            )
            
            # Update document metadata
            document.document_type = document_type
            document.language = language.split('+')[0] if '+' in language else language
            document.is_handwritten = is_handwritten
            document.save()
            
            # Process OCR based on user preference
            if process_ocr == 'immediate' and len(uploaded_files) <= 10:
                success, message, ocr_evidence = process_document_ocr(
                    document, file_path, language, is_handwritten, user, organization
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
    
    # Store results in session for display
    request.session['upload_results'] = results
    
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
    
    context = {
        'evidence': evidence,
    }
    
    return render(request, 'documents/ocr_detail.html', context)
