from __future__ import annotations

import logging
import shutil
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings, validate_for_startup
from app.core.logging_config import configure_logging
from app.db.database import SessionLocal, engine
from app.routers import (
    admin,
    analyses,
    auth,
    chat,
    contact,
    files,
    history,
    ingredients,
    profile,
    progress,
    reports,
    scans,
    shop,
)
from app.services.ingredient_seed import seed_ingredients

configure_logging(settings.log_level)
logger = logging.getLogger("skyntri")

# Fail fast on unsafe production configuration (SK-03 / SEC-AUTH-008).
for _warning in validate_for_startup(settings):
    logger.warning(_warning)

logger.info(
    "admin_bootstrap",
    extra={
        "event": "admin_bootstrap",
        "admin_emails_configured": len(settings.admin_email_list),
        "hint": "Users whose e-mail is in ADMIN_EMAILS become admin when they sign up or log in.",
    },
)


# ---------------------------------------------------------------------------
# Database initialisation
# ---------------------------------------------------------------------------

def run_migrations() -> None:
    """Apply Alembic migrations (SK-09). Safe for fresh and legacy databases."""
    from app.db.migrate import upgrade_to_head

    upgrade_to_head()


def initialize_database() -> None:
    if settings.auto_migrate:
        run_migrations()

    db = SessionLocal()
    try:
        seed_ingredients(db)
    finally:
        db.close()


def warm_up_model() -> None:
    if not settings.model_warmup:
        return
    try:
        from app.services.skin_analysis import load_dataset3_model

        load_dataset3_model()
        logger.info("model_loaded", extra={"event": "model_loaded", "model_version": settings.facial_model_version})
    except Exception:
        logger.exception("model_load_failed", extra={"event": "model_load_failed"})


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    warm_up_model()
    yield


app = FastAPI(
    title="Skyntri API",
    description=(
        "AI-Based Skin Health Assistant API providing skin analysis, "
        "ingredient scanning, recommendations, progress tracking, "
        "reports, chat, profile and authentication services."
    ),
    version="1.1.0",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """Reject oversized bodies before they are buffered (SEC-UP-001)."""
    length = request.headers.get("content-length")
    if length is not None:
        try:
            too_big = int(length) > settings.max_request_bytes
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length header."})
        if too_big:
            return JSONResponse(status_code=413, content={"detail": "The request is too large."})
    return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Secure response headers (SEC-APP-002)."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "cross-origin")

    if not request.url.path.startswith(("/docs", "/redoc", "/openapi.json")):
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'none'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'",
        )

    if settings.is_production:
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )

    return response


# Added last so it runs first and also decorates error responses.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in settings.cors_origin_list if o != "*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Content-Disposition", "Retry-After"],
    max_age=600,
)


# ---------------------------------------------------------------------------
# Error handling (SEC-APP-004)
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "unhandled_error",
        extra={"event": "unhandled_error", "path": request.url.path, "method": request.method},
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Return field locations/messages only; never echo submitted values
    # (they may contain passwords).
    errors = [
        {"loc": list(err.get("loc", [])), "msg": err.get("msg", "Invalid value."), "type": err.get("type")}
        for err in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


# ---------------------------------------------------------------------------
# API routers
# ---------------------------------------------------------------------------
# NOTE: /uploads is intentionally NOT mounted as static files any more
# (SK-04). Private images are served through signed /files/... URLs.

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(contact.router)

app.include_router(analyses.router)
app.include_router(scans.router)
app.include_router(ingredients.router)

app.include_router(progress.router)
app.include_router(reports.router)
app.include_router(history.router)

app.include_router(chat.router)
app.include_router(files.router)
app.include_router(shop.router)
app.include_router(admin.router)


# ---------------------------------------------------------------------------
# Health (SK-10 / SEC-APP-008)
# ---------------------------------------------------------------------------

@app.get("/health", tags=["health"])
def health_check():
    """Liveness: the process is up. Deliberately does no dependency checks."""
    return {"status": "ok", "service": "Skyntri API"}


@app.get("/health/live", tags=["health"])
def liveness():
    return {"status": "ok"}


def _facial_version() -> str:
    try:
        from app.services.skin_analysis import facial_model_config

        return facial_model_config()["model_version"]
    except Exception:
        return settings.facial_model_version


@app.get("/health/ready", tags=["health"])
def readiness():
    """
    Readiness: database, model artifact/load state, OCR binary, storage.
    Returns 503 when a required dependency is unavailable. No secrets,
    paths or stack traces are included.
    """
    from app.services.image_gate import current_gate_version, face_detector_available
    from app.services.skin_analysis import model_artifact_available, model_loaded

    checks: dict[str, dict] = {}

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["database"] = {"ok": True}
    except Exception:
        checks["database"] = {"ok": False}

    artifact = model_artifact_available()
    checks["facial_model"] = {
        "ok": artifact and (model_loaded() or not settings.model_warmup),
        "artifact_present": artifact,
        "loaded": model_loaded(),
        "version": _facial_version(),
    }

    from app.services import disease_screening

    if settings.disease_screening_enabled:
        files_ok = disease_screening.model_files_present()
        checks["disease_model"] = {
            "ok": files_ok,
            "enabled": True,
            "artifact_present": files_ok,
            "loaded": disease_screening.model_loaded(),
        }
    else:
        checks["disease_model"] = {"ok": True, "enabled": False}

    checks["input_gate"] = {
        "ok": True,
        "version": current_gate_version(),
        "face_detector": face_detector_available(),
    }

    tesseract_ok = shutil.which("tesseract") is not None
    if not tesseract_ok:
        try:
            import pytesseract

            pytesseract.get_tesseract_version()
            tesseract_ok = True
        except Exception:
            tesseract_ok = False
    checks["ocr"] = {"ok": tesseract_ok}

    try:
        probe = settings.upload_path / ".readiness-probe"
        probe.write_bytes(b"ok")
        probe.unlink(missing_ok=True)
        checks["storage"] = {"ok": True}
    except Exception:
        checks["storage"] = {"ok": False}

    ready = all(item["ok"] for item in checks.values())

    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ready" if ready else "not_ready", "checks": checks},
    )
