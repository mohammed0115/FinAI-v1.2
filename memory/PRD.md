# FinAI - AI-Powered Financial Audit Platform
## Product Requirements Document (PRD)

**Version**: 6.0  
**Last Updated**: January 27, 2026  
**Status**: Phase 7 Complete - LLM Integration for AI Explanations

---

## 1. Original Problem Statement

Build an AI-Powered Financial Audit Platform (FinAI) targeting the GCC market with:
- Django REST API backend
- SQLite database
- AI/LLM-based analysis
- Document processing with OCR
- Multi-country GCC compliance
- Financial analytics and reporting
- Audit trail and traceability
- **ZATCA e-invoicing compliance (Saudi Arabia)**
- **VAT reconciliation and audit**
- **Zakat calculation and comparison**
- **Arabic-first reporting**
- **Server-rendered Django Template frontend (Arabic RTL)**
- **ZATCA Live Verification (READ-ONLY)**
- **Arabic PDF Audit Reports**
- **Document Ingestion with OCR (Tesseract)**

---

## 2. What Has Been Implemented

### Phase 1: Backend Core (Complete)
- User authentication with JWT
- Organization management
- Document upload and processing models
- Transaction and Account models (Chart of Accounts)
- Journal Entry (double-entry bookkeeping)
- Compliance check models
- Audit flags and insights

### Phase 2: Compliance Module (Complete)
- **ZATCA E-Invoice Validation**: Pre-integration validation for Saudi e-invoicing requirements
- **VAT Reconciliation**: Compare VAT collected vs. reported with variance analysis
- **Zakat Calculation**: Calculate Zakat base and amount with detailed breakdown
- **Arabic Audit Reports**: Generate comprehensive Arabic audit reports
- **Regulatory References**: Database of regulatory articles/clauses (ZATCA, IFRS, etc.)
- **Audit Findings**: Track and manage audit findings with risk levels

### Phase 3: Django Template Frontend (Complete - Jan 27, 2026)
- **Arabic RTL Layout**: Full right-to-left support with IBM Plex Sans Arabic font
- **Data-Rich Dashboard**: Statistics, compliance summary, recent findings, anomalies, transactions
- **Compliance Overview**: ZATCA score (100%), VAT score (85%), Zakat score (90%) with breakdowns
- **Audit Findings**: List with filters (risk level, type, status), detail views with AI explanations
- **Transactions Page**: Filterable table with type, anomaly, date filters
- **Accounts Page**: Chart of accounts with type summary and balance display
- **Arabic Audit Report**: Printable report with executive summary, findings, recommendations, conclusion
- **Navigation**: Full Arabic navigation bar with 7 menu items

### Phase 4: ZATCA Live Verification (Complete - Jan 27, 2026)
- **READ-ONLY Verification**: Post-transaction validation of existing invoice data
- **Scope Documentation**: Clear separation between ERP invoice generation vs. FinAI verification
- **Verification Checks**: Mandatory fields, format validation, calculation verification, business rules
- **ZATCA Error Codes**: Full Arabic error messages with regulatory article references
- **Audit Evidence Storage**: All verifications stored for regulatory audit trail

### Phase 5: Arabic PDF Reports (Complete - Jan 27, 2026)
- **PDF Generation**: ReportLab-based PDF generation with Arabic support
- **Arabic Text Shaping**: Using arabic-reshaper and python-bidi for proper RTL text
- **Report Content**: Executive summary, compliance scores, audit findings, recommendations
- **Download Endpoint**: `/report/pdf/` endpoint for on-demand PDF generation
- **File Size**: ~47KB properly formatted PDF

### Phase 6: Document Ingestion with OCR (Complete - Jan 27, 2026)
- **Tesseract OCR**: Installed tesseract-ocr 5.3.0 with Arabic (ara) and English (eng) support
- **Document Upload**: Support for PDF, JPG, PNG, TIFF, BMP files (max 50MB)
- **OCR Processing**: Extract text from documents with confidence scoring
- **OCREvidence Model**: Store extracted text as immutable audit evidence with SHA-256 hash
- **Structured Data Extraction**: Best-effort extraction of invoice numbers, VAT numbers, amounts
- **Handwriting Support**: Toggle for handwritten document processing
- **Processing Metrics**: Confidence score, word count, page count, processing time

### Phase 7: LLM Integration for AI Explanations (Complete - Jan 27, 2026)
- **Live LLM**: Gemini 3 Flash via emergentintegrations library
- **Arabic-First**: All explanations generated in Arabic with professional financial terminology
- **Advisory Only**: Explanations are non-decision-making, human review required
- **Audit Trail**: AIExplanationLog model stores all generations with:
  - Confidence score (default 85%)
  - Model used and provider
  - Session ID and processing time
  - SHA-256 audit hash for integrity
  - Approval status (pending/approved/modified/rejected)
  - Human review tracking
- **Compliance**: No automatic scoring changes, all outputs clearly marked as advisory
- **UI Integration**: "توليد شرح جديد" button on finding detail page

---

## 3. Architecture

### Backend (Django)
```
/app/backend/
├── config/          # Settings, URLs (LOGIN_URL='/login/', ALLOWED_HOSTS=['*'])
├── core/            # User, Organization, Web Views
│   └── web_views.py # All page views including document_upload_view, ocr_evidence_*
├── documents/       # Document, Transaction, Account, JournalEntry, OCREvidence models
│   └── ocr_service.py # DocumentOCRService using Tesseract
├── reports/         # Report, Insight models
│   └── pdf_generator.py # ArabicPDFGenerator using ReportLab
├── compliance/      # ZATCA, VAT, Zakat, AuditFinding models
│   └── zatca_live_verification.py # ZATCA Live Verification Service
├── templates/       # Django Templates (Arabic RTL)
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── compliance/overview.html
│   ├── findings/list.html, detail.html
│   ├── transactions.html, transactions_detail.html
│   ├── accounts/list.html, detail.html
│   ├── reports/arabic_report.html
│   └── documents/upload.html, ocr_list.html, ocr_detail.html  # NEW
└── db.sqlite3
```

### Frontend Routing
- `/` - Dashboard (requires login)
- `/login/` - Login page
- `/logout/` - Logout
- `/compliance/` - Compliance overview
- `/findings/` - Audit findings list
- `/findings/<id>/` - Finding detail
- `/transactions/` - Transactions list
- `/transactions/<id>/` - Transaction detail
- `/accounts/` - Accounts list
- `/accounts/<id>/` - Account detail
- `/report/arabic/` - Arabic audit report (web view)
- `/report/pdf/` - Arabic audit report (PDF download)
- `/documents/upload/` - Document upload for OCR (NEW)
- `/ocr/` - OCR evidence list (NEW)
- `/ocr/<id>/` - OCR evidence detail (NEW)

### Proxy Configuration
- Nginx on port 3000 proxies to Django on port 8001
- External URL: https://ocr-audit.preview.emergentagent.com

---

## 4. Test Credentials

- **Email**: admin@finai.com
- **Password**: adminpassword
- **Organization**: FinAI Demo Company

---

## 5. Test Data

- 50 transactions
- 16 accounts (Chart of Accounts)
- 4 audit findings
- 10 ZATCA invoices
- 1 VAT reconciliation
- 1 Zakat calculation
- Regulatory references
- 2 OCR evidence records (from testing)

---

## 6. Upcoming/Future Tasks

### P2 - Medium Priority
1. **Database Migration**: Move from SQLite to PostgreSQL for production
2. **Dashboard Charts**: Add trend charts for income/expense over time
3. **Multi-Language Toggle**: Add English translation option
4. **Refactoring**: Split `web_views.py` into smaller focused files per app
5. **AI Explanation Review Workflow**: Add UI for approving/rejecting AI explanations

### P3 - Future
1. **Email Notifications**: Alert users of critical findings
2. **Role-Based Access**: Granular permissions by user role
3. **Full ZATCA API Integration**: Connect to live ZATCA API for invoice reporting/clearing

---

## 7. Test Reports

- `/app/test_reports/iteration_1.json` - Backend API tests (passed)
- `/app/test_reports/iteration_2.json` - Backend quality gate (passed)
- `/app/test_reports/iteration_3.json` - Frontend tests (28/28 passed, 100%)
- `/app/test_reports/iteration_4.json` - Frontend tests (10/10 passed, 100%) - Jan 27, 2026
- `/app/test_reports/iteration_5.json` - LLM Integration tests (10/10 passed, 100%) - Jan 27, 2026

---

## 8. Design Principles

- **Arabic-First**: All UI in Arabic with RTL layout
- **Data-Rich**: Tables over cards, high information density
- **Minimal**: Minimal colors and animations, regulator-friendly
- **Auditor-Focused**: Conservative, professional design for compliance officers

---

## 9. Dependencies Installed

### Python (Backend)
- Django 5.0+
- django-rest-framework
- reportlab (PDF generation)
- arabic-reshaper, python-bidi (Arabic text shaping)
- pytesseract (OCR interface)
- pdf2image (PDF to image conversion for OCR)
- Pillow (Image processing)

### System
- tesseract-ocr 5.3.0 with ara (Arabic) and eng (English) language packs

---

## 10. Known Limitations

### MOCKED Features
- **AI Explanations**: The `ai_explanation_ar` field in AuditFinding model contains static seeded data, NOT live LLM-generated content. LLM integration is a P1 task pending user authorization.

### ZATCA Scope Limitation
- ✓ Validates existing invoice data
- ✓ Stores verification results as audit evidence
- ✗ Does NOT generate invoices
- ✗ Does NOT submit to ZATCA
- ✗ Does NOT sign invoices
- ✗ Does NOT act on behalf of taxpayers

### OCR Scope Limitation
- ✓ Extracts text from documents as audit evidence
- ✓ Best-effort structured data extraction
- ✗ Extracted text is NOT source of accounting truth
- ✗ NOT used for automatic accounting entries
