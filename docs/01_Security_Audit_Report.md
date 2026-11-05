# Skyntri — Security & Deployment Audit Report (v1.1, remediation status)

**Original audit:** 31 October 2026, commit `a2f08db` (static review of selected files).
**This update:** 31 October 2026. Every finding was re-checked against the code at `a2f08db` before it was fixed.
**Evidence:** automated tests in `backend/tests/` (68 passing locally with Python 3.13, see "Test evidence" below).

> This is still **not** a penetration test, clinical validation or deployment certification. Items marked *Open* or *Partial* block a public launch.

## Status summary

| ID | Severity | Verified at a2f08db? | Status | Fix (main files) | Test evidence |
|---|---|---|---|---|---|
| SK-01 Public contact listing | Critical | Confirmed (`routers/contact.py`, `GET /contact` had no auth) | **Fixed** | `routers/contact.py`, `dependencies.require_admin`, `User.role` | `test_contact_submission_is_public_but_listing_is_admin_only` |
| SK-02 Reset token returned by API | Critical | Confirmed (`dev_reset_token` in response; token stored in clear) | **Fixed** | `routers/auth.py`, `services/email.py`, `core/security.hash_opaque_token` | `test_forgot_password_never_returns_token_and_stores_only_hash`, `test_reset_token_is_single_use`, `test_expired_and_superseded_reset_tokens_fail`, `test_password_reset_disabled_in_production_without_email` |
| SK-03 Insecure default JWT secret | Critical | Confirmed (`config.py` default `change-this-to-a-long-random-secret`) | **Fixed** (rotate any secret used in a past public deployment) | `core/config.validate_for_startup`, `core/security` (iss/aud/iat/typ claims) | `test_production_refuses_weak_secrets`, `test_tokens_without_expected_claims_are_rejected` |
| SK-04 Uploads served as public static files | High | Confirmed (`app.mount("/uploads", StaticFiles…)`) | **Fixed** | `main.py` (mount removed), `routers/files.py`, `services/uploads.signed_url`, schema serializers | `test_uploads_are_not_publicly_served_and_signed_urls_are_owner_scoped`, `test_signed_urls_expire`, `test_manual_analysis_cannot_reference_another_users_file` |
| SK-05 OpenCV missing | High | Confirmed (`services/progress.py` imports `cv2`; not in requirements) | **Fixed** | `requirements.txt` (`opencv-python-headless==4.14.0.94`) | progress integration test runs real OpenCV code |
| SK-06 Tesseract binary not installed | High | Confirmed (only `pytesseract`) | **Fixed in Docker image**; readiness reports OCR state | `backend/Dockerfile`, `/health/ready` | readiness test; container build **not run here** (no Docker in this environment) |
| SK-07 In-memory login lockout | Medium | Confirmed (`_failed_attempts` dict) | **Fixed** (database-backed rolling windows, no permanent lock-out) | `services/rate_limit.py`, `RateLimitEvent` table | `test_login_failures_are_throttled_in_the_shared_database`, `test_contact_submission_is_rate_limited` |
| SK-08 JWT in localStorage | Medium | Confirmed | **Partial** — kept for compatibility; mitigated with production CSP, 30-min tokens, token cleared on 401. Cookie migration is a planned breaking change. | `frontend/vite.config.js`, `frontend/src/services/api.js` | manual (built `dist/index.html` contains CSP) |
| SK-09 No migrations | Medium | Confirmed (`create_all` at start-up) | **Fixed** | `backend/alembic.ini`, `backend/migrations/` (baseline + 0002), `app/db/migrate.py` | Migrated a fresh DB and a legacy `create_all` DB with data (run twice, idempotent) |
| SK-10 Health ≠ readiness | Medium | Confirmed | **Fixed** | `/health` (liveness), `/health/ready` (DB, model, gate, OCR, storage) | `test_liveness_and_readiness` |
| SK-11 TensorFlow resources | Medium | Confirmed | **Partial** — one worker, optional warm-up, inference concurrency limit, artifact check. Memory/latency on the target host still **not measured**. | `Dockerfile`, `services/skin_analysis.py` | — |
| SK-12 Upload validation | High | Confirmed (MIME header + size only; no decode) | **Fixed** | `services/uploads.py` (decode, real format, dimensions, pixel cap, animation, random names, temp cleanup), body-size middleware | `test_spoofed_mime_type_is_rejected`, `test_corrupt_image_is_rejected`, `test_gif_and_svg_are_rejected`, `test_huge_dimensions_are_rejected`, `test_valid_image_gets_random_server_name_and_real_extension`, `test_security_headers_and_oversized_requests` |
| SK-13 Public endpoint abuse | Medium | Confirmed | **Fixed** (rate limits on contact, register, login, reset, analysis, scan, progress, chat, avatar) | `services/rate_limit.py`, routers | `test_contact_submission_is_rate_limited` |
| ML-01 Non-skin images get labels | Critical | Confirmed (sample `test_input_image.jpg` = solid blue, `test_skin.jpg` = solid black; both reached the model) | **Partial** — staged gate + abstention implemented; gate is an interim heuristic, not a trained/validated classifier | `services/image_gate.py`, `routers/analyses.py`, `services/skin_analysis.py` | `tests/test_input_gate.py`; sample evaluation in `docs/ML_INPUT_GATE.md` |
| SK-ML-01 Disease vs facial tracks | High | Design issue | **Fixed for scope**: Model B is not released; API rejects it with `track_not_available`; results record `analysis_track` + `model_version` | `routers/analyses.py`, `SkinAnalysis` columns | `test_disease_track_is_not_available_yet` |
| SK-PROD-01 Product/price data | Medium | Feature not built at audit time | **Addressed in the shop design**: admin-entered prices carry source + checked date, stale prices labelled, sponsored items labelled and not boosted, no products suggested after disease results, patch-test cautions | `routers/shop.py`, `services/shop.py` | `tests/test_shop.py` |

## Additional issues found during the re-audit

| ID | Severity | Finding | Status |
|---|---|---|---|
| SK-14 | High | `POST /profile/avatar` wrote the file with a **client-supplied extension** and no content validation, then served it publicly. | Fixed — uses `save_upload` (decoded, random name, private), old avatar deleted. |
| SK-15 | High | `POST /analyses` (manual result) accepted any `image_url`; with signed URLs this could have been used to obtain a link to another user's file. | Fixed — internal references must already belong to the caller. Test: `test_manual_analysis_cannot_reference_another_users_file`. |
| SK-16 | Medium | `POST /reports/generate` returned `str(exc)` to the client; `FileResponse` used the raw user-provided title as the download filename. | Fixed — generic message, exception logged; filename sanitised. |
| SK-17 | Medium | Login timing and messages could reveal whether an account exists. | Fixed — dummy bcrypt check for unknown e-mails; identical 401 body. Test: `test_unknown_email_and_wrong_password_look_the_same`. |
| SK-18 | Medium | Account deletion left the user's images and PDFs on disk. | Fixed — files removed after the DB delete. Test: `test_account_deletion_removes_private_files`. |
| SK-19 | Low | Validation errors echoed submitted values (could include passwords). | Fixed — custom handler returns only location/message. Test: `test_validation_errors_do_not_echo_passwords`. |
| SK-20 | Low | `POST /scans/scan` was `async` but ran blocking OCR, blocking the event loop. | Fixed — now a sync endpoint (runs in the threadpool). |
| SK-21 | Low | CORS allowed all methods/headers with credentials. | Fixed — explicit methods/headers, no credentials, `*` rejected in production. |
| SK-22 | Info | `requirements.txt` pinned `numpy==1.26.4`, which has no wheels for Python ≥ 3.13, while TensorFlow 2.20 runs on 3.13. | Fixed — versions pinned to the set that was installed and tested together. |

## Test evidence

```
cd backend
pip install -r requirements-dev.txt
ruff check .          # All checks passed!
pytest -q             # 68 passed
```

Run locally on Python 3.13.18 with the pinned requirements. An end-to-end run with the real EfficientNetB0 model was also done: a face photo returned facial-concern labels; a synthetic laptop image returned `422 not_skin_image` without calling the model.

Not executed in this environment: Docker image build, PostgreSQL migration, dependency vulnerability scan (`pip-audit`, `npm audit`) and secret scan (gitleaks). They are configured in `.github/workflows/ci.yml`.

## Still blocking a public launch

1. **ML-01:** replace the heuristic gate with a trained skin/non-skin model and evaluate it on a held-out, diverse hard-negative set (see `docs/ML_INPUT_GATE.md`). Agree numeric thresholds with the product owner.
2. Reproduce Model A metrics against the exact artifact and split (historical numbers are unverified).
3. Measure memory and latency on the target host; run the container smoke test and a PostgreSQL migration and restore test.
4. Configure SMTP (password reset is disabled in production until it is).
5. Decide on SK-08 (HttpOnly cookie sessions + CSRF) and add security headers at the frontend host.
6. Privacy notice, retention policy and provider disclosure for the optional LLM (SEC-DATA-005/008/009).
