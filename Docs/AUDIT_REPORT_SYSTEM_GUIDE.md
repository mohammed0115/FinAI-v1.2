# تقرير التدقيق الشامل للفواتير - FinAI Comprehensive Invoice Audit Report System

## الملخص التنفيذي (Executive Summary)

تم تطوير نظام تقرير تدقيق شامل يعمل بالكامل عند رفع أي فاتورة. النظام يستخدم:
- **محرك OCR**: OpenAI Vision API (مع تعطيل Tesseract)
- **المخرجات**: تقرير تدقيق شامل بـ 11 قسم
- **الحفظ**: في قاعدة البيانات قبل العرض
- **العرض**: في صفحة تقرير خط المعالجة

## آلية العمل (System Architecture)

### المرحلة 1: رفع المستند (Document Upload)
```
User Upload → Validation → Storage → OCR Processing Initiation
```

#### الملف:
- [core/views/document_views.py](backend/core/views/document_views.py) - وظيفة `process_document_ocr`
- استخدام OpenAI Vision API فقط (بدون Tesseract)

### المرحلة 2: معالجة OCR (OCR Processing)
```
OpenAI Vision → Extract Structured Data → Create OCR Evidence Record
```

#### المخرجات:
- `OCREvidence` - سجل أدلة التعرف الضوئي
- `ocr_engine = 'openai_vision'`
- `confidence_score` - درجة الثقة (0-100)
- `structured_data_json` - البيانات المستخرجة

#### الملف:
- [core/views/document_views.py](backend/core/views/document_views.py#L163) - `process_document_ocr`

### المرحلة 3: خط المعالجة بعد OCR (Post-OCR Pipeline)
```
OCR Evidence → Extract Data → Compliance Checks → Risk Score → AI Summary → Audit Report
```

#### الخطوات:
1. **Create ExtractedData** - حفظ البيانات المستخرجة
   - `extraction_provider = 'openai_vision'`
   - جميع حقول الفاتورة
   - قائمة البنود

2. **Compliance Findings** - إنشاء ملاحظات الامتثال
   - فحص معدل الضريبة
   - التحقق من البيانات المفقودة
   - فحص ثقة OCR

3. **Risk Scoring** - حساب درجة المخاطرة
   - تقييم الملاحظات
   - حساب المخاطر الإجمالية

4. **AI Summary** - ملخص ذكي
   - توليد الملخص التنفيذي
   - إنشاء التوصيات

5. **Comprehensive Audit Report** - تقرير التدقيق الشامل
   - جمع جميع البيانات في InvoiceAuditReport
   - إنشاء JSON التقرير الكامل

#### الملف:
- [core/post_ocr_pipeline.py](backend/core/post_ocr_pipeline.py) - `process_ocr_evidence`

### المرحلة 4: عرض التقرير (Report Display)
```
Pipeline Result View → Get Audit Report → Render Template with All 11 Sections
```

#### الملف:
- [templates/documents/pipeline_result.html](backend/templates/documents/pipeline_result.html)

## أقسام التقرير الـ 11 (11 Report Sections)

التقرير يحتوي على 11 قسم شامل:

### 1. معلومات المستند (Document Information)
```python
upload_date        # تاريخ الرفع
ocr_engine         # محرك OCR (OpenAI Vision)
ocr_confidence_score  # درجة الثقة
processing_status  # حالة المعالجة
```

### 2. بيانات الفاتورة المستخرجة (Invoice Data Extraction)
```python
invoice_number
issue_date
due_date
vendor_name
vendor_address
customer_name
customer_address
```

### 3. تفاصيل البنود (Line Items)
```python
line_items_json = [
  {
    "description": "...",
    "quantity": 1,
    "unit_price": 100,
    "discount": 0,
    "line_total": 100
  }
]
```

### 4. الإجمالي المالي (Financial Totals)
```python
subtotal_amount
vat_amount
total_amount
currency
```

### 5. نتائج التحقق (Validation Results)
```python
validation_results_json = {
  "invoice_number": {"status": "pass|warning|fail", ...},
  "vendor": {...},
  "customer": {...},
  "items": {...},
  "total_match": {...},
  "vat": {...}
}
```

### 6. كشف التكرار (Duplicate Detection)
```python
duplicate_score        # 0-100 (احتمالية التكرار)
duplicate_status       # no_duplicate, low_risk, medium_risk, high_risk, confirmed_duplicate
duplicate_matched_documents_json  # IDs of matched documents
```

### 7. كشف الأنماط غير الطبيعية (Anomaly Detection)
```python
anomaly_score          # 0-100
anomaly_status         # no_anomaly, low_anomaly, medium_anomaly, high_anomaly, critical_anomaly
anomaly_explanation    # شرح الأنماط المكتشفة
anomaly_reasons_json   # [{"reason": "...", "type": "..."}]
```

### 8. تقييم المخاطر (Risk Assessment)
```python
risk_score             # 0-100 (درجة المخاطرة)
risk_level             # low, medium, high, critical
risk_factors_json      # [list of risk factors found]
```

**حساب المخاطرة:**
- 0-30: منخفضة (Low)
- 30-60: متوسطة (Medium)
- 60-80: عالية (High)
- 80-100: حرجة (Critical)

### 9. ملخص الذكاء الاصطناعي (AI Summary)
```python
ai_summary              # ملخص شامل من OpenAI
ai_summary_ar          # نسخة عربية
ai_findings            # النتائج والملاحظات
ai_findings_ar         # نسخة عربية
ai_review_required     # هل تحتاج مراجعة يدوية
```

### 10. التوصيات (Recommendations)
```python
recommendation         # approve, manual_review, reject
recommendation_reason  # السبب والتفاصيل
```

### 11. سجل التدقيق (Audit Trail)
```python
audit_trail_json = [
  {
    "timestamp": "2026-03-07T10:30:00Z",
    "event": "upload",
    "status": "success",
    "title": "Document Uploaded",
    "description": "..."
  }
]
```

## نموذج البيانات (Data Model)

### جدول InvoiceAuditReport
```python
class InvoiceAuditReport(models.Model):
    # الروابط
    extracted_data:OneToOneField  → ExtractedData
    document:OneToOneField        → Document
    ocr_evidence:ForeignKey       → OCREvidence
    
    # الأقسام الـ 11
    # 1. معلومات المستند
    upload_date, ocr_engine, ocr_confidence_score, processing_status
    
    # 2-4. البيانات المالية
    extracted_invoice_number, extracted_issue_date, extracted_due_date
    extracted_vendor_name, extracted_customer_name
    line_items_json, subtotal_amount, vat_amount, total_amount
    
    # 5-11. نتائج التحليل
    validation_results_json, duplicate_score, anomaly_score
    risk_score, risk_level, ai_summary, recommendation
    audit_trail_json, full_report_json
```

## المسارات والروابط (Routes & URLs)

### رفع المستند
```
POST /documents/upload/
```

### عرض تقرير التدقيق
```
GET /pipeline/<document_id>/
```

رابط المثال:
```
http://localhost:8000/pipeline/12345678-1234-1234-1234-123456789abc/
```

## المتطلبات المسبقة (Prerequisites)

### 1. مفتاح OpenAI API
```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

### 2. قاعدة البيانات
```bash
python manage.py migrate
```

## التثبيت والتشغيل (Installation & Running)

### 1. تفعيل البيئة الافتراضية
```bash
cd /home/mohamed/FinAI-v1.2
source .venv/bin/activate
cd backend
```

### 2. تشغيل الخادم
```bash
python manage.py runserver 0.0.0.0:8000
```

### 3. الوصول إلى التطبيق
```
http://localhost:8000/documents/upload/
```

## خطوات الاستخدام (Usage Steps)

### 1. تسجيل الدخول
- استخدم بيانات الدخول الخاصة بك
- تأكد من وجود منشأة مرتبطة بالحساب

### 2. رفع فاتورة
- اذهب إلى صفحة رفع المستندات
- اختر صورة الفاتورة (JPG, PNG)
- اضغط رفع

### 3. المعالجة التلقائية
سيحدث التالي تلقائياً:
```
1. استخراج باستخدام OpenAI Vision
2. إنشاء سجل OCREvidence
3. معالجة خط OCR اللاحق:
   - إنشاء ExtractedData
   - إجراء فحوصات الامتثال
   - حساب درجات المخاطرة
   - توليد الملخص الذكي
   - إنشاء تقرير التدقيق الشامل
4. إعادة التوجيه إلى صفحة التقرير
```

### 4. عرض التقرير
ستظهر صفحة التقرير بـ 11 قسم يحتوي على:
- جميع بيانات الفاتورة المستخرجة
- نتائج جميع الفحوصات
- تقييمات المخاطرة
- التوصيات
- سجل التدقيق كاملاً

## معالجة الأخطاء (Error Handling)

### خطأ: "OpenAI API key not configured"
```
الحل: تأكد من تعيين OPENAI_API_KEY في متغيرات البيئة
```

### خطأ: "No extraction provider found"
```
الحل: تأكد من أن OpenAI API يعمل بشكل صحيح
```

### خطأ: "Report not generated"
```
الحل: راجع السجلات - python manage.py runserver
```

## السجلات والتشخيص (Logging & Diagnostics)

### عرض السجلات
```bash
tail -f /var/log/finai/application.log
```

### تفعيل السجلات المفصلة
```python
# في settings.py
LOGGING = {
    'level': 'DEBUG',
    'handlers': ['console', 'file'],
}
```

## الاختبار (Testing)

### اختبار نهائي شامل
```bash
cd /home/mohamed/FinAI-v1.2/backend
python manage.py test documents.tests
```

### اختبار خط المعالجة
```bash
# 1. قم برفع فاتورة
# 2. اذهب إلى صفحة التقرير
# 3. تحقق من ظهور جميع 11 قسم
# 4. تحقق من وجود البيانات في كل قسم
```

## الملفات الرئيسية (Key Files Modified/Created)

| الملف | الوصف |
|------|-------|
| `/backend/core/post_ocr_pipeline.py` | خط المعالجة بعد OCR **[تم التعديل]** |
| `/backend/documents/services/audit_report_service.py` | خدمة إنشاء التقرير الشامل |
| `/backend/documents/models.py‍` | نموذج InvoiceAuditReport |
| `/backend/templates/documents/pipeline_result.html` | قالب عرض التقرير الشامل **[تم التعديل]** |
| `/backend/core/views/document_views.py` | معالج رفع المستندات |

## الملاحظات المهمة (Important Notes)

### 1. OpenAI Vision فقط
- تم تعطيل Tesseract بالكامل
- جميع المعالجات تستخدم OpenAI Vision
- لا توجد خيارات بديلة

### 2. إنشاء التقرير التلقائي
- التقرير ينشأ تلقائياً بعد OCR
- لا يتطلب تفعيل يدوي
- يُحفظ في InvoiceAuditReport فوراً

### 3. البيانات المفقودة
- إذا كانت بعض الحقول مفقودة من الفاتورة
- التقرير يعرض الفقرات المتاحة
- المقاطع الفارغة تظهر "—" أو "لا تتوفر البيانات"

### 4. الخصوصية والأمان
- جميع البيانات محفوظة على الخادم
- لا ترسل بيانات إلى خارج النظام (إلا OpenAI)
- سجل التدقيق يتتبع كل الإجراءات

## المساعدة والدعم

للمساعدة، تحقق من:
1. السجلات: `django.log`
2. قاعدة البيانات: جدول `invoice_audit_reports`
3. صفحة المسؤول: `/admin/`

---

**آخر تحديث:** 7 مارس 2026
**الإصدار:** 1.2
**الحالة:** ✅ جاهز للإنتاج
