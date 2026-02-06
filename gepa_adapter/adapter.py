"""Interactive GEPA adapter for human-in-the-loop prompt optimization."""

from dataclasses import dataclass, field
from typing import Optional

from llm.client import LLMClient
from .feedback_converter import FeedbackItem, FeedbackConverter


@dataclass
class MutationProposal:
    """A proposed mutation to the prompt."""

    new_prompt: str
    explanation: str  # Human-readable summary
    analysis: str  # Detailed analysis of issues
    changes: list[str] = field(default_factory=list)  # Bullet points of changes


class InteractiveGEPAAdapter:
    """
    Custom GEPA adapter for interactive human-in-the-loop optimization.

    Key differences from standard GEPA usage:
    1. Single-iteration mode (pauses for human approval)
    2. Feedback comes from human judgments, not automated metrics
    3. Exposes mutation explanations for UI display
    """

    def __init__(
        self,
        initial_prompt: str,
        task_description: str,
        llm_client: LLMClient,
        reflection_model: Optional[str] = None,
    ):
        """
        Initialize the GEPA adapter.

        Args:
            initial_prompt: The starting prompt text
            task_description: Description of what the prompt should do
            llm_client: LLM client for making API calls
            reflection_model: Model to use for reflection (defaults to client default)
        """
        self.current_prompt = initial_prompt
        self.task_description = task_description
        self.llm_client = llm_client
        self.reflection_model = reflection_model
        self.pareto_frontier: list[str] = [initial_prompt]
        self.iteration_count = 0
        self.feedback_converter = FeedbackConverter()

    def run_prompt(self, prompt: str, input_content: str) -> str:
        """Execute prompt on a single input."""
        formatted = prompt.replace("{input}", input_content)
        response = self.llm_client.complete(formatted)
        return response.text

    def propose_mutation(
        self,
        feedback_batch: list[FeedbackItem],
    ) -> MutationProposal:
        """
        Given a batch of human feedback, propose an improved prompt.

        Returns:
            MutationProposal with new prompt and explanation

        NOTE: Does NOT automatically accept - waits for user decision.
        """
        # Convert feedback to GEPA format
        feedback_text = self.feedback_converter.convert(feedback_batch)

        # Build and execute reflection prompt
        reflection_prompt = self._build_reflection_prompt(feedback_text)
        reflection_response = self.llm_client.complete(
            reflection_prompt,
            model=self.reflection_model,
        )

        # Parse response into structured proposal
        proposal = self._parse_reflection(reflection_response.text)

        return proposal

    def accept_mutation(self, proposal: MutationProposal) -> None:
        """Accept a proposed mutation, updating internal state."""
        self.current_prompt = proposal.new_prompt
        self.pareto_frontier.append(proposal.new_prompt)
        self.iteration_count += 1

    def reject_mutation(self, proposal: MutationProposal) -> None:
        """Reject a proposed mutation, keeping current prompt."""
        pass  # No state change needed

    def _build_reflection_prompt(self, feedback_text: str) -> str:
        """Build the reflection prompt for GEPA."""
        return f"""You are an expert prompt engineer analyzing a prompt that needs improvement.

TASK DESCRIPTION:
{self.task_description}

CURRENT PROMPT:
\"\"\"
{self.current_prompt}
\"\"\"

HUMAN FEEDBACK ON RECENT OUTPUTS:

{feedback_text}

INSTRUCTIONS:
1. Analyze the patterns in the bad outputs
2. Identify what the prompt is missing or doing wrong
3. Propose specific changes to fix the issues
4. Write the complete improved prompt

Respond in this exact format:

ANALYSIS:
[Your analysis of the failure patterns]

CHANGES:
- [Change 1]
- [Change 2]
- [Change 3]

NEW PROMPT:
\"\"\"
[The complete improved prompt]
\"\"\"
"""

    def _parse_reflection(self, response: str) -> MutationProposal:
        """Parse GEPA reflection response into structured proposal."""
        analysis = ""
        changes = []
        new_prompt = ""

        # Parse ANALYSIS section
        if "ANALYSIS:" in response:
            analysis_start = response.index("ANALYSIS:") + len("ANALYSIS:")
            analysis_end = (
                response.index("CHANGES:") if "CHANGES:" in response else len(response)
            )
            analysis = response[analysis_start:analysis_end].strip()

        # Parse CHANGES section
        if "CHANGES:" in response:
            changes_start = response.index("CHANGES:") + len("CHANGES:")
            changes_end = (
                response.index("NEW PROMPT:")
                if "NEW PROMPT:" in response
                else len(response)
            )
            changes_text = response[changes_start:changes_end].strip()
            changes = [
                line.strip().lstrip("- ").lstrip("* ")
                for line in changes_text.split("\n")
                if line.strip().startswith("-") or line.strip().startswith("*")
            ]

        # Parse NEW PROMPT section - try multiple formats
        if "NEW PROMPT:" in response:
            prompt_section = response.split("NEW PROMPT:")[-1].strip()

            # Try triple double quotes
            if '"""' in prompt_section:
                parts = prompt_section.split('"""')
                if len(parts) >= 2:
                    new_prompt = parts[1].strip()
            # Try triple single quotes
            elif "'''" in prompt_section:
                parts = prompt_section.split("'''")
                if len(parts) >= 2:
                    new_prompt = parts[1].strip()
            # Try code block with backticks
            elif "```" in prompt_section:
                parts = prompt_section.split("```")
                if len(parts) >= 2:
                    # Remove optional language identifier on first line
                    content = parts[1]
                    if content.startswith("\n"):
                        content = content[1:]
                    elif "\n" in content:
                        first_line = content.split("\n")[0]
                        # If first line looks like a language identifier, skip it
                        if first_line.strip().isalpha() or first_line.strip() == "":
                            content = "\n".join(content.split("\n")[1:])
                    new_prompt = content.strip()
            # Try single backticks or just take everything after
            else:
                # Remove leading/trailing backticks if present
                new_prompt = prompt_section.strip().strip("`").strip()

        # If still no prompt found, try to find any code block in response
        if not new_prompt and "```" in response:
            parts = response.split("```")
            if len(parts) >= 3:  # At least one complete code block
                # Take the last complete code block
                content = parts[-2]
                if content.startswith("\n"):
                    content = content[1:]
                elif "\n" in content:
                    first_line = content.split("\n")[0]
                    if first_line.strip().isalpha() or first_line.strip() == "":
                        content = "\n".join(content.split("\n")[1:])
                new_prompt = content.strip()

        # Generate human-readable explanation
        explanation = f"Made {len(changes)} changes to address feedback issues."
        if changes:
            explanation = "; ".join(changes[:3])
            if len(changes) > 3:
                explanation += f"; and {len(changes) - 3} more changes"

        # Fallback: if we still don't have a new prompt, use the current one
        final_prompt = new_prompt if new_prompt else self.current_prompt

        return MutationProposal(
            new_prompt=final_prompt,
            explanation=explanation,
            analysis=analysis,
            changes=changes,
        )

    def get_feedback_summary(self, feedback_batch: list[FeedbackItem]) -> dict:
        """Get a summary of the feedback for display."""
        good_count = sum(1 for f in feedback_batch if f.is_good)
        bad_count = sum(1 for f in feedback_batch if not f.is_good)

        # Extract common issues from bad feedback
        issues = []
        for item in feedback_batch:
            if not item.is_good and item.reason:
                issues.append(item.reason)

        return {
            "good": good_count,
            "bad": bad_count,
            "issues": issues,
        }
