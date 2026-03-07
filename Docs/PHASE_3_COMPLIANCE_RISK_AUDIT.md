# Phase 3: Invoice Compliance, Risk Scoring & Audit Trail

## Overview

Phase 3 completes the invoice extraction pipeline by adding:

1. **Compliance Checks** - 9 different compliance checks on invoice data
2. **Risk Scoring** - Numeric risk score (0-100) + risk level classification
3. **Audit Summary** - OpenAI-generated executive summary with key risks and actions
4. **Audit Trail** - Complete event log of all processing steps
5. **Audit Findings** - Formal findings from failed compliance checks

**When it Runs:** Automatically after Phase 2 (normalization & validation)

**Time:** <500ms additional per invoice

---

## 9 Compliance Checks

### 1. Invoice Number Check
**Check Name:** `invoice_number`

Validates invoice number presence and format.

**Checks:**
- Invoice number must be present (not empty)
- Invoice number must be ≤50 characters
- Format must be alphanumeric with dashes/slashes allowed

**Severity Mapping:**
- Missing → CRITICAL
- Unusually long → WARNING
- Invalid format → WARNING

**Example:**
```json
{
  "check_name": "invoice_number",
  "status": "PASS",
  "severity": "INFO",
  "message": "Invoice number 'INV-2024-001' is valid"
}
```

---

### 2. Vendor Presence Check
**Check Name:** `vendor_presence`

Validates vendor (seller) information.

**Checks:**
- Vendor name must be present
- TAX ID/TIN should be present (warning if missing)

**Severity Mapping:**
- Missing vendor name → CRITICAL
- Missing TAX ID → WARNING
- Complete vendor info → INFO

**Example:**
```json
{
  "check_name": "vendor_presence",
  "status": "PASS",
  "severity": "INFO",
  "message": "Vendor 'ACME Corp' with TAX ID present"
}
```

---

### 3. Customer Presence Check
**Check Name:** `customer_presence`

Validates customer (buyer) information.

**Checks:**
- Customer name must be present
- TAX ID/TIN should be present (warning if missing)

**Severity Mapping:**
- Missing customer name → CRITICAL
- Missing TAX ID → WARNING
- Complete customer info → INFO

**Example:**
```json
{
  "check_name": "customer_presence",
  "status": "PASS",
  "severity": "INFO",
  "message": "Customer 'John Doe' with TAX ID present"
}
```

---

### 4. Items Existence Check
**Check Name:** `items_existence`

Validates line items are present and reasonable count.

**Checks:**
- At least one line item must exist
- Item count should not exceed 1000 (unusual if > 1000)

**Severity Mapping:**
- No items → CRITICAL
- > 1000 items → WARNING
- Normal count (1-1000) → INFO

**Example:**
```json
{
  "check_name": "items_existence",
  "status": "PASS",
  "severity": "INFO",
  "message": "Invoice has 5 line item(s)"
}
```

---

### 5. Total Consistency Check
**Check Name:** `total_consistency`

Validates invoice total matches sum of line items.

**Checks:**
- Calculate sum of all line item amounts
- Compare with invoice total
- Tolerance: ±$0.01

**Severity Mapping:**
- Sum missing or can't calculate → CRITICAL
- Mismatch > $0.01 → CRITICAL
- Matches within tolerance → INFO

**Example:**
```json
{
  "check_name": "total_consistency",
  "status": "PASS",
  "severity": "INFO",
  "message": "Total 1000.00 matches line items sum 1000.00"
}
```

---

### 6. VAT/TIN Check
**Check Name:** `vat_tin_check`

Validates VAT/TAX ID presence for both parties.

**Checks:**
- Vendor TAX ID present
- Customer TAX ID present
- Both or either missing?

**Severity Mapping:**
- Both missing → ERROR
- One missing → WARNING
- Both present → INFO

**Example:**
```json
{
  "check_name": "vat_tin_check",
  "status": "PASS",
  "severity": "INFO",
  "message": "Both vendor and customer TAX IDs present"
}
```

---

### 7. Due Date Logic Check
**Check Name:** `due_date_logic`

Validates due date is reasonable and after issue date.

**Checks:**
- Due date must be after issue date
- Due date should be ≤365 days from issue date
- Due date 180-365 days → warning (unusual)

**Severity Mapping:**
- No due date → WARNING
- Due date before issue date → CRITICAL
- Due date > 365 days → WARNING
- Due date 180-365 days → WARNING
- Normal → INFO

**Example:**
```json
{
  "check_name": "due_date_logic",
  "status": "PASS",
  "severity": "INFO",
  "message": "Due date is 30 days after issue date (valid)"
}
```

---

### 8. Currency Validity Check
**Check Name:** `currency_validity`

Validates currency is valid ISO 4217 code.

**Valid Codes:** USD, EUR, GBP, JPY, CHF, CAD, AUD, NZD, CNY, INR, MXN, BRL, ZAR, SGD, HKD, AED, SAR, QAR, KWD, etc.

**Severity Mapping:**
- Missing currency → ERROR
- Valid ISO code → INFO
- Unknown code → WARNING

**Example:**
```json
{
  "check_name": "currency_validity",
  "status": "PASS",
  "severity": "INFO",
  "message": "Currency 'USD' is valid ISO 4217 code"
}
```

---

### 9. Suspicious Discount Detection
**Check Name:** `suspicious_discount`

Detects unusually large discounts (fraud risk indicator).

**Checks:**
- Calculate discount percentage for each line item
- Flag if any item has discount > 5%
- Severity based on discount size

**Severity Mapping:**
- No discounts → INFO
- 5-25% discount → INFO
- 25-50% discount → WARNING
- > 50% discount → CRITICAL

**Example:**
```json
{
  "check_name": "suspicious_discount",
  "status": "PASS",
  "severity": "INFO",
  "message": "No suspicious discounts detected"
}
```

---

## Risk Scoring

### Calculation Method

Each compliance check contributes to overall risk:

**Severity Weights:**
- INFO → 0 points
- WARNING → 10 points
- ERROR → 25 points
- CRITICAL → 50 points

**Status Weights:**
- PASS → 0 points
- AVAILABLE (incomplete) → 5 points
- WARNING → 15 points
- INVALID → 25 points
- MISSING → 40 points

**Final Risk Score:** Sum of all weights, capped at 100

### Risk Levels

| Score Range | Level | Action |
|---|---|---|
| 0-20 | **Low** | Approve automatically |
| 21-50 | **Medium** | Review recommended |
| 51-80 | **High** | Manual review required |
| 81+ | **Critical** | Requires approval + supervisor sign-off |

### Risk Level Determination

```python
if critical_checks > 0:
    risk_level = "Critical"
elif risk_score >= 80 or error_checks >= 3:
    risk_level = "High"
elif risk_score >= 40 or error_checks >= 1:
    risk_level = "Medium"
else:
    risk_level = "Low"
```

### Example Risk Scores

**Low Risk Invoice:**
```
Invoice number: PASS (0)
Vendor: PASS (0)
Customer: PASS (0)
Items: PASS (0)
Total: PASS (0)
VAT/TIN: PASS (0)
Due date: PASS (0)
Currency: PASS (0)
Discount: PASS (0)

Total Score: 0/100 → Risk Level: Low ✅
```

**High Risk Invoice:**
```
Invoice number: PASS (0)
Vendor: PASS (0)
Customer: MISSING (CRITICAL - 50)
Items: PASS (0)
Total: CRITICAL (50)
VAT/TIN: ERROR (25)
Due date: WARNING (10)
Currency: PASS (0)
Discount: CRITICAL (50)

Total Score: 185 → Capped at 100 → Risk Level: Critical 🔴
```

---

## Audit Summary (OpenAI Generated)

Phase 3 uses OpenAI to generate a comprehensive audit summary.

### Summary Sections

**1. Executive Summary** (2-3 sentences)
High-level overview of invoice quality and readiness.

**2. Key Risks** (top 3-5)
Most important issues identified with severity.

**3. Recommended Actions** (list)
Specific steps to address identified issues.

**4. Final Status**
- `READY_TO_POST` - Safe to proceed
- `REVIEW_RECOMMENDED` - Manual review suggested
- `REQUIRES_REVIEW` - Must review before posting
- `BLOCKED_FOR_REVIEW` - Critical issues must be resolved

### Fallback Summary (Rule-Based)

If OpenAI is unavailable, rule-based summary is generated:

```python
# Based on risk level and validation results
if risk_level == "Critical":
    status = "BLOCKED_FOR_REVIEW"
    summary = "Invoice has critical compliance issues..."
elif risk_level == "High":
    status = "REQUIRES_REVIEW"
    summary = "Invoice has significant issues..."
```

### Example Response

```json
{
  "audit_summary": {
    "executive_summary": "Invoice INV-2024-001 from ACME Corp appears valid and complete with minimal issues. All critical compliance checks passed and data consistency verified.",
    "key_risks": [
      "Due date is 90 days away (slightly long payment term)",
      "No VAT/TIN information for customer (minor issue)"
    ],
    "recommended_actions": [
      "Verify customer TAX ID if required for jurisdiction",
      "Confirm payment terms with vendor",
      "Standard accounting review before posting"
    ],
    "final_status": "READY_TO_POST",
    "requires_review": false,
    "generated_by": "openai"
  }
}
```

---

## Audit Trail

Complete event log of all processing steps.

### Event Types

| Event Type | Fired When | Phase |
|---|---|---|
| `upload` | Document uploaded | Setup |
| `extraction` | OpenAI extraction completes | Phase 1 |
| `normalization` | Data normalization completes | Phase 2 |
| `validation` | Validation checks complete | Phase 2 |
| `compliance_check` | All 9 checks complete | Phase 3 |
| `risk_score` | Risk score calculated | Phase 3 |
| `audit_summary` | Summary generated | Phase 3 |
| `review` | User opens review | Review |
| `accept` | User accepts invoice | Review |
| `reject` | User rejects invoice | Review |
| `correct` | User corrects fields | Review |
| `finding_created` | Audit finding created | Throughout |
| `finding_resolved` | Finding marked resolved | Throughout |

### Audit Trail Entry Structure

```json
{
  "id": "uuid",
  "event_type": "compliance_check",
  "title": "Compliance checks completed successfully",
  "description": "All 9 compliance checks executed",
  "severity": "info",
  "event_time": "2024-03-15T10:30:45Z",
  "success": true,
  "phase": "phase3",
  "duration_ms": 245,
  "result_summary": "Risk Level: Medium, Score: 45/100"
}
```

### Audit Trail Timeline Example

```
10:25:00 → Upload: Document uploaded
10:25:05 → Extraction: OpenAI Vision extraction completed (confidence: 92)
10:25:10 → Normalization: Invoice data normalized
10:25:15 → Validation: 0 errors, 2 warnings
10:25:20 → Compliance: 9 checks, 1 warning
10:25:25 → Risk Score: Score 35/100, Level: Medium
10:25:30 → Audit Summary: Status = REVIEW_RECOMMENDED
10:26:00 → Review: User opened review (john.doe@example.com)
10:27:15 → Accept: User accepted invoice
```

---

## Audit Findings from Compliance

For each failed compliance check, an `InvoiceAuditFinding` record is created.

### Mapping: Check → Finding

| Check | Finding Type | Severity Mapping |
|---|---|---|
| invoice_number | missing_field | CRITICAL → critical |
| vendor_presence | missing_field | CRITICAL → critical |
| customer_presence | missing_field | CRITICAL → critical |
| items_existence | missing_field | CRITICAL → critical |
| total_consistency | total_mismatch | CRITICAL → critical |
| vat_tin_check | vat_flag | ERROR → high |
| due_date_logic | date_mismatch | CRITICAL → critical |
| currency_validity | invalid_value | WARNING → medium |
| suspicious_discount | other | CRITICAL → critical |

### Finding with Full Details

```json
{
  "id": "uuid",
  "finding_type": "total_mismatch",
  "severity": "critical",
  "description": "Sum of line totals (950.00) does not match invoice total (1000.00)",
  "field": "total_amount",
  "expected_value": "950.00",
  "actual_value": "1000.00",
  "difference": 50.00,
  "is_resolved": false,
  "created_at": "2024-03-15T10:25:20Z"
}
```

---

## Review Endpoint Response (Complete)

### GET /api/extracted-data/{id}/review/

Returns complete snapshot including Phase 3 data:

```json
{
  "id": "uuid",
  "document": { ... },
  "extracted_invoice": { ... },
  "normalized_invoice": { ... },
  "validation": { ... },
  "audit_findings": [ ... ],
  "compliance": {
    "checks": [
      {
        "check_name": "invoice_number",
        "status": "PASS",
        "severity": "INFO",
        "message": "Invoice number 'INV-2024-001' is valid"
      },
      // ... 8 more checks
    ],
    "risk_score": 35,
    "risk_level": "Medium",
    "completed_at": "2024-03-15T10:25:30Z"
  },
  "audit_summary": {
    "executive_summary": "...",
    "key_risks": [ ... ],
    "recommended_actions": [ ... ],
    "final_status": "REVIEW_RECOMMENDED",
    "requires_review": true
  },
  "audit_trail": [
    {
      "event_type": "upload",
      "title": "Document uploaded",
      "event_time": "2024-03-15T10:25:00Z",
      "success": true,
      "phase": null
    },
    {
      "event_type": "extraction",
      "title": "Invoice extracted via OpenAI Vision",
      "event_time": "2024-03-15T10:25:05Z",
      "success": true,
      "phase": "phase1"
    },
    // ... more events
  ],
  "status": "pending",
  "extraction_status": "extracted"
}
```

---

## Full Processing Timeline

```
Phase 1: Extraction (8-15s)
├─ Upload document
├─ Call OpenAI Vision API
├─ Fallback to Tesseract if needed
└─ Save extracted_json

Phase 2: Normalization & Validation (200-500ms)
├─ Normalize dates → ISO 8601
├─ Normalize amounts → Decimal
├─ Normalize currency → ISO codes
├─ Validate required fields
├─ Validate business rules
├─ Validate data consistency
└─ Create audit findings

Phase 3: Compliance, Risk & Audit (200-300ms)
├─ Run 9 compliance checks
├─ Calculate risk score (0-100)
├─ Determine risk level
├─ Generate audit summary
├─ Create audit trail entries
└─ Create findings from checks

User Review & Action
├─ GET /review/ → See all Phase 1+2+3 data
├─ POST /accept/ → Mark as validated
├─ POST /reject/ → Reject with reason
└─ POST /correct/ → Correct fields → re-validate

Phase 4: Financial Posting (Future)
├─ Create Transaction record
├─ Create JournalEntry draft
├─ Flag VAT transactions
└─ Prepare for GL posting
```

---

## Database Schema

### compliance_checks (JSONField in ExtractedData)

Stores array of compliance check results:

```json
[
  {
    "check_name": "invoice_number",
    "status": "PASS",
    "severity": "INFO",
    "message": "..."
  },
  // ... 8 more
]
```

### risk fields (ExtractedData)

- `risk_score` (IntegerField) - 0-100
- `risk_level` (CharField) - Low/Medium/High/Critical

### audit_summary (JSONField)

```json
{
  "executive_summary": "...",
  "key_risks": [ "risk1", "risk2" ],
  "recommended_actions": [ "action1", "action2" ],
  "final_status": "READY_TO_POST",
  "requires_review": false,
  "generated_by": "openai" | "rule_based"
}
```

### AuditTrail Table

Records all events with timestamps, user, result summary.

---

## Configuration

**Environment Variables:**
```bash
OPENAI_API_KEY=sk-...  # For OpenAI summary generation
```

**Settings:**
- Compliance check tolerance: ±$0.01
- Max invoice amount: $999,999.99
- Max items per invoice: 1000
- Max discount to investigate: > 50%

---

## Next Steps (Phase 4)

Phase 3 completes the audit pipeline. Next phase creates financial objects:

1. Create Transaction from validated invoice
2. Map vendor/customer to Chart of Accounts
3. Create JournalEntry in draft
4. Flag VAT transactions
5. Prepare for GL posting

---

## Support & Testing

### Test Phase 3 Manually

```bash
# 1. Upload invoice (triggers full pipeline)
curl -X POST http://localhost:8000/api/documents/upload/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@invoice.jpg" \
  -F "document_type=invoice"

# 2. Get review with Phase 3 data
curl -X GET http://localhost:8000/api/extracted-data/{id}/review/ \
  -H "Authorization: Bearer $TOKEN"

# 3. Check compliance and risk data
echo "Risk Score: $(jq '.compliance.risk_score' review.json)"
echo "Risk Level: $(jq '.compliance.risk_level' review.json)"
echo "Checks: $(jq '.compliance.checks | length' review.json)"
```

### Check Audit Trail Directly

```bash
# Via Django shell
python manage.py shell
>>> from documents.models import AuditTrail
>>> AuditTrail.objects.filter(extracted_data_id='...').order_by('event_time')
```

---

**Phase 3 is complete and production-ready!** 🚀
