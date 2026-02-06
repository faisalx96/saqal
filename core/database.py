"""Database connection and initialization for Saqal."""

import os
from pathlib import Path

from sqlmodel import SQLModel, create_engine, Session as SQLSession

# Default database path
DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "workbench.db"

_engine = None


def get_database_path() -> Path:
    """Get the database path from environment or use default."""
    db_path = os.getenv("DATABASE_PATH")
    if db_path:
        return Path(db_path)
    return DEFAULT_DB_PATH


def get_engine():
    """Get or create the SQLAlchemy engine singleton."""
    global _engine
    if _engine is None:
        db_path = get_database_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
    return _engine


def init_db():
    """Initialize the database, creating all tables."""
    from .models import Session, Input, PromptVersion, RunResult  # noqa: F401

    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    _run_migrations()


def _run_migrations():
    """Run any pending schema migrations for new nullable columns."""
    import sqlite3

    db_path = get_database_path()
    if not db_path.exists():
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # Add mlflow_trace_id to runresult
        cursor.execute("PRAGMA table_info(runresult)")
        columns = [row[1] for row in cursor.fetchall()]
        if columns and "mlflow_trace_id" not in columns:
            cursor.execute("ALTER TABLE runresult ADD COLUMN mlflow_trace_id TEXT")

        # Add mlflow_experiment_id to session
        cursor.execute("PRAGMA table_info(session)")
        columns = [row[1] for row in cursor.fetchall()]
        if columns and "mlflow_experiment_id" not in columns:
            cursor.execute(
                "ALTER TABLE session ADD COLUMN mlflow_experiment_id TEXT"
            )

        conn.commit()
    finally:
        conn.close()


def get_session() -> SQLSession:
    """Get a new database session."""
    engine = get_engine()
    return SQLSession(engine)
