#!/usr/bin/env python
"""
Test to manually trigger audit report generation for the latest document
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, '/home/mohamed/FinAI-v1.2/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FinAI.settings')
django.setup()

from documents.models import Document, ExtractedData, InvoiceAuditReport, OCREvidence
from core.post_ocr_pipeline import generate_audit_report

# Get the latest document with ExtractedData but no AuditReport
doc = Document.objects.filter(status='completed', audit_report__isnull=True).order_by('-processed_at').first()

if not doc:
    print("❌ No eligible document found")
    sys.exit(1)

print(f"📄 Document: {doc.file_name}")
print(f"📄 ID: {doc.id}")

# Get related objects
extracted = doc.extracted_data
evidence = OCREvidence.objects.filter(document=doc).first()
organization = doc.organization

print(f"✓ ExtractedData: {extracted.id}")
print(f"✓ OCREvidence: {evidence.id if evidence else 'None'}")
print(f"✓ Organization: {organization.id}")
print()

print("🔄 Attempting to generate audit report...")
try:
    report = generate_audit_report(extracted, doc, organization, evidence)
    if report:
        print(f"✅ Success! Report generated: {report.report_number}")
        print(f"   ID: {report.id}")
        print(f"   Status: {report.status}")
    else:
        print("❌ Function returned None")
except Exception as e:
    print(f"❌ Exception occurred: {e}")
    import traceback
    traceback.print_exc()

# Check again if report was created
try:
    audit_report = doc.audit_report
    print(f"\n✅ InvoiceAuditReport now exists: {audit_report.report_number}")
except Exception as e:
    print(f"\n❌ InvoiceAuditReport still doesn't exist: {e}")
