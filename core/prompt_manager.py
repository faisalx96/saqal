"""Prompt version management for Saqal."""

import difflib
from typing import Optional

from sqlmodel import select

from .database import get_session
from .models import PromptVersion


class PromptManager:
    """Manages prompt version CRUD operations."""

    def create_version(
        self,
        session_id: str,
        prompt_text: str,
        parent_version_id: Optional[str] = None,
        mutation_explanation: Optional[str] = None,
        status: str = "proposed",
    ) -> PromptVersion:
        """Create a new prompt version. Auto-increments version_number."""
        # Get the next version number
        with get_session() as db:
            statement = (
                select(PromptVersion)
                .where(PromptVersion.session_id == session_id)
                .order_by(PromptVersion.version_number.desc())
            )
            latest = db.exec(statement).first()
            next_version = 1 if not latest else latest.version_number + 1

            version = PromptVersion(
                session_id=session_id,
                version_number=next_version,
                prompt_text=prompt_text,
                parent_version_id=parent_version_id,
                mutation_explanation=mutation_explanation,
                status=status,
            )
            db.add(version)
            db.commit()
            db.refresh(version)
            db.expunge(version)
            return version

    def get_version(self, version_id: str) -> Optional[PromptVersion]:
        """Get a prompt version by ID."""
        with get_session() as db:
            statement = select(PromptVersion).where(PromptVersion.id == version_id)
            result = db.exec(statement).first()
            if result:
                db.expunge(result)
            return result

    def get_current_version(self, session_id: str) -> Optional[PromptVersion]:
        """Get the latest accepted version for a session."""
        with get_session() as db:
            statement = (
                select(PromptVersion)
                .where(PromptVersion.session_id == session_id)
                .where(PromptVersion.status == "accepted")
                .order_by(PromptVersion.version_number.desc())
            )
            result = db.exec(statement).first()
            if result:
                db.expunge(result)
            return result

    def get_latest_version(self, session_id: str) -> Optional[PromptVersion]:
        """Get the latest version (any status) for a session."""
        with get_session() as db:
            statement = (
                select(PromptVersion)
                .where(PromptVersion.session_id == session_id)
                .order_by(PromptVersion.version_number.desc())
            )
            result = db.exec(statement).first()
            if result:
                db.expunge(result)
            return result

    def get_version_history(
        self,
        session_id: str,
    ) -> list[PromptVersion]:
        """Get all versions for a session, ordered by version_number."""
        with get_session() as db:
            statement = (
                select(PromptVersion)
                .where(PromptVersion.session_id == session_id)
                .order_by(PromptVersion.version_number)
            )
            results = db.exec(statement).all()
            for r in results:
                db.expunge(r)
            return list(results)

    def update_version_status(
        self,
        version_id: str,
        status: str,
    ) -> Optional[PromptVersion]:
        """Update the status of a version."""
        with get_session() as db:
            statement = select(PromptVersion).where(PromptVersion.id == version_id)
            version = db.exec(statement).first()
            if not version:
                return None

            version.status = status
            db.add(version)
            db.commit()
            db.refresh(version)
            db.expunge(version)
            return version

    def get_diff(
        self,
        old_version_id: str,
        new_version_id: str,
    ) -> list[dict]:
        """Generate structured diff between two versions."""
        old_version = self.get_version(old_version_id)
        new_version = self.get_version(new_version_id)

        if not old_version or not new_version:
            return []

        return generate_diff(old_version.prompt_text, new_version.prompt_text)


def generate_diff(old_prompt: str, new_prompt: str) -> list[dict]:
    """Generate a structured diff for UI display."""
    differ = difflib.unified_diff(
        old_prompt.splitlines(keepends=True),
        new_prompt.splitlines(keepends=True),
        lineterm="",
    )

    result = []
    for line in differ:
        if line.startswith("+++") or line.startswith("---"):
            continue  # Skip file headers
        if line.startswith("@@"):
            continue  # Skip hunk headers
        if line.startswith("+"):
            result.append({"type": "added", "text": line[1:].rstrip("\n")})
        elif line.startswith("-"):
            result.append({"type": "removed", "text": line[1:].rstrip("\n")})
        elif line.startswith(" "):
            result.append({"type": "unchanged", "text": line[1:].rstrip("\n")})
        elif line.strip():
            # Handle lines that don't have diff markers (context)
            result.append({"type": "unchanged", "text": line.rstrip("\n")})

    return result
