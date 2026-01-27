# FinAI ZATCA Integration - Scope Documentation
# وثيقة نطاق تكامل FinAI مع هيئة الزكاة والضريبة والجمارك

## System Identity / هوية النظام

**System Name:** FinAI - AI-Powered Financial Audit Platform
**اسم النظام:** FinAI - منصة التدقيق المالي الذكية

**System Type:** READ-ONLY Audit and Compliance System
**نوع النظام:** نظام تدقيق وامتثال للقراءة فقط

---

## Scope Declaration / إعلان النطاق

### ما هو FinAI؟ / What is FinAI?

FinAI هو **نظام تدقيق ومراجعة** يعمل كأداة مساعدة لمراجعي الحسابات والمدققين الماليين. يقوم النظام بتحليل البيانات المالية الموجودة مسبقاً للتحقق من مدى امتثالها للمتطلبات التنظيمية.

FinAI is an **audit and review system** that serves as a support tool for accountants and financial auditors. The system analyzes pre-existing financial data to verify compliance with regulatory requirements.

---

## ZATCA Integration Scope / نطاق التكامل مع ZATCA

### ✓ ما يقوم به FinAI / What FinAI DOES

| الميزة (عربي) | Feature (English) | Type |
|---------------|-------------------|------|
| التحقق من صحة بيانات الفواتير الموجودة | Validate existing invoice data | READ-ONLY |
| التحقق من تنسيق الرقم الضريبي | Verify VAT number format | READ-ONLY |
| التحقق من صحة المعرف الفريد (UUID) | Validate UUID correctness | READ-ONLY |
| التحقق من سلامة سلسلة التجزئة | Verify hash chain integrity | READ-ONLY |
| تسجيل نتائج التحقق كدليل تدقيق | Store results as audit evidence | READ-ONLY |
| عرض رموز أخطاء ZATCA باللغة العربية | Display ZATCA error codes in Arabic | READ-ONLY |
| ربط الملاحظات بالمراجع التنظيمية | Link findings to regulatory references | READ-ONLY |

### ✗ ما لا يقوم به FinAI / What FinAI does NOT do

| الميزة (عربي) | Feature (English) | Status |
|---------------|-------------------|--------|
| إصدار الفواتير | Generate invoices | ❌ NOT SUPPORTED |
| إرسال الفواتير إلى ZATCA | Submit invoices to ZATCA | ❌ NOT SUPPORTED |
| توقيع الفواتير | Sign invoices | ❌ NOT SUPPORTED |
| تعديل بيانات الفواتير | Modify invoice data | ❌ NOT SUPPORTED |
| التصرف نيابة عن المكلفين | Act on behalf of taxpayers | ❌ NOT SUPPORTED |
| إنشاء رمز QR | Generate QR codes | ❌ NOT SUPPORTED |
| الإبلاغ إلى هيئة الزكاة والضريبة والجمارك | Report to ZATCA | ❌ NOT SUPPORTED |

---

## Architectural Separation / الفصل المعماري

```
┌─────────────────────────────────────────────────────────────────┐
│                    ERP/Accounting System                        │
│                    (نظام المحاسبة/ERP)                          │
├─────────────────────────────────────────────────────────────────┤
│  ✓ Generate invoices                                            │
│  ✓ Submit to ZATCA                                              │
│  ✓ Sign invoices                                                │
│  ✓ Generate QR codes                                            │
│  ✓ Handle Phase 2 integration                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Invoice data
                              │ (already generated)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FinAI Audit Platform                         │
│                    (منصة FinAI للتدقيق)                         │
├─────────────────────────────────────────────────────────────────┤
│  ✓ READ existing invoice data                                   │
│  ✓ VERIFY against ZATCA requirements                            │
│  ✓ STORE verification results as audit evidence                 │
│  ✓ REPORT compliance status                                     │
│  ✗ NO write operations                                          │
│  ✗ NO ZATCA submission                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## API Endpoints / نقاط API

### ZATCA Live Verification Endpoints

| Endpoint | Method | Description (EN) | الوصف (عربي) |
|----------|--------|------------------|---------------|
| `/api/compliance/zatca-verification/scope_declaration/` | GET | Get scope documentation | الحصول على وثيقة النطاق |
| `/api/compliance/zatca-verification/{id}/verify/` | GET | Verify single invoice | التحقق من فاتورة واحدة |
| `/api/compliance/zatca-verification/verify-batch/` | POST | Verify multiple invoices | التحقق من مجموعة فواتير |
| `/api/compliance/zatca-verification/verify-vat-number/` | POST | Verify VAT number format | التحقق من تنسيق الرقم الضريبي |
| `/api/compliance/zatca-verification/verification-history/` | GET | Get verification audit trail | سجل التحققات السابقة |
| `/api/compliance/zatca-verification/{id}/evidence/` | GET | Get verification evidence | الحصول على دليل التحقق |

---

## ZATCA Error Codes Supported / رموز أخطاء ZATCA المدعومة

### Mandatory Field Errors / أخطاء الحقول الإلزامية
- `ZATCA-MF-001` - رقم الفاتورة مفقود
- `ZATCA-MF-002` - المعرف الفريد (UUID) مفقود
- `ZATCA-MF-003` - تاريخ الإصدار مفقود
- `ZATCA-MF-004` - اسم البائع مفقود
- `ZATCA-MF-005` - الرقم الضريبي للبائع مفقود
- `ZATCA-MF-006` - اسم المشتري مفقود
- `ZATCA-MF-007` - المجموع بدون الضريبة مفقود
- `ZATCA-MF-008` - مبلغ الضريبة مفقود
- `ZATCA-MF-009` - المجموع شامل الضريبة مفقود

### Format Errors / أخطاء التنسيق
- `ZATCA-FMT-001` - تنسيق الرقم الضريبي غير صحيح
- `ZATCA-FMT-002` - تنسيق المعرف الفريد غير صحيح
- `ZATCA-FMT-003` - طول رقم الفاتورة غير صحيح
- `ZATCA-FMT-004` - تنسيق التاريخ غير صحيح
- `ZATCA-FMT-005` - رمز العملة غير صحيح

### Calculation Errors / أخطاء الحساب
- `ZATCA-CALC-001` - خطأ في حساب ضريبة القيمة المضافة
- `ZATCA-CALC-002` - خطأ في حساب المجموع
- `ZATCA-CALC-003` - نسبة ضريبة القيمة المضافة غير صحيحة

### Business Rule Errors / أخطاء قواعد العمل
- `ZATCA-BR-001` - تاريخ الفاتورة في المستقبل
- `ZATCA-BR-002` - نوع الفاتورة غير صحيح
- `ZATCA-BR-003` - النوع الفرعي للفاتورة غير صحيح

### Integrity Errors / أخطاء السلامة
- `ZATCA-INT-001` - تجزئة الفاتورة غير صحيحة
- `ZATCA-INT-002` - سلسلة التجزئة منقطعة
- `ZATCA-INT-003` - رمز QR غير صحيح

---

## Regulatory References / المراجع التنظيمية

Each verification check references relevant ZATCA regulations:

| المادة | Article | Description |
|--------|---------|-------------|
| المادة 53 | Article 53 | متطلبات الفاتورة الضريبية |
| المادة 66 | Article 66 | شروط الرقم الضريبي |
| المادة 2 | Article 2 | نسبة ضريبة القيمة المضافة |
| متطلبات Phase 2 | Phase 2 Requirements | متطلبات المرحلة الثانية من فاتورة |

---

## Audit Evidence Storage / تخزين أدلة التدقيق

All verification operations are stored as audit evidence with:

- **Verification timestamp** / الطابع الزمني للتحقق
- **User who performed verification** / المستخدم الذي أجرى التحقق
- **Complete verification results** / نتائج التحقق الكاملة
- **Hash verification details** / تفاصيل التحقق من التجزئة
- **Arabic and English summaries** / ملخصات بالعربية والإنجليزية
- **Scope declaration** / إعلان النطاق

---

## Disclaimer / إخلاء المسؤولية

### العربية

FinAI هو نظام تدقيق ومراجعة فقط. لا يُعتبر نظام فوترة إلكترونية معتمداً من هيئة الزكاة والضريبة والجمارك. يجب على المنشآت استخدام أنظمة فوترة إلكترونية معتمدة للامتثال لمتطلبات هيئة الزكاة والضريبة والجمارك.

التحقق الذي يقوم به FinAI هو للمراجعة الداخلية فقط ولا يُغني عن التحقق الرسمي من خلال بوابة هيئة الزكاة والضريبة والجمارك.

### English

FinAI is an audit and review system only. It is not a ZATCA-certified e-invoicing system. Organizations must use certified e-invoicing systems to comply with ZATCA requirements.

Verification performed by FinAI is for internal review purposes only and does not substitute for official verification through the ZATCA portal.

---

## Version Information / معلومات الإصدار

- **Document Version:** 1.0
- **Last Updated:** January 27, 2026
- **System Version:** FinAI v3.0
- **ZATCA Phase:** Phase 2 (Fatoorah) Verification Support
