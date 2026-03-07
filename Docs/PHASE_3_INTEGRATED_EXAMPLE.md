# Phase 3 Integrated Example & Walkthrough

## Complete End-to-End Flow

This document shows a complete invoice processing example from upload through Phase 3 with actual API calls and responses.

---

## Scenario: ACME Corp Invoice Processing

### Invoice Details
- Vendor: ACME Corporation (TIN: 123-456-789)
- Invoice #: INV-2024-0527
- Customer: ABC Industries (TIN: 987-654-321)
- Date: March 15, 2024
- Due: April 15, 2024 (31 days)
- Items: 3 line items
- Amount: $5,500 USD

### Timeline
```
10:25:00 → Upload
10:25:05 → Phase 1: Extraction
10:25:15 → Phase 2: Normalization & Validation
10:25:25 → Phase 3: Compliance & Risk
10:26:00 → User opens review
10:27:00 → User accepts invoice
```

---

## Step 1: Document Upload

### Request
```bash
curl -X POST http://localhost:8000/api/documents/upload/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -F "file=@acme_invoice_2024_0527.jpg" \
  -F "document_type=invoice"
```

### Response (201 Created)
```json
{
  "id": "a1b2c3d4-e5f6-4789-abcd-ef1234567890",
  "document": {
    "id": "d4c3b2a1-f6e5-4321-dcba-098765432109",
    "file_name": "acme_invoice_2024_0527.jpg",
    "file_type": "image/jpeg",
    "file_size": 285000,
    "storage_url": "/media/documents/acme_invoice_2024_0527.jpg",
    "document_type": "invoice",
    "uploaded_at": "2024-03-15T10:25:00.123456Z"
  },
  "extracted_json": {
    "invoice_number": "INV-2024-0527",
    "issue_date": "2024-03-15",
    "vendor": {
      "name": "ACME Corporation",
      "address": "123 Industrial Ave, Tech City, TC 12345",
      "tax_id": "123-456-789"
    },
    "customer": {
      "name": "ABC Industries",
      "address": "456 Business Blvd, Commerce City, CC 67890",
      "tax_id": "987-654-321"
    },
    "items": [
      {
        "product": "Industrial Widget Premium",
        "quantity": 50,
        "unit_price": 100.00,
        "amount": 5000.00
      },
      {
        "product": "Installation Service",
        "quantity": 1,
        "unit_price": 300.00,
        "amount": 300.00
      },
      {
        "product": "Training & Documentation",
        "quantity": 1,
        "unit_price": 200.00,
        "amount": 200.00
      }
    ],
    "subtotal": 5500.00,
    "tax_amount": 0.00,
    "total_amount": 5500.00,
    "currency": "USD",
    "due_date": "2024-04-15"
  },
  "extraction_status": "extracted",
  "confidence": 94,
  "extracted_at": "2024-03-15T10:25:05.234567Z"
}
```

**What happened:**
- Upload triggered Phase 1 (OpenAI extraction in background)
- Response includes raw extracted data
- Confidence score: 94% (excellent)

---

## Step 2: Phase 2 Processing (Automatic)

*Processing happens in background after upload completes*

### Phase 2 Operations

**Normalization:**
```
- Dates: "2024-03-15" → "2024-03-15" ✅
- Amounts: 5500.00 → Decimal('5500.00') ✅
- Currency: "USD" → "USD" (ISO 4217) ✅
- Strings: "ACME Corporation" → "ACME Corporation" ✅
```

**Validation (Phase 2):**
```
Required Fields:
✅ invoice_number: INV-2024-0527
✅ issue_date: 2024-03-15
✅ vendor_name: ACME Corporation
✅ items: 3 items
✅ total_amount: 5500.00

Business Rules:
✅ issue_date ≤ due_date: 2024-03-15 ≤ 2024-04-15 ✅
✅ Currency valid (USD) ✅
✅ Amounts positive ✅

Consistency:
✅ Line items total: 5000 + 300 + 200 = 5500 ✅
✅ Invoice total: 5500 ✅
✅ Match within tolerance ✅

Result: VALID ✅
```

---

## Step 3: Phase 3 Processing (Automatic)

*Starts after Phase 2 completes, ~200-300ms*

### Compliance Checks

Let's see what happens with each of the 9 compliance checks:

#### Check 1: Invoice Number
```json
{
  "check_name": "invoice_number",
  "status": "PASS",
  "severity": "INFO",
  "message": "Invoice number 'INV-2024-0527' is valid"
}
```
✅ Present, format valid

#### Check 2: Vendor Presence
```json
{
  "check_name": "vendor_presence",
  "status": "PASS",
  "severity": "INFO",
  "message": "Vendor 'ACME Corporation' with TAX ID present"
}
```
✅ Complete vendor info with TIN

#### Check 3: Customer Presence
```json
{
  "check_name": "customer_presence",
  "status": "PASS",
  "severity": "INFO",
  "message": "Customer 'ABC Industries' with TAX ID present"
}
```
✅ Complete customer info with TIN

#### Check 4: Items Existence
```json
{
  "check_name": "items_existence",
  "status": "PASS",
  "severity": "INFO",
  "message": "Invoice has 3 line item(s)"
}
```
✅ Normal item count (3 items)

#### Check 5: Total Consistency
```json
{
  "check_name": "total_consistency",
  "status": "PASS",
  "severity": "INFO",
  "message": "Total 5500.00 matches line items sum 5500.00"
}
```
✅ Perfect match

#### Check 6: VAT/TIN Check
```json
{
  "check_name": "vat_tin_check",
  "status": "PASS",
  "severity": "INFO",
  "message": "Both vendor and customer TAX IDs present"
}
```
✅ Both parties have TIN

#### Check 7: Due Date Logic
```json
{
  "check_name": "due_date_logic",
  "status": "PASS",
  "severity": "INFO",
  "message": "Due date is 31 days after issue date (valid)"
}
```
✅ Reasonable payment terms (31 days)

#### Check 8: Currency Validity
```json
{
  "check_name": "currency_validity",
  "status": "PASS",
  "severity": "INFO",
  "message": "Currency 'USD' is valid ISO 4217 code"
}
```
✅ Recognized currency

#### Check 9: Suspicious Discount
```json
{
  "check_name": "suspicious_discount",
  "status": "PASS",
  "severity": "INFO",
  "message": "No suspicious discounts detected"
}
```
✅ No unusual markdowns

### Risk Score Calculation

**Scoring:**
```
Check 1 (invoice_number):     INFO (0)
Check 2 (vendor_presence):    INFO (0)
Check 3 (customer_presence):  INFO (0)
Check 4 (items_existence):    INFO (0)
Check 5 (total_consistency):  INFO (0)
Check 6 (vat_tin_check):      INFO (0)
Check 7 (due_date_logic):     INFO (0)
Check 8 (currency_validity):  INFO (0)
Check 9 (suspicious_discount):INFO (0)

Total Score: 0/100
Status: All PASS, no critical issues
Critical issues: 0
Error-level issues: 0

→ Risk Level: LOW ✅
```

### Audit Summary (OpenAI Generated)

```json
{
  "executive_summary": "Invoice INV-2024-0527 from ACME Corporation to ABC Industries is complete and well-documented. All critical compliance checks pass, financial data is consistent, and both parties have valid TAX IDs. This invoice appears ready for posting.",
  "key_risks": [
    "No significant risks identified",
    "Payment terms are reasonable (31 days)",
    "All required information present"
  ],
  "recommended_actions": [
    "Verify ACME Corporation is in approved vendor list",
    "Confirm ABC Industries account is active",
    "Standard accounting review for GL posting"
  ],
  "final_status": "READY_TO_POST",
  "requires_review": false,
  "generated_by": "openai"
}
```

---

## Step 4: User Opens Review

```bash
curl -X GET "http://localhost:8000/api/extracted-data/a1b2c3d4-e5f6-4789-abcd-ef1234567890/review/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Response (Complete Review Data)

```json
{
  "id": "a1b2c3d4-e5f6-4789-abcd-ef1234567890",
  
  "document": {
    "id": "d4c3b2a1-f6e5-4321-dcba-098765432109",
    "file_name": "acme_invoice_2024_0527.jpg",
    "image_url": "http://localhost:8000/media/documents/acme_invoice_2024_0527.jpg",
    "uploaded_at": "2024-03-15T10:25:00.123456Z"
  },
  
  "extracted_invoice": {
    "invoice_number": "INV-2024-0527",
    "vendor_name": "ACME Corporation",
    "customer_name": "ABC Industries",
    "invoice_date": "2024-03-15T00:00:00Z",
    "due_date": "2024-04-15T00:00:00Z",
    "total_amount": 5500.00,
    "currency": "USD",
    "items": [
      {"product": "Industrial Widget Premium", "quantity": "50", "unit_price": "100.00", "amount": "5000.00"},
      {"product": "Installation Service", "quantity": "1", "unit_price": "300.00", "amount": "300.00"},
      {"product": "Training & Documentation", "quantity": "1", "unit_price": "200.00", "amount": "200.00"}
    ],
    "confidence": 94
  },
  
  "normalized_invoice": {
    "invoice_number": "INV-2024-0527",
    "issue_date": "2024-03-15",
    "vendor": {"name": "ACME Corporation", "tax_id": "123-456-789"},
    "customer": {"name": "ABC Industries", "tax_id": "987-654-321"},
    "items": [
      {"product": "Industrial Widget Premium", "quantity": 50, "unit_price": 100.00, "amount": "5000.00"},
      {"product": "Installation Service", "quantity": 1, "unit_price": 300.00, "amount": "300.00"},
      {"product": "Training & Documentation", "quantity": 1, "unit_price": 200.00, "amount": "200.00"}
    ],
    "total_amount": "5500.00",
    "currency": "USD",
    "due_date": "2024-04-15"
  },
  
  "validation": {
    "is_valid": true,
    "completed_at": "2024-03-15T10:25:15.345678Z",
    "errors": [],
    "warnings": []
  },
  
  "audit_findings": [],
  
  "compliance": {
    "checks": [
      {
        "check_name": "invoice_number",
        "status": "PASS",
        "severity": "INFO",
        "message": "Invoice number 'INV-2024-0527' is valid"
      },
      {
        "check_name": "vendor_presence",
        "status": "PASS",
        "severity": "INFO",
        "message": "Vendor 'ACME Corporation' with TAX ID present"
      },
      {
        "check_name": "customer_presence",
        "status": "PASS",
        "severity": "INFO",
        "message": "Customer 'ABC Industries' with TAX ID present"
      },
      {
        "check_name": "items_existence",
        "status": "PASS",
        "severity": "INFO",
        "message": "Invoice has 3 line item(s)"
      },
      {
        "check_name": "total_consistency",
        "status": "PASS",
        "severity": "INFO",
        "message": "Total 5500.00 matches line items sum 5500.00"
      },
      {
        "check_name": "vat_tin_check",
        "status": "PASS",
        "severity": "INFO",
        "message": "Both vendor and customer TAX IDs present"
      },
      {
        "check_name": "due_date_logic",
        "status": "PASS",
        "severity": "INFO",
        "message": "Due date is 31 days after issue date (valid)"
      },
      {
        "check_name": "currency_validity",
        "status": "PASS",
        "severity": "INFO",
        "message": "Currency 'USD' is valid ISO 4217 code"
      },
      {
        "check_name": "suspicious_discount",
        "status": "PASS",
        "severity": "INFO",
        "message": "No suspicious discounts detected"
      }
    ],
    "risk_score": 0,
    "risk_level": "Low",
    "completed_at": "2024-03-15T10:25:25.456789Z"
  },
  
  "audit_summary": {
    "executive_summary": "Invoice INV-2024-0527 from ACME Corporation to ABC Industries is complete and well-documented. All critical compliance checks pass, financial data is consistent, and both parties have valid TAX IDs.",
    "key_risks": [
      "No significant risks identified"
    ],
    "recommended_actions": [
      "Verify ACME Corporation is in approved vendor list",
      "Standard accounting review for GL posting"
    ],
    "final_status": "READY_TO_POST",
    "requires_review": false,
    "generated_by": "openai"
  },
  
  "audit_trail": [
    {
      "id": "trail-001",
      "event_type": "upload",
      "title": "Document uploaded",
      "description": "Invoice file uploaded via API",
      "severity": "info",
      "event_time": "2024-03-15T10:25:00.123456Z",
      "success": true,
      "phase": null
    },
    {
      "id": "trail-002",
      "event_type": "extraction",
      "title": "Invoice extracted via OpenAI Vision",
      "description": "Extracted JSON from invoice image",
      "severity": "info",
      "event_time": "2024-03-15T10:25:05.234567Z",
      "success": true,
      "phase": "phase1"
    },
    {
      "id": "trail-003",
      "event_type": "normalization",
      "title": "Invoice data normalized",
      "description": "Applied normalization to dates, amounts, currency",
      "severity": "info",
      "event_time": "2024-03-15T10:25:10.345678Z",
      "success": true,
      "phase": "phase2"
    },
    {
      "id": "trail-004",
      "event_type": "validation",
      "title": "Invoice validation completed",
      "description": "Validation passed: 0 errors, 0 warnings",
      "severity": "info",
      "event_time": "2024-03-15T10:25:15.456789Z",
      "success": true,
      "phase": "phase2"
    },
    {
      "id": "trail-005",
      "event_type": "compliance_check",
      "title": "Compliance checks completed",
      "description": "All 9 compliance checks executed",
      "severity": "info",
      "event_time": "2024-03-15T10:25:20.567890Z",
      "success": true,
      "phase": "phase3"
    },
    {
      "id": "trail-006",
      "event_type": "audit_summary",
      "title": "Audit summary generated",
      "description": "OpenAI audit summary completed",
      "severity": "info",
      "event_time": "2024-03-15T10:25:25.678901Z",
      "success": true,
      "phase": "phase3"
    }
  ],
  
  "status": "pending",
  "extraction_status": "extracted",
  "extracted_at": "2024-03-15T10:25:05.234567Z"
}
```

**What the user sees:**
- ✅ All 9 compliance checks passed
- ✅ Risk Score: 0/100 (Low)
- ✅ Ready to post immediately
- ✅ Complete audit trail of processing
- ✅ Original image, extracted data, normalized data
- ✅ No errors or warnings

---

## Step 5: User Accepts Invoice

```bash
curl -X POST "http://localhost:8000/api/extracted-data/a1b2c3d4-e5f6-4789-abcd-ef1234567890/accept/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "All compliance checks passed. Vendor approved. Proceeding with posting."
  }'
```

### Response (200 OK)
```json
{
  "id": "a1b2c3d4-e5f6-4789-abcd-ef1234567890",
  "status": "pending",
  "validation_status": "validated",
  "updated_at": "2024-03-15T10:27:00.123456Z",
  "message": "Invoice accepted and ready for GL posting"
}
```

**What happened:**
- Validation status changed from "pending" to "validated"
- Audit trail entry created
- Invoice now ready for Phase 4 (financial posting)

---

## Database State After Complete Processing

### ExtractedData Record

```sql
SELECT * FROM extracted_data WHERE id = 'a1b2c3d4-e5f6-4789-abcd-ef1234567890';

/* Results:
id: a1b2c3d4-e5f6-4789-abcd-ef1234567890
document_id: d4c3b2a1-f6e5-4321-dcba-098765432109
organization_id: org-uuid
vendor_name: ACME Corporation
customer_name: ABC Industries
invoice_number: INV-2024-0527
invoice_date: 2024-03-15
due_date: 2024-04-15
total_amount: 5500.00
currency: USD
confidence: 94
validation_status: validated
is_valid: TRUE
validation_completed_at: 2024-03-15 10:25:15 UTC
extraction_status: extracted
extraction_completed_at: 2024-03-15 10:25:05 UTC
compliance_checks: [9 check objects with PASS/PASS/... status]
risk_score: 0
risk_level: Low
audit_summary: {executive_summary: "...", key_risks: [], ...}
audit_completed_at: 2024-03-15 10:25:25 UTC
validated_by_id: user-uuid
validated_at: 2024-03-15 10:27:00 UTC
extracted_at: 2024-03-15 10:25:00 UTC
*/
```

### Audit Trail Entries

```sql
SELECT event_type, title, event_time, success FROM audit_trails 
WHERE extracted_data_id = 'a1b2c3d4-e5f6-4789-abcd-ef1234567890' 
ORDER BY event_time;

/* Results:
event_type          | title                              | event_time                    | success
upload              | Document uploaded                  | 2024-03-15 10:25:00.123456   | t
extraction          | Invoice extracted via OpenAI       | 2024-03-15 10:25:05.234567   | t
normalization       | Invoice data normalized            | 2024-03-15 10:25:10.345678   | t
validation          | Validation completed               | 2024-03-15 10:25:15.456789   | t
compliance_check    | Compliance checks completed        | 2024-03-15 10:25:20.567890   | t
audit_summary       | Audit summary generated            | 2024-03-15 10:25:25.678901   | t
accept              | Invoice accepted                   | 2024-03-15 10:27:00.789012   | t
*/
```

### Audit Findings

```sql
SELECT finding_type, severity, description FROM invoice_audit_findings 
WHERE extracted_data_id = 'a1b2c3d4-e5f6-4789-abcd-ef1234567890';

/* Results: 
EMPTY - No findings (all checks passed)
*/
```

---

## Comparison: What Would Happen with Problems

### Scenario: Missing Customer Info

If customer name was missing:

**Compliance Check Result:**
```json
{
  "check_name": "customer_presence",
  "status": "MISSING",
  "severity": "CRITICAL",
  "message": "Customer name is missing"
}
```

**Risk Calculation:**
```
Invoice number: PASS (0)
Vendor: PASS (0)
Customer: CRITICAL (50) ← This is a problem
Items: PASS (0)
Total: PASS (0)
VAT/TIN: PASS (0)
Due date: PASS (0)
Currency: PASS (0)
Discount: PASS (0)

Total Score: 50/100 → Risk Level: Medium
```

**Audit Summary:**
```json
{
  "final_status": "REQUIRES_REVIEW",
  "requires_review": true,
  "key_risks": ["Customer information is missing"]
}
```

**Audit Finding Created:**
```json
{
  "finding_type": "missing_field",
  "severity": "critical",
  "description": "Customer name is missing",
  "is_resolved": false
}
```

**User Review:**
```
Review endpoint shows:
- Risk Score: 50/100 (MEDIUM)
- Risk Level: Medium
- Compliance checks: 8/9 pass
- 1 audit finding created
- Final status: REQUIRES_REVIEW

User must correct customer_name before accepting
```

---

## Key Metrics from This Example

| Metric | Value | Status |
|---|---|---|
| Extraction confidence | 94% | ✅ Excellent |
| Compliance checks passed | 9/9 | ✅ Perfect |
| Risk score | 0/100 | ✅ Low |
| Validation errors | 0 | ✅ None |
| Validation warnings | 0 | ✅ None |
| Audit findings | 0 | ✅ None |
| Time to process | ~25 seconds | ✅ Fast |
| Ready status | READY_TO_POST | ✅ Yes |

---

## Summary

This example shows:
1. ✅ Upload triggers Phase 1 extraction
2. ✅ Phase 2 normalizes and validates data
3. ✅ Phase 3 runs 9 compliance checks
4. ✅ Risk score calculated (0 = low risk)
5. ✅ Audit summary generated
6. ✅ Audit trail tracks all events
7. ✅ Review endpoint shows all data
8. ✅ User can accept, reject, or correct
9. ✅ Findings created only for issues

**Result: Complete invoice audit pipeline, end-to-end!** 🎉

