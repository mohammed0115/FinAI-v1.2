#!/usr/bin/env python
"""
Backfill AI Summaries using DEFAULT SUMMARIES (no OpenAI API)
For deployment when API is unavailable or too slow
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FinAI.settings')
django.setup()

from documents.models import ExtractedData
from compliance.models import AuditFinding
from datetime import datetime
from django.utils import timezone

def generate_default_summary(extracted_data, findings):
    """Generate default summary without OpenAI API"""
    
    risk_levels = [f.risk_level for f in findings]
    highest_risk = "critical" if "critical" in risk_levels else \
                  "high" if "high" in risk_levels else \
                  "medium" if "medium" in risk_levels else "low"
    
    return {
        "executive_summary": f"فاتورة من {extracted_data.vendor_name or 'بائع غير معروف'} برقم {extracted_data.invoice_number or 'غير محدد'}",
        "key_risks": [f.title_ar for f in findings[:3]],
        "recommended_actions": [
            "مراجعة النتائج المرفقة",
            "التحقق من صحة البيانات المستخرجة",
            "متابعة الإجراءات المقترحة"
        ],
        "final_status": "review" if highest_risk in ["high", "critical"] else "approved"
    }

def backfill_ai_summaries():
    """Generate default summaries for existing documents without them"""
    
    print("="*70)
    print("Backfill AI Summaries (Default - No OpenAI API)")
    print("="*70)
    
    # Find documents without AI summary
    docs_without_summary = ExtractedData.objects.filter(audit_summary__isnull=True)
    
    total = docs_without_summary.count()
    print(f"\nFound {total} documents without AI summaries\n")
    
    if total == 0:
        print("All documents already have AI summaries!")
        return
    
    processed = 0
    failed = 0
    
    for ed in docs_without_summary:
        try:
            # Get findings
            findings = list(AuditFinding.objects.filter(
                related_entity_type='document',
                related_entity_id=ed.document.id
            ))
            
            # Generate default summary
            summary = generate_default_summary(ed, findings)
            
            # Save to database
            ed.audit_summary = summary
            ed.audit_completed_at = timezone.now()
            ed.save()
            
            print(f"[✓] {processed+1:3d}/{total} Invoice {ed.invoice_number:15s} | Findings: {len(findings):2d} | Risk: {ed.risk_level:8s}")
            processed += 1
            
        except Exception as e:
            print(f"[✗] {processed+failed+1:3d}/{total} Error: {str(e)[:50]}")
            failed += 1
    
    print("\n" + "="*70)
    print(f"Summary: {processed} documents processed | {failed} failed")
    print("="*70)

if __name__ == '__main__':
    backfill_ai_summaries()
