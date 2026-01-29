# FinAI Frontend Design Specification
## لوحة معلومات التدقيق المالي - Arabic-First Auditor Dashboard

**Version**: 1.0  
**Date**: January 27, 2026  
**Language Priority**: Arabic (RTL) Primary, English Secondary

---

## 1. Design Principles - مبادئ التصميم

### 1.1 Arabic-First Approach
- **Default Direction**: RTL (Right-to-Left)
- **Primary Language**: Arabic for all labels, headings, and content
- **Font Family**: 
  - Arabic: `Noto Sans Arabic`, `Tajawal`, `IBM Plex Sans Arabic`
  - English fallback: `Inter`, `system-ui`
- **Number Format**: Arabic-Indic numerals optional, Western numerals acceptable
- **Date Format**: Hijri calendar option available, Gregorian default

### 1.2 Read-Only Audit Focus
- **NO editing** of financial entries from dashboard
- **View and analyze** only
- **Resolution actions** allowed (mark as resolved, add notes)
- **Report generation** allowed

### 1.3 Color Scheme (Dark Theme Professional)
```css
:root {
  --bg-primary: #0f172a;      /* Slate 900 */
  --bg-secondary: #1e293b;    /* Slate 800 */
  --bg-card: #334155;         /* Slate 700 */
  --text-primary: #f8fafc;    /* Slate 50 */
  --text-secondary: #94a3b8;  /* Slate 400 */
  --accent-green: #22c55e;    /* Success/Compliant */
  --accent-yellow: #eab308;   /* Warning */
  --accent-orange: #f97316;   /* High Risk */
  --accent-red: #ef4444;      /* Critical */
  --accent-blue: #3b82f6;     /* Info/Links */
}
```

---

## 2. Dashboard Layout - تخطيط لوحة المعلومات

### 2.1 Header - الشريط العلوي
```
┌─────────────────────────────────────────────────────────────┐
│  🏢 شركة الفيصل للتجارة        [EN/AR]  👤 محمد أحمد       │
│  FinAI - منصة التدقيق المالي                               │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Main Dashboard Grid
```
┌─────────────────────────────────────────────────────────────┐
│                    نظرة عامة على الامتثال                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ الامتثال │ │ الزكاة   │ │ ض.ق.م    │ │ فاتورة   │       │
│  │  العام   │ │          │ │          │ │ إلكترونية│       │
│  │   91%    │ │   90%    │ │   85%    │ │   80%    │       │
│  │ ██████░░ │ │ █████░░░ │ │ ████░░░░ │ │ ████░░░░ │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
├─────────────────────────────────────────────────────────────┤
│             ملاحظات التدقيق - Audit Findings                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 🔴 حرج (2)  🟠 مرتفع (2)  🟡 متوسط (4)  🟢 منخفض (0) │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ FND-SA-2026-001 │ ضعف في الفصل بين الصلاحيات       │   │
│  │ مستوى المخاطر: حرج  │ التأثير المالي: غير محدد      │   │
│  │ المرجع: نظام الرقابة الداخلية                       │   │
│  │ [عرض التفاصيل] [تم الحل ✓]                         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Core Components - المكونات الأساسية

### 3.1 Compliance Score Widget
```jsx
<ComplianceScoreCard
  score={91}
  label_ar="درجة الامتثال العام"
  label_en="Overall Compliance"
  trend="+5%"
  color="green"
/>
```

**Features**:
- Circular progress indicator
- Color-coded (green/yellow/orange/red)
- Trend indicator (arrow up/down)
- Arabic label primary, English tooltip

### 3.2 Audit Flag Card
```jsx
<AuditFlagCard
  finding_number="FND-SA-2026-001"
  title_ar="عدم تقديم إقرار ضريبة القيمة المضافة في الموعد"
  risk_level="high"
  risk_level_ar="مرتفع"
  financial_impact={25000}
  currency="SAR"
  regulatory_ref="المادة 40 - نظام ضريبة القيمة المضافة"
  is_resolved={false}
  ai_confidence={85}
/>
```

**Features**:
- Risk level badge with Arabic label
- Financial impact in SAR
- Regulatory reference link
- AI confidence indicator
- Resolution action button

### 3.3 Transaction Drill-Down
```jsx
<TransactionDetail
  transaction_id="txn-uuid"
  amount={50000}
  vat_amount={7500}
  vendor="شركة النور للتجارة"
  date="2026-01-15"
  flags={[
    { type: 'vat_error', message_ar: 'خطأ في حساب الضريبة' }
  ]}
  ai_explanation_ar="تم اكتشاف فرق في حساب الضريبة بقيمة 250 ريال"
/>
```

### 3.4 AI Explanation Panel
```jsx
<AIExplanationPanel
  title_ar="سبب التنبيه"
  explanation_ar="تم اكتشاف هذه الملاحظة من خلال تحليل الذكاء الاصطناعي"
  confidence={85}
  factors={[
    { factor_ar: 'مبلغ غير اعتيادي', weight: 0.4 },
    { factor_ar: 'توقيت غير معتاد', weight: 0.3 },
    { factor_ar: 'نمط مكرر', weight: 0.3 }
  ]}
/>
```

---

## 4. Page Structure - هيكل الصفحات

### 4.1 Navigation Menu (RTL)
```
┌──────────────────────────┐
│      القائمة الرئيسية     │
├──────────────────────────┤
│  📊 لوحة المعلومات       │
│  📋 ملاحظات التدقيق      │
│  💰 ضريبة القيمة المضافة  │
│  🕌 الزكاة               │
│  📄 الفواتير الإلكترونية  │
│  📈 التقارير             │
│  ⚙️ الإعدادات           │
└──────────────────────────┘
```

### 4.2 Pages List

| Page | Arabic Name | Purpose |
|------|-------------|---------|
| Dashboard | لوحة المعلومات | Overall compliance overview |
| Audit Findings | ملاحظات التدقيق | List and detail of all findings |
| VAT | ضريبة القيمة المضافة | VAT reconciliation and discrepancies |
| Zakat | الزكاة | Zakat calculation and comparison |
| E-Invoices | الفواتير الإلكترونية | ZATCA invoice validation |
| Reports | التقارير | Arabic audit report generation |
| Settings | الإعدادات | Language, theme, notifications |

---

## 5. Feature Specifications

### 5.1 Compliance Score Widgets
- **Display**: Circular gauge with percentage
- **Colors**: 
  - 90-100%: Green (ممتاز)
  - 70-89%: Yellow (جيد)
  - 50-69%: Orange (يحتاج تحسين)
  - 0-49%: Red (حرج)
- **Drill-down**: Click to see score breakdown

### 5.2 Audit Flags Table
- **Columns**: رقم الملاحظة, العنوان, مستوى المخاطر, التأثير المالي, الحالة
- **Sorting**: By risk level (default), date, financial impact
- **Filtering**: By risk level, type, resolution status
- **Actions**: View details, mark resolved (not edit)

### 5.3 AI Explainability
- **Why Flagged**: Arabic explanation of AI reasoning
- **Confidence Score**: Percentage with visual bar
- **Contributing Factors**: List with weights
- **Human Override**: Allow auditor to dismiss with reason

### 5.4 Regulatory Mapping
- **Display**: Finding linked to regulatory article
- **Content**:
  - Article number (المادة XX)
  - Arabic title and description
  - Penalty information
  - Source link
- **Interaction**: Expandable panel

---

## 6. Arabic Report Generation

### 6.1 Report Types
1. **تقرير التدقيق الشامل** - Comprehensive Audit Report
2. **تقرير ضريبة القيمة المضافة** - VAT Compliance Report
3. **تقرير الزكاة السنوي** - Annual Zakat Report
4. **تقرير الفواتير الإلكترونية** - E-Invoice Compliance Report

### 6.2 Report Structure
```
┌─────────────────────────────────────────┐
│          تقرير التدقيق المالي            │
│         Financial Audit Report           │
├─────────────────────────────────────────┤
│ رقم التقرير: AUD-SA-20260127            │
│ التاريخ: 27 يناير 2026                   │
│ المنشأة: شركة الفيصل للتجارة             │
├─────────────────────────────────────────┤
│           الملخص التنفيذي                │
│  • درجة الامتثال: 91%                    │
│  • مستوى المخاطر: منخفض                  │
│  • إجمالي الملاحظات: 4                   │
├─────────────────────────────────────────┤
│             النتائج والملاحظات            │
│  1. ملاحظة رقم 001...                   │
│  2. ملاحظة رقم 002...                   │
├─────────────────────────────────────────┤
│              التوصيات                    │
│  • تعزيز إجراءات الامتثال...             │
├─────────────────────────────────────────┤
│              الخلاصة                     │
│  رأي غير متحفظ...                       │
├─────────────────────────────────────────┤
│ المدقق: _______________                 │
│ التوقيع: _______________                │
└─────────────────────────────────────────┘
```

---

## 7. Technical Requirements

### 7.1 RTL Support
```css
html[dir="rtl"] {
  direction: rtl;
  text-align: right;
}

.card {
  direction: inherit;
}

.number {
  direction: ltr; /* Numbers always LTR */
}
```

### 7.2 API Integration
All data from existing endpoints:
- `GET /api/compliance/dashboard/overview/`
- `GET /api/compliance/audit-findings/`
- `GET /api/compliance/audit-findings/generate_report_ar/`
- `GET /api/compliance/vat-reconciliations/`
- `GET /api/compliance/zakat-calculations/`
- `GET /api/compliance/zatca-invoices/`

### 7.3 State Management
- Use React Query for server state
- Local state for UI (filters, sort)
- No editing mutations (read-only)

---

## 8. DO NOT Include

❌ Transaction editing forms
❌ Invoice creation/modification
❌ Account balance adjustments
❌ Decorative charts without audit value
❌ Unnecessary animations
❌ Non-audit features

---

## 9. Accessibility

- WCAG 2.1 AA compliance
- Keyboard navigation
- Screen reader support (Arabic)
- High contrast mode
- Font size adjustment

---

*Document prepared for FinAI Auditor Dashboard v1*
