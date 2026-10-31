# Skyntri — AI-Based Skin Health Assistant

Final Year Project (MUST, Dept. of Software Engineering).
React + Vite frontend, FastAPI backend, EfficientNetB0 facial skin-concern model, Tesseract OCR ingredient scanner, OpenCV progress comparison, PDF reports and an AI assistant.

> Skyntri gives AI estimates for skin-care information. It is **not** a medical diagnosis tool.

```
backend/    FastAPI API, model, migrations, tests, Dockerfile
frontend/   React/Vite single-page app
docs/       security audit, requirements, runbook, model card, test plan
```

## Quick start (development)

Backend (Python 3.13 recommended; install Tesseract for the ingredient scanner):

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
cp .env.example .env      # VITE_API_URL=http://localhost:8000
npm run dev
```

Tests: `cd backend && pytest -q`. See [backend/README.md](backend/README.md) and [docs/](docs/README.md).

## What changed in v1.1 (production-readiness pass)

* **Security:** admin-only contact messages; e-mailed, hashed, single-use password-reset links; production refuses weak JWT secrets; private image storage with short-lived signed URLs (no public `/uploads`); decode-based upload validation; database-backed rate limits; Alembic migrations; liveness/readiness checks; security headers; structured logs.
* **Non-skin images:** a staged input gate (quality → skin/non-skin → facial scope) and model-uncertainty abstention. Images that are not skin are rejected with guidance and never receive condition labels.
* **Two analysis tracks:** "Facial skin concerns" (Model A) is live. "Skin disease screening support" (Model B) is shown but not available until clinically reviewed and validated.
* **Deployment:** Dockerfile with Tesseract, CI workflow, runbook, environment reference.

Open items before a public launch are listed in [docs/01_Security_Audit_Report.md](docs/01_Security_Audit_Report.md#still-blocking-a-public-launch).
