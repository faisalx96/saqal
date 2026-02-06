"""Session management for Saqal."""

from datetime import datetime
from typing import Optional

from sqlmodel import select

from .database import get_session
from .models import Session, Input, PromptVersion, RunResult


class SessionManager:
    """Manages session CRUD operations."""

    def create_session(
        self,
        name: str,
        task_description: str,
        output_description: Optional[str],
        model_provider: str,
        model_name: str,
        model_temperature: float = 0.7,
        batch_size: int = 10,
    ) -> Session:
        """Create a new session. Returns the created Session object."""
        session_obj = Session(
            name=name,
            task_description=task_description,
            output_description=output_description,
            model_provider=model_provider,
            model_name=model_name,
            model_temperature=model_temperature,
            batch_size=batch_size,
        )
        with get_session() as db:
            db.add(session_obj)
            db.commit()
            db.refresh(session_obj)
        return session_obj

    def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve a session by ID. Returns None if not found."""
        with get_session() as db:
            statement = select(Session).where(Session.id == session_id)
            result = db.exec(statement).first()
            if result:
                # Detach from session to avoid lazy loading issues
                db.expunge(result)
            return result

    def list_sessions(
        self,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> list[Session]:
        """List sessions, optionally filtered by status."""
        with get_session() as db:
            statement = select(Session).order_by(Session.updated_at.desc())
            if status:
                statement = statement.where(Session.status == status)
            statement = statement.limit(limit)
            results = db.exec(statement).all()
            # Detach all from session
            for r in results:
                db.expunge(r)
            return list(results)

    def update_session(
        self,
        session_id: str,
        **kwargs,
    ) -> Optional[Session]:
        """Update session fields. Returns updated Session or None if not found."""
        with get_session() as db:
            statement = select(Session).where(Session.id == session_id)
            session_obj = db.exec(statement).first()
            if not session_obj:
                return None

            for key, value in kwargs.items():
                if hasattr(session_obj, key):
                    setattr(session_obj, key, value)

            session_obj.updated_at = datetime.utcnow()
            db.add(session_obj)
            db.commit()
            db.refresh(session_obj)
            db.expunge(session_obj)
            return session_obj

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all related data. Returns success."""
        with get_session() as db:
            # First delete all related run results
            inputs = db.exec(
                select(Input).where(Input.session_id == session_id)
            ).all()
            input_ids = [inp.id for inp in inputs]

            if input_ids:
                run_results = db.exec(
                    select(RunResult).where(RunResult.input_id.in_(input_ids))
                ).all()
                for rr in run_results:
                    db.delete(rr)

            # Delete prompt versions
            versions = db.exec(
                select(PromptVersion).where(PromptVersion.session_id == session_id)
            ).all()
            for v in versions:
                db.delete(v)

            # Delete inputs
            for inp in inputs:
                db.delete(inp)

            # Delete session
            session_obj = db.exec(
                select(Session).where(Session.id == session_id)
            ).first()
            if not session_obj:
                return False

            db.delete(session_obj)
            db.commit()
            return True
