# Skyntri Backend

FastAPI backend for **Skyntri — AI-Based Skin Health Assistant**.

## Features

* **Auth:** register, login (JWT with issuer/audience/expiry checks), e-mailed password reset (hashed, single-use links), change password, delete account (removes files too). Database-backed login throttling.
* **Roles:** `user` / `admin`, stored server-side. Admins come from `ADMIN_EMAILS`, `python -m app.cli make-admin EMAIL`, or another admin (*Admin → Users*).
* **Admin panel API:** `/admin/stats`, `/admin/users`, `/admin/products`, `/admin/orders` (order and payment status).
* **Skin analysis** (`POST /analyses/analyze`): input gate (quality, skin vs non-skin, facial scope), Model A facial concerns and optional Model B disease screening, both EfficientNet models trained with `../ml/notebooks/` and loaded from `models/` (face crop, TTA, abstention when uncertain). Without a model file the track reports `model_not_installed`.
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
* Make yourself admin: add your e-mail to `ADMIN_EMAILS` and log in again, or run `python -m app.cli make-admin you@example.com`.
* Trained models go in `models/` (see `models/README.md` and `../ml/README.md`).

## Database and migrations

SQLite by default for quick local runs; PostgreSQL 16 in Docker Compose, CI and production (`DATABASE_URL=postgresql+psycopg://user:pass@host:5432/skyntri`).
Migrations run automatically at start-up in development (`AUTO_MIGRATE=true`) and from the Docker entrypoint in production. Existing `skyntri.db` files created by the old `create_all` are upgraded in place.

```bash
alembic upgrade head          # apply
alembic revision -m "change"  # new migration (then edit it)
```

## Tests and checks

```bash
ruff check .
pytest -q
TEST_DATABASE_URL=postgresql+psycopg://skyntri:pw@localhost:5432/skyntri_test pytest -q tests/test_shop.py tests/test_admin_panel.py   # against PostgreSQL
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
                progress, reports, history, chat, files, shop, admin
  services/     uploads (private storage), image_gate, model_io, skin_analysis,
                disease_screening, shop, rate_limit, email, OCR, progress,
                PDF, chat, user_files
  cli.py        make-admin / remove-admin / list-admins
  schemas.py    Pydantic models (signs private image URLs on output)
  main.py       app, middleware, error handlers, health checks
migrations/     Alembic revisions (0001 baseline … 0004 admin payments)
models/         trained .keras files + metadata (git-ignored)
scripts/        evaluate_input_gate.py
tests/          pytest suite
```
