"""Database setup and session management."""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import get_settings
from src.models import Base


def get_engine():
    """Create SQLAlchemy engine."""
    settings = get_settings()

    # Ensure database directory exists for SQLite
    if settings.database_url.startswith("sqlite:///"):
        db_path = Path(settings.database_url.replace("sqlite:///", ""))
        db_path.parent.mkdir(parents=True, exist_ok=True)

    return create_engine(
        settings.database_url,
        # SQLite-specific settings
        connect_args={"check_same_thread": False}
        if settings.database_url.startswith("sqlite")
        else {},
        echo=settings.log_level == "DEBUG",
    )


def init_db() -> None:
    """Initialize database and create all tables."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def get_session_factory():
    """Get a session factory."""
    engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Get a database session as a context manager."""
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
