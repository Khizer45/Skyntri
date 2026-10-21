from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.db.database import Base, SessionLocal, engine
from app.routers import (
    analyses,
    auth,
    chat,
    contact,
    history,
    ingredients,
    profile,
    progress,
    reports,
    scans,
)
from app.services.ingredient_seed import seed_ingredients


def initialize_database() -> None:
    """
    Create database tables for the local/dev deployment and seed the
    ingredient database.

    The seed operation is idempotent, so existing ingredient records are
    preserved and only missing records are inserted.
    """
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        seed_ingredients(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Skyntri API",
    description=(
        "AI-Based Skin Health Assistant API providing skin analysis, "
        "ingredient scanning, recommendations, progress tracking, "
        "reports, chat, profile and authentication services."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount(
    "/uploads",
    StaticFiles(directory=str(settings.upload_path)),
    name="uploads",
)


# ---------------------------------------------------------------------------
# API routers
# ---------------------------------------------------------------------------

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


@app.get("/health", tags=["health"])
def health_check():
    return {
        "status": "ok",
        "service": "Skyntri API",
    }