#!/usr/bin/env python3
"""
Test script for OpenAI Invoice Extraction Pipeline

This script tests:
1. OpenAI invoice service initialization
2. Invoice schema validation
3. Confidence calculation
4. OCR service integration
5. Document view integration
"""

import os
import sys
import json
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_path))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FinAI.settings')

import django
django.setup()

from core.openai_invoice_service import OpenAIInvoiceService, get_openai_invoice_service
from documents.ocr_service import document_ocr_service, OpenAIVisionOCRProvider


def test_openai_service_initialization():
    """Test that OpenAI service initializes correctly"""
    print("\n=== Test 1: OpenAI Service Initialization ===")
    service = get_openai_invoice_service()
    print(f"✓ OpenAI service initialized")
    print(f"  API Key configured: {service.is_available()}")
    print(f"  Model: {service.MODEL}")
    print(f"  Max image size: {service.MAX_IMAGE_SIZE / (1024*1024):.1f} MB")
    print(f"  Supported formats: {service.SUPPORTED_FORMATS}")
    return True


def test_schema_validation():
    """Test invoice schema validation"""
    print("\n=== Test 2: Schema Validation ===")
    service = OpenAIInvoiceService()
    
    # Test with incomplete data
    test_data = {
        "invoice_number": "INV-001",
        "vendor": {"name": "ACME Corp"},
        "customer": {"name": "John Doe"},
        "total_amount": "1000.00"
    }
    
    validated = service._validate_schema(test_data)
    print(f"✓ Schema validated")
    print(f"  Invoice #: {validated['invoice_number']}")
    print(f"  Vendor: {validated['vendor']['name']}")
    print(f"  Total: {validated['total_amount']}")
    print(f"  Currency: {validated['currency']} (filled with empty string as expected)")
    
    # Check all required fields exist
    required_fields = ['invoice_number', 'issue_date', 'due_date', 'vendor', 
                       'customer', 'items', 'total_amount', 'currency']
    for field in required_fields:
        assert field in validated, f"Missing field: {field}"
    
    print(f"✓ All required fields present")
    return True


def test_confidence_calculation():
    """Test confidence scoring"""
    print("\n=== Test 3: Confidence Calculation ===")
    service = OpenAIInvoiceService()
    
    # Full data
    full_data = {
        "invoice_number": "INV-001",
        "issue_date": "2024-01-15",
        "vendor": {"name": "ACME Corp", "address": "123 Main St"},
        "customer": {"name": "John Doe", "address": "456 Oak Ave"},
        "items": [{"product": "Widget", "quantity": "10"}],
        "total_amount": "1000.00"
    }
    
    confidence_full = service._calculate_confidence(full_data)
    print(f"✓ Full data confidence: {confidence_full}%")
    
    # Minimal data
    minimal_data = {
        "invoice_number": "INV-001",
        "issue_date": "",
        "vendor": {"name": ""},
        "customer": {"name": ""},
        "items": [],
        "total_amount": ""
    }
    
    confidence_minimal = service._calculate_confidence(minimal_data)
    print(f"✓ Minimal data confidence: {confidence_minimal}%")
    
    # Confidence should be higher for full data
    assert confidence_full > confidence_minimal, "Confidence calculation logic error"
    print(f"✓ Confidence increases with data completeness")
    return True


def test_ocr_service_integration():
    """Test OCR service integration"""
    print("\n=== Test 4: OCR Service Integration ===")
    
    # Check that extract_invoice_with_openai method exists
    assert hasattr(document_ocr_service, 'extract_invoice_with_openai'), \
        "extract_invoice_with_openai method not found"
    print(f"✓ extract_invoice_with_openai method exists")
    
    # Check that OpenAIVisionOCRProvider exists
    provider = OpenAIVisionOCRProvider()
    assert provider.service is not None, "OpenAI service not initialized in provider"
    print(f"✓ OpenAIVisionOCRProvider initialized")
    
    # Test unsupported format handling
    result = document_ocr_service.extract_invoice_with_openai(
        file_path="/nonexistent/file.pdf",
        file_type=".pdf"
    )
    assert not result['success'], "Should fail for PDF"
    assert "not supported" in result['error'].lower() or "pdf" in result['error'].lower(), \
        "Should indicate unsupported format"
    print(f"✓ Returns error for unsupported formats (PDF)")
    
    return True


def test_error_handling():
    """Test error handling"""
    print("\n=== Test 5: Error Handling ===")
    service = get_openai_invoice_service()
    
    # Non-existent file
    result = service.extract_invoice_from_file("/nonexistent/file.jpg")
    assert not result['success'], "Should handle missing file"
    assert "not found" in result['error'].lower(), "Should indicate file not found"
    print(f"✓ Handles missing files gracefully")
    
    # Invalid format
    result = document_ocr_service.extract_invoice_with_openai(
        file_path="/nonexistent/file.txt",
        file_type=".txt"
    )
    assert not result['success'], "Should handle invalid format"
    print(f"✓ Handles invalid formats gracefully")
    
    return True


def test_model_schema():
    """Test that ExtractedData model can store extracted data"""
    print("\n=== Test 6: ExtractedData Model Compatibility ===")
    from documents.models import ExtractedData, Document
    from core.models import Organization, User
    from decimal import Decimal
    from datetime import datetime, timedelta
    
    try:
        # Get or create a test organization and user
        org, _ = Organization.objects.get_or_create(
            name='Test Org',
            defaults={'gstin': '00000000000000'}
        )
        
        user, _ = User.objects.get_or_create(
            email='test@example.com',
            defaults={
                'name': 'Test User',
                'role': 'accountant',
                'organization': org
            }
        )
        
        # Create a test document
        doc, _ = Document.objects.get_or_create(
            file_name='test_invoice.jpg',
            organization=org,
            uploaded_by=user,
            defaults={
                'file_type': 'image/jpeg',
                'file_size': 1000,
                'storage_key': 'test/key',
                'storage_url': 'test/url',
                'document_type': 'invoice',
                'status': 'completed'
            }
        )
        
        # Try to create ExtractedData with all fields
        extracted, created = ExtractedData.objects.get_or_create(
            document=doc,
            organization=org,
            defaults={
                'vendor_name': 'ACME Corp',
                'customer_name': 'John Doe',
                'invoice_number': 'INV-001',
                'invoice_date': datetime.now(),
                'due_date': datetime.now() + timedelta(days=30),
                'total_amount': Decimal('1000.00'),
                'currency': 'SAR',
                'items_json': [
                    {
                        'product': 'Widget',
                        'quantity': '10',
                        'unit_price': '100.00',
                        'total': '1000.00'
                    }
                ],
                'confidence': 85
            }
        )
        
        print(f"✓ ExtractedData model accepts invoice data")
        print(f"  Invoice #: {extracted.invoice_number}")
        print(f"  Vendor: {extracted.vendor_name}")
        print(f"  Total: {extracted.total_amount}")
        print(f"  Confidence: {extracted.confidence}%")
        print(f"  Items: {len(extracted.items_json)} line items")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing ExtractedData model: {e}")
        return False


def test_views_integration():
    """Test that views can call the extraction methods"""
    print("\n=== Test 7: Views Integration ===")
    from documents.views import DocumentViewSet
    
    # Check that _extract_invoice_data method exists
    assert hasattr(DocumentViewSet, '_extract_invoice_data'), \
        "_extract_invoice_data method not found in DocumentViewSet"
    print(f"✓ DocumentViewSet has _extract_invoice_data method")
    
    # Check that it's properly defined
    import inspect
    sig = inspect.signature(DocumentViewSet._extract_invoice_data)
    params = list(sig.parameters.keys())
    assert 'file_path' in params, "Missing file_path parameter"
    assert 'document' in params, "Missing document parameter"
    print(f"✓ Method has correct parameters: {params}")
    
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("OpenAI Invoice Extraction Pipeline - Test Suite")
    print("=" * 60)
    
    tests = [
        ("Service Initialization", test_openai_service_initialization),
        ("Schema Validation", test_schema_validation),
        ("Confidence Calculation", test_confidence_calculation),
        ("OCR Service Integration", test_ocr_service_integration),
        ("Error Handling", test_error_handling),
        ("Model Schema", test_model_schema),
        ("Views Integration", test_views_integration),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✓ PASSED: {test_name}")
            else:
                failed += 1
                print(f"✗ FAILED: {test_name}")
        except AssertionError as e:
            failed += 1
            print(f"✗ FAILED: {test_name}")
            print(f"  Reason: {e}")
        except Exception as e:
            failed += 1
            print(f"✗ ERROR: {test_name}")
            print(f"  Exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print(f"✗ {failed} test(s) failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
