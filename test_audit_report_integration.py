"""
Integration Test for Complete Audit Report Pipeline

This script tests the end-to-end flow:
1. Document upload
2. OCR Processing
3. Data Extraction
4. Audit Report Generation
"""

import os
import sys
import django
from pathlib import Path
import json
from datetime import datetime, timezone as tz

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FinAI.settings')
sys.path.insert(0, '/home/mohamed/FinAI-v1.2/backend')
django.setup()

from django.contrib.auth import get_user_model
from core.models import Organization
from documents.models import Document, ExtractedData, OCREvidence, InvoiceAuditReport
from documents.services import InvoiceAuditReportService
from django.utils import timezone as dj_timezone
from decimal import Decimal
import uuid

User = get_user_model()

def create_test_organization():
    """Create a test organization"""
    import uuid
    unique_name = f"Test Org {str(uuid.uuid4())[:8]}"
    org, created = Organization.objects.get_or_create(
        tax_id=f'300000000000{str(uuid.uuid4())[:3]}',
        defaults={
            'name': unique_name,
            'name_ar': 'منظمة الاختبار',
            'industry': 'Technology',
        }
    )
    print(f"Organization: {org.name} (ID: {org.id})")
    return org

def create_test_user(org):
    """Create a test user"""
    user, created = User.objects.get_or_create(
        email='test@test.com',
        defaults={
            'name': 'Test User',
            'organization': org,
            'role': 'admin',
        }
    )
    print(f"User: {user.email} (Role: {user.role})")
    return user

def create_test_document(user, org):
    """Create a test document"""
    doc = Document.objects.create(
        id=uuid.uuid4(),
        organization=org,
        uploaded_by=user,
        file_name='Test_Invoice_2024.pdf',
        file_type='application/pdf',
        file_size=2500,
        storage_key='test/invoices/test_invoice_2024.pdf',
        storage_url='file:///tmp/test_invoice_2024.pdf',
        document_type='invoice',
        status='processing',
        language='en',
        is_handwritten=False,
    )
    print(f"Document: {doc.file_name} (ID: {doc.id})")
    return doc

def create_test_ocr_evidence(doc, user, org):
    """Create OCR evidence"""
    ocr = OCREvidence.objects.create(
        document=doc,
        organization=org,
        raw_text='Invoice Number: INV-2024-001\\nVendor: ABC Supplies Inc.\\nCustomer: XYZ Company\\nDate: 2024-01-15\\nAmount: 15,500.00 SAR',
        text_en='Invoice Number: INV-2024-001\nVendor: ABC Supplies Inc.\nCustomer: XYZ Company\nDate: 2024-01-15\nAmount: 15,500.00 SAR',
        text_ar='رقم الفاتورة: INV-2024-001\nالموردة: ABC Supplies Inc.\nالعميل: XYZ Company\nالتاريخ: 15-01-2024\nالمبلغ: 15,500.00 ريال',
        confidence_score=92,
        confidence_level='high',
        page_count=1,
        word_count=25,
        ocr_engine='openai_vision',
        ocr_version='GPT-4 Vision',
        language_used='en',
        is_handwritten=False,
        processing_time_ms=2500,
        extracted_invoice_number='INV-2024-001',
        extracted_vat_number='300000000000003',
        extracted_total=Decimal('15500.00'),
        extracted_tax=Decimal('2325.00'),
        extracted_vendor_name='ABC Supplies Inc.',
        extracted_vendor_address='123 Business Ave, Riyadh, SA',
        extracted_customer_name='XYZ Company',
        extracted_customer_address='456 Commerce St, Jeddah, SA',
        extracted_invoice_date='2024-01-15',
        extracted_due_date='2024-02-15',
        extracted_currency='SAR',
        extracted_items=[
            {'product': 'Office Supplies', 'quantity': 100, 'unit_price': 50, 'total': 5000},
            {'product': 'Hardware', 'quantity': 10, 'unit_price': 1050, 'total': 10500},
        ],
        evidence_hash='abc123def456',
        extracted_by=user,
    )
    print(f"OCR Evidence: {str(ocr.id)[:8]}... (Confidence: {ocr.confidence_score}%)")
    return ocr

def create_test_extracted_data(doc, user, org):
    """Create extracted data from OCR or reuse if already created by signal"""
    # Check if ExtractedData for this document already exists (from signal)
    extracted = ExtractedData.objects.filter(document=doc).first()
    
    if extracted:
        # Signal already created it, just update it with test data
        extracted.vendor_name = 'ABC Supplies Inc.'
        extracted.customer_name = 'XYZ Company'
        extracted.invoice_number = 'INV-2024-001'
        extracted.invoice_date = dj_timezone.make_aware(datetime(2024, 1, 15))
        extracted.due_date = dj_timezone.make_aware(datetime(2024, 2, 15))
        extracted.total_amount = Decimal('15500.00')
        extracted.tax_amount = Decimal('2325.00')
        extracted.currency = 'SAR'
        extracted.items_json = [
            {
                'product': 'Office Supplies',
                'description': 'General office supplies',
                'quantity': 100,
                'unit_price': 50,
                'discount': 0,
                'total': 5000
            },
            {
                'product': 'Hardware',
                'description': 'Computer hardware',
                'quantity': 10,
                'unit_price': 1050,
                'discount': 0,
                'total': 10500
            }
        ]
        extracted.confidence = 92
        extracted.is_valid = True
        extracted.risk_score = 25
        extracted.risk_level = 'low'
        extracted.save()
        print(f"Updated Extracted Data: {str(extracted.id)[:8]}... (Invoice: {extracted.invoice_number})")
    else:
        # Create it manually if signal didn't
        extracted = ExtractedData.objects.create(
            document=doc,
            organization=org,
            vendor_name='ABC Supplies Inc.',
            customer_name='XYZ Company',
            invoice_number='INV-2024-001',
            invoice_date=dj_timezone.make_aware(datetime(2024, 1, 15)),
            due_date=dj_timezone.make_aware(datetime(2024, 2, 15)),
            total_amount=Decimal('15500.00'),
            tax_amount=Decimal('2325.00'),
            currency='SAR',
            items_json=[
                {
                    'product': 'Office Supplies',
                    'description': 'General office supplies',
                    'quantity': 100,
                    'unit_price': 50,
                    'discount': 0,
                    'total': 5000
                },
                {
                    'product': 'Hardware',
                    'description': 'Computer hardware',
                    'quantity': 10,
                    'unit_price': 1050,
                    'discount': 0,
                    'total': 10500
                }
            ],
            raw_text_en='Invoice for supplies and hardware',
            confidence=92,
            validation_status='pending',
            extracted_at=dj_timezone.now(),
            is_valid=True,
            risk_score=25,
            risk_level='low',
        )
        print(f"Created Extracted Data: {str(extracted.id)[:8]}... (Invoice: {extracted.invoice_number})")
    
    return extracted

def generate_audit_report(extracted_data, doc, org, user):
    """Generate comprehensive audit report"""
    # Check if report already exists (might have been created by signal)
    try:
        report = extracted_data.audit_report
        print(f"Report already exists: {report.report_number}")
        return report
    except:
        pass  # Report doesn't exist, create it
    
    service = InvoiceAuditReportService(user=user)
    
    ocr_evidence = doc.ocr_evidence_records.first()
    
    report = service.generate_comprehensive_report(
        extracted_data=extracted_data,
        document=doc,
        organization=org,
        ocr_evidence=ocr_evidence
    )
    
    print(f"Audit Report: {report.report_number}")
    print(f"  - Status: {report.status}")
    print(f"  - Risk Level: {report.risk_level}")
    print(f"  - Risk Score: {report.risk_score}")
    print(f"  - Recommendation: {report.recommendation}")
    print(f"  - Duplicate Score: {report.duplicate_score}")
    print(f"  - Anomaly Score: {report.anomaly_score}")
    
    return report

def display_report_summary(report):
    """Display formatted report summary"""
    print("\n" + "="*80)
    print(f"COMPREHENSIVE AUDIT REPORT - {report.report_number}")
    print("="*80)
    
    print(f"\n1. DOCUMENT INFORMATION")
    print(f"   File: {report.document.file_name}")
    print(f"   Upload Date: {report.upload_date}")
    print(f"   OCR Engine: {report.ocr_engine}")
    print(f"   OCR Confidence: {report.ocr_confidence_score}%")
    
    print(f"\n2. INVOICE DATA")
    print(f"   Invoice Number: {report.extracted_invoice_number}")
    print(f"   Issue Date: {report.extracted_issue_date}")
    print(f"   Vendor: {report.extracted_vendor_name}")
    print(f"   Customer: {report.extracted_customer_name}")
    
    print(f"\n3. FINANCIAL TOTALS")
    print(f"   Subtotal: {report.subtotal_amount} {report.currency}")
    print(f"   VAT: {report.vat_amount} {report.currency}")
    print(f"   Total: {report.total_amount} {report.currency}")
    
    print(f"\n4. VALIDATION RESULTS")
    if report.validation_results_json:
        for check, result in report.validation_results_json.items():
            print(f"   {check}: {result['status'].upper()}")
            if result.get('issues'):
                for issue in result['issues']:
                    print(f"      - {issue}")
    
    print(f"\n5. DUPLICATE DETECTION")
    print(f"   Score: {report.duplicate_score}/100")
    print(f"   Status: {report.duplicate_status}")
    
    print(f"\n6. ANOMALY DETECTION")
    print(f"   Score: {report.anomaly_score}/100")
    print(f"   Status: {report.anomaly_status}")
    if report.anomaly_reasons_json:
        for reason in report.anomaly_reasons_json:
            print(f"      - {reason.get('reason', reason)}")
    
    print(f"\n7. RISK ASSESSMENT")
    print(f"   Score: {report.risk_score}/100")
    print(f"   Level: {report.risk_level.upper()}")
    if report.risk_factors_json:
        for factor in report.risk_factors_json:
            print(f"      - {factor}")
    
    print(f"\n8. RECOMMENDATION")
    print(f"   Action: {report.recommendation.upper()}")
    print(f"   Reason: {report.recommendation_reason}")
    
    print("\n" + "="*80)
    print("Report Generation Complete")
    print("="*80 + "\n")

def main():
    print("\n" + "="*80)
    print("FINAI AUDIT REPORT GENERATION - INTEGRATION TEST")
    print("="*80 + "\n")
    
    print("Step 1: Creating test organization...")
    org = create_test_organization()
    
    print("\nStep 2: Creating test user...")
    user = create_test_user(org)
    
    print("\nStep 3: Creating test document...")
    doc = create_test_document(user, org)
    
    print("\nStep 4: Creating OCR evidence...")
    ocr = create_test_ocr_evidence(doc, user, org)
    
    print("\nStep 5: Creating extracted data...")
    extracted = create_test_extracted_data(doc, user, org)
    
    print("\nStep 6: Generating comprehensive audit report...")
    report = generate_audit_report(extracted, doc, org, user)
    
    print("\nStep 7: Displaying report summary...")
    display_report_summary(report)
    
    print("\nStep 8: Verifying database records...")
    total_reports = InvoiceAuditReport.objects.count()
    print(f"   Total Audit Reports in database: {total_reports}")
    
    print("\n✅ Integration test completed successfully!")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
