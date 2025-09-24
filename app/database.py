from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from flask import Flask
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import scoped_session, sessionmaker

_engine: Engine | None = None
_SessionFactory: scoped_session | None = None


def init_engine(app: Flask) -> None:
    """Initialise the SQLAlchemy engine and scoped session."""
    global _engine, _SessionFactory

    if _engine is not None:
        return

    database_url = app.config["DATABASE_URL"]
    _engine = create_engine(database_url, future=True, pool_pre_ping=True)
    _SessionFactory = scoped_session(
        sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)
    )

    @app.teardown_appcontext
    def _remove_session(exception: Exception | None) -> None:  # pragma: no cover - Flask hook
        if _SessionFactory is not None:
            _SessionFactory.remove()


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("Database engine has not been initialized")
    return _engine


@contextmanager
def session_scope(session_identifier: str | None = None) -> Iterator:
    """Provide a transactional scope around a series of operations."""
    if _SessionFactory is None:
        raise RuntimeError("Database session factory not configured")

    session = _SessionFactory()
    try:
        if session_identifier:
            session.execute(text("SELECT set_config('app.current_session_id', :session_id, true)"), {"session_id": session_identifier})
        else:
            session.execute(text("SELECT set_config('app.current_session_id', NULL, true)"))
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
