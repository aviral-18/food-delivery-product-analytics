"""
Database engine, session factory, and declarative base.

We use a synchronous SQLAlchemy 2.0 engine against PostgreSQL (psycopg 3).
`pool_pre_ping` guards against stale connections; the connection pool is sized
from settings so the analytics endpoints can serve concurrent dashboard loads.
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _make_engine():
    """Create the engine. PostgreSQL is the production target; SQLite is
    supported for zero-dependency local dev/tests (it ignores QueuePool sizing)."""
    kwargs: dict = {"echo": settings.SQL_ECHO, "pool_pre_ping": True, "future": True}
    if settings.DATABASE_URL.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_size"] = settings.DB_POOL_SIZE
        kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
    return create_engine(settings.DATABASE_URL, **kwargs)


engine = _make_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
