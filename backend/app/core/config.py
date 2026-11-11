from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Known development placeholders that must never be used to sign tokens in
# production (SK-03 / SEC-AUTH-008).
INSECURE_SECRET_PLACEHOLDERS = {
    "",
    "change-this-to-a-long-random-secret",
    "changeme",
    "change-me",
    "secret",
    "dev",
    "development",
    "replace-me",
}

MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    """
    Central application configuration.

    Values are supplied through environment variables or a local .env file.
    See docs/ENVIRONMENT_VARIABLES.md for the full reference.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    # ========================================================================
    # Environment
    # ========================================================================

    # "development" or "production". Production enables strict validation
    # (strong secret, restrictive CORS, no development reset links, HSTS).
    environment: str = "development"

    log_level: str = "INFO"

    # ========================================================================
    # Application / Security
    # ========================================================================

    # No usable default: development generates an ephemeral secret at
    # start-up, production refuses to start (see validate_for_startup).
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    jwt_issuer: str = "skyntri-api"
    jwt_audience: str = "skyntri-web"

    # Comma-separated e-mail addresses that are granted the server-side
    # "admin" role when they register or log in. Admin rights are never
    # taken from the client.
    admin_emails: str = ""

    # ========================================================================
    # Database
    # ========================================================================

    database_url: str = "sqlite:///./skyntri.db"

    # Run Alembic migrations automatically at start-up. Recommended for local
    # development; in production run `alembic upgrade head` as a release step.
    auto_migrate: bool = True

    # ========================================================================
    # CORS
    # ========================================================================

    cors_origins: str = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173"
    )

    # ========================================================================
    # Private file storage
    # ========================================================================

    # Relative paths are resolved against the backend app/ folder for
    # backward compatibility. In production point this to a private
    # persistent volume (absolute path) that is NOT publicly served.
    upload_dir: str = "uploads"

    # Lifetime of signed URLs used by the browser to display a user's own
    # private images.
    signed_url_ttl_seconds: int = 900

    max_upload_bytes: int = 10 * 1024 * 1024
    max_request_bytes: int = 25 * 1024 * 1024
    max_image_pixels: int = 40_000_000
    max_image_side: int = 8000
    min_image_side: int = 64

    # ========================================================================
    # Password reset / e-mail
    # ========================================================================

    frontend_url: str = "http://localhost:5173"
    password_reset_token_minutes: int = 30

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True

    # Development only: write reset links to the server log when SMTP is not
    # configured. Always ignored in production.
    dev_log_reset_links: bool = True

    # ========================================================================
    # Rate limiting (database-backed, shared across workers)
    # ========================================================================

    rate_limit_enabled: bool = True
    login_max_failures: int = 5
    login_window_minutes: int = 15
    login_ip_max_attempts: int = 50
    forgot_password_per_hour: int = 5
    reset_password_per_hour: int = 10
    contact_per_hour: int = 5
    analysis_per_hour: int = 30
    scan_per_hour: int = 40
    progress_per_hour: int = 20
    chat_per_hour: int = 60

    # Number of TensorFlow inferences allowed at the same time per process.
    max_concurrent_inference: int = 2
    inference_queue_timeout_seconds: float = 20.0

    # ========================================================================
    # ML Model
    # ========================================================================

    # Model A — facial skin concerns (EfficientNetB0, 10-label multi-label).
    # Default file name exported by ml/notebooks/01_facial_skin_concerns_efficientnet.ipynb
    dataset3_model_path: str = "models/facial_concerns_efficientnet.keras"
    facial_model_version: str = "facial-concerns-effnetb0-v1"
    # Exported by ml/notebooks/01_facial_skin_concerns_efficientnet.ipynb.
    # Optional: classes, thresholds, image size and version for Model A.
    facial_model_metadata_path: str = "models/facial_concerns_metadata.json"

    # Model B - skin disease screening support (face and body).
    # Exported by ml/notebooks/02_skin_disease_screening_efficientnet.ipynb.
    # The track stays unavailable unless BOTH files exist AND
    # DISEASE_SCREENING_ENABLED=true (set only after clinical review).
    disease_screening_enabled: bool = False
    disease_model_path: str = "models/skin_disease_efficientnet.keras"
    disease_model_metadata_path: str = "models/skin_disease_metadata.json"

    # Optional trained skin / non-skin gate (binary Keras model whose single
    # sigmoid output is P(skin)). When absent the interim heuristic gate is
    # used. See docs/ML_INPUT_GATE.md.
    skin_gate_model_path: str = "models/skin_gate.keras"
    skin_gate_accept_threshold: float = 0.80
    skin_gate_reject_threshold: float = 0.40

    # Load the facial model during start-up so the first request is not slow
    # and readiness reflects the real state.
    model_warmup: bool = False

    # ========================================================================
    # Shop / orders
    # ========================================================================

    shop_currency: str = "PKR"
    # Prices older than this are labelled "may be outdated" (SEC-PROD-001).
    price_stale_after_days: int = 30
    order_per_hour: int = 20
    max_cart_quantity: int = 10

    # ========================================================================
    # LLM Configuration
    # ========================================================================

    llm_enabled: bool = False
    llm_provider: str = "gemini"
    openai_api_key: str = ""
    openai_model: str = "gpt-5.6-luna"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    llm_max_output_tokens: int = 1200

    # Illustrations in the assistant ("draw a morning routine"). Off by
    # default: image models are billed per image by the provider.
    llm_image_enabled: bool = False
    gemini_image_model: str = "gemini-2.5-flash-image"
    openai_image_model: str = "gpt-image-1"
    chat_images_per_day: int = 10

    # ========================================================================
    # Sign in with Google
    # ========================================================================

    # OAuth 2.0 "Web application" client ID from Google Cloud Console.
    # Empty = the Google button is hidden and /auth/google returns 503.
    google_client_id: str = ""

    # ========================================================================
    # Clinic (doctors and appointments)
    # ========================================================================

    clinic_name: str = "Skyntri Clinic"
    # Working hours of doctors are entered in this time zone.
    clinic_timezone: str = "Asia/Karachi"
    appointment_min_notice_minutes: int = 60
    appointment_max_days_ahead: int = 60
    appointment_bookings_per_day: int = 6
    consultation_messages_per_hour: int = 120

    # ========================================================================
    # Online payments (card through Stripe, PayPal)
    # ========================================================================

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    paypal_client_id: str = ""
    paypal_client_secret: str = ""
    paypal_mode: str = "sandbox"  # "sandbox" or "live"
    # PayPal cannot charge every currency (PKR is not supported). When the
    # shop currency differs, set how many units of the shop currency equal
    # one unit of PAYPAL_CURRENCY, e.g. 280 for PKR per USD.
    paypal_currency: str = "USD"
    paypal_exchange_rate: float = 0.0

    payment_checkouts_per_hour: int = 20

    # ========================================================================
    # Automation (n8n, Zapier, custom agents)
    # ========================================================================

    # Host names that webhooks may call even though they are private
    # addresses, e.g. "n8n" for the n8n container. In development every
    # host is allowed.
    automation_allowed_hosts: str = ""
    webhook_timeout_seconds: float = 8.0
    automation_requests_per_hour: int = 600

    # Run the built-in agents from inside the API process. Leave off when an
    # external scheduler (n8n, cron) calls /automation/v1/agents/<name>/run.
    agents_scheduler_enabled: bool = False
    # Hour of the day (clinic time zone) for the daily report and daily post.
    agent_daily_hour: int = 8
    # False = daily posts are saved as drafts for an administrator to publish.
    agent_posts_auto_publish: bool = False

    # ========================================================================
    # Properties
    # ========================================================================

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() in {"production", "prod"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def admin_email_list(self) -> set[str]:
        return {
            email.strip().lower()
            for email in self.admin_emails.split(",")
            if email.strip()
        }

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_from)

    @property
    def stripe_configured(self) -> bool:
        return bool(self.stripe_secret_key)

    @property
    def paypal_configured(self) -> bool:
        return bool(self.paypal_client_id and self.paypal_client_secret)

    @property
    def automation_allowed_host_list(self) -> set[str]:
        return {h.strip().lower() for h in self.automation_allowed_hosts.split(",") if h.strip()}

    @property
    def project_root(self) -> Path:
        """Root directory of the backend project."""
        return Path(__file__).resolve().parent.parent.parent

    @property
    def upload_path(self) -> Path:
        """Private upload directory (created if necessary)."""
        configured = Path(self.upload_dir)

        if configured.is_absolute():
            path = configured
        else:
            path = Path(__file__).resolve().parent.parent / configured

        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def models_path(self) -> Path:
        path = self.project_root / "models"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def dataset3_model(self) -> Path:
        return self.project_root / self.dataset3_model_path

    @property
    def facial_model_metadata(self) -> Path:
        return self.project_root / self.facial_model_metadata_path

    @property
    def disease_model(self) -> Path:
        return self.project_root / self.disease_model_path

    @property
    def disease_model_metadata(self) -> Path:
        return self.project_root / self.disease_model_metadata_path

    @property
    def skin_gate_model(self) -> Path:
        return self.project_root / self.skin_gate_model_path


settings = Settings()


class ConfigurationError(RuntimeError):
    """Raised when the configuration is unsafe for the current environment."""


def secret_problems(secret: str) -> list[str]:
    problems: list[str] = []

    if secret.strip().lower() in INSECURE_SECRET_PLACEHOLDERS:
        problems.append("SECRET_KEY is missing or a known placeholder")
    elif len(secret) < MIN_SECRET_LENGTH:
        problems.append(
            f"SECRET_KEY must be at least {MIN_SECRET_LENGTH} characters"
        )
    elif len(set(secret)) < 10:
        problems.append("SECRET_KEY has too little variety to be random")

    return problems


def validate_for_startup(config: Settings) -> list[str]:
    """
    Validate configuration before the API starts.

    Production: raise ConfigurationError for unsafe settings.
    Development: fill in an ephemeral secret and return warnings.
    """
    warnings: list[str] = []
    problems: list[str] = []

    secret_issues = secret_problems(config.secret_key)

    if config.is_production:
        problems.extend(secret_issues)

        if config.algorithm not in {"HS256", "HS384", "HS512"}:
            problems.append("ALGORITHM must be an HMAC algorithm (HS256/384/512)")

        if any(origin == "*" for origin in config.cors_origin_list):
            problems.append("CORS_ORIGINS must not contain '*' in production")

        if not config.cors_origin_list:
            problems.append("CORS_ORIGINS must list the frontend origin(s)")

        if any(
            origin.startswith("http://")
            and "localhost" not in origin
            and "127.0.0.1" not in origin
            for origin in config.cors_origin_list
        ):
            warnings.append("CORS_ORIGINS contains a non-HTTPS origin")

        if config.database_url.startswith("sqlite"):
            warnings.append(
                "SQLite is not recommended in production; use PostgreSQL"
            )

        if config.stripe_configured and not config.stripe_webhook_secret:
            warnings.append(
                "STRIPE_WEBHOOK_SECRET is not set: card payments are only confirmed "
                "when the customer returns to the site"
            )

        if config.stripe_secret_key.startswith("sk_test_"):
            warnings.append("STRIPE_SECRET_KEY is a test key: no real card is charged")

        if config.paypal_configured and config.paypal_mode.strip().lower() != "live":
            warnings.append("PAYPAL_MODE is sandbox: no real payment is taken")

        if problems:
            raise ConfigurationError(
                "Unsafe production configuration: " + "; ".join(problems)
            )
    elif secret_issues:
        import secrets as _secrets

        config.secret_key = _secrets.token_urlsafe(48)
        warnings.append(
            "SECRET_KEY is missing/weak; using an ephemeral development "
            "secret (tokens will be invalid after restart). Set SECRET_KEY "
            "in backend/.env."
        )

    return warnings
