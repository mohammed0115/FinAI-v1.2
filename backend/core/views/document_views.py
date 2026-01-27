"""
Document Views - وجهات المستندات
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.conf import settings
import os
import uuid
import logging

from core.models import Organization
from documents.models import Document
from documents.ocr_service import document_ocr_service
from documents.models import OCREvidence

logger = logging.getLogger(__name__)


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
    صفحة رفع المستندات مع OCR
    Document Upload with OCR Processing
    
    Supports: PDF, JPG, PNG, TIFF, BMP
    Max size: 50MB (GCC requirement)
    """
    user = request.user
    organization = user.organization
    
    if request.method == 'POST' and request.FILES.get('document'):
        uploaded_file = request.FILES['document']
        document_type = request.POST.get('document_type', 'other')
        language = request.POST.get('language', 'ara+eng')
        is_handwritten = request.POST.get('is_handwritten') == 'on'
        
        # Validate file size
        if uploaded_file.size > settings.MAX_UPLOAD_SIZE:
            messages.error(request, f'حجم الملف يتجاوز الحد المسموح ({settings.MAX_UPLOAD_SIZE // (1024*1024)}MB)')
            return redirect('document_upload')
        
        # Validate file type
        content_type = uploaded_file.content_type
        if content_type not in settings.ALLOWED_DOCUMENT_TYPES:
            messages.error(request, 'نوع الملف غير مدعوم. الأنواع المدعومة: PDF, JPG, PNG, TIFF')
            return redirect('document_upload')
        
        try:
            # Save the document
            document = Document.objects.create(
                organization=organization,
                title=uploaded_file.name,
                file=uploaded_file,
                file_type=content_type,
                file_size=uploaded_file.size,
                status='processing',
                uploaded_by=user,
            )
            
            # Process with OCR
            file_path = document.file.path
            ocr_result = document_ocr_service.process_document(
                file_path=file_path,
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
                document_type
            )
            
            # Get JSON-serializable version for storage
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
            document.status = 'processed'
            document.save()
            
            messages.success(
                request, 
                f'تم معالجة المستند بنجاح. درجة الثقة: {confidence}%'
            )
            
            return redirect('ocr_evidence_detail', evidence_id=ocr_evidence.id)
            
        except Exception as e:
            logger.error(f"Document processing error: {e}")
            messages.error(request, f'خطأ في معالجة المستند: {str(e)}')
            return redirect('document_upload')
    
    # GET request - show upload form
    recent_documents = Document.objects.filter(
        organization=organization
    ).order_by('-uploaded_at')[:5]
    
    context = {
        'recent_documents': recent_documents,
    }
    
    return render(request, 'documents/upload.html', context)


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
