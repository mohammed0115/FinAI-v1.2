# 📋 Upload Form & Request Flow Documentation

## 🎯 Upload Form (upload.html)

### Single File Upload Form
**Endpoint**: `POST /documents/upload/`

**Form Fields**:
```
document                 (file) - PDF, JPG, PNG, TIFF, BMP
document_type           (select) - invoice | receipt | bank_statement | contract | other
language                (select) - ara+eng | ara | eng
is_handwritten          (checkbox) - true | false
```

**Example HTML Form**:
```html
<form method="post" enctype="multipart/form-data">
    {% csrf_token %}
    <input type="hidden" name="upload_mode" value="single">
    <input type="file" name="document" required>
    <select name="document_type">
        <option value="invoice">فاتورة</option>
    </select>
    <select name="language">
        <option value="ara+eng">عربي وإنجليزي</option>
    </select>
    <input type="checkbox" name="is_handwritten">
    <button type="submit">رفع ومعالجة</button>
</form>
```

---

## 📤 Request Data Structure

### Multipart Form Data Sent to Server
```
Content-Type: multipart/form-data

document=@invoice.pdf
document_type=invoice
language=ara+eng
is_handwritten=false
upload_mode=single
csrfmiddlewaretoken=xxxx
```

### Server Processing Flow:
1. **View Handler**: `document_upload_view()` (web_views.py)
2. **Validation**: Check file type, size, extension
3. **Storage**: Save to `/media/uploads/{org_id}/{timestamp}_{filename}`
4. **Document Record**: Create `Document` object
5. **OCR Processing**: `process_document_ocr()` → OpenAI Vision API
6. **Extract**: Convert image to JSON with invoice data
7. **OCREvidence**: Store raw OCR output
8. **Pipeline**: Trigger `process_ocr_evidence()` 

---

## 🔄 Complete Processing Pipeline

```
1. Upload Form (upload.html)
   ├─ Single file or batch
   ├─ Set document type
   └─ Choose language
   
2. Server Receives (web_views.py)
   ├─ Validate file type & size
   ├─ Save to storage
   └─ Create Document record
   
3. OpenAI Vision API
   ├─ Extract text (Arabic/English)
   ├─ Structure data as JSON
   └─ Confidence score (0-100%)
   
4. OCREvidence Created
   ├─ Store raw OCR output
   ├─ Save structured JSON
   └─ Save confidenc score
   
5. Post-OCR Pipeline (post_ocr_pipeline.py)
   ├─ Parse dates safely
   ├─ Convert amounts to Decimal
   └─ Create ExtractedData
   
6. Compliance Checks
   ├─ Validate vendor name
   ├─ Validate customer name
   ├─ Check invoice number
   └─ Verify VAT rate
   
7. Risk Scoring (calculate_risk_score)
   ├─ Count audit findings
   ├─ Calculate 0-100 score
   └─ Set risk level
   
8. AI Summary (generate_ai_summary)
   ├─ Call OpenAI again
   ├─ Generate narrative
   └─ Identify key issues
   
9. Report Generation (generate_audit_report)
   ├─ Duplicate detection
   ├─ Anomaly detection
   ├─ Compile all sections
   └─ Save InvoiceAuditReport
   
10. Redirect to Result
    └─ pipeline_result.html displays 11 sections
```

---

## 📊 11-Section Audit Report Structure

### Section 1: Document Information
```json
{
  "section": "document_info",
  "title": "معلومات المستند",
  "fields": {
    "document_id": "516e9f2c-...",
    "upload_date": "2026-03-07 18:15",
    "ocr_engine": "openai_vision",
    "confidence_score": "85%",
    "processing_status": "completed"
  }
}
```

### Section 2: Invoice Data
```json
{
  "section": "invoice_data",
  "title": "بيانات الفاتورة",
  "fields": {
    "invoice_number": "INV-2026-001",
    "issue_date": "2026-03-06",
    "due_date": "—",
    "vendor": "Example Trading Co. Ltd",
    "customer": "Acme Industries Ltd",
    "currency": "SAR"
  }
}
```

### Section 3: Line Items
```json
{
  "section": "line_items",
  "title": "تفاصيل البنود",
  "items": [
    {
      "product": "Product A",
      "quantity": 2,
      "unit_price": 150.0,
      "total": 300.0
    },
    {
      "product": "Product B",
      "quantity": 1,
      "unit_price": 200.0,
      "total": 200.0
    }
  ]
}
```

### Section 4: Financial Totals
```json
{
  "section": "financial_totals",
  "title": "الإجمالي المالي",
  "fields": {
    "subtotal": "SAR 500.00",
    "vat": "SAR 75.00",
    "total": "SAR 575.00",
    "currency": "SAR"
  }
}
```

### Section 5: Validation Results
```json
{
  "section": "validation_results",
  "title": "نتائج التحقق",
  "validations": {
    "invoice_number": "✓ Pass",
    "vendor": "⚠ Warning",
    "customer": "⚠ Warning",
    "items": "⚠ Warning",
    "total_match": "⚠ Warning",
    "vat": "✓ Pass"
  }
}
```

### Section 6: Duplicate Detection
```json
{
  "section": "duplicate_detection",
  "title": "كشف التكرار",
  "fields": {
    "duplicate_score": "100/100",
    "matched_documents": 1,
    "status": "Potential duplicate detected"
  }
}
```

### Section 7: Anomaly Detection
```json
{
  "section": "anomalies",
  "title": "كشف الأنماط غير الطبيعية",
  "fields": {
    "anomaly_score": 0,
    "anomaly_status": "Normal",
    "explanation": "No unusual patterns detected"
  }
}
```

### Section 8: Risk Assessment
```json
{
  "section": "risk_assessment",
  "title": "تقييم المخاطر",
  "fields": {
    "risk_score": "90/100",
    "risk_level": "🔴 Critical",
    "factors": [
      "Warning in vendor validation",
      "Warning in customer validation",
      "Potential duplicate detected"
    ]
  }
}
```

### Section 9: AI Summary
```json
{
  "section": "ai_summary",
  "title": "ملخص الذكاء الاصطناعي",
  "narrative": "Overall, the invoice (INV-2026-001) from Example Trading Co. Ltd to Acme Industries Ltd appears to be in good standing with no issues detected. The amount billed is 575.00 SAR, and the risk level is classified as critical..."
}
```

### Section 10: Recommendations
```json
{
  "section": "recommendations",
  "title": "التوصيات",
  "recommendation": "Manual Review",
  "actions": [
    "Review vendor details",
    "Verify customer information",
    "Check for duplicates in records"
  ]
}
```

### Section 11: Audit Trail
```json
{
  "section": "audit_trail",
  "title": "سجل التدقيق",
  "events": [
    {
      "event": "Document Uploaded",
      "timestamp": "18:15 2026/03/07",
      "status": "✓"
    },
    {
      "event": "OCR (openai_vision)",
      "timestamp": "18:15 2026/03/07",
      "status": "✓"
    },
    {
      "event": "Data Extraction",
      "timestamp": "18:15 2026/03/07",
      "status": "✓"
    },
    {
      "event": "Compliance Check",
      "timestamp": "18:15 2026/03/07",
      "status": "✓"
    },
    {
      "event": "Report Generated",
      "timestamp": "18:15 2026/03/07",
      "status": "✓"
    }
  ]
}
```

---

## 🗄️ Database Records Created

### 1. Document Record
```python
document = Document.objects.create(
    organization=organization,
    uploaded_by=user,
    file_name="invoice.pdf",
    file_type=".pdf",
    file_size=245600,
    storage_key="uploads/org_id/20260307_181500_invoice.pdf",
    storage_url="/media/uploads/org_id/...",
    document_type="invoice",
    status="completed",
    language="ara+eng",
    is_handwritten=False
)
```

### 2. OCREvidence Record
```python
ocr_evidence = OCREvidence.objects.create(
    document=document,
    ocr_engine="openai_vision",
    confidence_score=85,
    text_ar="النص العربي المستخرج...",
    text_en="Extracted English text...",
    structured_data_json={
        "invoice_number": "INV-2026-001",
        "issue_date": "2026-03-06",
        "due_date": "",
        "vendor_name": "Example Trading Co. Ltd",
        ...
    }
)
```

### 3. ExtractedData Record
```python
extracted_data = ExtractedData.objects.create(
    document=document,
    organization=organization,
    invoice_number="INV-2026-001",
    vendor_name="Example Trading Co. Ltd",
    customer_name="Acme Industries Ltd",
    invoice_date=datetime(2026, 3, 6),
    due_date=None,
    total_amount=Decimal("575.00"),
    tax_amount=Decimal("75.00"),
    currency="SAR",
    items_json=[...],
    validation_status="validated",
    risk_score=90,
    risk_level="critical",
    extraction_provider="openai_vision"
)
```

### 4. InvoiceAuditReport Record
```python
report = InvoiceAuditReport.objects.create(
    document=document,
    extracted_data=extracted_data,
    organization=organization,
    risk_level="critical",
    overall_status="manual_review_required",
    report_sections=[
        # All 11 sections compiled here
    ],
    recommendations="Manual Review"
)
```

---

## ✅ Request Data Validation

### Form Validation Rules
| Field | Type | Rules | Example |
|-------|------|-------|---------|
| document | File | Required, Max 50MB | invoice.pdf |
| document_type | Select | invoice\|receipt\|... | invoice |
| language | Select | ara\|eng\|ara+eng | ara+eng |
| is_handwritten | Checkbox | Boolean | false |

### File Type Validation
✅ Supported: `.pdf`, `.jpg`, `.jpeg`, `.png`, `.tiff`, `.tif`, `.bmp`
❌ Not Supported: `.doc`, `.docx`, `.xlsx`, `.csv`

### Processing Validation
- File must be readable by OpenAI Vision
- Document must not be corrupted
- Extracted data must be valid JSON
- No personal information disclosure

---

## 🚀 Clean Code Standards

✅ **Applied to This Implementation**:
- No hardcoded values in pipeline
- All dates safely parsed
- All amounts converted to Decimal
- Graceful error handling
- Type safety throughout
- Bilingual support (Arabic/English)
- Database transactions atomic
- Proper logging at each step

❌ **Avoided**:
- Messy type conversions
- Unhandled exceptions
- Magic strings
- Hardcoded paths
- Mixed concerns in models

---

## 📝 Testing Checklist

- ✅ Single file upload works
- ✅ File validation enforced
- ✅ OpenAI API integration working
- ✅ Date parsing handles all formats
- ✅ Amount conversion to Decimal
- ✅ All 11 sections display
- ✅ Bilingual content shows correctly
- ✅ Risk scoring accurate
- ✅ AI summary generated
- ✅ Audit trail complete
- ✅ No type errors
- ✅ Graceful error handling

---

## 📞 API Endpoints

### Upload Document
```
POST http://localhost:8000/documents/upload/
Form Data: document, document_type, language, is_handwritten
Response: Redirect to pipeline_result page
```

### View Results
```
GET http://localhost:8000/pipeline/{document_id}/
Response: HTML page with 11-section audit report
```

### List Uploads
```
GET http://localhost:8000/documents/upload/
Response: HTML page showing recent documents
```

