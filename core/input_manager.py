"""Input management for Saqal."""

from typing import Optional

from sqlmodel import select

from .database import get_session
from .models import Input


class InputManager:
    """Manages input CRUD operations."""

    def create_inputs(
        self,
        session_id: str,
        inputs: list[dict],
    ) -> list[Input]:
        """
        Bulk create inputs for a session.

        Args:
            session_id: The session to add inputs to
            inputs: List of dicts with 'content' and optionally 'ground_truth', 'input_metadata' (or 'metadata' for backward compatibility)

        Returns:
            List of created Input objects
        """
        input_objs = []
        for inp in inputs:
            input_obj = Input(
                session_id=session_id,
                content=inp.get("content", ""),
                ground_truth=inp.get("ground_truth"),
                input_metadata=inp.get("input_metadata") or inp.get("metadata"),  # Support both for backward compatibility
            )
            input_objs.append(input_obj)

        with get_session() as db:
            for obj in input_objs:
                db.add(obj)
            db.commit()
            for obj in input_objs:
                db.refresh(obj)
                db.expunge(obj)

        return input_objs

    def get_inputs(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[Input]:
        """Get inputs for a session with pagination."""
        with get_session() as db:
            statement = (
                select(Input)
                .where(Input.session_id == session_id)
                .order_by(Input.created_at)
                .offset(offset)
            )
            if limit:
                statement = statement.limit(limit)
            results = db.exec(statement).all()
            for r in results:
                db.expunge(r)
            return list(results)

    def get_input(self, input_id: str) -> Optional[Input]:
        """Get a single input by ID."""
        with get_session() as db:
            statement = select(Input).where(Input.id == input_id)
            result = db.exec(statement).first()
            if result:
                db.expunge(result)
            return result

    def get_batch(
        self,
        session_id: str,
        batch_size: int,
        exclude_ids: Optional[list[str]] = None,
    ) -> list[Input]:
        """Get a batch of inputs, excluding already-processed ones."""
        exclude_ids = exclude_ids or []
        with get_session() as db:
            statement = (
                select(Input)
                .where(Input.session_id == session_id)
                .order_by(Input.created_at)
            )
            if exclude_ids:
                statement = statement.where(Input.id.notin_(exclude_ids))
            statement = statement.limit(batch_size)
            results = db.exec(statement).all()
            for r in results:
                db.expunge(r)
            return list(results)

    def count_inputs(self, session_id: str) -> int:
        """Count total inputs for a session."""
        with get_session() as db:
            statement = select(Input).where(Input.session_id == session_id)
            results = db.exec(statement).all()
            return len(results)

    def delete_input(self, input_id: str) -> bool:
        """Delete an input by ID."""
        with get_session() as db:
            statement = select(Input).where(Input.id == input_id)
            input_obj = db.exec(statement).first()
            if not input_obj:
                return False
            db.delete(input_obj)
            db.commit()
            return True
