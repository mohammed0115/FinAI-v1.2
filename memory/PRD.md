# FinAI – AI-Powered Financial Audit Platform

## Product Overview
A read-only audit and compliance verification platform for Saudi Arabian financial regulations (ZATCA, VAT, Zakat). Features Arabic-first (RTL) design using server-rendered Django Templates.

## Architecture
- **Backend:** Django (Monolithic) on port 8001
- **Frontend:** Server-rendered Django Templates (SSR)
- **Proxy:** Node.js/Express on port 3000 (routes to Django)
- **Database:** SQLite
- **OCR:** Tesseract (pytesseract)
- **LLM:** Emergent Integration (Gemini 3 Flash)

## Completed Features (P0)

### Core Features ✅
- [x] User authentication (session-based)
- [x] Auditor Dashboard with compliance stats
- [x] ZATCA invoice verification (simulated)
- [x] VAT reconciliation tracking
- [x] Zakat calculation and compliance
- [x] Arabic PDF audit report generation
- [x] Multi-language UI toggle (AR/EN)
- [x] Company settings with country-specific VAT validation

### Document Processing ✅
- [x] Single file upload
- [x] Multi-file upload (100+ files)
- [x] ZIP batch upload with extraction
- [x] OCR processing for Arabic/English
- [x] AI-powered document explanations

### UI Redesign (Partial) ✅
- [x] New BI-style base template with sidebar
- [x] Modern dashboard layout
- [x] KPI card components
- [x] Analytics page redesign
- [x] Reports page redesign
- [x] Fixed duplicate block content error
- [x] Fixed compliance view query bug

## Known Issues

### Infrastructure Issue (BLOCKING for Preview URL)
**Status:** Escalated to Emergent Support

The external preview URL (`finai-audit-1.preview.emergentagent.com`) returns 520 errors for authenticated HTML pages:

| Endpoint | Local | External |
|----------|-------|----------|
| Health check | ✅ | ✅ |
| Login page | ✅ | ✅ |
| API endpoints | ✅ | ✅ |
| Dashboard (37KB) | ✅ | ❌ 520 |
| Compliance (35KB) | ✅ | ❌ 520 |

**Root Cause:** Kubernetes ingress/Cloudflare issue - requests never reach application.

**Workaround:** Test locally using `localhost:3000` or `localhost:8001`

## Environment Setup Notes

### For New Sessions:
1. Install Tesseract OCR:
   ```bash
   apt-get update && apt-get install -y tesseract-ocr tesseract-ocr-ara
   ```

2. Restart services:
   ```bash
   sudo supervisorctl restart backend frontend
   ```

### Test Credentials:
- Email: `admin@finai.com`
- Password: `adminpassword`

## File Structure
```
/app/backend/
├── config/            # Django settings, URLs
├── core/              # Main views, web URLs
├── compliance/        # ZATCA, VAT, Zakat models/views
├── documents/         # Upload, OCR processing
├── reports/           # PDF generation
└── templates/         # Django templates (redesigned)

/app/frontend/
└── server.js          # Express proxy server
```

## API Endpoints
- `POST /api/auth/token/` - JWT authentication
- `GET /api/compliance/` - Compliance data (JWT required)
- `GET /api/documents/` - Document list (JWT required)
- `POST /api/documents/upload/` - Document upload
- `GET /health` - Health check

## Mocked Integrations
- **ZATCA API:** Simulated responses (not connected to live ZATCA)

## Backlog / Future Tasks
- None specified at this time
- Continue development assuming Django Templates as final architecture
- No React/SPA migration authorized

## Support Contact (for Infrastructure Issue)
- Discord: https://discord.gg/VzKfwCXC4A
- Email: support@emergent.sh
