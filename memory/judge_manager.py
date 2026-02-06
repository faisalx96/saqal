"""MemAlign judge management for Saqal."""

from dataclasses import dataclass
from typing import Optional

import mlflow
from mlflow.genai.judges import make_judge
from mlflow.genai.judges.optimizers import MemAlignOptimizer

from .mlflow_config import get_mlflow_model_uri


@dataclass
class JudgeSuggestion:
    """Auto-judge suggestion for a single output."""

    is_good: bool
    rationale: str


@dataclass
class AlignmentResult:
    """Result of aligning the judge with accumulated feedback."""

    aligned_judge: object  # The aligned judge callable
    distilled_principles: str  # Extracted from aligned_judge.instructions
    trace_count: int  # Number of traces used for alignment
    original_instructions: str


class JudgeManager:
    """
    Manages the MemAlign judge lifecycle:
    1. Creates a base judge
    2. Aligns it with accumulated human feedback traces
    3. Extracts distilled principles for GEPA injection
    4. Runs the aligned judge for auto-suggestions
    """

    BASE_INSTRUCTIONS = (
        "Evaluate whether the LLM output is good or bad based on "
        "the task requirements and input context.\n"
        "Input: {{ inputs }}\n"
        "Output: {{ outputs }}\n"
        "Return True if the output is acceptable, False if it has issues."
    )

    def __init__(
        self,
        model_name: str,
        provider: str = "openrouter",
        embedding_model: Optional[str] = None,
        retrieval_k: int = 3,
    ):
        self.model_uri = get_mlflow_model_uri(model_name, provider)
        self.embedding_model = embedding_model or "openai:/text-embedding-3-small"
        self.retrieval_k = retrieval_k
        self._aligned_judge = None
        self._alignment_result: Optional[AlignmentResult] = None

    def align(self, experiment_id: str) -> AlignmentResult:
        """
        Align the judge with all accumulated human feedback traces
        from the given experiment.

        This is the core MemAlign operation: it distills semantic
        principles from all past feedback and enriches the judge's
        instructions.
        """
        # Create base judge
        base_judge = make_judge(
            name="output_quality",
            instructions=self.BASE_INSTRUCTIONS,
            feedback_value_type=bool,
            model=self.model_uri,
        )

        # Get all traces with feedback from this experiment
        mlflow.set_experiment(experiment_id=experiment_id)
        traces = mlflow.search_traces(return_type="list")

        if not traces:
            self._aligned_judge = base_judge
            self._alignment_result = AlignmentResult(
                aligned_judge=base_judge,
                distilled_principles="",
                trace_count=0,
                original_instructions=self.BASE_INSTRUCTIONS,
            )
            return self._alignment_result

        # Create optimizer
        optimizer = MemAlignOptimizer(
            reflection_lm=self.model_uri,
            embedding_model=self.embedding_model,
            retrieval_k=self.retrieval_k,
        )

        # Align: distills principles + stores episodic memory
        aligned_judge = base_judge.align(
            traces=traces,
            optimizer=optimizer,
        )

        # Extract the distilled principles from enriched instructions
        distilled = aligned_judge.instructions
        principles_only = distilled
        if distilled.startswith(self.BASE_INSTRUCTIONS):
            principles_only = distilled[len(self.BASE_INSTRUCTIONS) :].strip()

        self._aligned_judge = aligned_judge
        self._alignment_result = AlignmentResult(
            aligned_judge=aligned_judge,
            distilled_principles=principles_only,
            trace_count=len(traces),
            original_instructions=self.BASE_INSTRUCTIONS,
        )

        return self._alignment_result

    def suggest(
        self,
        input_content: str,
        output: str,
    ) -> Optional[JudgeSuggestion]:
        """
        Run the aligned judge on a single input/output pair.

        Returns a suggestion, or None if the judge hasn't been aligned
        or if evaluation fails.
        """
        if self._aligned_judge is None:
            return None

        try:
            feedback = self._aligned_judge(
                inputs={"input": input_content},
                outputs={"output": output},
            )
            return JudgeSuggestion(
                is_good=bool(feedback.value),
                rationale=feedback.rationale or "",
            )
        except Exception:
            # Auto-judge failure should never block the user
            return None

    def get_principles(self) -> str:
        """
        Get the distilled principles from the last alignment.

        Returns empty string if no alignment has been done.
        """
        if self._alignment_result is None:
            return ""
        return self._alignment_result.distilled_principles

    @property
    def is_aligned(self) -> bool:
        return self._aligned_judge is not None

    @property
    def trace_count(self) -> int:
        if self._alignment_result is None:
            return 0
        return self._alignment_result.trace_count
