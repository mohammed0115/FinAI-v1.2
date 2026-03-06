# FinAI - AI Integration Plan
## Production-Grade OpenAI Integration Architecture

**Date:** March 2026  
**Status:** PLANNING PHASE  
**Priority:** HIGH

---

## Executive Summary

This document outlines the comprehensive refactoring of FinAI's AI layer to replace the unavailable **emergentintegrations** SDK with production-grade **OpenAI API** integration. The new architecture will be:

- **Secure**: No SSRF vulnerabilities, proper organization isolation, secure file handling
- **Scalable**: Async processing via Celery for heavy operations (OCR, PDF processing)
- **Maintainable**: Centralized AI service layer in `core/ai/` with separation of concerns
- **Observable**: Comprehensive logging, audit trails, and error handling
- **Compliant**: Required for ZATCA compliance, VAT reconciliation, Zakat calculations

---

## Part 1: Current State Analysis

### 1.1 Existing AI Components

| Component | Location | Status | Issue |
|-----------|----------|--------|-------|
| Vision Processing | `core/ai_service.py` | ❌ Broken | emergentintegrations SDK unavailable |
| Document OCR | `documents/ocr_service.py` | ⚠️ Unused | Tesseract ready but not integrated |
| AI Explanations | `compliance/ai_explanation_service.py` | ❌ Broken | emergentintegrations SDK unavailable |
| Cash Flow Forecast | `core/ai_service.py` | ❌ Broken | emergentintegrations SDK unavailable |
| Anomaly Detection | `core/ai_service.py` | ❌ Broken | emergentintegrations SDK unavailable |
| PDF Reports | `reports/pdf_generator.py` | ✅ Working | No AI integration (could benefit from AI summaries) |

### 1.2 Security Issues Identified

| Issue | Location | Risk | Fix |
|-------|----------|------|-----|
| **SSRF Vulnerability** | `documents/views.py:124` | HIGH | `request.build_absolute_uri()` + `requests.get()` on media files |
| **Organization Injection** | `documents/views.py:50` | MEDIUM | `organization_id` from request.data, not validated against user |
| **No File Validation** | `documents/ocr_service.py` | MEDIUM | No max file size checks before processing |
| **Unbounded PDF Pages** | `documents/ocr_service.py:191` | MEDIUM | No page limit enforcement when converting PDF to images |
| **API Key Exposure** | `core/ai_service.py:25` | MEDIUM | No redaction in logs |

### 1.3 Current Dependencies

- **openai==1.99.9** ✅ Already available
- **requests==2.32.5** ✅ Already available  
- **pytesseract** ✅ Available (but Tesseract binary often missing)
- **pdf2image** ✅ Available
- **Celery** ❌ NOT installed (will add for async tasks)

---

## Part 2: Target Architecture

### 2.1 Unified AI Service Layer

```
backend/core/ai/
├── __init__.py                 # Package init
├── client.py                   # OpenAI unified client (retries, timeouts, logging)
├── prompts.py                  # Organized prompts for each task
├── ocr.py                      # OCR logic (vision model + Tesseract fallback)
├── extract.py                  # Structured data extraction (JSON schema)
├── explain.py                  # Compliance explanations
├── errors.py                   # Unified error types
├── constants.py                # Configuration constants
└── utils.py                    # Base64 encoding, file type detection, page limiting
```

### 2.2 Data Flow Diagram

```
Upload Document
    ↓
[Permission Check: organization isolation]
    ↓
[File Validation: size, type, organization]
    ↓
Store on Disk (media/uploads/)
    ↓
[If Heavy/PDF: Enqueue Celery Task]
    ↓
AI Processing:
  - Read file from disk (not via URL)
  - Encode to base64
  - Send to OpenAI Vision API (with retries)
  - Parse structured JSON response
    ↓
[Store results: OCRExtraction, ExtractedData models]
    ↓
[Generate audit trail + confidence scores]
    ↓
Return to user with metadata
```

---

## Part 3: Detailed Implementation Plan

### Phase 1: Foundation (Core AI Module)
**Duration:** 2-3 hours  
**Files to create/modify:**

1. **`backend/core/ai/client.py`** (NEW - 150 lines)
   - Unified OpenAI client wrapper
   - Exponential retry logic with jitter
   - Request/response logging with redaction
   - Timeout management
   - Error categorization

2. **`backend/core/ai/errors.py`** (NEW - 80 lines)
   - `AIServiceError` base class
   - `AIAPIError` (OpenAI API failures)
   - `FileProcessingError` (invalid files, too large, etc.)
   - `RateLimitError` (429 handling)
   - `TimeoutError` (slow API)

3. **`backend/core/ai/constants.py`** (NEW - 60 lines)
   - Model configurations
   - Temperature, tokens, timeouts
   - Error messages (Arabic + English)
   - Supported file types

4. **`backend/core/ai/utils.py`** (NEW - 120 lines)
   - `encode_file_to_base64(file_path)` - safe encoding
   - `detect_file_type(file_path)` - MIME type validation
   - `limit_pdf_pages(pdf_path, max_pages)` - extract first N pages
   - `validate_file_size(file_path, max_size)` - size check
   - `redact_sensitive_data(text)` - remove PII before logging

5. **`backend/core/ai/prompts.py`** (NEW - 200 lines)
   - `SYSTEM_PROMPTS` dict with role-based system messages
   - `OCR_PROMPT_TEMPLATE` - detailed OCR instructions
   - `EXTRACT_INVOICE_PROMPT` - structured extraction
   - `EXPLAIN_FINDING_PROMPT_AR` - Arabic compliance explanation
   - `SUMMARIZE_REPORT_PROMPT` - executive summary

6. **`backend/core/ai/ocr.py`** (NEW - 250 lines)
   - `OCRProcessor` class
   - `process_with_vision(file_path)` - OpenAI vision API
   - `process_with_tesseract(file_path)` - fallback local OCR
   - Fallback chain: Vision → Tesseract → error
   - Language detection (ar/en/mixed)
   - Confidence scoring

7. **`backend/core/ai/extract.py`** (NEW - 280 lines)
   - `StructuredExtractor` class
   - `extract_invoice_data(ocr_text_or_image)` - JSON schema
   - `extract_accounting_entries(ocr_text)` - proposed journal entries
   - `validate_json_schema(data, schema)` - response validation
   - Retry with refinement prompts on invalid JSON

8. **`backend/core/ai/explain.py`** (NEW - 200 lines)
   - `ComplianceExplainer` class
   - `explain_audit_finding(finding)` - Arabic explanation
   - `explain_vat_discrepancy(discrepancy)` - VAT insights
   - `explain_zatca_result(verification_result)` - ZATCA findings
   - Confidence + audit trail logging

---

### Phase 2: Configuration & Security
**Duration:** 1 hour  
**Files to modify:**

1. **`backend/config/settings.py`** (MODIFY)
   ```python
   # AI/OpenAI Configuration
   OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
   OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
   OPENAI_VISION_MODEL = os.environ.get('OPENAI_VISION_MODEL', 'gpt-4o-mini')
   OPENAI_TIMEOUT = int(os.environ.get('OPENAI_TIMEOUT', '120'))
   OPENAI_MAX_TOKENS = int(os.environ.get('OPENAI_MAX_TOKENS', '2000'))
   OPENAI_TEMPERATURE = float(os.environ.get('OPENAI_TEMPERATURE', '0.3'))
   
   # File Upload Constraints
   MAX_UPLOAD_SIZE = int(os.environ.get('MAX_UPLOAD_SIZE', '50')) * 1024 * 1024  # 50MB
   MAX_OCR_PAGES = int(os.environ.get('MAX_OCR_PAGES', '20'))
   ALLOWED_DOCUMENT_TYPES = ['pdf', 'jpeg', 'png', 'jpg']
   
   # AI Rate Limiting
   AI_RATE_LIMIT_REQUESTS = int(os.environ.get('AI_RATE_LIMIT_REQUESTS', '100'))
   AI_RATE_LIMIT_PERIOD = int(os.environ.get('AI_RATE_LIMIT_PERIOD', '3600'))  # per hour
   
   # Celery Configuration (optional but recommended)
   CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
   CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
   ```

2. **`.env.example`** (CREATE/UPDATE)
   ```
   # OpenAI Configuration
   OPENAI_API_KEY=sk-...your-key-here
   OPENAI_MODEL=gpt-4o-mini
   OPENAI_VISION_MODEL=gpt-4o-mini
   OPENAI_TIMEOUT=120
   OPENAI_MAX_TOKENS=2000
   OPENAI_TEMPERATURE=0.3
   
   # File Processing
   MAX_UPLOAD_SIZE=50  # MB
   MAX_OCR_PAGES=20
   
   # AI Rate Limiting
   AI_RATE_LIMIT_REQUESTS=100
   AI_RATE_LIMIT_PERIOD=3600
   
   # Redis/Celery (optional)
   CELERY_BROKER_URL=redis://localhost:6379/0
   CELERY_RESULT_BACKEND=redis://localhost:6379/1
   ```

3. **`backend/config/urls.py`** (VERIFY)
   - Remove any debug endpoints (e.g., `/debug-auth/`)
   - Ensure no test routes in production

---

### Phase 3: Migrations & Data Models
**Duration:** 1-2 hours  
**Files to create/modify:**

1. **`backend/documents/models.py`** (MODIFY)
   - Add `OCRExtraction` model to store OCR results
   - Add idempotency field: `processing_request_id`
   - Add metadata: `ocr_confidence`, `ocr_language`, `processing_time_ms`

2. **`backend/compliance/models.py`** (MODIFY)
   - Add fields to `AuditFinding`:
     - `ai_explanation_ar` (already exists, verify)
     - `ai_explanation_confidence`
     - `ai_explanation_timestamp`
     - `ai_explanation_model`
   - Track AI generation in `AIExplanationLog` (already exists, verify)

3. **Create Migration**
   ```
   python manage.py makemigrations documents compliance
   python manage.py migrate
   ```

---

### Phase 4: Refactor Existing Views/Services
**Duration:** 3-4 hours  
**Files to modify:**

1. **`backend/documents/views.py`** (REFACTOR)
   - Remove `build_absolute_uri()` + `requests.get()` pattern
   - Read files directly from disk `MEDIA_ROOT`
   - Add organization validation before processing
   - Implement rate limiting middleware
   - Implement idempotency check (don't reprocess same file)
   - Add proper error handling with 400/403/413/429/500 responses

2. **`backend/documents/services.py`** (REFACTOR)
   - Use new `core.ai.ocr.OCRProcessor` instead of emergentintegrations
   - Use new `core.ai.extract.StructuredExtractor` for data extraction
   - Add transaction-based atomic operations
   - Add audit logging for all AI operations

3. **`backend/core/ai_service.py`** (DEPRECATE)
   - Keep as backward-compatibility wrapper OR replace entirely
   - All new code should import from `core.ai.*` instead

4. **`backend/compliance/views.py`** (ADD ENDPOINTS)
   - Add `@action` to generate AI explanations for findings:
     ```python
     @action(detail=True, methods=['post'])
     def generate_explanation(self, request, pk=None):
         # Uses core.ai.explain.ComplianceExplainer
     ```

5. **`backend/compliance/services.py`** (ADD METHOD)
   - `generate_ai_explanation_for_finding(finding_id)`
   - Called from compliance checks or manually from admin

6. **`backend/reports/services.py`** (MODIFY)
   - Add `generate_ai_summary(report_data)` method
   - Uses `core.ai.extract.StructuredExtractor`
   - Creates executive summary (6-10 bullet points Arabic)

---

### Phase 5: Async Processing (Optional but Recommended)
**Duration:** 2 hours  
**Files to create/modify:**

1. **`backend/core/tasks.py`** (NEW - if using Celery)
   ```python
   from celery import shared_task
   
   @shared_task
   def process_document_async(document_id):
       # Async OCR + extraction
       # Called for PDFs or files >10MB
   
   @shared_task
   def generate_explanation_async(finding_id):
       # Async explanation generation
   ```

2. **Requires**: `celery`, `redis` packages + Redis instance

---

### Phase 6: Testing & Documentation
**Duration:** 2-3 hours  
**Files to create:**

1. **`backend/tests/test_ai_ocr.py`** (NEW)
   - Test file type validation
   - Test file size limits
   - Test page limiting for PDFs
   - Test mock OpenAI calls

2. **`backend/tests/test_ai_extraction.py`** (NEW)
   - Test structured JSON extraction
   - Test schema validation
   - Test fallback mechanics

3. **`backend/tests/test_ai_security.py`** (NEW)
   - Test organization isolation (user can't access other org documents)
   - Test SSRF prevention
   - Test rate limiting
   - Test idempotency

4. **`docs/AI_IMPLEMENTATION_GUIDE.md`** (NEW)
   - How to use the new AI endpoints
   - API examples (curl, Python)
   - Error codes and handling
   - Troubleshooting guide

---

## Part 4: API Endpoints & Integration Points

### New/Modified Endpoints

#### Document Processing (REFACTORED)
```
POST /api/documents/upload
  - Validate file type, size, organization
  - Store on disk (not public URL)
  - Return document_id for polling/async processing

POST /api/documents/{id}/process
  - Read file from disk
  - Process with AI OCR + extraction
  - Return: extracted_data_id, confidence, language, processing_time

GET /api/documents/{id}/status
  - Check processing status (pending/processing/completed/failed)
  - Return: progress%, error message (if failed)
```

#### Compliance AI Explanations (NEW)
```
GET /api/compliance/findings/{id}
  (existing, returns finding data)

POST /api/compliance/findings/{id}/explain
  - Generate AI explanation for finding
  - Returns: ai_explanation_ar, confidence, timestamp

GET /api/compliance/findings/{id}/explanation-log
  - Audit trail of all AI explanations generated
```

#### VAT/Zakat AI Insights (NEW)
```
POST /api/compliance/vat-discrepancies/{id}/explain
  - AI explanation for why VAT differs

POST /api/compliance/zakat/calculations/{id}/explain
  - AI explanation for Zakat base calculation
```

#### Report AI Summaries (NEW)
```
GET /api/reports/{id}/ai-summary
  - Executive summary generated by AI
  - Returns: bullet_points[], timestamp, model_used, confidence
```

---

## Part 5: Security & Compliance Checklist

- [ ] All files read from `MEDIA_ROOT` (not via URL)
- [ ] Organization validation on every document access
- [ ] API key never logged or exposed in responses
- [ ] Rate limiting on AI endpoints (e.g., 100 requests/hour)
- [ ] File size enforced before processing
- [ ] PDF page limit enforced (max 20 pages)
- [ ] Idempotency: same document not reprocessed
- [ ] All errors redact sensitive data (invoice numbers, amounts, etc.)
- [ ] Audit trail for every AI operation (logging to database)
- [ ] Fallback mechanisms work (Tesseract if Vision API fails)
- [ ] No debug endpoints in production
- [ ] CSRF protection on POST endpoints
- [ ] Input validation on all user-provided data

---

## Part 6: Implementation Order

1. **Phase 1** → Create `core/ai/` module with all utilities
2. **Phase 2** → Update settings and environment
3. **Phase 3** → Create migrations
4. **Phase 4** → Refactor views/services to use new AI layer
5. **Phase 5** → (Optional) Add Celery async tasks
6. **Phase 6** → Write tests and documentation
7. **Validation** → Manual testing of all endpoints

---

## Part 7: Success Criteria

- ✅ Document OCR works via OpenAI Vision API
- ✅ Fallback to Tesseract if Vision API unavailable
- ✅ Extracted data saved with confidence scores
- ✅ Compliance findings have AI explanations
- ✅ All AI operations audit logged
- ✅ No SSRF vulnerabilities
- ✅ Organization isolation verified
- ✅ Rate limiting prevents abuse
- ✅ All tests pass
- ✅ Backward compatibility maintained (no broken URLs)
- ✅ Documentation complete

---

## Part 8: Rollback Plan

If issues occur:
1. Keep old `core/ai_service.py` as fallback wrapper
2. Use feature flags to toggle between old/new implementations
3. Revert recent migrations if data schema issues arise
4. Have backup ENV configuration for previous API keys

---

## Estimated Timeline

| Phase | Duration | Critical? |
|-------|----------|-----------|
| Phase 1: Core AI module | 2-3h | YES |
| Phase 2: Configuration | 1h | YES |
| Phase 3: Migrations | 1-2h | YES |
| Phase 4: Refactor views | 3-4h | YES |
| Phase 5: Async (optional) | 2h | NO |
| Phase 6: Testing & docs | 2-3h | YES |
| **TOTAL** | **11-15h** | |

---

## Questions Before Implementation Starts

1. Do you want Celery async processing, or sync-only is fine?
2. Should old extracted data be migrated or discarded?
3. What's the target response time for OCR (should fallback to Tesseract if Vision API >5s)?
4. Need ZATCA live verification integration or existing verification is sufficient?
5. Should AI explanations be generated automatically or on-demand?

---

**Next Step:** Wait for approval + any clarifications. Ready to start Phase 1 implementation immediately. 🚀
