# FinAI OpenAI Integration - Quick Start Guide

## 🚀 Getting Started (5 Minutes)

### Step 1: Set Up Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your OpenAI API key
# Get it from: https://platform.openai.com/account/api-keys
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
```

### Step 2: Verify Setup

```bash
cd backend

# Test imports
python manage.py shell << 'EOF'
from core.ai import OCRProcessor, StructuredExtractor, ComplianceExplainer
print("✅ All AI modules loaded successfully!")
EOF
```

### Step 3: Upload & Process a Document

**Using Python/Django:**
```python
from core.ai import OCRProcessor, StructuredExtractor
from decimal import Decimal

# OCR: Extract text from document
processor = OCRProcessor()
ocr_result = processor.process('/path/to/invoice.pdf', language_hint='ar')

print(f"Extracted text length: {len(ocr_result['extracted_text'])} chars")
print(f"Language detected: {ocr_result['language']}")
print(f"Confidence: {ocr_result['confidence']:.0%}")
print(f"Method used: {ocr_result['method']}")

# Structured Extraction: Parse invoice details
extractor = StructuredExtractor()
extraction_result = extractor.extract_invoice_data(
    ocr_text=ocr_result['extracted_text'],
    language=ocr_result['language']
)

invoice_data = extraction_result['extracted_data']
print(f"Invoice #: {invoice_data.get('invoice_number')}")
print(f"Vendor: {invoice_data.get('vendor_name')}")
print(f"Total: {invoice_data.get('total')} {invoice_data.get('currency')}")
print(f"Extraction confidence: {extraction_result['confidence']:.0%}")
```

**Using REST API:**
```bash
# 1. Upload document
curl -X POST http://localhost:8000/api/documents/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@invoice.pdf" \
  -F "organization_id=org-uuid" \
  -F "document_type=invoice"

# Response: {"id": "doc-uuid-1234", "status": "pending", ...}

# 2. Process document
curl -X POST http://localhost:8000/api/documents/doc-uuid-1234/process \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response:
# {
#   "success": true,
#   "extracted_data_id": "ext-uuid-5678",
#   "ocr_confidence": 0.92,
#   "extraction_confidence": 0.88,
#   "language": "ar",
#   "method": "vision",
#   "processing_time_ms": 3200
# }

# 3. Retrieve extracted data
curl http://localhost:8000/api/extracted-data/ext-uuid-5678/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🔑 Key Features

### 1. OCR with Dual Strategy
```python
processor = OCRProcessor()
result = processor.process('document.pdf')
# ✅ Tries OpenAI Vision API first (fast, cloud-based)
# ✅ Falls back to Tesseract if Vision unavailable (local, always works)
```

### 2. Structured Data Extraction
```python
extractor = StructuredExtractor()

# Extract invoice fields
invoice = extractor.extract_invoice_data(text)
# Returns: vendor_name, invoice_number, date, total, line_items, etc.

# Extract accounting entries
entries = extractor.extract_accounting_entries(text)
# Returns: suggested journal entries with debit/credit

# Custom extraction with schema
result = extractor.extract_with_schema(text, schema, instructions)
```

### 3. Compliance Explanations (Arabic)
```python
from decimal import Decimal
from core.ai import ComplianceExplainer

explainer = ComplianceExplainer()

# Explain audit finding (returns detailed Arabic explanation)
explanation = explainer.explain_audit_finding(
    finding_title_ar="عدم مطابقة الفاتورة",
    finding_description_ar="الفاتورة تفتقد حقول إلزامية",
    risk_level="high",
    finding_type="compliance",
    financial_impact=Decimal("5000.00"),
    regulatory_reference="نظام الفاتورة الإلكترونية"
)

print(explanation['explanation_ar'])
# Outputs comprehensive Arabic explanation with:
# - Executive summary
# - Root cause analysis
# - Impact analysis
# - Recommendations
# - Implementation timeline
# - Regulatory references
```

---

## ⚙️ Configuration

### Required Environment Variables

```bash
# ===== OpenAI API (Required for AI features) =====
OPENAI_API_KEY=sk-proj-...                  # Get from https://platform.openai.com/account/api-keys
OPENAI_MODEL=gpt-4o-mini                    # Text extraction model
OPENAI_VISION_MODEL=gpt-4o-mini             # Image/OCR model
OPENAI_TIMEOUT=120                          # Seconds to wait
OPENAI_MAX_TOKENS=2000                      # Max response size

# ===== File Processing =====
MAX_UPLOAD_SIZE_MB=50                       # Max file size
MAX_OCR_PAGES=20                            # Max PDF pages to process
ALLOWED_DOCUMENT_TYPES=pdf,jpeg,png,jpg     # Supported formats

# ===== Rate Limiting =====
AI_RATE_LIMIT_REQUESTS=100                  # Requests per period
AI_RATE_LIMIT_PERIOD=3600                   # Period in seconds
```

### Optional

```bash
# Tesseract path (auto-detected usually)
TESSERACT_CMD=/usr/bin/tesseract

# Celery (for async processing - not yet implemented)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

---

## 🛡️ Security

All operations are **secure by design**:

✅ **No SSRF**: Files read from disk, never fetched via URL  
✅ **Organization isolation**: Every operation checks ownership  
✅ **Path traversal prevention**: File paths validated  
✅ **API key protection**: Environment variables only  
✅ **Sensitive data redaction**: Logged safely  
✅ **File validation**: Size & type checks  
✅ **Error handling**: No information leakage  

---

## 📊 Error Handling

```python
from core.ai.errors import (
    FileProcessingError,
    AIAPIError,
    RateLimitError,
    TimeoutError
)

try:
    result = processor.process(file_path)
except FileProcessingError as e:
    print(f"File error: {e.message}")
    # File validation failed (size, type, path)
    
except RateLimitError as e:
    print(f"Rate limited. Retry in {e.details['retry_after_seconds']}s")
    
except TimeoutError as e:
    print(f"Timeout after {e.details['timeout_seconds']}s")
    
except AIAPIError as e:
    print(f"OpenAI API error: {e.message}")
```

---

## 🧪 Testing

```bash
# Run AI module tests (when available)
python manage.py test core.tests.test_ai_ocr
python manage.py test core.tests.test_ai_extraction
python manage.py test core.tests.test_ai_security
```

---

## 📈 Performance Tips

1. **Set `MAX_OCR_PAGES=5`** for quick processing (less pages = faster)
2. **Use `OPENAI_TEMPERATURE=0.1`** for accuracy (extraction)
3. **Use `OPENAI_TEMPERATURE=0.4`** for creativity (explanations)
4. **Tesseract fallback** works automatically if Vision API slow
5. **Check OpenAI status** at https://status.openai.com/ if timeouts

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| `OPENAI_API_KEY not set` | Add to `.env` and restart server |
| `Vision API timeout` | Increase `OPENAI_TIMEOUT` to 180-240 |
| `Tesseract not found` | `apt install tesseract-ocr` or fallback to Vision API |
| `Rate limit (429)` | Reduce `AI_RATE_LIMIT_REQUESTS` or upgrade OpenAI plan |
| `File too large` | Increase `MAX_UPLOAD_SIZE_MB` or split PDF |
| `Extraction has warnings` | Check VAT/date formats, may need manual review |

---

## 📚 Full Documentation

- [OPENAI_IMPLEMENTATION_GUIDE.md](./OPENAI_IMPLEMENTATION_GUIDE.md) - Complete API reference
- [AI_INTEGRATION_PLAN.md](./AI_INTEGRATION_PLAN.md) - Architecture details
- [OpenAI API Docs](https://platform.openai.com/docs/api-reference)

---

## ✨ What's Included

- ✅ OCR (Vision API + Tesseract fallback)
- ✅ Invoice data extraction
- ✅ Accounting entry suggestions
- ✅ Compliance explanations (Arabic)
- ✅ Secure file handling (disk-based, no URLs)
- ✅ Organization isolation
- ✅ Retry logic with exponential backoff
- ✅ Comprehensive error handling
- ✅ Request/response logging
- 🔲 Celery async processing (TODO)
- 🔲 Full test suite (TODO)
- 🔲 Admin dashboard (TODO)

---

## 🚦 API Status

Check OpenAI API status:
```bash
curl https://status.openai.com/api/v2/status.json
```

---

**Ready to use!** 🎉

Start with Step 1 above and you'll be OCR'ing documents in minutes.
Questions? Check the full docs or review the source code in `backend/core/ai/`.
