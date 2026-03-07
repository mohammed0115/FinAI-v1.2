#!/usr/bin/env python
"""
Dashboard Test Suite - Generate sample data and test monitoring dashboard
Creates test documents, runs them through OCR, compliance checks, and risk scoring
"""

import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal
import random
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FinAI.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from core.models import Organization
from documents.models import Document, OCREvidence
from compliance.models import AuditFinding

User = get_user_model()


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_success(text):
    """Print success message"""
    print(f"✅ {text}")


def print_info(text):
    """Print info message"""
    print(f"ℹ️  {text}")


def create_test_organization():
    """Create or get test organization"""
    print_header("Step 1: Creating Test Organization")
    
    org, created = Organization.objects.get_or_create(
        name="Dashboard Test Org",
        defaults={
            'country': 'SA',
            'tax_id': '1234567890',
            'vat_rate': 15,
            'currency': 'SAR',
            'industry': 'Technology',
            'company_type': 'private',
        }
    )
    
    if created:
        print_success(f"Created organization: {org.name}")
    else:
        print_info(f"Using existing organization: {org.name}")
    
    return org


def create_test_user(org):
    """Create or get test user"""
    print_header("Step 2: Creating Test User")
    
    user, created = User.objects.get_or_create(
        email='dashboard_test@finai.local',
        defaults={
            'name': 'Dashboard Tester',
            'organization': org,
        }
    )
    
    if created:
        user.set_password('testpass123')
        user.save()
        print_success(f"Created user: {user.name}")
    else:
        print_info(f"Using existing user: {user.name}")
    
    return user


def generate_sample_invoice_image():
    """Generate a synthetic invoice image"""
    width, height = 800, 600
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)
    
    # Invoice template
    y_pos = 20
    draw.text((50, y_pos), "SAMPLE INVOICE", fill='black')
    y_pos += 40
    
    draw.text((50, y_pos), "Invoice #: INV-2026-001234", fill='black')
    y_pos += 30
    draw.text((50, y_pos), "Date: 2026-03-07", fill='black')
    y_pos += 30
    draw.text((50, y_pos), f"Amount: {random.randint(1000, 50000)} SAR", fill='black')
    y_pos += 30
    draw.text((50, y_pos), "VAT (15%): " + str(random.randint(100, 5000)) + " SAR", fill='black')
    y_pos += 40
    
    draw.text((50, y_pos), "Vendor: Al-Ahli Trading Co.", fill='black')
    y_pos += 30
    draw.text((50, y_pos), "VAT Number: 300123456789", fill='black')
    y_pos += 30
    draw.text((50, y_pos), "Description: Office Supplies", fill='black')
    
    # Add some table lines
    draw.line([(50, y_pos + 20), (750, y_pos + 20)], fill='black', width=2)
    
    return image


def create_sample_documents(org, user, count=5):
    """Create sample documents"""
    print_header(f"Step 3: Creating {count} Sample Documents")
    
    documents = []
    statuses = ['completed', 'pending', 'processing', 'completed', 'completed']
    types = ['invoice', 'receipt', 'invoice', 'bank_statement', 'invoice']
    
    for i in range(count):
        # Generate sample image
        image = generate_sample_invoice_image()
        image_bytes = BytesIO()
        image.save(image_bytes, format='PNG')
        image_bytes.seek(0)
        
        doc_dict = {
            'organization': org,
            'uploaded_by': user,
            'file_name': f"test_invoice_{i+1}.png",
            'file_type': '.png',
            'file_size': image_bytes.getbuffer().nbytes,
            'storage_key': f"test_invoice_{i+1}.png",
            'storage_url': f"/media/test_invoice_{i+1}.png",
            'document_type': types[i],
            'status': statuses[i],
            'language': 'mixed',
            'is_handwritten': False,
        }
        
        # Create document
        doc = Document.objects.create(**doc_dict)
        
        if doc.status == 'completed':
            doc.processed_at = timezone.now() - timedelta(hours=random.randint(0, 12))
            doc.save()
        
        documents.append(doc)
        print_success(f"Created document: {doc.file_name} ({doc.status})")
    
    return documents


def create_ocr_evidence(documents, user, org):
    """Create OCR evidence records"""
    print_header("Step 4: Creating OCR Evidence")
    
    ocr_records = []
    confidence_levels = ['high', 'high', 'medium', 'low', 'high']
    
    for doc, confidence_level in zip(documents, confidence_levels):
        if doc.status == 'completed':
            # Generate confidence score
            if confidence_level == 'high':
                confidence = random.randint(80, 99)
            elif confidence_level == 'medium':
                confidence = random.randint(60, 79)
            else:
                confidence = random.randint(40, 59)
            
            # Create OCR evidence
            evidence = OCREvidence.objects.create(
                document=doc,
                organization=org,
                raw_text=f"Invoice #{random.randint(1000, 9999)}\nDate: 2026-03-07\nAmount: {random.randint(1000, 50000)} SAR\nVAT: {random.randint(100, 5000)} SAR",
                text_ar="فاتورة توريد السلع",
                text_en="Goods Supply Invoice",
                confidence_score=confidence,
                confidence_level=confidence_level,
                page_count=random.randint(1, 3),
                word_count=random.randint(50, 200),
                ocr_engine='tesseract',
                ocr_version='5.3.0',
                language_used='ara+eng',
                is_handwritten=False,
                processing_time_ms=random.randint(500, 3000),
                extracted_invoice_number=f"INV-{random.randint(100000, 999999)}",
                extracted_vat_number="300123456789",
                extracted_total=Decimal(str(random.randint(5000, 100000))),
                extracted_tax=Decimal(str(random.randint(500, 10000))),
                structured_data_json={
                    'invoice_number': f"INV-{random.randint(100000, 999999)}",
                    'date': '2026-03-07',
                    'total_amount': random.randint(5000, 100000),
                    'tax_amount': random.randint(500, 10000),
                    'vendor_name': 'Al-Ahli Trading Co.',
                    'vat_number': '300123456789',
                },
                evidence_hash='abc123def456',
                extracted_by=user,
            )
            
            ocr_records.append(evidence)
            print_success(f"Created OCR evidence for {doc.file_name} (confidence: {confidence}%)")
    
    return ocr_records


def create_compliance_checks(documents, org, user):
    """Create compliance audit findings"""
    print_header("Step 5: Creating Audit Findings")
    
    findings = []
    finding_types = ['compliance', 'accuracy', 'completeness', 'documentation', 'internal_control']
    risk_levels = ['low', 'medium', 'high', 'critical', 'medium']
    
    for i, doc in enumerate(documents):
        finding_type = finding_types[i]
        risk_level = risk_levels[i]
        
        # Use unique finding number with timestamp to avoid conflicts
        finding_number = f"FIND-{timezone.now().timestamp()}-{i}"
        
        try:
            finding = AuditFinding.objects.create(
                organization=org,
                finding_number=finding_number,
                finding_type=finding_type,
                risk_level=risk_level,
                title_ar=f"نتيجة التدقيق - {finding_type.upper()}",
                title_en=f"Audit Finding - {finding_type.upper()}",
                description_ar=f"تفاصيل النتيجة: {finding_type}",
                description_en=f"Finding details: {finding_type}",
                impact_ar="تأثير النتيجة على الامتثال",
                impact_en="Impact of finding on compliance",
                recommendation_ar="يُوصى بإجراء فحص إضافي",
                recommendation_en="Additional review is recommended",
                related_entity_type='document',
                related_entity_id=doc.id,
                ai_confidence=random.randint(70, 99),
                identified_by=user,
                is_resolved=False,
            )
            
            findings.append(finding)
            print_success(f"Created finding: {finding_type} - Risk: {risk_level}")
        except Exception as e:
            print(f"⚠️  Skipped finding: {e}")
    
    return findings


def create_risk_assessments(documents, org):
    """Create risk assessment simulations (using audit findings)"""
    print_header("Step 6: Risk Assessment (via Findings)")
    
    risk_levels = ['critical', 'high', 'medium', 'low', 'low']
    
    for doc, risk_level in zip(documents, risk_levels):
        # Risk simulation based on finding risk level
        if risk_level == 'critical':
            risk_score = random.randint(80, 100)
        elif risk_level == 'high':
            risk_score = random.randint(60, 79)
        elif risk_level == 'medium':
            risk_score = random.randint(40, 59)
        else:
            risk_score = random.randint(0, 39)
        
        print_success(f"Risk assessment: {risk_level} (score: {risk_score}%)")
    
    return []


def display_dashboard_stats():
    """Display dashboard statistics"""
    print_header("Step 7: Dashboard Statistics")
    
    from core.monitoring import (
        DocumentProcessingMetrics,
        OCRPerformanceMetrics,
        ComplianceMetrics,
        SystemHealthMetrics,
    )
    
    # Get stats
    doc_stats = DocumentProcessingMetrics.get_processing_stats(days=7)
    queue_status = DocumentProcessingMetrics.get_processing_queue_status()
    ocr_stats = OCRPerformanceMetrics.get_ocr_stats(days=7)
    compliance_stats = ComplianceMetrics.get_compliance_stats(days=7)
    health = SystemHealthMetrics.get_system_health()
    
    print_info("📊 Document Processing Statistics")
    print(f"  Total Documents: {doc_stats['total_documents']}")
    print(f"  Success Rate: {doc_stats['success_rate']}%")
    print(f"  Avg Processing Time: {doc_stats['avg_processing_time_ms']}ms")
    
    print_info("⏳ Queue Status")
    print(f"  Pending: {queue_status['pending']}")
    print(f"  Processing: {queue_status['processing']}")
    print(f"  Completed: {queue_status['completed']}")
    print(f"  Failed: {queue_status['failed']}")
    
    print_info("🔍 OCR Performance")
    print(f"  Avg Confidence: {ocr_stats['average_confidence']}%")
    print(f"  High Confidence: {ocr_stats['high_confidence']}")
    print(f"  Medium Confidence: {ocr_stats['medium_confidence']}")
    print(f"  Low Confidence: {ocr_stats['low_confidence']}")
    
    print_info("⚖️  Compliance Checks")
    print(f"  Total Checks: {compliance_stats['total_checks']}")
    print(f"  Passed: {compliance_stats['passed_checks']}")
    print(f"  Failed: {compliance_stats['failed_checks']}")
    print(f"  Critical Issues: {compliance_stats['critical_issues']}")
    
    print_info(f"🏥 System Health: {health['status'].upper()}")
    if health['alerts']:
        for alert in health['alerts']:
            print(f"  ⚠️  {alert['message']}")


def main():
    """Run complete test suite"""
    print("\n" + "=" * 80)
    print("  FINAI DASHBOARD TEST SUITE")
    print("  Generating sample data for monitoring dashboard")
    print("=" * 80)
    
    try:
        # Create test data
        org = create_test_organization()
        user = create_test_user(org)
        documents = create_sample_documents(org, user, count=5)
        ocr_records = create_ocr_evidence(documents, user, org)
        compliance_records = create_compliance_checks(documents, org, user)
        risk_records = create_risk_assessments(documents, org)
        
        # Display results
        display_dashboard_stats()
        
        print_header("✨ Test Complete!")
        print_success("Dashboard is now populated with test data")
        print_info("Access the monitoring dashboard at:")
        print(f"  🌐 http://localhost:8000/monitoring/")
        print(f"  🔐 Login with: {user.email} / testpass123")
        print_info("Available dashboards:")
        print("  • Main Dashboard: http://localhost:8000/monitoring/")
        print("  • Processing Pipeline: http://localhost:8000/monitoring/pipeline/")
        print("  • OCR Metrics: http://localhost:8000/monitoring/ocr-metrics/")
        print("  • Compliance Report: http://localhost:8000/monitoring/compliance/")
        print("  • Risk Dashboard: http://localhost:8000/monitoring/risk/")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
