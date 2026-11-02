# Deployment runbook

## Architecture (simple first)

* **Frontend:** static build (`npm run build` → `frontend/dist`) on any static host. Set `VITE_API_URL` at build time; the build adds a Content-Security-Policy meta tag for that API origin. Configure the host to add `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff` and HSTS.
* **Backend:** `backend/Dockerfile` (Python 3.13, Tesseract installed, non-root user, one Uvicorn worker, TensorFlow inside the API).
* **Database:** managed PostgreSQL (`DATABASE_URL=postgresql+psycopg://…`).
* **Private files:** a persistent volume mounted at `/data/uploads` (`UPLOAD_DIR`). It is **never** publicly served; the API issues signed URLs.

## First deployment

1. Create secrets in the hosting platform (never in Git): `SECRET_KEY` (≥ 32 random chars, e.g. `python -c "import secrets;print(secrets.token_urlsafe(48))"`), `DATABASE_URL`, `SMTP_*`, `ADMIN_EMAILS`, optional LLM keys.
2. Set `ENVIRONMENT=production`, `CORS_ORIGINS=https://<frontend-domain>`, `FRONTEND_URL=https://<frontend-domain>`.
3. Build: `docker build -t skyntri-api:<git-sha> backend`.
4. Run with the volume: `docker run -p 8000:8000 --env-file prod.env -v skyntri-uploads:/data/uploads skyntri-api:<git-sha>`.
   The entrypoint runs `alembic upgrade head`, then starts Uvicorn. Production refuses to start with a weak/default secret or `CORS_ORIGINS=*`.
5. Check `GET /health` (liveness) and `GET /health/ready` (database, model, gate, OCR, storage). Route traffic only when ready returns 200.
6. Put the API behind HTTPS. If a reverse proxy is used, keep `--proxy-headers` and set `FORWARDED_ALLOW_IPS` to the proxy address so rate limits see real client IPs.

## Resource profile (to be measured)

| Item | Status |
|---|---|
| Image size | Expect ~2–3 GB (TensorFlow). Measure with `docker images`. |
| RAM per worker | TensorFlow + EfficientNetB0 loaded once per worker. **Measure** with `docker stats` after warm-up and under load; start with ≥ 2 GB. |
| Cold start | Model warm-up runs at start-up (`MODEL_WARMUP=true`). Measure the time to ready. |
| Inference latency | Measure p50/p95 on the target CPU. `MAX_CONCURRENT_INFERENCE` limits parallel inferences per worker. |

Do not assume a free hosting tier can run TensorFlow; measure first. Add workers or containers only after measuring memory.

## Backups and restore

* **Database:** enable automated daily backups and point-in-time recovery on the managed PostgreSQL. Manual: `pg_dump --format=custom "$DATABASE_URL" > skyntri-$(date +%F).dump`. With Docker Compose: `docker compose exec db pg_dump -U skyntri --format=custom skyntri > skyntri-$(date +%F).dump`.
* **Files:** snapshot the `/data/uploads` volume daily (or sync it to a private, encrypted bucket).
* **Restore drill (do this before launch and quarterly):**
  1. `pg_restore --clean --no-owner -d "$RESTORE_DATABASE_URL" skyntri-YYYY-MM-DD.dump`
  2. Restore the volume snapshot to a test volume.
  3. Start a staging container against both; run `alembic upgrade head`; log in with a test account; open history and a report.
* Retention: keep 30 daily backups. Deleting an account removes live files immediately; backups age out with the retention window. State this in the privacy notice.

## Release procedure

1. CI green (lint, tests, migration, frontend build, scans, container smoke test).
2. Take a DB backup.
3. Deploy the new image; the entrypoint runs migrations.
4. Watch `/health/ready`, error logs and `analysis_abstained` / `analysis_completed` event rates.

## Rollback

* **App only (no schema change):** redeploy the previous image tag.
* **With a migration:** migrations `0002+` have `downgrade()`. Run `alembic downgrade <previous-revision>` *only* if the new columns are not needed by the old code. The safer default is to roll the image back and keep the additive schema (old code ignores the new columns). The baseline `0001` is never downgraded; restore from backup instead.
* **Model:** keep the previous artifact and its version string. Set `DATASET3_MODEL_PATH` / `FACIAL_MODEL_VERSION` back, then restart.
* **Bad gate model:** remove or rename `models/skin_gate.keras`; the heuristic gate is used again.

## Secret rotation

Changing `SECRET_KEY` logs everyone out and invalidates outstanding signed file URLs. Rotate it if it was ever committed, shared, or used with the old default in any public deployment.
