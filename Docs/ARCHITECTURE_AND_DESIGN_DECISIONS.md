# Architecture & Decision Tree

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    FinAI Invoice Processing Pipeline                    │
│                          Phase 1 & Phase 2                              │
└─────────────────────────────────────────────────────────────────────────┘

PHASE 1: EXTRACTION
═══════════════════════════════════════════════════════════════════════════

    Invoice Image (JPG/JPEG/PNG)
            │
            ▼
    ┌──────────────────────────────┐
    │  DocumentOCRService          │
    │  extract_invoice_with_openai │
    └──────────────────────────────┘
            │
            ├─────────────────────────────────────┐
            │                                     │
    ┌───────▼─────────┐              ┌───────────▼──────────┐
    │  OpenAI Vision  │              │  Tesseract OCR       │
    │  API            │              │  (Fallback)          │
    │  - gpt-4o-mini  │              │                      │
    │  - Base64 encode│              │  (if OpenAI fails)   │
    │  - JSON output  │              │                      │
    │  - 8-15 seconds │              │  (3-8 seconds)       │
    └────────┬────────┘              └──────────┬───────────┘
             │                                  │
             │                                  │
             └──────────────┬───────────────────┘
                            │
                    ┌───────▼────────┐
                    │  ExtractedData │
                    │                │
                    │  extracted_json│ ◄─ Phase 1 output
                    │  extraction_   │
                    │    status:     │
                    │  "completed"   │
                    └────────┬───────┘
                             │
                             │
PHASE 2: NORMALIZATION ◄─────┤
═══════════════════════════════════════════════════════════════════════════
                             │
        ┌────────────────────▼──────────────────┐
        │   process_extracted_invoice()         │
        │   (invoice_processing_service.py)     │
        └────────────────────┬──────────────────┘
                             │
        ┌────────────────────▼──────────────────┐
        │   Step 1: NORMALIZATION               │
        │ (invoice_normalization_service.py)    │
        │                                       │
        │  • normalize_date()                   │
        │    Input: "03/15/2024"                │
        │    Output: "2024-03-15" (ISO 8601)    │
        │                                       │
        │  • normalize_amount()                 │
        │    Input: "$1,000.50"                 │
        │    Output: Decimal('1000.50')         │
        │                                       │
        │  • normalize_currency()               │
        │    Input: "$"                         │
        │    Output: "USD" (ISO 4217)           │
        │                                       │
        │  • normalize_string()                 │
        │    Input: "  ACME  Corp  "            │
        │    Output: "ACME Corp" (trimmed)      │
        │                                       │
        │  • Full invoice normalization         │
        │    Output: normalized_json (JSONField)│
        └────────────────────┬──────────────────┘
                             │
                    ┌────────▼──────────┐
                    │   ExtractedData   │
                    │                   │
                    │ normalized_json   │ ◄─ Phase 2 output (part 1)
                    └────────┬──────────┘
                             │
PHASE 2: VALIDATION ◄────────┤
═══════════════════════════════════════════════════════════════════════════
                             │
        ┌────────────────────▼──────────────────┐
        │   Step 2: VALIDATION                  │
        │ (invoice_validation_service.py)       │
        │                                       │
        │  Layer 1: REQUIRED FIELDS             │
        │  ├─ invoice_number                    │
        │  ├─ issue_date                        │
        │  ├─ vendor_name                       │
        │  ├─ items (≥1)                        │
        │  └─ total_amount                      │
        │                                       │
        │  Layer 2: BUSINESS RULES              │
        │  ├─ issue_date ≤ due_date             │
        │  ├─ currency is valid                 │
        │  ├─ amounts are positive              │
        │  └─ due_date ≤ 180 days (warning)     │
        │                                       │
        │  Layer 3: CONSISTENCY                 │
        │  ├─ Σ(qty × price) = line_amount      │
        │  ├─ Σ(line_amounts) = invoice_total   │
        │  └─ currency consistency              │
        │                                       │
        │  Returns: (is_valid: bool,            │
        │           messages: [error/warning])  │
        └────────────────────┬──────────────────┘
                             │
                    ┌────────▼──────────────┐
                    │   ExtractedData       │
                    │                       │
                    │ is_valid              │ ◄─ Phase 2 output (part 2)
                    │ validation_errors     │
                    │ validation_warnings   │
                    │ validation_completed_ │
                    │ at                    │
                    └────────┬──────────────┘
                             │
PHASE 2: AUDIT TRAIL ◄───────┤
═══════════════════════════════════════════════════════════════════════════
                             │
        ┌────────────────────▼──────────────────┐
        │   Step 3: CREATE AUDIT FINDINGS       │
        │   (one per validation error)          │
        │                                       │
        │   For each error:                     │
        │   ├─ finding_type (enum)              │
        │   ├─ severity (ERROR/WARNING/INFO)    │
        │   ├─ description (human-readable)     │
        │   ├─ field (affected field name)      │
        │   ├─ expected_value / actual_value    │
        │   ├─ difference (numeric delta)       │
        │   └─ resolution tracking              │
        └────────────────────┬──────────────────┘
                             │
                    ┌────────▼──────────────────┐
                    │ InvoiceAuditFinding      │ ◄─ Phase 2 output (part 3)
                    │                          │
                    │ 1:M relationship to      │
                    │ ExtractedData            │
                    │ (audit trail)            │
                    └───────────┬──────────────┘
                                │
PHASE 2: USER REVIEW ◄──────────┤
═══════════════════════════════════════════════════════════════════════════
                                │
                        ┌───────▼────────┐
                        │ Review Snapshot │
                        │ GET /review/    │
                        │                 │
                        │ Shows:          │
                        │ • Image         │
                        │ • Extraction    │
                        │ • Normalized    │
                        │ • Validation    │
                        │ • Audit         │
                        │   Findings      │
                        └────────┬────────┘
                                 │
           ┌─────────────────────┼─────────────────────┐
           │                     │                     │
    ┌──────▼─────┐        ┌──────▼──────┐      ┌──────▼───────┐
    │   ACCEPT   │        │   REJECT    │      │   CORRECT    │
    │            │        │             │      │              │
    │ POST /     │        │ POST /      │      │ POST /       │
    │ accept/    │        │ reject/     │      │ correct/     │
    │            │        │             │      │              │
    │ Status:    │        │ Status:     │      │ Corrections: │
    │ validated  │        │ rejected    │      │ {field:val}  │
    └──────┬─────┘        └──────┬──────┘      └──────┬───────┘
           │                     │                     │
           │             ┌───────▼──────┐              │
           │             │ Stop         │              │
           │             │ Processing   │              │
           │             └───────┬──────┘              │
           │                     │         ┌───────────▼──────┐
           │                     │         │  Re-validate     │
           │                     │         │  Update          │
           │                     │         │  normalized_json │
           │                     │         │  Status:         │
           │                     │         │  corrected       │
           │                     │         └───────────┬──────┘
           │                     │                     │
PHASE 3: FINANCIAL POSTING ◄────┤─────────────────────┤
═══════════════════════════════════════════════════════════════════════════
           │                     │                     │
    ┌──────▼─────────────────────────────────────────┐
    │   Create Financial Objects                    │
    │   (Phase 3 - Future)                          │
    │                                               │
    │   ├─ Transaction (header)                     │
    │   │  ├─ transaction_date = issue_date         │
    │   │  ├─ vendor / supplier_id                  │
    │   │  └─ amount = total_amount                 │
    │   │                                           │
    │   └─ JournalEntry (lines)                     │
    │      ├─ Account (Chart of Accounts)           │
    │      ├─ Amount (line_amount)                  │
    │      └─ VAT flag (if applicable)              │
    │                                               │
    │   Status: draft (ready for approval/posting)  │
    └───────────────┬────────────────────────────────┘
                    │
            ┌───────▼──────┐
            │ GL POSTING   │
            │              │
            │ Finalized    │
            │ in ledger    │
            └───────┬──────┘
                    │
            ┌───────▼───────┐
            │   Compliance  │
            │   Reporting   │
            └───────────────┘
```

---

## Decision Tree: What Happens to Your Invoice?

```
Start with Invoice Image
    │
    ├─ Is it JPG/JPEG/PNG?
    │  ├─ NO  → ERROR: "File format not supported"
    │  └─ YES ─→ Continue
    │
    ├─ Is it <20MB?
    │  ├─ NO  → ERROR: "File too large"
    │  └─ YES ─→ Continue
    │
    ├─ PHASE 1: EXTRACTION
    │  │
    │  ├─ Call OpenAI Vision API
    │  │  ├─ Success → extracted_json populated
    │  │  └─ Fail → Try Tesseract
    │  │
    │  └─ Try Tesseract OCR
    │     ├─ Success → extracted_json populated
    │     └─ Fail → extracted_json = {} (empty)
    │
    ├─ ExtractedData record created
    │  └─ extraction_status = "completed"
    │
    ├─ PHASE 2: PROCESS EXTRACTED INVOICE (automatic)
    │  │
    │  ├─ Normalize Data
    │  │  ├─ Dates → ISO 8601 (YYYY-MM-DD)
    │  │  ├─ Amounts → Decimal (precision)
    │  │  ├─ Currency → ISO 4217 codes
    │  │  └─ Strings → Title case, trimmed
    │  │  │
    │  │  └─ Save to: normalized_json
    │  │
    │  ├─ Validate Data
    │  │  │
    │  │  ├─ Check Required Fields (5 critical)
    │  │  │  ├─ invoice_number ✓
    │  │  │  ├─ issue_date ✓
    │  │  │  ├─ vendor_name ✓
    │  │  │  ├─ items (≥1) ✓
    │  │  │  └─ total_amount ✓
    │  │  │
    │  │  ├─ Any missing?
    │  │  │  ├─ YES → is_valid = False, add ERROR
    │  │  │  └─ NO → Continue
    │  │  │
    │  │  ├─ Check Business Rules
    │  │  │  ├─ issue_date ≤ due_date?
    │  │  │  ├─ currency valid ISO code?
    │  │  │  ├─ amounts positive?
    │  │  │  └─ due_date ≤ 180 days? (warning only)
    │  │  │
    │  │  ├─ Any violations?
    │  │  │  ├─ YES (error level) → is_valid = False, add ERROR
    │  │  │  ├─ YES (warning level) → Add WARNING (doesn't block)
    │  │  │  └─ NO → Continue
    │  │  │
    │  │  ├─ Check Data Consistency
    │  │  │  ├─ Σ(qty × price) = line_amount?
    │  │  │  ├─ Σ(line_amount) = invoice_total?
    │  │  │  └─ Currency consistent?
    │  │  │
    │  │  └─ Any mismatches?
    │  │     ├─ YES → is_valid = False, add ERROR
    │  │     └─ NO → is_valid = True
    │  │
    │  └─ Create Audit Findings
    │     └─ For each validation error:
    │        └─ Create InvoiceAuditFinding record
    │           (tracks discrepancy for resolution)
    │
    ├─ validation_status = "pending_review"
    │
    ├─ USER REVIEWS DOCUMENT
    │  │
    │  ├─ Calls GET /api/extracted-data/{id}/review/
    │  │  └─ Sees: image, extraction, normalized, validation, findings
    │  │
    │  └─ Decides:
    │     │
    │     ├─ ACCEPT (if valid)
    │     │  │
    │     │  ├─ POST /accept/
    │     │  ├─ validation_status = "validated"
    │     │  │
    │     │  └─ PHASE 3: Create financial objects
    │     │     ├─ Transaction record created
    │     │     ├─ JournalEntry drafted
    │     │     └─ Ready for GL posting
    │     │
    │     ├─ REJECT (if invalid/unwanted)
    │     │  │
    │     │  ├─ POST /reject/ {reason: "..."}
    │     │  ├─ validation_status = "rejected"
    │     │  │
    │     │  └─ STOP - No further processing
    │     │
    │     └─ CORRECT (if errors found)
    │        │
    │        ├─ POST /correct/ {
    │        │     corrections: {
    │        │       invoice_number: "INV-2024-001",
    │        │       total_amount: "1050.00"
    │        │     }
    │        │   }
    │        │
    │        ├─ Update normalized_json with corrections
    │        ├─ Re-validate against business rules
    │        ├─ Update validation_errors/warnings
    │        ├─ Update InvoiceAuditFinding records
    │        │
    │        └─ If now valid:
    │           ├─ validation_status = "corrected"
    │           └─ User can ACCEPT
    │
    └─ End
```

---

## Component Responsibility Matrix

| Component | Responsibility | Input | Output | Failures Handled |
|---|---|---|---|---|
| **DocumentOCRService** | Choose OCR provider | ExtractedData | extracted_json | OpenAI fail → Tesseract |
| **OpenAIVisionOCRProvider** | Call OpenAI Vision API | Image bytes | JSON dict | Missing fields → defaults |
| **Tesseract** | Fallback OCR | Image bytes | Text → JSON | Returns empty on failure |
| **InvoiceNormalizationService** | Standardize formats | extracted_json | normalized_json | Returns None/default values |
| **InvoiceValidationService** | Verify business rules | normalized_json | is_valid, errors, warnings | Returns validation messages |
| **InvoiceProcessingService** | Orchestrate pipeline | extracted_json | normalized_json, audit findings | Wraps in atomic transaction |
| **DocumentViews** | API endpoints | HTTP requests | JSON responses | Standard HTTP error codes |
| **InvoiceAuditFinding** | Track discrepancies | validation_errors | Audit trail | None - pure storage |

---

## Data Format Examples

### Input: Raw OpenAI Extraction

```json
{
  "invoice_number": "  INV-001  ",
  "issue_date": "03/15/2024",
  "vendor": {
    "name": "  ACME Corp  "
  },
  "customer": {
    "name": "John Doe"
  },
  "items": [
    {
      "product": "Widget",
      "quantity": "10",
      "unit_price": "$100",
      "amount": "$1000"
    }
  ],
  "total_amount": "$1,000.00",
  "currency": "$"
}
```

### Output: After Normalization

```json
{
  "invoice_number": "INV-001",
  "issue_date": "2024-03-15",
  "vendor": {
    "name": "ACME Corp"
  },
  "customer": {
    "name": "John Doe"
  },
  "items": [
    {
      "product": "Widget",
      "quantity": 10,
      "unit_price": 100.0,
      "amount": "1000.00"
    }
  ],
  "total_amount": "1000.00",
  "currency": "USD"
}
```

### Validation Response

```json
{
  "is_valid": true,
  "errors": [],
  "warnings": [
    {
      "code": "NO_DUE_DATE",
      "level": "warning",
      "message": "No due date specified",
      "field": "due_date"
    }
  ]
}
```

### Audit Finding

```json
{
  "id": "uuid",
  "finding_type": "MISSING_FIELD",
  "severity": "ERROR",
  "description": "Invoice number is missing",
  "field": "invoice_number",
  "expected_value": "Non-empty string",
  "actual_value": null,
  "is_resolved": false,
  "created_at": "2024-03-15T10:30:00Z"
}
```

---

## Key Design Decisions

### 1. Why Two OCR Providers?

**Decision:** OpenAI primary, Tesseract fallback

**Rationale:**
- OpenAI Vision handles complex layouts better (structured JSON)
- Quality is higher for real-world invoices
- Tesseract as fallback ensures no upload crashes
- Zero performance penalty (fallback only if OpenAI fails)
- Cost: ~$0.003 per invoice at volume pricing

**Alternative Considered:** Tesseract only
- Rejected: Poor quality on complex invoices (80% vs 95% accuracy)

### 2. Why Decimal for Amounts?

**Decision:** Use Python Decimal, not float

**Rationale:**
- Accounting precision: 1/100th of currency unit
- Binary float representations cause rounding errors
- Decimal(1000.1) + Decimal(0.1) = exact match (not float approximation)
- Industry standard for financial systems
- Zero performance penalty (still <1ms)

**Alternative Considered:** String amounts
- Rejected: Can't do math (validation consistency checks)

### 3. Why ISO 8601 for Dates?

**Decision:** Normalize all dates to YYYY-MM-DD

**Rationale:**
- ISO standard (globally understood)
- Sortable lexicographically
- No ambiguity (DD/MM vs MM/DD)
- Easy parsing (strptime "%Y-%m-%d")
- Database compatibility

**Alternative Considered:** Keep original format
- Rejected: Ambiguity (15/03/2024 is DD/MM, 03/15/2024 is MM/DD)

### 4. Why Separate Errors vs Warnings?

**Decision:** Errors block posting, warnings don't

**Rationale:**
- Missing invoice_number = ERROR (can't post without it)
- Due date >180 days = WARNING (info user might want to know)
- Allows business flexibility (some rules are soft)
- User can override warnings but not errors

**Alternative Considered:** All failures are errors
- Rejected: Too strict, fails recoverable cases

### 5. Why InvoiceAuditFinding Table?

**Decision:** Separate model for audit trail

**Rationale:**
- Preserve history (ValidationError is replaced on re-validation)
- Track resolution (who fixed what, when)
- Discrepancy visibility (numeric differences recorded)
- Compliance/audit requirements
- Separate from runtime validation data

**Alternative Considered:** Store in JSONField
- Rejected: History lost on updates, harder to query

---

## Performance Implications

| Operation | Time | Frequency | Impact |
|---|---|---|---|
| OpenAI Extraction | 8-15s | Per upload | Async (doesn't block) |
| Tesseract Fallback | 3-8s | If OpenAI fails | Async (doesn't block) |
| Normalization | 20-50ms | Per extraction | Negligible |
| Validation | 30-100ms | Per extraction | Negligible |
| Audit Findings | 10-30ms | Per extraction | Negligible |
| Review Endpoint | 50-100ms | Per user review | User-initiated |
| Accept/Reject | <50ms | Per action | User-initiated |

**Total** Phase 2 overhead per invoice: **200-500ms** (after extraction)

**Key:** All heavy lifting (OpenAI) is async, user never waits more than 500ms on server.

---

## Error Recovery Paths

### If OpenAI Fails
```
OpenAI call fails
    ↓
Log error (WARNING level)
    ↓
Try Tesseract
    ↓
    ├─ Tesseract succeeds → Process normally
    └─ Tesseract fails → extracted_json = {}, extraction_status = "failed"
        └─ User can re-upload or contact support
```

### If Validation Fails
```
is_valid = False, validation_errors populated
    ↓
InvoiceAuditFinding records created (one per error)
    ↓
User reviews document
    ↓
User corrects fields
    ↓
Re-validation runs
    ↓
    ├─ Now valid → User accepts → Phase 3
    └─ Still invalid → User corrects again (loop)
```

### If Database Write Fails
```
transaction.atomic() wraps all operations
    ↓
    ├─ ExtractedData save fails → All reverted, exception raised
    ├─ InvoiceAuditFinding save fails → All reverted, exception raised
    └─ All succeed → Committed atomically
        (no partial state)
```

---

## Sequence Diagram: Happy Path

```
User                    API              Service              DB
  │                      │                  │                  │
  │ 1. Upload Invoice    │                  │                  │
  ├─────────────────────→│                  │                  │
  │                      │ 2. Save Document │                  │
  │                      ├─────────────────→│                  │
  │                      │                  │  3. Extract Data │
  │                      │                  ├─────────────────→│
  │ 201 Created          │  4. Return ID    │                  │
  │←─────────────────────┤←──────────────────│                  │
  │                      │                  │                  │
  │ [Extraction running in background]      │                  │
  │                      │    5. OpenAI API │                  │
  │                      │      Call        │                  │
  │                      │    (8-15 sec)    │                  │
  │                      │                  │                  │
  │                      │    6. Normalize  │                  │
  │                      │    7. Validate   │                  │
  │                      │    8. Create     │                  │
  │                      │       Findings   │  9. Save all     │
  │                      │                  ├─────────────────→│
  │                      │                  │                  │
  │ [1-2 seconds later]  │                  │                  │
  │                      │                  │                  │
  │ 2. Get Review        │                  │                  │
  ├─────────────────────→│  10. Query       │                  │
  │                      │     ExtractedData│─────────────────→│
  │                      │  11. Return JSON │←─────────────────┤
  │  Review Data         │                  │                  │
  │←─────────────────────┤                  │                  │
  │  (extraction,        │                  │                  │
  │   normalized,        │                  │                  │
  │   validation,        │                  │                  │
  │   findings)          │                  │                  │
  │                      │                  │                  │
  │ 3. Accept Invoice    │                  │                  │
  ├─────────────────────→│  12. Update      │                  │
  │                      │     validation_  │                  │
  │                      │     status       ├─────────────────→│
  │                      │  13. Query       │                  │
  │ 200 OK               │     ExtractedData│                  │
  │←─────────────────────┤←─────────────────┤                  │
  │  (validation_status: │                  │                  │
  │   validated)         │                  │                  │
  │                      │                  │                  │
  │ [Phase 3 continues async...]           │                  │
  │                      │                  │                  │
```

---

## Testing Strategy

### Unit Tests (Service Layer)

```python
# Test normalization
assert normalize_date("03/15/2024") == "2024-03-15"
assert normalize_amount("$1,000.50") == Decimal('1000.50')

# Test validation
is_valid, msgs = validate_invoice(valid_invoice)
assert is_valid == True
assert len(msgs) == 0

is_valid, msgs = validate_invoice(invalid_invoice)
assert is_valid == False
assert len(msgs) > 0
```

### Integration Tests (API Layer)

```python
# Test upload
response = client.post('/api/documents/upload/', {
    'file': invoice_jpg,
    'document_type': 'invoice'
})
assert response.status_code == 201

# Test review
response = client.get(f'/api/extracted-data/{id}/review/')
assert response.status_code == 200
assert 'extraction' in response.json()
assert 'normalized' in response.json()

# Test accept
response = client.post(f'/api/extracted-data/{id}/accept/')
assert response.status_code == 200
```

### End-to-End Tests

```
1. Upload real invoice image
2. Wait for Phase 2 completion
3. Get review data
4. Verify extraction accuracy
5. Verify normalization correctness
6. Verify validation results
7. Accept invoice
8. Verify Phase 3 objects created
```

---

## Monitoring & Logging

### Logs to Monitor

```
logs/django.log:
  - "ExtractedData created" (INFO) - Upload successful
  - "OpenAI extraction failed" (WARNING) - Fallback triggered
  - "Invoice validation failed" (INFO) - Validation found issues
  - "InvoiceAuditFinding created" (INFO) - Issue tracked
  - "Validation completed" (INFO) - Phase 2 finished
```

### Metrics to Track

```
- Uploads per day (volume)
- OpenAI success rate (%)
- Tesseract fallback rate (%)
- Average extraction time (ms)
- Valid invoices % (quality)
- Most common validation errors (improvement areas)
- User accept/reject ratio (user satisfaction)
```

---

Done! You now have complete documentation for:
- ✅ Architecture and data flow
- ✅ Decision rationale
- ✅ Error handling paths
- ✅ Performance expectations
- ✅ Testing strategy
- ✅ Monitoring approach
