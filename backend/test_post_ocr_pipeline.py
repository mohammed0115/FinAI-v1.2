#!/usr/bin/env python
"""
Test Post-OCR Pipeline
Process recent OCR evidence through the full pipeline
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FinAI.settings')
django.setup()

from documents.models import Document, OCREvidence, ExtractedData
from compliance.models import AuditFinding
from core.post_ocr_pipeline import process_ocr_evidence

def test_pipeline():
    """Test the post-OCR pipeline"""
    print("="*60)
    print("Testing Post-OCR Pipeline")
    print("="*60)
    
    # Get recent OCR evidence without ExtractedData
    ocr_records = OCREvidence.objects.filter(
        document__extracted_data__isnull=True
    ).order_by('-extracted_at')[:5]
    
    print("\nFound {} OCR records without ExtractedData\n".format(ocr_records.count()))
    
    if ocr_records.count() == 0:
        print("All OCR records already have ExtractedData!")
        return
    
    # Process each
    processed = 0
    for ocr_ev in ocr_records:
        try:
            print("Processing OCR Evidence: {}".format(ocr_ev.id))
            print("  Document: {}".format(ocr_ev.document.file_name))
            print("  Confidence: {}%".format(ocr_ev.confidence_score))
            
            # Process pipeline
            extracted_data = process_ocr_evidence(ocr_ev)
            
            if extracted_data:
                # Count findings
                findings = AuditFinding.objects.filter(
                    related_entity_type='document',
                    related_entity_id=ocr_ev.document_id
                ).count()
                print("  [OK] ExtractedData created: {}".format(extracted_data.id))
                print("  [OK] Compliance findings: {}".format(findings))
                processed += 1
            else:
                print("  [ERROR] Pipeline failed")
        except Exception as e:
            print("  [ERROR] Exception: {}".format(str(e)))
        print()
    
    print("="*60)
    print("Summary: {} documents processed".format(processed))
    print("="*60)

if __name__ == '__main__':
    test_pipeline()
