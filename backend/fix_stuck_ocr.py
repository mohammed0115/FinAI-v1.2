#!/usr/bin/env python
"""
Fix stuck documents - Reprocess documents without OCR evidence
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FinAI.settings')
django.setup()

from documents.models import Document, OCREvidence
from core.views.document_views import process_document_ocr
from django.contrib.auth import get_user_model

User = get_user_model()

def fix_stuck_documents():
    """Reprocess documents stuck in processing/pending without OCR"""
    
    # Find stuck documents
    stuck_docs = Document.objects.exclude(ocr_evidence_records__isnull=False).filter(
        status__in=['processing', 'pending']
    )
    
    print("Found {} stuck documents".format(stuck_docs.count()))
    
    if stuck_docs.count() == 0:
        print("[OK] No stuck documents found!")
        return
    
    # Get system admin for extracted_by field
    admin_user = User.objects.filter(role='admin').first()
    if not admin_user:
        admin_user = User.objects.first()
    
    if not admin_user:
        print("[ERROR] No admin user found")
        return
    
    # Process each stuck document
    reprocessed = 0
    for doc in stuck_docs[:10]:  # Process first 10
        try:
            # Get file path
            if not doc.storage_key or not doc.storage_url:
                print("WARN Skipping {} - no storage".format(doc.file_name))
                continue
            
            file_path = os.path.join('/home/mohamed/FinAI-v1.2/backend/media', doc.storage_key)
            
            if not os.path.exists(file_path):
                print("WARN Skipping {} - file not found at {}".format(doc.file_name, file_path))
                continue
            
            # Reprocess with OCR
            success, message, ocr_evidence = process_document_ocr(
                document=doc,
                file_path=file_path,
                language=doc.language or 'ara+eng',
                is_handwritten=doc.is_handwritten or False,
                user=admin_user,
                organization=doc.organization
            )
            
            if success:
                print("[OK] {} - Confidence: {}%".format(doc.file_name, ocr_evidence.confidence_score))
                reprocessed += 1
            else:
                print("[ERROR] {} - Error: {}".format(doc.file_name, message))
                
        except Exception as e:
            print("[ERROR] {} - Exception: {}".format(doc.file_name, str(e)))
    
    print("\n" + "="*50)
    print("Reprocessed: {}/{} documents".format(reprocessed, min(10, stuck_docs.count())))
    print("Remaining stuck: {}".format(stuck_docs.count() - reprocessed))

if __name__ == '__main__':
    fix_stuck_documents()
