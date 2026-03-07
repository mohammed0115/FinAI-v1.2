#!/usr/bin/env python
"""
Production Testing & Validation Script for FinAI Pipeline
Tests invoice uploading, processing, and dashboard access
"""

import os
import sys
import django
import json
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FinAI.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from documents.models import ExtractedData, Document
from core.models import Organization
from core.pipeline_config import get_config

User = get_user_model()


def print_header(title):
    """Print section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def test_1_configuration():
    """Test 1: Verify Configuration"""
    print_header("TEST 1: Configuration Verification")
    
    config = get_config()
    
    print("\n✓ Configuration Modules Loaded:")
    for key in config:
        print(f"  - {key}")
    
    # Test environment variables
    print("\n✓ Environment Variables:")
    env_vars = [
        'OPENAI_API_KEY',
        'DEBUG',
        'ALLOWED_HOSTS',
        'DATABASE_NAME',
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            display = f"{value[:20]}..." if len(str(value)) > 20 else value
            print(f"  - {var}: {display}")
        else:
            print(f"  - {var}: NOT SET (optional)")
    
    return True


def test_2_pipeline_imports():
    """Test 2: Verify All Services Load"""
    print_header("TEST 2: Pipeline Services Import")
    
    services = []
    
    try:
        from core.openai_invoice_extraction_service import get_openai_extraction_service
        service = get_openai_extraction_service()
        services.append(("Phase 1: OpenAI Extraction", "OK"))
    except Exception as e:
        services.append(("Phase 1: OpenAI Extraction", f"FAIL: {e}"))
    
    try:
        from core.data_normalization_service import DataNormalizationValidator
        services.append(("Phase 2: Normalization", "OK"))
    except Exception as e:
        services.append(("Phase 2: Normalization", f"FAIL: {e}"))
    
    try:
        from core.compliance_findings_service import ComplianceCheckService
        services.append(("Phase 3: Compliance", "OK"))
    except Exception as e:
        services.append(("Phase 3: Compliance", f"FAIL: {e}"))
    
    try:
        from core.cross_document_service import (
            DuplicateDetectionService, AnomalyDetectionService, VendorRiskService
        )
        services.append(("Phase 4: Cross-Document", "OK"))
    except Exception as e:
        services.append(("Phase 4: Cross-Document", f"FAIL: {e}"))
    
    try:
        from core.financial_intelligence_service import (
            CashFlowForecastService, SpendIntelligenceService, FinancialNarrativeService
        )
        services.append(("Phase 5: Financial Intelligence", "OK"))
    except Exception as e:
        services.append(("Phase 5: Financial Intelligence", f"FAIL: {e}"))
    
    try:
        from core.invoice_processing_pipeline import get_pipeline_manager
        services.append(("Pipeline Orchestrator", "OK"))
    except Exception as e:
        services.append(("Pipeline Orchestrator", f"FAIL: {e}"))
    
    print("\n✓ Service Load Status:")
    all_ok = True
    for service, status in services:
        icon = "✓" if status == "OK" else "✗"
        print(f"  {icon} {service}: {status}")
        if status != "OK":
            all_ok = False
    
    return all_ok


def test_3_database():
    """Test 3: Verify Database Access"""
    print_header("TEST 3: Database Access")
    
    try:
        # Count organizations
        org_count = Organization.objects.count()
        print(f"✓ Organizations in database: {org_count}")
        
        if org_count == 0:
            print("  ⚠️  No organizations found. Create one before processing invoices.")
        else:
            org = Organization.objects.first()
            print(f"  - Sample: {org.name}")
        
        # Count users
        user_count = User.objects.count()
        print(f"✓ Users in database: {user_count}")
        
        if user_count > 0:
            user = User.objects.first()
            print(f"  - Sample: {user.email}")
        
        # Count extracted data
        extracted_count = ExtractedData.objects.count()
        print(f"✓ Extracted invoices: {extracted_count}")
        
        if extracted_count > 0:
            sample = ExtractedData.objects.first()
            print(f"  - Sample invoice: {sample.invoice_number}")
            print(f"  - Risk score: {sample.risk_score}/100")
            print(f"  - Valid: {sample.is_valid}")
        
        return True
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False


def test_4_dashboard():
    """Test 4: Verify Dashboard View"""
    print_header("TEST 4: Dashboard View Access")
    
    try:
        user = User.objects.first()
        if not user:
            print("✗ No test user found")
            return False
        
        client = Client()
        client.force_login(user)
        
        # Test dashboard URL
        response = client.get('/api/documents/dashboard/')
        
        if response.status_code == 200:
            print("✓ Dashboard view is accessible (HTTP 200)")
            
            # Check context data
            if 'total_invoices' in response.context:
                print(f"  - Total invoices: {response.context['total_invoices']}")
                print(f"  - High risk count: {response.context['high_risk_count']}")
                print(f"  - Validation rate: {response.context['validation_rate']:.1f}%")
            
            return True
        else:
            print(f"✗ Dashboard returned HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Dashboard view error: {e}")
        return False


def test_5_sample_invoice_processing():
    """Test 5: Process Sample Invoice Data"""
    print_header("TEST 5: Sample Invoice Processing")
    
    try:
        from core.data_normalization_service import DataNormalizationValidator
        
        # Create sample extracted data
        sample_data = {
            'vendor_name': 'Test Vendor',
            'invoice_number': 'TEST-001',
            'issue_date': '2024-03-06',
            'due_date': '2024-04-05',
            'subtotal': '10000.00',
            'tax_amount': '1500.00',
            'total_amount': '11500.00',
            'currency': 'SAR',
            'items': [
                {
                    'description': 'Test Item',
                    'quantity': 10,
                    'unit_price': '1000.00',
                    'line_total': '10000.00'
                }
            ]
        }
        
        # Test normalization
        normalized = DataNormalizationValidator.normalize_invoice_data(sample_data)
        print("✓ Normalization completed")
        print(f"  - Vendor: {normalized.get('vendor_name')}")
        print(f"  - Amount: {normalized.get('total_amount')} {normalized.get('currency')}")
        
        # Test validation
        is_valid, errors, warnings = DataNormalizationValidator.validate_invoice_data(normalized)
        print("✓ Validation completed")
        print(f"  - Valid: {is_valid}")
        print(f"  - Errors: {len(errors)}")
        print(f"  - Warnings: {len(warnings)}")
        
        # Test compliance
        from core.compliance_findings_service import ComplianceCheckService
        
        checks = ComplianceCheckService.perform_compliance_checks(normalized)
        print("✓ Compliance checks completed")
        
        risk_score = ComplianceCheckService.calculate_overall_risk_score(checks)
        print(f"  - Risk score: {risk_score}/100")
        print(f"  - Risk level: {ComplianceCheckService.get_risk_level(risk_score)}")
        
        return True
    except Exception as e:
        print(f"✗ Sample processing error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_6_performance_logging():
    """Test 6: Verify Performance Monitoring"""
    print_header("TEST 6: Performance Monitoring Setup")
    
    try:
        from core.performance_monitor import PerformanceMetrics, track_performance
        
        # Test performance tracking
        @track_performance("test_function")
        def sample_function():
            import time
            time.sleep(0.1)
            return "done"
        
        # Run test function
        result = sample_function()
        print("✓ Performance tracking works")
        
        # Get stats
        stats = PerformanceMetrics.get_stats("test_function")
        if stats:
            print(f"  - Last execution: {stats['last']:.3f}s")
            print(f"  - Average: {stats['avg']:.3f}s")
        
        print("✓ Performance monitoring configured")
        return True
    except Exception as e:
        print(f"✗ Performance monitoring error: {e}")
        return False


def run_all_tests():
    """Run all tests and generate report"""
    print("\n" + "="*70)
    print("FINAI PRODUCTION READINESS TEST SUITE")
    print("="*70)
    
    tests = [
        ("Configuration", test_1_configuration),
        ("Pipeline Services", test_2_pipeline_imports),
        ("Database Access", test_3_database),
        ("Dashboard View", test_4_dashboard),
        ("Invoice Processing", test_5_sample_invoice_processing),
        ("Performance Monitoring", test_6_performance_logging),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, "PASS" if result else "FAIL"))
        except Exception as e:
            print(f"\n✗ Test exception: {e}")
            results.append((test_name, "ERROR"))
    
    # Print summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for _, status in results if status == "PASS")
    total = len(results)
    
    print(f"\nResults: {passed}/{total} tests passed\n")
    
    for test_name, status in results:
        icon = "✓" if status == "PASS" else ("✗" if status == "FAIL" else "⚠")
        print(f"  {icon} {test_name}: {status}")
    
    print("\n" + "="*70)
    
    if passed == total:
        print("✓ ALL TESTS PASSED - SYSTEM READY FOR PRODUCTION")
        return 0
    else:
        print("✗ SOME TESTS FAILED - PLEASE REVIEW ERRORS ABOVE")
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
