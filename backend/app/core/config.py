from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application configuration.

    Values can be supplied through environment variables or .env.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ========================================================================
    # Application / Security
    # ========================================================================

    secret_key: str = "change-this-to-a-long-random-secret"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # ========================================================================
    # Database
    # ========================================================================

    database_url: str = "sqlite:///./skyntri.db"

    # ========================================================================
    # CORS
    # ========================================================================

    cors_origins: str = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173"
    )

    # ========================================================================
    # Uploads
    # ========================================================================

    upload_dir: str = "uploads"

    # ========================================================================
    # ML Model
    # ========================================================================

    # Final FYP model:
    # Dataset 3 — 10-class multi-label skin condition classification
    # EfficientNetB0 + Weighted Focal Loss + Fine-Tuning
    dataset3_model_path: str = (
        "models/EfficientNetB0_weighted_focal_finetuned_best.keras"
    )

    # ========================================================================
    # LLM Configuration
    # ========================================================================

    # External LLM can be enabled through .env.
    # If the external API is disabled, unavailable, or fails,
    # Skyntri automatically uses the local rule-based fallback.
    llm_enabled: bool = False

    # Current provider used by the FYP.
    # Supported external provider:
    #   gemini
    #
    # Regardless of provider/API availability, local fallback remains active.
    llm_provider: str = "gemini"

    # OpenAI configuration is retained for future provider support.
    openai_api_key: str = ""
    openai_model: str = "gpt-5.6-luna"

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # Maximum response length allowed from the external LLM.
    llm_max_output_tokens: int = 1200

    # ========================================================================
    # Properties
    # ========================================================================

    @property
    def cors_origin_list(self) -> list[str]:
        """
        Convert comma-separated CORS origins into a clean list.
        """
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def project_root(self) -> Path:
        """
        Return the root directory of the Skyntri backend project.
        """
        return Path(__file__).resolve().parent.parent.parent

    @property
    def upload_path(self) -> Path:
        """
        Return the upload directory and create it if necessary.
        """
        path = Path(__file__).resolve().parent.parent / self.upload_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def models_path(self) -> Path:
        """
        Return the ML models directory and create it if necessary.
        """
        path = self.project_root / "models"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def dataset3_model(self) -> Path:
        """
        Return the final Dataset 3 EfficientNetB0 model path.
        """
        return self.project_root / self.dataset3_model_path


settings = Settings()