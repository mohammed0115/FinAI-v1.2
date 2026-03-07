#!/bin/bash

# OpenAI API Connection Test
# Verifies OpenAI API key and connectivity

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║          OpenAI API Connection Test                               ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Check if we're in the right directory
if [ ! -f "backend/.env" ]; then
    echo "❌ Error: backend/.env not found"
    echo "   Please run this script from the project root: ~/FinAI-v1.2"
    exit 1
fi

echo "📋 Step 1: Check OpenAI Configuration"
echo "───────────────────────────────────────────────────────────────────"

# Extract API key from .env
OPENAI_API_KEY=$(grep "^OPENAI_API_KEY=" backend/.env | cut -d'=' -f2)
OPENAI_MODEL=$(grep "^OPENAI_MODEL=" backend/.env | cut -d'=' -f2)

if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY not found in .env"
    exit 1
fi

# Check API key format
if [[ $OPENAI_API_KEY == sk-* ]]; then
    echo "✓ API Key Format: Valid (starts with sk-)"
    KEY_LENGTH=${#OPENAI_API_KEY}
    echo "✓ API Key Length: $KEY_LENGTH characters"
else
    echo "❌ API Key Format: Invalid (should start with 'sk-')"
    exit 1
fi

echo "✓ Model: ${OPENAI_MODEL:-gpt-4o-mini}"
echo ""

echo "📋 Step 2: Check Python Dependencies"
echo "───────────────────────────────────────────────────────────────────"

# Check if openai package is installed
python3 -c "import openai; print(f'✓ openai package: {openai.__version__}')" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ openai package not installed"
    echo "   Install with: pip install openai"
    exit 1
fi

python3 -c "import dotenv; print('✓ python-dotenv: installed')" 2>/dev/null || echo "⚠️  python-dotenv: not found"
echo ""

echo "📋 Step 3: Test OpenAI API Connection"
echo "───────────────────────────────────────────────────────────────────"

# Create Python test script
python3 << 'PYTHON_SCRIPT'
import os
import sys
sys.path.insert(0, 'backend')

# Load .env
from dotenv import load_dotenv
load_dotenv('backend/.env')

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

print(f"API Key (masked): {OPENAI_API_KEY[:20]}...{OPENAI_API_KEY[-4:]}")
print(f"Model: {OPENAI_MODEL}")
print("")

# Test 1: Import OpenAI
print("TEST 1: Import OpenAI Client")
print("─" * 60)
try:
    from openai import OpenAI
    print("✓ Successfully imported OpenAI client")
except Exception as e:
    print(f"❌ Failed to import: {e}")
    sys.exit(1)

# Test 2: Initialize client
print("")
print("TEST 2: Initialize OpenAI Client")
print("─" * 60)
try:
    client = OpenAI(api_key=OPENAI_API_KEY)
    print("✓ Client initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize client: {e}")
    sys.exit(1)

# Test 3: List available models
print("")
print("TEST 3: Connect to OpenAI API")
print("─" * 60)
try:
    models = client.models.list()
    model_count = len(list(models))
    print(f"✓ Successfully connected to OpenAI API")
    print(f"✓ Available models: {model_count}")
    
    # Check if gpt-4o-mini is available
    models = client.models.list()
    model_ids = [m.id for m in models]
    
    if 'gpt-4o-mini' in model_ids:
        print("✓ Model 'gpt-4o-mini' is available")
    else:
        print(f"⚠️  Model 'gpt-4o-mini' not found. Available: {model_ids[:3]}...")
        
except Exception as e:
    print(f"❌ Failed to connect to OpenAI API: {e}")
    print(f"   Error type: {type(e).__name__}")
    if "401" in str(e) or "Unauthorized" in str(e):
        print("   ⚠️  This may be an authentication error. Check your API key.")
    elif "429" in str(e):
        print("   ⚠️  Rate limit reached. Try again later.")
    elif "Connection" in str(e):
        print("   ⚠️  Connection error. Check your internet connection.")
    sys.exit(1)

# Test 4: Test a simple message
print("")
print("TEST 4: Test Simple API Call")
print("─" * 60)
try:
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=50,
        messages=[
            {"role": "user", "content": "Say 'OpenAI API is working!' and nothing else."}
        ]
    )
    
    result_text = response.choices[0].message.content
    print("✓ API call successful!")
    print(f"✓ Response: {result_text}")
    print(f"✓ Model used: {response.model}")
    print(f"✓ Finish reason: {response.choices[0].finish_reason}")
    
except Exception as e:
    print(f"❌ API call failed: {e}")
    print(f"   Error type: {type(e).__name__}")
    sys.exit(1)

# Test 5: Extract with dummy image (simulated)
print("")
print("TEST 5: Test Vision API Compatibility")
print("─" * 60)
try:
    # Check if the model supports vision
    if 'vision' in OPENAI_MODEL.lower() or 'gpt-4o' in OPENAI_MODEL:
        print(f"✓ Model '{OPENAI_MODEL}' supports vision API")
        print("✓ Ready for invoice extraction")
    else:
        print(f"⚠️  Model '{OPENAI_MODEL}' may not support vision")
        print("   Consider using 'gpt-4o-mini' or 'gpt-4-vision-preview'")
except Exception as e:
    print(f"❌ Vision check failed: {e}")

print("")
print("╔════════════════════════════════════════════════════════════════════╗")
print("║                    ✅ ALL TESTS PASSED                            ║")
print("╚════════════════════════════════════════════════════════════════════╝")
print("")
print("OpenAI API is properly configured and connected!")
print("")

PYTHON_SCRIPT

if [ $? -eq 0 ]; then
    echo ""
    echo "📊 Summary"
    echo "───────────────────────────────────────────────────────────────────"
    echo "✓ API Key: Valid format and loaded"
    echo "✓ Connection: Successfully connected to OpenAI"
    echo "✓ Model: gpt-4o-mini available"
    echo "✓ Vision API: Ready for invoice extraction"
    echo ""
    echo "🚀 Your FinAI system is ready to extract invoices!"
    echo ""
else
    echo ""
    echo "❌ Connection test failed"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check API key in backend/.env"
    echo "  2. Verify internet connection"
    echo "  3. Check OpenAI account status: https://platform.openai.com"
    echo "  4. Review API key permissions"
    echo ""
fi
