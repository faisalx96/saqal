"""Feedback converter for GEPA integration."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FeedbackItem:
    """A single feedback item from human review."""

    input_content: str
    output: str
    is_good: bool
    reason: Optional[str] = None
    correction: Optional[str] = None


class FeedbackConverter:
    """Converts human feedback to GEPA-compatible text format."""

    def convert(self, feedback_batch: list[FeedbackItem]) -> str:
        """Convert feedback items to GEPA-compatible text format."""
        good_examples = []
        bad_examples = []

        for item in feedback_batch:
            if item.is_good:
                good_examples.append(
                    f'Input: "{item.input_content}"\nOutput: "{item.output}"'
                )
            else:
                bad_entry = f'Input: "{item.input_content}"\nOutput: "{item.output}"'
                if item.reason:
                    bad_entry += f'\nWhy wrong: "{item.reason}"'
                if item.correction:
                    bad_entry += f'\nShould be: "{item.correction}"'
                bad_examples.append(bad_entry)

        return self._format_feedback_text(good_examples, bad_examples)

    def _format_feedback_text(self, good: list[str], bad: list[str]) -> str:
        """Format feedback into structured text."""
        sections = []

        if good:
            sections.append("GOOD OUTPUTS (keep doing this):\n\n" + "\n\n".join(good))

        if bad:
            sections.append("BAD OUTPUTS (fix these):\n\n" + "\n\n".join(bad))

        return "\n\n---\n\n".join(sections)
