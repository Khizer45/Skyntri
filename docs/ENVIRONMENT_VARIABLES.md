# Backend environment variables

Set these in the hosting platform's secret/config store, or in `backend/.env` for local development. Never commit `.env`. Names are case-insensitive.

| Variable | Default | Production | Purpose |
|---|---|---|---|
| `ENVIRONMENT` | `development` | **`production`** | Enables strict start-up validation, HSTS, hides `/docs`, disables dev reset links |
| `LOG_LEVEL` | `INFO` | `INFO` | JSON logs to stdout |
| `SECRET_KEY` | *(empty)* | **required**, ≥ 32 random chars | Signs JWTs and file URLs. Placeholders refused in production; dev uses an ephemeral key |
| `ALGORITHM` | `HS256` | `HS256` | JWT HMAC algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | 15–60 | Access-token lifetime |
| `JWT_ISSUER` / `JWT_AUDIENCE` | `skyntri-api` / `skyntri-web` | keep | Validated claims |
| `ADMIN_EMAILS` | *(empty)* | support staff | Comma-separated e-mails granted the admin role at register/login. Alternative: `python -m app.cli make-admin EMAIL` |
| `DATABASE_URL` | `sqlite:///./skyntri.db` (Docker: the `db` PostgreSQL service) | `postgresql+psycopg://user:pass@host:5432/skyntri` | SQLAlchemy URL. PostgreSQL 16 is the supported production database |
| `SITE_DOMAIN` / `API_DOMAIN` | — | **required** for `docker-compose.prod.yml` | Public names of the app and the API (no `https://`). They set `CORS_ORIGINS`, `FRONTEND_URL` and `VITE_API_URL`, and Caddy gets HTTPS certificates for them |
| `POSTGRES_PASSWORD` | `skyntri-local-password` | **required**, long random value | Docker Compose only: password of the bundled PostgreSQL service. Set it before the first `docker compose up`; changing it later needs the `skyntri-pg` volume to be reset |
| `AUTO_MIGRATE` | `true` | `false` (entrypoint runs migrations) | Run Alembic at app start-up |
| `CORS_ORIGINS` | localhost:5173 | `https://<frontend>` | Comma-separated; `*` refused in production |
| `FRONTEND_URL` | `http://localhost:5173` | `https://<frontend>` | Used in reset links |
| `UPLOAD_DIR` | `uploads` (under `app/`) | `/data/uploads` | Private file storage; absolute path recommended |
| `SIGNED_URL_TTL_SECONDS` | `900` | 300–900 | Lifetime of image links |
| `MAX_UPLOAD_BYTES` | `10485760` | keep | Per-file upload limit |
| `MAX_REQUEST_BYTES` | `26214400` | keep | Whole-request limit (413 above) |
| `MAX_IMAGE_PIXELS` / `MAX_IMAGE_SIDE` / `MIN_IMAGE_SIDE` | `40000000` / `8000` / `64` | keep | Decoded image limits |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_TLS` | empty / 587 / … | **required for password reset** | Reset e-mails (port 465 uses implicit TLS) |
| `PASSWORD_RESET_TOKEN_MINUTES` | `30` | 15–30 | Reset-link lifetime |
| `DEV_LOG_RESET_LINKS` | `true` | ignored | Dev only: log reset links when SMTP is missing |
| `RATE_LIMIT_ENABLED` | `true` | `true` | Database-backed limits |
| `LOGIN_MAX_FAILURES`, `LOGIN_WINDOW_MINUTES`, `LOGIN_IP_MAX_ATTEMPTS` | `5`, `15`, `50` | tune | Login throttling |
| `FORGOT_PASSWORD_PER_HOUR`, `RESET_PASSWORD_PER_HOUR`, `CONTACT_PER_HOUR` | `5`, `10`, `5` | tune | Per IP |
| `ANALYSIS_PER_HOUR`, `SCAN_PER_HOUR`, `PROGRESS_PER_HOUR`, `CHAT_PER_HOUR` | `30`, `40`, `20`, `60` | tune | Per user |
| `MAX_CONCURRENT_INFERENCE` | `2` | 1–2 | Parallel TensorFlow inferences per worker |
| `INFERENCE_QUEUE_TIMEOUT_SECONDS` | `20` | keep | Wait before returning 503 busy |
| `DATASET3_MODEL_PATH` | `models/facial_concerns_efficientnet.keras` | exported file | Model A artifact (notebook 01). If the file is missing, the facial track reports `model_not_installed` |
| `FACIAL_MODEL_VERSION` | `facial-concerns-effnetb0-v1` | — | Fallback only; the version in `facial_concerns_metadata.json` is used when present |
| `SKIN_GATE_MODEL_PATH` | `models/skin_gate.keras` | trained gate (notebook 03) | Optional; heuristic used if missing |
| `SKIN_GATE_ACCEPT_THRESHOLD` / `SKIN_GATE_REJECT_THRESHOLD` | `0.80` / `0.40` | from validation | Trained-gate decision band; overridden by `skin_gate_metadata.json` when present |
| `FACIAL_MODEL_METADATA_PATH` | `models/facial_concerns_metadata.json` | the exported JSON | Classes, output type, thresholds, abstain level, face crop, TTA, image size and version for Model A |
| `DISEASE_SCREENING_ENABLED` | `false` | `true` **only after clinical review** | Turns on Model B |
| `DISEASE_MODEL_PATH` / `DISEASE_MODEL_METADATA_PATH` | `models/skin_disease_efficientnet.keras` / `models/skin_disease_metadata.json` | exported files | Model B artifact and metadata |
| `SHOP_CURRENCY` | `PKR` | keep | Default currency shown in the shop |
| `PRICE_STALE_AFTER_DAYS` | `30` | keep | Older prices are labelled "may be outdated" |
| `ORDER_PER_HOUR` / `MAX_CART_QUANTITY` | `20` / `10` | tune | Order rate limit per user, max quantity per cart line |
| `MODEL_WARMUP` | `false` | `true` (Docker default) | Load the model at start-up |
| `LLM_ENABLED`, `LLM_PROVIDER`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `OPENAI_API_KEY`, `LLM_MAX_OUTPUT_TOKENS` | disabled | only after privacy review | Optional assistant provider; local fallback always works. A retired `GEMINI_MODEL` is replaced automatically; `LLM_MAX_OUTPUT_TOKENS` (1500) is the wanted answer size |

Frontend: `VITE_API_URL` (build time) — the API base URL; also used in the production CSP.

## Accounts, clinic, payments and automation

Setup steps for each provider: [INTEGRATIONS.md](INTEGRATIONS.md).

| Variable | Default | Production | Meaning |
|---|---|---|---|
| `GOOGLE_CLIENT_ID` | empty | optional | OAuth client ID for "Continue with Google". Empty hides the button |
| `LLM_IMAGE_ENABLED`, `GEMINI_IMAGE_MODEL`, `OPENAI_IMAGE_MODEL`, `CHAT_IMAGES_PER_DAY` | off, 10 per day | optional, billed per image | Illustrations in the assistant. Image models are never replaced automatically |
| `CLINIC_NAME`, `CLINIC_TIMEZONE` | `Skyntri Clinic`, `Asia/Karachi` | set | Name on prescriptions and payments; doctors' working hours are in this time zone |
| `APPOINTMENT_MIN_NOTICE_MINUTES`, `APPOINTMENT_MAX_DAYS_AHEAD`, `APPOINTMENT_BOOKINGS_PER_DAY` | 60, 60, 6 | as needed | Booking window and per-patient limit |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | empty | secret | Card payments. `sk_test_` keys take no real money |
| `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_MODE` | empty, `sandbox` | secret | PayPal. `PAYPAL_MODE=live` takes real money |
| `PAYPAL_CURRENCY`, `PAYPAL_EXCHANGE_RATE` | `USD`, `0` | set when the shop currency is not supported by PayPal | Shop amount ÷ rate is charged in `PAYPAL_CURRENCY`. `0` keeps PayPal off for other currencies |
| `AUTOMATION_ALLOWED_HOSTS` | empty (`n8n` in Compose) | only hosts you run | Private host names webhooks may call. Other private or local addresses are refused in production |
| `AGENTS_SCHEDULER_ENABLED`, `AGENT_DAILY_HOUR` | `false`, `8` | `true` unless n8n or cron starts the agents | Built-in agent schedule (clinic time zone) |
| `AGENT_POSTS_AUTO_PUBLISH` | `false` | as wanted | Default for the admin switch "Publish daily posts automatically" |
| `DISEASE_SCREENING_ENABLED` | `false` | — | Default only: the switch under **Admin → Settings** overrides it once it has been used |

