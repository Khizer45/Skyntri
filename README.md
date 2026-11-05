# Skyntri — AI-Based Skin Health Assistant

Final Year Project (MUST, Dept. of Software Engineering).
React + Vite frontend, FastAPI backend with PostgreSQL, EfficientNet skin models (trained by you on Colab from `ml/notebooks/`), Tesseract OCR ingredient scanner, OpenCV progress comparison, PDF reports, an AI assistant, an ingredient-based shop and an admin panel.

> Skyntri gives AI estimates for skin-care information. It is **not** a medical diagnosis tool.

```
backend/    FastAPI API, migrations, tests, Dockerfile; backend/models/ holds the trained models
frontend/   React/Vite single-page app
ml/         Colab notebooks: dataset cleaning, training, evaluation, export (see ml/README.md)
docs/       security audit, requirements, runbook, model card, test plan
```

## Run with Docker (easiest: nothing else to install)

Install **Docker Desktop**, then in the project folder:

```bash
docker compose up --build
```

* Before the first start, copy `.env.docker.example` to `.env` and set `POSTGRES_PASSWORD` (database password), `SECRET_KEY` (keeps you logged in across restarts) and `ADMIN_EMAILS` (your e-mail becomes admin).
* App: http://localhost:5173 · API: http://localhost:8000 (docs at `/docs`)
* The first build downloads TensorFlow, so it takes a while. Later starts are fast: `docker compose up`
* **Database:** PostgreSQL 16 runs as the `db` service. Its data lives in the Docker volume `skyntri-pg`, uploaded images in `skyntri-data`; both survive restarts.
* **Admin:** log in with the e-mail from `ADMIN_EMAILS` (log out and in again after changing it). Or run `docker compose exec backend python -m app.cli make-admin you@example.com`. The *Admin panel* section at the top of the sidebar has Overview, Products, Orders & Payments and Users.
* **Trained models:** copy them into `backend/models/` with the names in [ml/README.md](ml/README.md#4-where-to-save-the-trained-models-backend), then `docker compose restart backend`. No rebuild and no `.env` change are needed because the folder is mounted and the names are the defaults.
* Stop: `docker compose down`. Delete all data too: `docker compose down -v`.

## Put it live (server + HTTPS)

To let other people open Skyntri from a link, follow [docs/DEPLOY_VPS.md](docs/DEPLOY_VPS.md):
1. Get a VPS (4 GB RAM or more) and two web addresses for it.
2. `cp .env.production.example .env` and fill it in.
3. Copy the model files into `backend/models/`.
4. Run `docker compose -f docker-compose.prod.yml up -d --build`.

Caddy gets the HTTPS certificates automatically.

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

## v1.2 additions

* **ML notebooks** in [`ml/`](ml/README.md): Colab notebooks for Model A (facial concerns) and Model B (skin disease screening). They cover dataset loading, cleaning, augmentation, EfficientNet training, evaluation metrics, export and prediction. Model A and Model B have been trained once; the results are in [`ml/results/facial_v1/`](ml/results/facial_v1/README.md) and [`ml/results/disease_v1/`](ml/results/disease_v1/README.md). The skin gate (notebook 03) is not trained yet. See [ml/README.md](ml/README.md#4-where-to-save-the-trained-models-backend) for where the trained files go.
* **Model B plug-in:** the backend loads the exported disease model when `DISEASE_SCREENING_ENABLED=true`. Referral comes first, it abstains when unsure, and it never gives an all-clear.
* **Shop:** search products by the ingredients they contain or avoid, get suggestions from your latest facial analysis, then use the cart and cash-on-delivery orders. Admins create, edit and delete products (with images) and manage orders.

Open items before a public launch are listed in [docs/01_Security_Audit_Report.md](docs/01_Security_Audit_Report.md#still-blocking-a-public-launch).

## v1.3 additions

* **Input gate v2:** real skin photos under warm or cool indoor light are no longer rejected as "not a skin image" (valid-skin rejection on the sample set fell from 10.7 % to 1.8 %). A trainable gate model (notebook 03) replaces the rules when installed.
* **PostgreSQL** in Docker Compose and CI; SQLite still works for quick local runs.
* **Admin panel:** overview (sales, payments, orders, stock, users), products, orders with cash-on-delivery payment tracking (unpaid → paid → refunded), and user management. CLI: `python -m app.cli make-admin | remove-admin | list-admins`.
* **New look:** teal/coral theme, new sidebar and header with cart count, dashboard hero, dark mode.
* **Models:** the old facial model was removed. New notebooks use better datasets (Kaggle Skin Issues v2 + Facial Skin 8-class for concerns; Skin Diseases Image Dataset + PAD-UFES-20 + optional ISIC 2019 for disease; COCO + DTD for the gate), face crop, test-time augmentation and an abstain threshold. See [ml/README.md](ml/README.md).
