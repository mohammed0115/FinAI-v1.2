# Copilot Instructions for FinAI Backend

## Project Overview
- **FinAI** is a Django-based backend for financial audit, compliance, and reporting, with AI-powered features (LLM explanations, OCR, analytics).
- Major domains: `core`, `documents`, `ai_plugins`, `analytics`, `reports`, `compliance`, `hard_rules` (each is a Django app).
- ASGI-first: entrypoint is `server.py` (for uvicorn), not just `manage.py`.
- Uses both REST API (DRF) and async/ASGI patterns.

## Key Workflows
- **Startup:** Use `startup.sh` for production: runs migrations, static collection, DB init, then launches with `uvicorn server:app`.
- **Development:**
  - Use `python manage.py runserver` for local dev.
  - Environment config via `.env` (see `server.py` and `FinAI/settings.py`).
- **Testing:**
  - Main tests in `tests/` (see `test_ai_explanation.py` for LLM/AI integration tests).
  - Run with `pytest` (see `requirements.txt`).
  - Some tests use Django shell via subprocess for DB assertions.

## Project Conventions & Patterns
- **App boundaries:** Each domain (e.g., `compliance`, `reports`) is a Django app with its own `models.py`, `services.py`, `views.py`, etc.
- **AI/LLM integration:**
  - AI logic in `ai_plugins/` and `compliance/ai_explanation_service.py`.
  - LLM provider/model is tracked in DB (`AIExplanationLog.model_used`).
- **Hard rules engine:** In `hard_rules/` (see `engine.py`, `gate.py`).
- **Static/media:**
  - Static: `/static/` (collected to `/staticfiles/` or `/home/u163153443/public_html/static` in prod).
  - Media: `/media/`.
- **Custom user model:** `core.User`.
- **REST API:** Uses JWT auth (see `FinAI/settings.py` > `REST_FRAMEWORK`, `SIMPLE_JWT`).
- **CORS/CSRF:** Configurable via env vars; see `FinAI/settings.py` for trusted origins.

## Integration Points
- **LLM/AI:** Google Gemini, OpenAI, and others (see `requirements.txt`, `ai_plugins/`, `compliance/`).
- **OCR:** `documents/ocr_service.py` (uses Tesseract, pdf2image, etc.).
- **PDF/reporting:** `reports/pdf_generator.py` (uses ReportLab).
- **External API:** ZATCA (Saudi tax authority) integration in `compliance/zatca_api_service.py`.

## Examples
- To add a new AI plugin: create a subdir in `ai_plugins/plugins/` and register in `ai_plugins/loader.py`.
- To add a new hard rule: implement in `hard_rules/engine.py` and expose via `hard_rules/gate.py`.
- To run all tests: `pytest tests/`.

## References
- Entrypoints: `server.py`, `startup.sh`, `FinAI/settings.py`
- Example test: `tests/test_ai_explanation.py`
- AI logic: `ai_plugins/`, `compliance/ai_explanation_service.py`
- Hard rules: `hard_rules/`
- Reporting: `reports/`
- OCR: `documents/ocr_service.py`

---
For more, see code comments in each app and the `requirements.txt` for dependencies.
