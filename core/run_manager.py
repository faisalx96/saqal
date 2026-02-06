"""Run management for Saqal."""

from typing import Callable, Optional

from sqlmodel import select

from .database import get_session
from .models import RunResult, Input, PromptVersion
from llm.client import LLMClient


class RunManager:
    """Manages prompt execution and result storage."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def run_batch(
        self,
        prompt_version_id: str,
        input_ids: list[str],
        on_progress: Optional[Callable[[int, int], None]] = None,
    ) -> list[RunResult]:
        """
        Run a prompt version on a batch of inputs.

        Calls on_progress(completed, total) after each completion.
        """
        # Get prompt version
        with get_session() as db:
            statement = select(PromptVersion).where(PromptVersion.id == prompt_version_id)
            version = db.exec(statement).first()
            if not version:
                raise ValueError(f"Prompt version {prompt_version_id} not found")
            prompt_text = version.prompt_text

        results = []
        total = len(input_ids)

        for idx, input_id in enumerate(input_ids):
            # Get input
            with get_session() as db:
                statement = select(Input).where(Input.id == input_id)
                input_obj = db.exec(statement).first()
                if not input_obj:
                    continue
                input_content = input_obj.content

            # Format prompt with input
            formatted_prompt = prompt_text.replace("{input}", input_content)

            # Execute LLM call
            try:
                response = self.llm_client.complete(formatted_prompt)
                output = response.text
                latency_ms = response.latency_ms
                tokens_used = response.tokens_used
            except Exception as e:
                output = f"Error: {str(e)}"
                latency_ms = 0
                tokens_used = 0

            # Create and store result
            result = RunResult(
                input_id=input_id,
                prompt_version_id=prompt_version_id,
                output=output,
                latency_ms=latency_ms,
                tokens_used=tokens_used,
            )

            with get_session() as db:
                db.add(result)
                db.commit()
                db.refresh(result)
                db.expunge(result)

            results.append(result)

            # Report progress
            if on_progress:
                on_progress(idx + 1, total)

        return results

    def run_single(
        self,
        prompt_version_id: str,
        input_id: str,
    ) -> RunResult:
        """Run a prompt on a single input."""
        results = self.run_batch(prompt_version_id, [input_id])
        if not results:
            raise ValueError(f"Failed to run prompt on input {input_id}")
        return results[0]

    def get_results_for_version(
        self,
        prompt_version_id: str,
    ) -> list[RunResult]:
        """Get all results for a specific prompt version."""
        with get_session() as db:
            statement = (
                select(RunResult)
                .where(RunResult.prompt_version_id == prompt_version_id)
                .order_by(RunResult.created_at)
            )
            results = db.exec(statement).all()
            for r in results:
                db.expunge(r)
            return list(results)

    def get_results_for_input(
        self,
        input_id: str,
    ) -> list[RunResult]:
        """Get all results for a specific input across all versions."""
        with get_session() as db:
            statement = (
                select(RunResult)
                .where(RunResult.input_id == input_id)
                .order_by(RunResult.created_at)
            )
            results = db.exec(statement).all()
            for r in results:
                db.expunge(r)
            return list(results)

    def get_result(self, result_id: str) -> Optional[RunResult]:
        """Get a single result by ID."""
        with get_session() as db:
            statement = select(RunResult).where(RunResult.id == result_id)
            result = db.exec(statement).first()
            if result:
                db.expunge(result)
            return result

    def update_feedback(
        self,
        result_id: str,
        human_feedback: str,
        feedback_reason: Optional[str] = None,
        human_correction: Optional[str] = None,
    ) -> Optional[RunResult]:
        """Update human feedback on a result."""
        with get_session() as db:
            statement = select(RunResult).where(RunResult.id == result_id)
            result = db.exec(statement).first()
            if not result:
                return None

            result.human_feedback = human_feedback
            result.feedback_reason = feedback_reason
            result.human_correction = human_correction
            db.add(result)
            db.commit()
            db.refresh(result)
            db.expunge(result)
            return result

    def update_comparison(
        self,
        result_id: str,
        comparison_result: str,
    ) -> Optional[RunResult]:
        """Update comparison result."""
        with get_session() as db:
            statement = select(RunResult).where(RunResult.id == result_id)
            result = db.exec(statement).first()
            if not result:
                return None

            result.comparison_result = comparison_result
            db.add(result)
            db.commit()
            db.refresh(result)
            db.expunge(result)
            return result

    def get_feedback_summary(
        self,
        prompt_version_id: str,
    ) -> dict:
        """Get feedback summary for a prompt version."""
        results = self.get_results_for_version(prompt_version_id)

        good_count = sum(1 for r in results if r.human_feedback == "good")
        bad_count = sum(1 for r in results if r.human_feedback == "bad")
        pending_count = sum(1 for r in results if r.human_feedback is None)

        return {
            "good": good_count,
            "bad": bad_count,
            "pending": pending_count,
            "total": len(results),
        }
