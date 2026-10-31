# Skyntri Backend

FastAPI backend for **Skyntri — AI-Based Skin Health Assistant**.

## Features

* **Auth:** register, login (JWT with issuer/audience/expiry checks), e-mailed password reset (hashed, single-use links), change password, delete account (removes files too). Database-backed login throttling.
* **Roles:** `user` / `admin`, stored server-side. Admins come from `ADMIN_EMAILS`.
* **Skin analysis** (`POST /analyses/analyze`): input gate (quality, skin vs non-skin, facial scope), Model A EfficientNetB0 facial concerns, abstention when uncertain. Model B (disease screening) is not released.
* **Ingredient scanner:** Tesseract OCR + curated ingredient database.
* **Progress checker:** OpenCV visual comparison (approximate, not clinical).
* **Reports:** ReportLab PDFs, owner-only download.
* **AI assistant:** local rule-based assistant with optional Gemini/OpenAI provider.
* **Contact:** public form; admin-only management.
* **Private files:** stored in `UPLOAD_DIR`, served only through signed `/files/...` URLs.
* **Ops:** Alembic migrations, `/health` + `/health/ready`, JSON logs, security headers, request-size limit.

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

* API: `http://localhost:8000`, docs at `/docs` (disabled when `ENVIRONMENT=production`).
* Install the Tesseract executable for OCR (`sudo apt install tesseract-ocr`, `brew install tesseract`, or the Windows installer).
* In development, if `SECRET_KEY` is empty an ephemeral key is generated (you are logged out on restart). Without SMTP, password-reset links are written to the server log.
* Make yourself admin: add your e-mail to `ADMIN_EMAILS` and log in again.

## Database and migrations

SQLite by default; PostgreSQL in production (`postgresql+psycopg://…`).
Migrations run automatically at start-up in development (`AUTO_MIGRATE=true`) and from the Docker entrypoint in production. Existing `skyntri.db` files created by the old `create_all` are upgraded in place.

```bash
alembic upgrade head          # apply
alembic revision -m "change"  # new migration (then edit it)
```

## Tests and checks

```bash
ruff check .
pytest -q
python scripts/evaluate_input_gate.py /path/to/dataset   # skin/ and non_skin/ folders
```

## Docker

```bash
docker build -t skyntri-api backend
docker run -p 8000:8000 --env-file prod.env -v skyntri-uploads:/data/uploads skyntri-api
```

See `../docs/DEPLOYMENT_RUNBOOK.md` and `../docs/ENVIRONMENT_VARIABLES.md`.

## Project structure

```
app/
  core/         settings + start-up validation, JWT/password/signing, logging
  db/           SQLAlchemy engine, ORM models, Alembic runner
  routers/      auth, profile, contact, analyses, scans, ingredients,
                progress, reports, history, chat, files
  services/     uploads (private storage), image_gate, skin_analysis,
                rate_limit, email, OCR, progress, PDF, chat, user_files
  schemas.py    Pydantic models (signs private image URLs on output)
  main.py       app, middleware, error handlers, health checks
migrations/     Alembic revisions (0001 baseline, 0002 security hardening)
scripts/        evaluate_input_gate.py
tests/          pytest suite
```
