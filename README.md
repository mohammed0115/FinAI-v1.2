# FinAI v1.2

Financial audit and compliance platform (Arabic-first, RTL) with:

- Django backend (`backend/`) serving API + web dashboard templates
- Optional proxy frontend (`frontend/`) that forwards traffic to Django
- Optional UI playground (`frontend-next/`) for Vite-based frontend experiments

## 1) Quick Start (Recommended)

Run the real app directly from Django templates.

### Prerequisites

- Python 3.10+
- pip
- Node.js 18+ (only if you want proxy/frontend folders)
- Optional for OCR: Tesseract OCR installed and available in PATH

### Backend setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py init_db
python manage.py runserver 8001
```

Open:

- `http://127.0.0.1:8001/login/`

Default dev users created by `init_db`:

- `admin@finai.com` / `admin123`
- `accountant@finai.com` / `accountant123`

## 2) Optional: Run Through Proxy (`frontend/`)

Use this if you want access via `localhost:3000`.

```powershell
cd frontend
npm install
npm start
```

Open:

- `http://127.0.0.1:3000`

Notes:

- Proxy forwards all traffic to Django at `http://127.0.0.1:8001`
- Keep backend running first

## 3) Optional: UI Playground (`frontend-next/`)

This is a standalone Vite app for UI work and does not replace Django routes.

```powershell
cd frontend-next
npm install
npm run dev
```

Open:

- `http://127.0.0.1:5173`

## 4) API Auth Endpoints

- Obtain JWT: `POST /api/auth/token/`
- Refresh JWT: `POST /api/auth/token/refresh/`

Base URL (local): `http://127.0.0.1:8001`

## 5) Useful Environment Variables

`backend/config/settings.py` reads these variables:

- `USE_SQLITE` (default `True`)
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `SECRET_KEY`
- `CORS_ORIGINS`
- `CSRF_TRUSTED_ORIGINS`
- `EMERGENT_LLM_KEY`
- `TESSERACT_CMD` (used by OCR service)

If no `.env` is provided, safe local defaults are used for development.

## 6) Troubleshooting

### `Tesseract OCR is not installed or not accessible`

- Install Tesseract and add it to PATH
- Or set `TESSERACT_CMD` to the executable path
- OCR features will stay disabled until configured

### Port already in use

- Change port: `python manage.py runserver 8002`
- Or stop process using the occupied port

### Static/admin pages in production-style run

Use the startup flow:

```powershell
cd backend
python manage.py collectstatic --noinput
python -m uvicorn server:app --host 0.0.0.0 --port 8001
```

## 7) Project Layout

- `backend/` Django apps, APIs, templates, auth, OCR, compliance
- `frontend/` Express proxy to backend
- `frontend-next/` Vite UI playground
- `tests/`, `backend/tests/` test suites
