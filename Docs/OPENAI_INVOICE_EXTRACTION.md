# OpenAI Invoice Extraction Pipeline - Implementation Guide

## Overview

This implementation adds a real invoice extraction pipeline using OpenAI's Vision API (gpt-4o-mini) with automatic Tesseract OCR fallback. The system extracts structured invoice data from image documents (jpg, jpeg, png) and saves it to the ExtractedData model.

## Architecture

### Components

1. **OpenAI Invoice Service** (`backend/core/openai_invoice_service.py`)
   - Primary invoice extraction using OpenAI Vision API
   - Base64 image encoding
   - Structured JSON schema validation
   - Confidence scoring
   - Error handling and logging

2. **OCR Service with OpenAI Provider** (`backend/documents/ocr_service.py`)
   - `OpenAIVisionOCRProvider`: New provider class for OpenAI Vision
   - `extract_invoice_with_openai()`: New method in DocumentOCRService for invoice extraction
   - Automatic fallback to Tesseract if OpenAI fails or is unavailable

3. **Document Views** (`backend/documents/views.py`)
   - Updated `upload()` and `batch_upload()` to trigger invoice extraction
   - New `_extract_invoice_data()` helper method
   - Uses user's organization instead of request parameter (security improvement)
   - Safe error handling without blocking uploads

## API Flow

### 1. Invoice Upload Endpoint

**Endpoint:** `POST /api/documents/upload/`

**Request:**
```json
{
  "file": <binary image file>,
  "document_type": "invoice"
}
```

**Response:**
```json
{
  "id": "uuid",
  "file_name": "invoice.jpg",
  "status": "completed",
  "document_type": "invoice",
  "extracted_data": {
    "id": "uuid",
    "invoice_number": "INV-2024-001",
    "total_amount": 1000.00,
    "confidence": 85
  }
}
```

### 2. Extraction Process

1. **File Upload & Validation**
   - Save file to storage
   - Create Document record (status: pending)
   - Get file path for processing

2. **Invoice Extraction** (if document_type == 'invoice')
   - Try OpenAI Vision first (primary path)
   - If unavailable/failed, use Tesseract fallback
   - Never crash the upload on extraction failure

3. **Data Validation & Storage**
   - Validate extracted JSON against schema
   - Parse dates and amounts
   - Create ExtractedData record
   - Update Document status to 'completed'

4. **Error Handling**
   - All errors are logged but don't fail the upload
   - Document remains accessible in storage
   - Failed extractions can be retried manual

## Extracted Invoice Schema

```json
{
  "invoice_number": "string",
  "issue_date": "YYYY-MM-DD",
  "due_date": "YYYY-MM-DD",
  "vendor": {
    "name": "string",
    "address": "string",
    "city": "string",
    "country": "string"
  },
  "customer": {
    "name": "string",
    "address": "string",
    "city": "string",
    "country": "string",
    "tin": "string"
  },
  "items": [
    {
      "product": "string",
      "description": "string",
      "quantity": "string",
      "unit_price": "string",
      "discount": "string",
      "total": "string"
    }
  ],
  "total_amount": "string",
  "currency": "string"
}
```

## Configuration

### Environment Variables

```bash
# Required for OpenAI Vision API
export OPENAI_API_KEY="sk-..."

# Optional: Django settings
export DJANGO_SETTINGS_MODULE="FinAI.settings"
```

### Django Settings

The implementation uses existing settings. No new settings required.

## File Mappings

### ExtractedData Model Fields

| Model Field | Source | Notes |
|---|---|---|
| `vendor_name` | `vendor.name` | Extracted vendor company name |
| `customer_name` | `customer.name` | Extracted customer name |
| `invoice_number` | `invoice_number` | Invoice reference number |
| `invoice_date` | `issue_date` | Parsed as DateTime |
| `due_date` | `due_date` | Parsed as DateTime |
| `total_amount` | `total_amount` | Parsed as Decimal |
| `currency` | `currency` | ISO currency code |
| `items_json` | `items` | Full line items array |
| `confidence` | Calculated | 0-100 score based on field completion |

## Confidence Scoring

The confidence score (0-100) is calculated based on data completeness:

- **Main fields:** invoice_number, issue_date, vendor, customer, total_amount (1 point each)
- **Items:** (1 point if present)
- **Score calculation:** (filled_fields / total_fields) * 100

Example scores:
- Full invoice: 95-100%
- Incomplete date/customer: 70-80%
- Only invoice number: 20-30%
- No extracted data: 0%

## Usage Examples

### 1. Upload Single Invoice

```bash
curl -X POST http://localhost:8000/api/documents/upload/ \
  -H "Authorization: Bearer <token>" \
  -F "file=@invoice.jpg" \
  -F "document_type=invoice"
```

### 2. Batch Upload Invoices

```bash
curl -X POST http://localhost:8000/api/documents/batch_upload/ \
  -H "Authorization: Bearer <token>" \
  -F "files=@invoice1.jpg" \
  -F "files=@invoice2.jpg" \
  -F "document_type=invoice"
```

### 3. Query Extracted Data

```bash
curl -X GET http://localhost:8000/api/extracted-data/ \
  -H "Authorization: Bearer <token>"
```

### 4. Validate Extracted Data

```bash
curl -X POST http://localhost:8000/api/extracted-data/{id}/validate_data/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"status": "validated"}'
```

## Error Handling

The implementation handles errors gracefully:

### OpenAI Vision Failures
- Logs error with full traceback
- Falls back to Tesseract OCR
- If both fail, still completes upload
- Returns extraction error in response

### File Format Issues
- Rejects unsupported formats (only jpg, jpeg, png for images)
- Returns HTTP 201 with document, but no extracted data
- Logs the rejection reason

### Network/API Errors
- Catches all requests exceptions
- Logs for debugging
- Falls back to Tesseract
- Doesn't crash the upload

### Database Errors
- Tries to save ExtractedData
- If save fails, logs error
- Document still saved successfully

## Logging

All operations are logged to the application logger at `__name__`. Key logs:

```python
logger.info(f"Starting invoice extraction for document {document.id}")
logger.info(f"Successfully extracted invoice with OpenAI (confidence: {result.get('confidence')}%)")
logger.warning(f"Invoice extraction failed for {document.id}: {error}")
logger.error(f"Unexpected error during invoice extraction: {error}", exc_info=True)
```

Enable debug logging to see all extraction details:

```python
import logging
logging.getLogger('documents.ocr_service').setLevel(logging.DEBUG)
logging.getLogger('core.openai_invoice_service').setLevel(logging.DEBUG)
```

## Testing

### Unit Tests

Run the unit tests:

```bash
cd /home/mohamed/FinAI-v1.2
python3 test_openai_invoice_pipeline.py
```

This tests:
- Service initialization
- Schema validation
- Confidence calculation
- OCR integration
- Error handling
- Model compatibility
- Views integration

### Integration Tests

Run the integration tests:

```bash
cd /home/mohamed/FinAI-v1.2
python3 test_integration_invoice.py
```

This:
- Creates a sample invoice image
- Tests OpenAI Vision extraction
- Validates schema
- Confirms OCR integration
- Verifies confidence scoring

## Performance

### OpenAI Vision API
- **Model:** gpt-4o-mini (fast, cost-effective)
- **Temperature:** 0.0 (deterministic extraction)
- **Max tokens:** 2000
- **Timeout:** 30 seconds
- **Image detail:** high (for accurate extraction)

### File Processing
- Supports images up to 20 MB
- Processing time: typically 5-15 seconds
- Concurrent uploads: depends on OpenAI API limits

## Security Considerations

### API Key Management
- Never commit OPENAI_API_KEY to version control
- Use environment variables
- Rotate API keys regularly
- Monitor usage in OpenAI dashboard

### File Validation
- Validates file type before processing
- Checks file size limits
- Sanitizes file paths
- Validates extracted data format

### Organization Isolation
- Uses logged-in user's organization (not request parameter)
- Prevents cross-organization data access
- All data queries filtered by organization

### Data Privacy
- Raw response from OpenAI is stored as audit trail
- Extracted data is sanitized
- No PII logging (unless in debug mode)
- Follows GDPR compliance patterns

## Limitations & Future Improvements

### Current Limitations
1. **Image-only:** Only processes jpg, jpeg, png
   - Future: Add PDF support via page-by-page extraction

2. **Single invoice per file:** Expects one invoice per image
   - Future: Detect and extract multiple invoices

3. **Language:** Optimized for English/Arabic
   - Future: Multi-language support

4. **Manual correction:** No built-in field editing UI
   - Future: Add manual correction interface

### Future Enhancements
1. **Batch processing API**
   - Queue multiple documents
   - Background job processing
   - Progress tracking

2. **AI training**
   - Learn from manual corrections
   - Custom model fine-tuning
   - Organization-specific patterns

3. **Validation rules**
   - Custom extraction rules per organization
   - Regex pattern matching
   - Amount consistency checks

4. **Export integration**
   - Direct journal entry creation
   - General ledger posting
   - Tax filing automation

## Troubleshooting

### OpenAI API Errors

**Error: "OPENAI_API_KEY not configured"**
```bash
# Set the environment variable
export OPENAI_API_KEY="sk-..."

# Verify (don't print the full key)
echo $OPENAI_API_KEY | head -c 10
```

**Error: "Invalid JSON response from OpenAI"**
- OpenAI returned non-JSON response
- Check OpenAI API status
- Verify model name is correct (gpt-4o-mini)
- Try with a clearer invoice image

**Error: "API request timeout after 30s"**
- OpenAI API is slow
- Image size is very large (reduce quality)
- Network connectivity issue

### Extraction Quality Issues

**Low confidence score (<50%)**
- Invoice image is blurry or small
- Text is handwritten
- Multiple invoices in one image
- Non-standard invoice format

**Missing or incorrect fields**
- Text is cut off in the image
- OCR can't read the field (color, font)
- Field uses non-standard format
- Manually validate and correct

**Fallback to Tesseract**
- OpenAI Vision unavailable
- Large batch causing rate limits
- API quota exhausted
- Check OpenAI dashboard for usage

## Support

For issues or questions:

1. Check logs: `docker logs <container>` or application logs
2. Review error messages in response JSON
3. Test with a different invoice image
4. Verify OPENAI_API_KEY is set correctly
5. Check OpenAI API status page

## References

- [OpenAI Vision API Docs](https://platform.openai.com/docs/guides/vision)
- [OpenAI Models](https://platform.openai.com/docs/models)
- [gpt-4o-mini Model Card](https://platform.openai.com/docs/models/gpt-4o-mini)
- [Image Processing Guide](https://platform.openai.com/docs/guides/vision/low-or-high-fidelity-image-understanding)
