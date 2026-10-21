from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


# SQLite requires this option when the database is accessed
# through FastAPI's request-handling threads.
connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)


engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
)


SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass


def get_db() -> Generator[Session, None, None]:
    """
    Provide a database session for a FastAPI request.

    The session is always closed after the request completes,
    including when an exception occurs.
    """
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()