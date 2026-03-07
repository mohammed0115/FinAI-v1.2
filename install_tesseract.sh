#!/bin/bash

# FinAI Tesseract Installation Script
# Installs Tesseract OCR and all dependencies for dual extraction

set -e  # Exit on error

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║     FinAI Tesseract OCR Installation                              ║"
echo "║     (Enables Tesseract fallback extraction)                       ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Detect Linux flavor
        if command -v apt-get &> /dev/null; then
            echo "ubuntu"
        elif command -v yum &> /dev/null; then
            echo "centos"
        elif command -v pacman &> /dev/null; then
            echo "arch"
        else
            echo "linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    else
        echo "unknown"
    fi
}

OS=$(detect_os)
echo "📦 Detected OS: $OS"
echo ""

# Install based on OS
case $OS in
    ubuntu)
        echo "Installing Tesseract for Ubuntu/Debian..."
        echo ""
        echo "This will:"
        echo "  1. Update package lists"
        echo "  2. Install tesseract-ocr (English & Arabic)"
        echo "  3. Install development libraries"
        echo ""
        echo "Requires: sudo password"
        echo "---"
        echo ""
        
        sudo apt-get update
        
        sudo apt-get install -y \
            tesseract-ocr \
            libtesseract-dev \
            tesseract-ocr-ara \
            tesseract-ocr-eng
        
        echo ""
        echo "✓ Installation complete!"
        tesseract --version
        ;;
        
    centos)
        echo "Installing Tesseract for CentOS/RHEL..."
        
        sudo yum install -y \
            tesseract \
            tesseract-devel \
            tesseract-langpack-ara \
            tesseract-langpack-eng
        
        echo ""
        echo "✓ Installation complete!"
        tesseract --version
        ;;
        
    arch)
        echo "Installing Tesseract for Arch Linux..."
        
        sudo pacman -S --noconfirm \
            tesseract \
            tesseract-data-ara \
            tesseract-data-eng
        
        echo ""
        echo "✓ Installation complete!"
        tesseract --version
        ;;
        
    macos)
        echo "Installing Tesseract for macOS..."
        echo ""
        echo "Checking for Homebrew..."
        
        if ! command -v brew &> /dev/null; then
            echo "❌ Homebrew not found. Install from: https://brew.sh"
            exit 1
        fi
        
        brew install tesseract --with-all-languages
        
        echo ""
        echo "✓ Installation complete!"
        tesseract --version
        ;;
        
    *)
        echo "❌ Unsupported OS. Please install Tesseract manually."
        echo ""
        echo "Installation guides:"
        echo "  Ubuntu/Debian: sudo apt-get install tesseract-ocr"
        echo "  CentOS/RHEL:   sudo yum install tesseract"
        echo "  macOS:         brew install tesseract"
        echo "  Windows:       https://github.com/UB-Mannheim/tesseract/wiki"
        exit 1
        ;;
esac

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                   POST-INSTALLATION SETUP                         ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Verify installation
echo "✓ Verifying installation..."
if command -v tesseract &> /dev/null; then
    echo "  ✓ Tesseract command found"
    TESSERACT_PATH=$(which tesseract)
    echo "  Path: $TESSERACT_PATH"
else
    echo "  ✗ Tesseract command not found"
    exit 1
fi

# Check languages
echo ""
echo "✓ Available languages:"
tesseract --list-langs 2>&1 | head -10

echo ""
echo "✓ Language packs installed:"
if tesseract --list-langs 2>&1 | grep -q ara; then
    echo "  ✓ Arabic (ara)"
fi
if tesseract --list-langs 2>&1 | grep -q eng; then
    echo "  ✓ English (eng)"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                   CONFIGURATION                                   ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Check if .env exists
if [ -f "backend/.env" ]; then
    echo "✓ .env file exists"
    
    if grep -q "TESSERACT_ENABLED=True" backend/.env; then
        echo "✓ TESSERACT_ENABLED already set to True"
    fi
    
    if grep -q "EXTRACTION_PRIMARY_METHOD=openai" backend/.env; then
        echo "✓ Primary extraction method: OpenAI (with Tesseract fallback)"
    fi
else
    echo "⚠️  .env file not found"
    echo "   Location should be: backend/.env"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                   VERIFICATION                                    ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Run extraction status check if script exists
if [ -f "check_extraction_status.sh" ]; then
    echo "Running extraction status check..."
    echo ""
    bash check_extraction_status.sh
else
    echo "✓ To verify setup, run:"
    echo "  bash check_extraction_status.sh"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                   ✨ READY FOR USE                                ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Your FinAI system now supports:"
echo "  1. OpenAI Vision API (primary)"
echo "  2. Tesseract OCR (fallback)"
echo "  3. Rule-based extraction (final fallback)"
echo ""
echo "To test:"
echo "  1. Start the server: python manage.py runserver"
echo "  2. Upload an invoice: http://localhost:8000"
echo "  3. Check extraction method used"
echo ""
echo "Documentation: DUAL_EXTRACTION_SETUP.md"
echo ""
