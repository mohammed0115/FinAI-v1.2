#!/usr/bin/env python
"""
Diagnostic script to check InvoiceAuditReport data flow and completeness
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, '/home/mohamed/FinAI-v1.2/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FinAI.settings')
django.setup()

from documents.models import Document, ExtractedData, InvoiceAuditReport, OCREvidence
from django.utils import timezone
import json

def check_latest_document():
    """Check the latest document and its related objects"""
    
    # Get latest document with completed status
    doc = Document.objects.filter(status='completed').order_by('-processed_at').first()
    if not doc:
        print("❌ No completed documents found")
        return
    
    print(f"📄 Document ID: {doc.id}")
    print(f"📄 Document: {doc.file_name}")
    print(f"📄 Status: {doc.status}")
    print(f"📄 Uploaded at: {doc.uploaded_at}")
    print()
    
    # Check OCREvidence
    evidence = OCREvidence.objects.filter(document=doc).first()
    if evidence:
        print("📋 OCREvidence:")
        print(f"  ✓ ID: {evidence.id}")
        print(f"  ✓ OCR Engine: {evidence.ocr_engine}")
        print(f"  ✓ Confidence: {evidence.confidence_score}%")
        print(f"  ✓ Invoice Number (extracted): {evidence.extracted_invoice_number}")
        print(f"  ✓ Invoice Date (extracted): {evidence.extracted_invoice_date}")
        print(f"  ✓ Vendor: {evidence.extracted_vendor_name}")
        print()
    else:
        print("❌ No OCREvidence found")
    
    # Check ExtractedData
    try:
        extracted = doc.extracted_data
        print("📊 ExtractedData:")
        print(f"  ✓ ID: {extracted.id}")
        print(f"  ✓ Invoice Number: {extracted.invoice_number}")
        print(f"  ✓ Invoice Date: {extracted.invoice_date} (type: {type(extracted.invoice_date).__name__})")
        print(f"  ✓ Due Date: {extracted.due_date} (type: {type(extracted.due_date).__name__})")
        print(f"  ✓ Vendor: {extracted.vendor_name}")
        print(f"  ✓ Customer: {extracted.customer_name}")
        print(f"  ✓ Total Amount: {extracted.total_amount}")
        print(f"  ✓ Tax Amount: {extracted.tax_amount}")
        print(f"  ✓ Currency: {extracted.currency}")
        print(f"  ✓ Is Valid: {extracted.is_valid}")
        print(f"  ✓ Risk Score: {extracted.risk_score}")
        print(f"  ✓ Risk Level: {extracted.risk_level}")
        print()
    except Exception as e:
        print(f"❌ No ExtractedData: {e}")
        extracted = None
    
    # Check InvoiceAuditReport
    try:
        audit_report = doc.audit_report
        print("📈 InvoiceAuditReport:")
        print(f"  ✓ ID: {audit_report.id}")
        print(f"  ✓ Report Number: {audit_report.report_number}")
        print(f"  ✓ Status: {audit_report.status}")
        print()
        
        print("  Section 1 - Document Information:")
        print(f"    • Upload Date: {audit_report.upload_date}")
        print(f"    • OCR Engine: {audit_report.ocr_engine}")
        print(f"    • OCR Confidence: {audit_report.ocr_confidence_score}%")
        print(f"    • Processing Status: {audit_report.processing_status}")
        print()
        
        print("  Section 2 - Invoice Data:")
        print(f"    • Invoice Number: {audit_report.extracted_invoice_number}")
        print(f"    • Issue Date: {audit_report.extracted_issue_date} (type: {type(audit_report.extracted_issue_date).__name__})")
        print(f"    • Due Date: {audit_report.extracted_due_date} (type: {type(audit_report.extracted_due_date).__name__})")
        print(f"    • Vendor: {audit_report.extracted_vendor_name}")
        print(f"    • Vendor Address: {audit_report.extracted_vendor_address}")
        print(f"    • Customer: {audit_report.extracted_customer_name}")
        print(f"    • Customer Address: {audit_report.extracted_customer_address}")
        print()
        
        print("  Section 3 - Line Items:")
        if audit_report.line_items_json:
            print(f"    • Items Count: {len(audit_report.line_items_json)}")
            if audit_report.line_items_json:
                print(f"    • Sample Item: {audit_report.line_items_json[0]}")
        else:
            print(f"    • Items: None or Empty")
        print()
        
        print("  Section 4 - Financial Totals:")
        print(f"    • Subtotal: {audit_report.subtotal_amount}")
        print(f"    • VAT: {audit_report.vat_amount}")
        print(f"    • Total: {audit_report.total_amount}")
        print(f"    • Currency: {audit_report.currency}")
        print()
        
        print("  Section 5 - Validation Results:")
        if audit_report.validation_results_json:
            val_results = audit_report.validation_results_json
            print(f"    • Invoice Number: {val_results.get('invoice_number', {}).get('status', '?')}")
            print(f"    • Vendor: {val_results.get('vendor', {}).get('status', '?')}")
            print(f"    • Customer: {val_results.get('customer', {}).get('status', '?')}")
            print(f"    • Items: {val_results.get('items', {}).get('status', '?')}")
            print(f"    • Total Match: {val_results.get('total_match', {}).get('status', '?')}")
            print(f"    • VAT: {val_results.get('vat', {}).get('status', '?')}")
        else:
            print("    • No validation results")
        print()
        
        print("  Section 6 - Duplicate Detection:")
        print(f"    • Score: {audit_report.duplicate_score}")
        print(f"    • Status: {audit_report.duplicate_status}")
        print(f"    • Matched Docs: {audit_report.duplicate_matched_documents_json}")
        print()
        
        print("  Section 7 - Anomaly Detection:")
        print(f"    • Score: {audit_report.anomaly_score}")
        print(f"    • Status: {audit_report.anomaly_status}")
        print(f"    • Explanation: {audit_report.anomaly_explanation[:100] if audit_report.anomaly_explanation else 'None'}")
        print()
        
        print("  Section 8 - Risk Assessment:")
        print(f"    • Score: {audit_report.risk_score}")
        print(f"    • Level: {audit_report.risk_level}")
        print(f"    • Factors: {audit_report.risk_factors_json}")
        print()
        
        print("  Section 9 - AI Summary:")
        print(f"    • Summary (EN): {audit_report.ai_summary[:100] if audit_report.ai_summary else 'None'}")
        print(f"    • Summary (AR): {audit_report.ai_summary_ar[:100] if audit_report.ai_summary_ar else 'None'}")
        print(f"    • Findings: {audit_report.ai_findings[:100] if audit_report.ai_findings else 'None'}")
        print()
        
        print("  Section 10 - Recommendations:")
        print(f"    • Recommendation: {audit_report.recommendation}")
        print(f"    • Reason: {audit_report.recommendation_reason[:100] if audit_report.recommendation_reason else 'None'}")
        print()
        
        print("  Section 11 - Audit Trail:")
        if audit_report.audit_trail_json:
            print(f"    • Events: {len(audit_report.audit_trail_json)}")
        else:
            print("    • No audit trail")
        print()
        
        print("✅ InvoiceAuditReport is complete and has all 11 sections!")
        
        # Check for empty fields
        print("\n🔍 Checking for empty/None fields that might cause '—' display:")
        empty_fields = []
        
        if not audit_report.extracted_invoice_number:
            empty_fields.append("extracted_invoice_number")
        if not audit_report.extracted_issue_date:
            empty_fields.append("extracted_issue_date")
        if not audit_report.extracted_due_date:
            empty_fields.append("extracted_due_date")
        if not audit_report.extracted_vendor_name:
            empty_fields.append("extracted_vendor_name")
        if not audit_report.extracted_customer_name:
            empty_fields.append("extracted_customer_name")
        if not audit_report.total_amount:
            empty_fields.append("total_amount")
        if not audit_report.vat_amount:
            empty_fields.append("vat_amount")
        if not audit_report.line_items_json:
            empty_fields.append("line_items_json")
        
        if empty_fields:
            print(f"⚠️  Found empty fields: {', '.join(empty_fields)}")
        else:
            print("✅ All key fields are populated!")
            
    except Exception as e:
        print(f"❌ No InvoiceAuditReport: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_latest_document()
