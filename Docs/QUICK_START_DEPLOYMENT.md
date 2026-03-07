# Quick Start: Phase 1 & 2 Deployment & Testing

## Pre-Deployment Checklist

### 1. Verify Files Exist

```bash
cd /home/mohamed/FinAI-v1.2

# Core services (Phase 1 & 2)
ls -la backend/core/openai_invoice_service.py
ls -la backend/core/invoice_normalization_service.py
ls -la backend/core/invoice_validation_service.py
ls -la backend/core/invoice_processing_service.py

# Modified files
ls -la backend/documents/models.py
ls -la backend/documents/views.py
ls -la backend/documents/serializers.py
ls -la backend/documents/ocr_service.py

# Documentation
ls -la PHASE_2_NORMALIZATION_VALIDATION.md
ls -la PHASE_2_IMPLEMENTATION_CHECKLIST.md
ls -la COMPLETE_IMPLEMENTATION_SUMMARY.md
```

All files should exist. ✅

### 2. Verify Python Dependencies

```bash
cd /home/mohamed/FinAI-v1.2/backend

# Check requirements.txt has:
# - openai (for API calls)
# - Pillow (for image handling)
# - pytesseract (for fallback OCR)
# Django and other existing dependencies

grep -E "openai|Pillow|pytesseract" requirements.txt

# Install if needed
pip install -r requirements.txt
```

### 3. Set Environment Variables

```bash
# OpenAI API Key
export OPENAI_API_KEY="sk-..."

# Verify it's set
echo $OPENAI_API_KEY  # Should show your key (first 3 chars + masked)
```

---

## Deployment Steps

### Step 1: Create Database Migration

```bash
cd /home/mohamed/FinAI-v1.2/backend

# Generate migration files for Phase 2 changes
python manage.py makemigrations documents

# Expected output:
# Migrations for 'documents':
#   documents/migrations/XXXX_phase_2_updates.py
#     - Add field normalized_json to extracteddata
#     - Add field is_valid to extracteddata
#     - Add field validation_errors to extracteddata
#     - Add field validation_warnings to extracteddata
#     - Add field validation_completed_at to extracteddata
#     - Create model InvoiceAuditFinding
```

**If errors occur:**
```bash
# Check migration folder
ls documents/migrations/

# If corrupted, reset carefully:
python manage.py migrate documents 0001  # Go to first migration
python manage.py showmigrations documents  # View history
```

### Step 2: Apply Database Migration

```bash
cd /home/mohamed/FinAI-v1.2/backend

# Apply the migration
python manage.py migrate documents

# Expected output:
# Running migrations:
#   Applying documents.XXXX_phase_2_updates... OK
```

**Verify in database:**
```bash
python manage.py dbshell

# In SQL shell:
DESCRIBE extracted_data;  # Should show new columns
DESCRIBE invoice_audit_findings;  # Should exist
.exit
```

### Step 3: Restart Application

```bash
# Option A: Development with runserver
cd /home/mohamed/FinAI-v1.2/backend
python manage.py runserver

# Option B: Production with Gunicorn
supervisorctl status gunicorn
supervisorctl restart gunicorn

# Option C: Production with uWSGI
systemctl status uwsgi
systemctl restart uwsgi

# Option D: Using Docker
docker-compose down
docker-compose up -d
```

### Step 4: Verify Installation

```bash
cd /home/mohamed/FinAI-v1.2/backend

# Enter Django shell
python manage.py shell

# Test Phase 1 imports
>>> from core.openai_invoice_service import openai_invoice_service
>>> print("✓ OpenAI service loaded")

# Test Phase 2 imports
>>> from core.invoice_normalization_service import invoice_normalization_service
>>> from core.invoice_validation_service import invoice_validation_service
>>> from core.invoice_processing_service import invoice_processing_service
>>> print("✓ Phase 2 services loaded")

# Test models
>>> from documents.models import ExtractedData, InvoiceAuditFinding
>>> print(f"ExtractedData records: {ExtractedData.objects.count()}")
>>> print(f"InvoiceAuditFinding records: {InvoiceAuditFinding.objects.count()}")
>>> print("✓ Models initialized")

# Exit shell
>>> exit()
```

---

## Testing Phase 1 (Extraction)

### Quick Test 1: OpenAI Service

```bash
cd /home/mohamed/FinAI-v1.2/backend
python manage.py shell

>>> from core.openai_invoice_service import openai_invoice_service
>>> from PIL import Image
>>> import io

# Create test image (small 100x100 white image)
>>> img = Image.new('RGB', (100, 100), color='white')
>>> img_bytes = io.BytesIO()
>>> img.save(img_bytes, format='PNG')
>>> img_bytes.seek(0)

# Try extraction (will fail on tiny image, but tests API call)
>>> result = openai_invoice_service.extract_invoice_from_bytes(
...     img_bytes.getvalue(),
...     filename="test.png"
... )

>>> print(f"Result: {result}")
>>> # Expected: extraction_confidence: 0 (tiny image has no invoice data)
```

### Quick Test 2: With Real Invoice Image

If you have a test invoice image:

```bash
cd /home/mohamed/FinAI-v1.2/backend
python manage.py shell

>>> from core.openai_invoice_service import openai_invoice_service

# Extract from file
>>> result = openai_invoice_service.extract_invoice_from_file(
...     "/path/to/invoice.jpg"
... )

>>> print(f"Extracted: {result}")
>>> # Should show: invoice_number, vendor, items, total_amount, etc.
```

### Quick Test 3: Document Upload via API

```bash
# Get authentication token (adjust for your auth method)
TOKEN="your_auth_token_here"

# Upload invoice
curl -X POST http://localhost:8000/api/documents/upload/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/invoice.jpg" \
  -F "document_type=invoice"

# Expected response (201 Created):
# {
#   "id": "uuid",
#   "document": {...},
#   "extracted_json": {...},  # Phase 1 output
#   "extraction_status": "completed",
#   "created_at": "..."
# }
```

### Test Result Expectations

| Test | Expected | Pass/Fail |
|---|---|---|
| OpenAI service loads | No error | ✅ |
| Extract from bytes | Returns dict with confidence | ✅ |
| Extract real invoice | Shows invoice data | ✅ |
| Upload endpoint | 201 response | ✅ |

---

## Testing Phase 2 (Normalization + Validation + Review)

### Quick Test 1: Normalization Service

```bash
cd /home/mohamed/FinAI-v1.2/backend
python manage.py shell

>>> from core.invoice_normalization_service import invoice_normalization_service
>>> from decimal import Decimal

# Test 1: Date normalization
>>> date = invoice_normalization_service.normalize_date("03/15/2024")
>>> assert date == "2024-03-15"
>>> print(f"✓ Date: {date}")

# Test 2: Amount normalization
>>> amount = invoice_normalization_service.normalize_amount("$1,000.50")
>>> assert amount == Decimal('1000.50')
>>> print(f"✓ Amount: {amount}")

# Test 3: Currency normalization
>>> currency = invoice_normalization_service.normalize_currency("€")
>>> assert currency == "EUR"
>>> print(f"✓ Currency: {currency}")

# Test 4: Full invoice normalization
>>> raw = {
...     "invoice_number": "  INV-001  ",
...     "issue_date": "2024-03-15",
...     "vendor": {"name": "  ACME Corp  "},
...     "customer": {"name": "John Doe"},
...     "items": [{"quantity": "10", "unit_price": "$100"}],
...     "total_amount": "$1,000.00",
...     "currency": "$"
... }
>>> normalized = invoice_normalization_service.normalize_invoice_json(raw)
>>> print(normalized["invoice_number"])  # Should be "INV-001"
>>> print(normalized["total_amount"])    # Should be Decimal('1000.00')
>>> print(normalized["currency"])         # Should be "USD"
>>> print("✓ Full invoice normalized")
```

### Quick Test 2: Validation Service

```bash
cd /home/mohamed/FinAI-v1.2/backend
python manage.py shell

>>> from core.invoice_validation_service import invoice_validation_service
>>> from decimal import Decimal

# Valid invoice
>>> valid_invoice = {
...     "invoice_number": "INV-001",
...     "issue_date": "2024-03-15",
...     "vendor_name": "ACME Corp",
...     "customer_name": "John Doe",
...     "items": [
...         {"product": "Widget", "quantity": "10", "price": "100.00", "amount": "1000.00"}
...     ],
...     "total_amount": Decimal('1000.00'),
...     "currency": "USD"
... }

>>> is_valid, messages = invoice_validation_service.validate_invoice(valid_invoice)
>>> print(f"Valid: {is_valid}")       # Should be True
>>> print(f"Errors: {len([m for m in messages if m['level'] == 'error'])}")  # Should be 0
>>> print("✓ Valid invoice passes")

# Invalid invoice (missing field)
>>> invalid_invoice = valid_invoice.copy()
>>> del invalid_invoice["invoice_number"]
>>> is_valid, messages = invoice_validation_service.validate_invoice(invalid_invoice)
>>> print(f"Valid: {is_valid}")       # Should be False
>>> print(f"Errors: {len([m for m in messages if m['level'] == 'error'])}")  # Should be > 0
>>> print("✓ Invalid invoice fails as expected")
```

### Quick Test 3: Review Endpoint

```bash
# Using existing extracted_data from Phase 1 upload

TOKEN="your_auth_token_here"

# Get review data
curl -X GET http://localhost:8000/api/extracted-data/{id}/review/ \
  -H "Authorization: Bearer $TOKEN"

# Expected response (200 OK):
# {
#   "id": "uuid",
#   "document_url": "...",
#   "extraction": { /* Phase 1 output */ },
#   "normalized": { /* Phase 2 output */ },
#   "validation": {
#     "is_valid": true/false,
#     "errors": [...],
#     "warnings": [...]
#   },
#   "audit_findings": [...]
# }
```

### Quick Test 4: Review Actions

**Test Accept:**
```bash
TOKEN="your_auth_token_here"

curl -X POST http://localhost:8000/api/extracted-data/{id}/accept/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Looks good"}'

# Expected: validation_status = "validated"
```

**Test Reject:**
```bash
TOKEN="your_auth_token_here"

curl -X POST http://localhost:8000/api/extracted-data/{id}/reject/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"rejection_reason": "Invalid vendor"}'

# Expected: validation_status = "rejected"
```

**Test Correct:**
```bash
TOKEN="your_auth_token_here"

curl -X POST http://localhost:8000/api/extracted-data/{id}/correct/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "corrections": {
      "invoice_number": "INV-2024-001",
      "total_amount": "1050.00"
    }
  }'

# Expected: validation_status = "corrected", normalized updated
```

---

## Full End-to-End Test (Success Scenario)

```bash
#!/bin/bash

# Set up
cd /home/mohamed/FinAI-v1.2/backend
TOKEN="your_auth_token_here"
INVOICE_FILE="/path/to/test_invoice.jpg"
API_URL="http://localhost:8000"

echo "=== Phase 1 & 2 End-to-End Test ==="

# 1. Upload invoice
echo "1. Uploading invoice..."
UPLOAD_RESPONSE=$(curl -s -X POST $API_URL/api/documents/upload/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@$INVOICE_FILE" \
  -F "document_type=invoice")

EXTRACTED_DATA_ID=$(echo $UPLOAD_RESPONSE | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
echo "   Created: $EXTRACTED_DATA_ID"

# 2. Wait for Phase 2 to complete
echo "2. Waiting for Phase 2 processing..."
sleep 2

# 3. Review extracted data
echo "3. Fetching review data..."
REVIEW=$(curl -s -X GET $API_URL/api/extracted-data/$EXTRACTED_DATA_ID/review/ \
  -H "Authorization: Bearer $TOKEN")

echo "   Extraction: $(echo $REVIEW | grep -o '"extraction"' | wc -l) section(s)"
echo "   Normalized: $(echo $REVIEW | grep -o '"normalized"' | wc -l) section(s)"
echo "   Validation: $(echo $REVIEW | grep -o '"validation"' | wc -l) section(s)"
echo "   Audit: $(echo $REVIEW | grep -o '"audit_findings"' | wc -l) section(s)"

# 4. Accept if valid
VALIDATION_VALID=$(echo $REVIEW | grep -o '"is_valid":true' | wc -l)
if [ $VALIDATION_VALID -gt 0 ]; then
  echo "4. Accepting invoice..."
  curl -s -X POST $API_URL/api/extracted-data/$EXTRACTED_DATA_ID/accept/ \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"notes":"Accepted via script"}' > /dev/null
  echo "   ✓ Accepted"
else
  echo "4. Invoice invalid, would need correction"
  echo "   See review output for validation errors"
fi

echo "=== Test Complete ==="
```

---

## Troubleshooting

### Issue: Migration Fails

```bash
# Check migration file
cat documents/migrations/XXXX_phase_2_updates.py

# Rollback if needed
python manage.py migrate documents 0001
python manage.py migrate documents zero  # Remove all migrations

# Try again
python manage.py makemigrations documents
python manage.py migrate documents
```

### Issue: Import Error

```bash
# Verify Python path
cd /home/mohamed/FinAI-v1.2/backend
python manage.py shell
>>> import sys
>>> print(sys.path)

# Re-install requirements
pip install -r requirements.txt --force-reinstall
```

### Issue: OpenAI API Error

```bash
# Check API key
echo $OPENAI_API_KEY

# Test API connection
python -c "
import openai
openai.api_key = '$OPENAI_API_KEY'
print('✓ API key configured')
"

# Check API quota/billing in OpenAI dashboard
```

### Issue: Phase 2 Not Running

```bash
# Check logs
tail -f logs/django.log | grep -i "invoice\|processing\|validation"

# Check if it's async
python manage.py shell
>>> from documents.models import ExtractedData
>>> ed = ExtractedData.objects.latest('id')
>>> print(ed.validation_completed_at)  # Should be recent timestamp

# If null, processing failed - check ED for errors
>>> print(ed.extraction_status)
>>> print(ed.normalized_json)
>>> print(ed.validation_errors)
```

---

## Quick Command Reference

```bash
# Migration & Deployment
cd /home/mohamed/FinAI-v1.2/backend
python manage.py makemigrations documents
python manage.py migrate documents
python manage.py runserver

# Testing
python manage.py shell
python manage.py test documents

# Check database
python manage.py dbshell

# Logs
tail -f logs/django.log

# API Testing
curl -X POST http://localhost:8000/api/documents/upload/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@invoice.jpg" \
  -F "document_type=invoice"

curl -X GET http://localhost:8000/api/extracted-data/{id}/review/ \
  -H "Authorization: Bearer $TOKEN"
```

---

## Success Checklist

After deployment, verify:

- [ ] Database migrations applied successfully
- [ ] No errors in Django logs
- [ ] OpenAI service loads without error
- [ ] Phase 2 services load without error
- [ ] Can upload invoice without errors
- [ ] Review endpoint returns valid JSON
- [ ] Audit findings created for invalid invoices
- [ ] Accept/reject/correct endpoints work
- [ ] Test invoice extracted correctly
- [ ] Test invoice validated correctly
- [ ] Normalized data has proper formats

**All items checked = READY FOR PRODUCTION** ✅

---

## Next Steps

1. **Run migrations** (required before testing)
   ```bash
   python manage.py makemigrations documents
   python manage.py migrate documents
   ```

2. **Test with sample invoice**
   - Upload via API
   - Review extracted data
   - Test accept/reject/correct

3. **Monitor logs** for any issues

4. **Plan Phase 3** (financial object creation)

Good luck! 🚀
