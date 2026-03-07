#!/usr/bin/env python
"""
Backfill AI Summaries for Existing Documents
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FinAI.settings')
django.setup()

from documents.models import ExtractedData
from compliance.models import AuditFinding
from core.post_ocr_pipeline import generate_ai_summary

def backfill_ai_summaries():
    """Generate AI summaries for existing documents without them"""
    
    print("="*70)
    print("Backfill AI Summaries")
    print("="*70)
    
    # Find documents without AI summary
    docs_without_summary = ExtractedData.objects.filter(audit_summary__isnull=True)
    
    print("\nFound {} documents without AI summaries\n".format(docs_without_summary.count()))
    
    if docs_without_summary.count() == 0:
        print("All documents already have AI summaries!")
        return
    
    processed = 0
    
    for ed in docs_without_summary[:10]:  # Process first 10
        try:
            # Get findings
            findings = list(AuditFinding.objects.filter(
                related_entity_type='document',
                related_entity_id=ed.document.id
            ))
            
            print("[{}] Processing: Invoice {}".format(processed+1, ed.invoice_number or "N/A"))
            print("    Risk: {} | Findings: {}".format(ed.risk_level, len(findings)))
            
            # Generate AI summary
            generate_ai_summary(ed, findings)
            
            print("    [✓] AI Summary Generated")
            processed += 1
            
        except Exception as e:
            print("    [✗] Error: {}".format(str(e)[:50]))
    
    print("\n" + "="*70)
    print("Summary: {} documents processed".format(processed))
    print("="*70)

if __name__ == '__main__':
    backfill_ai_summaries()
