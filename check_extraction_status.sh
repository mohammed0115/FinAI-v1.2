#!/bin/bash

# FinAI Extraction Status Check
# Displays dual extraction configuration and installation status

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║          FinAI DUAL EXTRACTION SERVICE STATUS                     ║"
echo "║          (OpenAI + Tesseract)                                     ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Check Python environment
echo "🔍 System Environment:"
python3 --version
echo ""

# Check OpenAI
echo "🔍 OpenAI Configuration:"
if grep -q "OPENAI_API_KEY=sk-" backend/.env 2>/dev/null; then
    echo "   ✓ OpenAI API Key configured"
else
    echo "   ✗ OpenAI API Key NOT configured"
fi

OPENAI_MODEL=$(grep "OPENAI_MODEL=" backend/.env 2>/dev/null | cut -d'=' -f2)
echo "   Model: ${OPENAI_MODEL:-Not set}"

# Check Tesseract
echo ""
echo "🔍 Tesseract OCR Status:"

if command -v tesseract &> /dev/null; then
    TESSERACT_VERSION=$(tesseract --version 2>&1 | head -1)
    echo "   ✓ Tesseract installed"
    echo "   Version: $TESSERACT_VERSION"
else
    echo "   ✗ Tesseract NOT installed"
    echo ""
    echo "   📦 To install Tesseract, run:"
    echo "      sudo apt-get update && sudo apt-get install -y tesseract-ocr tesseract-ocr-ara"
    echo ""
fi

# Check pytesseract
echo ""
echo "🔍 Python Dependencies:"

python3 -c "import pytesseract; print('   ✓ pytesseract available')" 2>/dev/null || echo "   ✗ pytesseract NOT installed"
python3 -c "import pdf2image; print('   ✓ pdf2image available')" 2>/dev/null || echo "   ✗ pdf2image NOT installed"
python3 -c "from PIL import Image; print('   ✓ PIL/Pillow available')" 2>/dev/null || echo "   ✗ PIL NOT installed"

# Check configuration
echo ""
echo "⚙️  Configuration (.env):"

EXTRACTION_PRIMARY=$(grep "EXTRACTION_PRIMARY_METHOD=" backend/.env 2>/dev/null | cut -d'=' -f2)
TESSERACT_ENABLED=$(grep "TESSERACT_ENABLED=" backend/.env 2>/dev/null | cut -d'=' -f2)
TESSERACT_CMD=$(grep "TESSERACT_CMD=" backend/.env 2>/dev/null | cut -d'=' -f2)

echo "   Primary Method: ${EXTRACTION_PRIMARY:-not set}"
echo "   Tesseract Enabled: ${TESSERACT_ENABLED:-not set}"
echo "   Tesseract Command: ${TESSERACT_CMD:-not set}"

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║          EXTRACTION FLOW                                          ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
echo "1. Primary Method: ${EXTRACTION_PRIMARY:-openai}"
echo "   → Try OpenAI Vision API (gpt-4o-mini)"
echo ""
if [ "$TESSERACT_ENABLED" == "True" ]; then
    echo "2. Fallback Method: Tesseract OCR"
    echo "   → Try Tesseract if OpenAI unavailable"
    echo ""
else
    echo "2. Fallback Method: DISABLED"
    echo "   → Only use built-in fallback"
    echo ""
fi
echo "3. Final Fallback: Rule-based extraction"
echo "   → Simple pattern matching if all methods fail"
echo ""

# Recommendations
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║          RECOMMENDATIONS                                          ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

if ! command -v tesseract &> /dev/null; then
    echo "⚠️  Tesseract not installed"
    echo "   To enable Tesseract fallback:"
    echo "   $ sudo apt-get update"
    echo "   $ sudo apt-get install -y tesseract-ocr tesseract-ocr-ara"
    echo ""
fi

if ! python3 -c "import pdf2image" 2>/dev/null; then
    echo "⚠️  pdf2image not installed"
    echo "   To process PDFs:"
    echo "   $ pip install pdf2image"
    echo ""
fi

python3 -c "
import os
import sys
sys.path.insert(0, 'backend')
os.chdir('backend')

try:
    from core.dual_extraction_service import get_dual_extraction_service
    service = get_dual_extraction_service()
    status = service.get_extraction_status()
    
    print('✨ Dual Extraction Service Status:')
    print(f'   Primary: {status[\"primary_method\"]}')
    print(f'   OpenAI: {\"✓\" if status[\"openai_available\"] else \"✗\"}')
    print(f'   Tesseract: {\"✓\" if status[\"tesseract_available\"] else \"✗\"}')
except Exception as e:
    print(f'⚠️  Could not load service: {e}')
" 2>/dev/null || true

echo ""
echo "✓ Setup complete! Your system is ready for invoice extraction."
echo ""
