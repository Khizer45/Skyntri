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
| `ADMIN_EMAILS` | *(empty)* | support staff | Comma-separated e-mails granted the admin role at register/login |
| `DATABASE_URL` | `sqlite:///./skyntri.db` | `postgresql+psycopg://…` | SQLAlchemy URL |
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
| `DATASET3_MODEL_PATH` | `models/EfficientNetB0_…keras` | keep | Model A artifact |
| `FACIAL_MODEL_VERSION` | `facial-concerns-effnetb0-v1` | update with the artifact | Stored with each analysis |
| `SKIN_GATE_MODEL_PATH` | `models/skin_gate.keras` | trained gate | Optional; heuristic used if missing |
| `SKIN_GATE_ACCEPT_THRESHOLD` / `SKIN_GATE_REJECT_THRESHOLD` | `0.80` / `0.40` | from validation | Trained-gate decision band |
| `MODEL_WARMUP` | `false` | `true` (Docker default) | Load the model at start-up |
| `LLM_ENABLED`, `LLM_PROVIDER`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `OPENAI_API_KEY`, `LLM_MAX_OUTPUT_TOKENS` | disabled | only after privacy review | Optional assistant provider; local fallback always works |

Frontend: `VITE_API_URL` (build time) — the API base URL; also used in the production CSP.
