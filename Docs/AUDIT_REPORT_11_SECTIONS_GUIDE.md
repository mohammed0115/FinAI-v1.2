# 🎨 11-Section Audit Report - Complete Assembly Guide

## Overview

The audit report is automatically generated and consists of 11 carefully structured sections displayed in `pipeline_result.html`.

---

## 📊 Section Assembly Process

### Trigger Point
```python
# In post_ocr_pipeline.py
generate_audit_report(extracted_data, document, organization, ocr_evidence)
```

### Service Method
```python
# In audit_report_service.py
report_service.generate_comprehensive_report(extracted_data)
```

### Creates InvoiceAuditReport
```python
InvoiceAuditReport.objects.create(
    document=document,
    extracted_data=extracted_data,
    organization=organization,
    risk_level=extracted_data.risk_level,
    overall_status=...,
    report_sections=[...11 sections...],
    recommendations=...,
    created_at=timezone.now()
)
```

---

## 🔧 Section 1: Document Information

### Data Collection
```python
document_info = {
    "section_number": 1,
    "title_ar": "معلومات المستند",
    "title_en": "Document Information",
    "icon": "📋",
    "fields": {
        "Document ID": str(extracted_data.document_id),
        "Upload Date": document.uploaded_at.strftime("%Y-%m-%d %H:%M:%S"),
        "OCR Engine": extracted_data.extraction_provider,  # openai_vision
        "Confidence Score": f"{ocr_evidence.confidence_score}%",
        "Processing Status": document.status  # completed
    }
}
```

### Display Template
```html
<div class="section">
    <h3>📋 معلومات المستند</h3>
    <table>
        <tr>
            <td>Document ID</td>
            <td>516e9f2c-da73-49e3-a342-fa38502dea3c</td>
        </tr>
        <tr>
            <td>Upload Date</td>
            <td>2026-03-07 18:15:00</td>
        </tr>
        <tr>
            <td>OCR Engine</td>
            <td>openai_vision</td>
        </tr>
        <tr>
            <td>Confidence Score</td>
            <td>85%</td>
        </tr>
        <tr>
            <td>Processing Status</td>
            <td>✓ Completed</td>
        </tr>
    </table>
</div>
```

---

## 🔧 Section 2: Invoice Data

### Data Collection
```python
invoice_data = {
    "section_number": 2,
    "title_ar": "بيانات الفاتورة المستخرجة",
    "title_en": "Invoice Data",
    "icon": "📄",
    "fields": {
        "Invoice Number": extracted_data.invoice_number,           # INV-2026-001
        "Issue Date": extracted_data.invoice_date or "—",          # 2026-03-06
        "Due Date": extracted_data.due_date or "—",               # —
        "Vendor (Supplier)": extracted_data.vendor_name,           # Example Trading Co. Ltd
        "Customer": extracted_data.customer_name,                 # Acme Industries Ltd
        "Currency": extracted_data.currency                       # SAR
    }
}
```

### Display Template
```html
<div class="section">
    <h3>📄 بيانات الفاتورة المستخرجة</h3>
    
    <div class="field-group">
        <label>Invoice Number</label>
        <value>INV-2026-001</value>
    </div>
    
    <div class="field-group">
        <label>Issue Date</label>
        <value>2026-03-06</value>
    </div>
    
    <div class="vendor-info">
        <h4>البائع (Vendor)</h4>
        <p>Example Trading Co. Ltd</p>
        
        <h4>العميل (Customer)</h4>
        <p>Acme Industries Ltd</p>
    </div>
</div>
```

---

## 🔧 Section 3: Line Items

### Data Collection
```python
line_items = {
    "section_number": 3,
    "title_ar": "تفاصيل البنود",
    "title_en": "Line Items",
    "icon": "📋",
    "items": [
        {
            "#": 1,
            "Product": "Product A",
            "Description": "Description A",
            "Quantity": 2,
            "Unit Price": 150.0,
            "Discount": 0,
            "Total": 300.0
        },
        {
            "#": 2,
            "Product": "Product B",
            "Description": "Description B",
            "Quantity": 1,
            "Unit Price": 200.0,
            "Discount": 0,
            "Total": 200.0
        }
    ]
}
```

### Display Template
```html
<div class="section">
    <h3>📋 تفاصيل البنود</h3>
    <table class="items-table">
        <thead>
            <tr>
                <th>#</th>
                <th>صنف</th>
                <th>الوصف</th>
                <th>الكمية</th>
                <th>السعر</th>
                <th>الخصم</th>
                <th>الإجمالي</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>1</td>
                <td>Product A</td>
                <td>Description</td>
                <td>2</td>
                <td>150.0</td>
                <td>0</td>
                <td>300.0</td>
            </tr>
            <tr>
                <td>2</td>
                <td>Product B</td>
                <td>Description</td>
                <td>1</td>
                <td>200.0</td>
                <td>0</td>
                <td>200.0</td>
            </tr>
        </tbody>
    </table>
</div>
```

---

## 🔧 Section 4: Financial Totals

### Data Collection
```python
from decimal import Decimal

subtotal = Decimal('500.00')  # Sum of all items
vat = Decimal('75.00')        # Tax amount
total = Decimal('575.00')     # Subtotal + VAT

financial_totals = {
    "section_number": 4,
    "title_ar": "الإجمالي المالي",
    "title_en": "Financial Totals",
    "icon": "💰",
    "fields": {
        "Subtotal": f"SAR {subtotal:,.2f}",
        "VAT (15%)": f"SAR {vat:,.2f}",
        "Total Amount": f"SAR {total:,.2f}",
        "Currency": "SAR"
    }
}
```

### Display Template
```html
<div class="section">
    <h3>💰 الإجمالي المالي</h3>
    
    <div class="financial-summary">
        <div class="financial-row">
            <span>المجموع قبل الضريبة</span>
            <span class="amount">SAR 500.00</span>
        </div>
        
        <div class="financial-row">
            <span>ضريبة القيمة المضافة (15%)</span>
            <span class="amount">SAR 75.00</span>
        </div>
        
        <div class="financial-row total">
            <span>الإجمالي النهائي</span>
            <span class="amount">SAR 575.00</span>
        </div>
        
        <div class="currency">العملة: SAR</div>
    </div>
</div>
```

---

## 🔧 Section 5: Validation Results

### Data Collection
```python
validation_results = {
    "section_number": 5,
    "title_ar": "نتائج التحقق",
    "title_en": "Validation Results",
    "icon": "✓",
    "validations": {
        "Invoice Number": {
            "status": "pass",      # pass | warning | fail
            "message": "Invoice number extracted successfully"
        },
        "Vendor": {
            "status": "warning",
            "message": "Vendor name extracted but needs verification"
        },
        "Customer": {
            "status": "warning",
            "message": "Customer name extracted but needs verification"
        },
        "Items": {
            "status": "warning",
            "message": "Items extracted but quantity/price needs verification"
        },
        "Total Match": {
            "status": "warning",
            "message": "Calculated total matches extracted total"
        },
        "VAT": {
            "status": "pass",
            "message": "VAT calculation is correct (15%)"
        }
    }
}
```

### Display Template
```html
<div class="section">
    <h3>✓ نتائج التحقق</h3>
    
    <div class="validation-items">
        <div class="validation-item pass">
            <span class="icon">✓</span>
            <span class="field">Invoice Number</span>
            <span class="status">Pass</span>
        </div>
        
        <div class="validation-item warning">
            <span class="icon">⚠</span>
            <span class="field">Vendor</span>
            <span class="status">Warning</span>
        </div>
        
        <div class="validation-item warning">
            <span class="icon">⚠</span>
            <span class="field">Customer</span>
            <span class="status">Warning</span>
        </div>
        
        <!-- More items... -->
    </div>
</div>
```

---

## 🔧 Section 6: Duplicate Detection

### Data Collection
```python
from documents.services.audit_report_service import DuplicateDetectionService

duplicate_score, matched_docs, duplicate_status = DuplicateDetectionService.calculate_duplicate_score(
    extracted_data
)

duplicate_detection = {
    "section_number": 6,
    "title_ar": "كشف التكرار",
    "title_en": "Duplicate Detection",
    "icon": "🔍",
    "fields": {
        "Duplicate Score": f"{duplicate_score}/100",
        "Matched Documents": len(matched_docs),
        "Duplicate Status": duplicate_status,  # No Duplicates | Potential Match | High Similarity
        "Action": "Manual review recommended" if duplicate_score > 80 else "OK"
    }
}
```

### Display Template
```html
<div class="section">
    <h3>🔍 كشف التكرار</h3>
    
    <div class="duplicate-status">
        <div class="score">
            <span class="label">Duplicate Score</span>
            <span class="value">100/100</span>
        </div>
        
        <div class="matched">
            <span class="label">Matched Documents</span>
            <span class="value">1</span>
        </div>
        
        <div class="status high">
            <span class="label">Status</span>
            <span class="value">Potential duplicate detected</span>
        </div>
    </div>
</div>
```

---

## 🔧 Section 7: Anomaly Detection

### Data Collection
```python
anomaly_detection = {
    "section_number": 7,
    "title_ar": "كشف الأنماط غير الطبيعية",
    "title_en": "Anomaly Detection",
    "icon": "📈",
    "fields": {
        "Anomaly Score": f"{extracted_data.anomaly_score}/100",
        "Anomaly Status": extracted_data.anomaly_flags or "Normal",
        "Explanation": "No unusual patterns detected in invoice data"
    }
}
```

### Display Template
```html
<div class="section">
    <h3>📈 كشف الأنماط غير الطبيعية</h3>
    
    <div class="anomaly-info">
        <div class="metric">
            <span class="label">Anomaly Score</span>
            <span class="value">0/100</span>
        </div>
        
        <div class="status">
            <span class="label">Status</span>
            <span class="badge normal">Normal</span>
        </div>
        
        <div class="explanation">
            No unusual patterns detected in invoice data
        </div>
    </div>
</div>
```

---

## 🔧 Section 8: Risk Assessment

### Data Collection
```python
risk_assessment = {
    "section_number": 8,
    "title_ar": "تقييم المخاطر",
    "title_en": "Risk Assessment",
    "icon": "⚠",
    "fields": {
        "Risk Score": f"{extracted_data.risk_score}/100",
        "Risk Level": extracted_data.risk_level,  # low | medium | high | critical
        "Risk Color": "🔴" if extracted_data.risk_level == "critical" else "🟠",
        "Contributing Factors": [
            "Warning in vendor validation",
            "Warning in customer validation",
            "Potential duplicate detected (score: 100)"
        ]
    }
}
```

### Display Template
```html
<div class="section">
    <h3>⚠ تقييم المخاطر</h3>
    
    <div class="risk-gauge">
        <svg class="circle-gauge">
            <!-- SVG circle showing 90/100 -->
        </svg>
        <span class="score">90</span>
        <span class="label">من 100</span>
    </div>
    
    <div class="risk-level critical">
        <span class="badge">🔴 حرجة - Critical</span>
        <p>مستوى حرج من المخاطر</p>
    </div>
    
    <div class="risk-factors">
        <h4>عوامل المخاطر:</h4>
        <ul>
            <li>تحذير في التحقق من المورد</li>
            <li>تحذير في التحقق من العميل</li>
            <li>فاتورة مشابهة محتملة</li>
        </ul>
    </div>
</div>
```

---

## 🔧 Section 9: AI Summary

### Data Collection
```python
ai_summary = {
    "section_number": 9,
    "title_ar": "ملخص الذكاء الاصطناعي",
    "title_en": "AI Summary",
    "icon": "🤖",
    "narrative": extracted_data.audit_summary.get('executive_summary', ''),
    "key_findings": extracted_data.audit_summary.get('key_risks', []),
    "recommendations": extracted_data.audit_summary.get('recommended_actions', [])
}
```

### Generated by OpenAI
```python
# In generate_ai_summary(extracted_data, findings):

prompt = f"""
تحليل فاتورة #{extracted_data.invoice_number}
من {extracted_data.vendor_name}
إلى {extracted_data.customer_name}

الإجمالي: {extracted_data.total_amount} {extracted_data.currency}

المشاكل المكتشفة:
{audit_findings_summary}

يرجى تقديم:
1. ملخص تنفيذي بجملة واحدة
2. المخاطر الرئيسية (3 نقاط)
3. الإجراءات الموصى بها (3 نقاط)
"""

response = openai.ChatCompletion.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}]
)

extracted_data.audit_summary = {
    "executive_summary": response.choices[0].message.content,
    "key_risks": [...],
    "recommended_actions": [...]
}
```

### Display Template
```html
<div class="section">
    <h3>🤖 ملخص الذكاء الاصطناعي</h3>
    
    <div class="ai-summary">
        <p class="narrative">
            Overall, the invoice (INV-2026-001) from Example Trading Co. Ltd to Acme Industries Ltd 
            appears to be in good standing with no issues detected...
        </p>
        
        <div class="key-findings">
            <h4>الملاحظات الرئيسية:</h4>
            <ul>
                <li>✓ Invoice number validation passed</li>
                <li>⚠ Vendor validation issued warnings</li>
                <li>🔴 Potential duplicate detected</li>
            </ul>
        </div>
    </div>
</div>
```

---

## 🔧 Section 10: Recommendations

### Data Collection
```python
recommendations = {
    "section_number": 10,
    "title_ar": "التوصيات",
    "title_en": "Recommendations",
    "icon": "📋",
    "recommendation": extracted_data.audit_summary.get('recommendation', 'Manual Review'),
    "actions": [
        "Review vendor details",
        "Verify customer information",
        "Check for duplicates in records"
    ],
    "priority": "high"
}
```

### Display Template
```html
<div class="section">
    <h3>📋 التوصيات</h3>
    
    <div class="recommendation-box">
        <div class="recommendation-status manual-review">
            <strong>التوصية:</strong> Manual Review
        </div>
        
        <div class="actions">
            <h4>الإجراءات المقترحة:</h4>
            <ul>
                <li>Review vendor details and verify information</li>
                <li>Contact customer to confirm invoice receipt</li>
                <li>Check historical records for similar invoices</li>
            </ul>
        </div>
        
        <div class="priority high">
            <strong>الأولوية:</strong> High
        </div>
    </div>
</div>
```

---

## 🔧 Section 11: Audit Trail

### Data Collection
```python
from documents.models import AuditTrail

audit_events = AuditTrail.objects.filter(
    extracted_data=extracted_data
).order_by('event_time')

audit_trail = {
    "section_number": 11,
    "title_ar": "سجل التدقيق",
    "title_en": "Audit Trail",
    "icon": "📝",
    "events": [
        {
            "event": "Document Uploaded",
            "timestamp": document.uploaded_at,
            "status": "success",
            "description": "File saved to storage"
        },
        {
            "event": "OCR Processing",
            "timestamp": ocr_evidence.extracted_at,
            "status": "success",
            "description": "openai_vision engine used, 85% confidence"
        },
        {
            "event": "Data Extraction",
            "timestamp": extracted_data.extracted_at,
            "status": "success",
            "description": "Invoice data extracted and validated"
        },
        {
            "event": "Compliance Check",
            "timestamp": extracted_data.validation_completed_at,
            "status": "completed",
            "description": "Compliance findings generated"
        },
        {
            "event": "Report Generated",
            "timestamp": timezone.now(),
            "status": "complete",
            "description": "Audit report assembled with 11 sections"
        }
    ]
}
```

### Display Template
```html
<div class="section">
    <h3>📝 سجل التدقيق</h3>
    
    <div class="audit-timeline">
        <div class="event">
            <span class="icon">✓</span>
            <span class="title">Document Uploaded</span>
            <span class="time">18:15 2026/03/07</span>
            <span class="status">✓</span>
        </div>
        
        <div class="event">
            <span class="icon">✓</span>
            <span class="title">OCR (openai_vision)</span>
            <span class="time">18:15 2026/03/07</span>
            <span class="status">✓</span>
        </div>
        
        <div class="event">
            <span class="icon">✓</span>
            <span class="title">Data Extraction</span>
            <span class="time">18:15 2026/03/07</span>
            <span class="status">✓</span>
        </div>
        
        <div class="event">
            <span class="icon">✓</span>
            <span class="title">Compliance Check</span>
            <span class="time">18:15 2026/03/07</span>
            <span class="status">✓</span>
        </div>
        
        <div class="event">
            <span class="icon">✓</span>
            <span class="title">Report Generated</span>
            <span class="time">18:15 2026/03/07</span>
            <span class="status">✓</span>
        </div>
    </div>
</div>
```

---

## 📦 Complete Report Object

```python
report = {
    "id": "07450edf-7caf-4ad2-bcc7-2abb7f48e2ac",
    "document_id": "516e9f2c-da73-49e3-a342-fa38502dea3c",
    "extracted_data_id": "ff5b656e-a37e-42b1-9394-074010862a0b",
    "organization_id": "org-abc123",
    
    "report_sections": [
        # Section 1: Document Information
        # Section 2: Invoice Data
        # Section 3: Line Items
        # Section 4: Financial Totals
        # Section 5: Validation Results
        # Section 6: Duplicate Detection
        # Section 7: Anomaly Detection
        # Section 8: Risk Assessment
        # Section 9: AI Summary
        # Section 10: Recommendations
        # Section 11: Audit Trail
    ],
    
    "risk_level": "critical",
    "overall_status": "manual_review_required",
    "recommendations": "Manual Review",
    "created_at": "2026-03-07 18:15:30"
}
```

---

## ✅ Quality Assurance

All 11 sections are:
- ✅ Automatically generated
- ✅ Properly typed (no type errors)
- ✅ Bilingual (Arabic/English)
- ✅ Stored in database
- ✅ Displayed in template
- ✅ Responsive design
- ✅ User-friendly layout
- ✅ Printable format

