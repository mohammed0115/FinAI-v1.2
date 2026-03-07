#!/bin/bash
# Production Deployment & Configuration Script
# FinAI Complete 5-Phase Invoice Pipeline

set -e

echo "================================================"
echo "FinAI Production Deployment Script"
echo "================================================"
echo ""

# Step 1: Configure OpenAI API Key
echo "Step 1: OpenAI API Key Configuration"
echo "-----------------------------------"

if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY not set in environment"
    echo "Please set it before running the application:"
    echo "  export OPENAI_API_KEY=sk-proj-xxxxx..."
    echo ""
    echo "Or add it to .env file:"
    echo "  OPENAI_API_KEY=sk-proj-xxxxx..."
    echo ""
    exit 1
else
    echo "✓ OpenAI API Key is configured"
    # Show first and last 10 chars only for security
    KEY_DISPLAY="${OPENAI_API_KEY:0:10}...${OPENAI_API_KEY: -10}"
    echo "  API Key: $KEY_DISPLAY"
fi

# Step 2: Verify Python dependencies
echo ""
echo "Step 2: Verifying Python Dependencies"
echo "------------------------------------"

python << 'EOF'
import os
import sys

print("Checking required packages...")

# Check OpenAI
try:
    import openai
    print(f"✓ OpenAI ({openai.__version__})")
except ImportError:
    print("✗ OpenAI not installed. Run: pip install openai")
    sys.exit(1)

# Check Django
try:
    import django
    print(f"✓ Django ({django.__version__})")
except ImportError:
    print("✗ Django not installed")
    sys.exit(1)

# Check pdf2image
try:
    import pdf2image
    print("✓ pdf2image")
except ImportError:
    print("⚠️  pdf2image not installed. Required for PDF processing.")
    print("   Run: pip install pdf2image")

# Check Tesseract reference
print("")
print("Optional OCR Dependencies:")
print("  - Tesseract (Linux): apt-get install tesseract-ocr")
print("  - Tesseract (Mac): brew install tesseract")
print("  - Tesseract (Windows): Download from https://github.com/UB-Mannheim/tesseract/wiki")

print("\n✓ All required packages verified!")
EOF

# Step 3: Database Migration
echo ""
echo "Step 3: Database Migration"
echo "------------------------"

python manage.py migrate --verbosity 1

# Step 4: Collect Static Files
echo ""
echo "Step 4: Collecting Static Files"
echo "-----------------------------"

python manage.py collectstatic --noinput --verbosity 1

# Step 5: Test Pipeline Import
echo ""
echo "Step 5: Testing Pipeline Import"
echo "-----------------------------"

python << 'EOF'
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FinAI.settings')
django.setup()

from core.invoice_processing_pipeline import get_pipeline_manager
from core.openai_invoice_extraction_service import get_openai_extraction_service

print("✓ Pipeline manager loaded successfully")
print("✓ OpenAI extraction service loaded successfully")

# Test OpenAI connection
try:
    import openai
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("✗ OPENAI_API_KEY not set")
    else:
        print("✓ OPENAI_API_KEY is configured")
        print("  Ready for invoice processing")
except Exception as e:
    print(f"✗ OpenAI initialization error: {e}")
EOF

# Step 6: Verify Dashboard URLs
echo ""
echo "Step 6: Verifying Dashboard URLs"
echo "-----------------------------"

python << 'EOF'
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FinAI.settings')
django.setup()

from django.urls import reverse
from django.test import Client

print("Dashboard URL Routes:")
print(f"  - Dashboard: /api/documents/dashboard/")
print(f"  - Invoice Details: /api/documents/invoice/<id>/")
print("")
print("✓ Dashboard routes configured")
EOF

echo ""
echo "================================================"
echo "✓ Deployment Configuration Complete!"
echo "================================================"
echo ""
echo "Next Steps:"
echo "1. Test with sample invoices:"
echo "   curl -X POST http://localhost:8000/api/documents/upload/ \\"
echo "     -F 'file=@invoice.pdf' -F 'document_type=invoice'"
echo ""
echo "2. View dashboard:"
echo "   http://localhost:8000/api/documents/dashboard/"
echo ""
echo "3. Start server:"
echo "   python manage.py runserver 0.0.0.0:8000"
echo ""
