#!/usr/bin/env python
"""
End-to-end test: Upload a test invoice and verify complete pipeline execution
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, '/home/mohamed/FinAI-v1.2/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FinAI.settings')
django.setup()

from documents.models import Document, OCREvidence, ExtractedData, InvoiceAuditReport
from core.models import Organization, User
import json
from datetime import datetime

# Use first existing organization or create a new one with unique name
import uuid
org = Organization.objects.first()
if not org:
    org = Organization.objects.create(
        name=f'Test Organization {uuid.uuid4().hex[:8]}',
        country='SA',
        industry='Technology'
    )

# Get or create test user
user = User.objects.first()
if not user:
    user = User.objects.create_user(
        email='test@example.com',
        name='Test User',
        password='testpass123',
        role='admin',
        organization=org,
    )

print("=" * 60)
print("END-TO-END PIPELINE TEST")
print("=" * 60)
print()

# Create a test document
doc = Document.objects.create(
    organization=org,
    uploaded_by=user,
    file_name='test_invoice_e2e.pdf',
    file_type='application/pdf',
    file_size=1024,
    storage_key='test/test_invoice_e2e.pdf',
    storage_url='file:///tmp/test_invoice_e2e.pdf',
    document_type='invoice',
    status='pending',
    language='en',
    is_handwritten=False
)

print(f"✓ Document created: {doc.id}")
print(f"  File: {doc.file_name}")
print(f"  Status: {doc.status}")
print()

# Create OCREvidence
ocr_evidence = OCREvidence.objects.create(
    document=doc,
    organization=org,
    extracted_by=user,
    ocr_engine='openai_vision',
    ocr_version='gpt-4o-mini',
    confidence_score=90,
    processing_time_ms=2500,
    text_ar='',
    text_en='Invoice 12345\nSuperStore\nAaron Test\n2026-03-07\n2026-04-07\n100.00 USD',
    language_used='en',
    is_handwritten=False,
    structured_data_json={
        'invoice_number': '12345',
        'vendor_name': 'SuperStore',
        'customer_name': 'Aaron Test',
        'issue_date': '2026-03-07',
        'due_date': '2026-04-07',
        'total_amount': 100.00,
        'tax_amount': 15.00,
        'currency': 'USD',
        'items': [
            {
                'description': 'Test Item',
                'quantity': 1,
                'unit_price': 85.00,
                'discount': 0,
                'line_total': 85.00
            }
        ]
    }
)

print(f"✓ OCREvidence created: {ocr_evidence.id}")
print(f"  Engine: {ocr_evidence.ocr_engine}")
print(f"  Confidence: {ocr_evidence.confidence_score}%")
print()

# Now run the post-OCR pipeline
print("🔄 Running post-OCR pipeline...")
from core.post_ocr_pipeline import process_ocr_evidence

try:
    extracted_data = process_ocr_evidence(ocr_evidence)
    
    if extracted_data:
        print(f"✓ Pipeline completed successfully")
        print(f"  ExtractedData: {extracted_data.id}")
        print(f"  Invoice: {extracted_data.invoice_number}")
        print(f"  Total: {extracted_data.total_amount} {extracted_data.currency}")
        print()
        
        # Check if InvoiceAuditReport was created
        try:
            audit_report = doc.audit_report
            print(f"✓ InvoiceAuditReport created: {audit_report.id}")
            print(f"  Report Number: {audit_report.report_number}")
            print(f"  Status: {audit_report.status}")
            print(f"  Risk Level: {audit_report.risk_level}")
            print(f"  Recommendation: {audit_report.recommendation}")
            print()
            
            # Verify all sections have data
            sections = {
                'Section 1 - Document Info': {
                    'Upload Date': audit_report.upload_date,
                    'OCR Engine': audit_report.ocr_engine,
                },
                'Section 2 - Invoice Data': {
                    'Invoice Number': audit_report.extracted_invoice_number,
                    'Vendor': audit_report.extracted_vendor_name,
                    'Customer': audit_report.extracted_customer_name,
                },
                'Section 4 - Financials': {
                    'Subtotal': audit_report.subtotal_amount,
                    'VAT': audit_report.vat_amount,
                    'Total': audit_report.total_amount,
                },
                'Section 5 - Validation': {
                    'Results': audit_report.validation_results_json is not None,
                },
                'Section 6 - Duplicates': {
                    'Score': audit_report.duplicate_score,
                },
                'Section 7 - Anomalies': {
                    'Score': audit_report.anomaly_score,
                },
                'Section 8 - Risk': {
                    'Score': audit_report.risk_score,
                    'Level': audit_report.risk_level,
                },
                'Section 9 - AI Summary': {
                    'Summary EN': audit_report.ai_summary is not None,
                },
                'Section 10 - Recommendations': {
                    'Recommendation': audit_report.recommendation,
                },
            }
            
            print("📊 SECTION COMPLETENESS CHECK:")
            for section, fields in sections.items():
                print(f"\n  {section}:")
                for field_name, value in fields.items():
                    if value:
                        print(f"    ✓ {field_name}: {value}")
                    else:
                        print(f"    ✗ {field_name}: MISSING")
            
            print("\n" + "=" * 60)
            print("✅ END-TO-END TEST PASSED!")
            print("=" * 60)
            
        except Exception as e:
            print(f"❌ InvoiceAuditReport not created: {e}")
            print("\n" + "=" * 60)
            print("❌ END-TO-END TEST FAILED!")
            print("=" * 60)
    else:
        print("❌ Pipeline returned None")
        print("\n" + "=" * 60)
        print("❌ END-TO-END TEST FAILED!")
        print("=" * 60)
        
except Exception as e:
    print(f"❌ Pipeline error: {e}")
    import traceback
    traceback.print_exc()
    print("\n" + "=" * 60)
    print("❌ END-TO-END TEST FAILED!")
    print("=" * 60)
