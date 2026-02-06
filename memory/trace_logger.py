"""MLflow trace logging for Saqal prompt runs and feedback."""

from typing import Optional

import mlflow
from mlflow.entities import AssessmentSource, AssessmentSourceType


class TraceLogger:
    """
    Logs prompt execution traces and human feedback to MLflow.

    Each prompt run (input -> LLM -> output) becomes an MLflow trace.
    Human feedback (good/bad + reason) is logged as assessments on those traces.
    """

    def __init__(self, experiment_id: str):
        self.experiment_id = experiment_id
        mlflow.set_experiment(experiment_id=experiment_id)

    def log_run_trace(
        self,
        input_content: str,
        prompt_text: str,
        output: str,
        model_name: str,
        prompt_version_id: str,
        run_result_id: str,
    ) -> str:
        """
        Create an MLflow trace for a single prompt execution.

        Returns the trace_id for later feedback attachment.
        """
        with mlflow.start_span(
            name="prompt_eval",
            attributes={
                "prompt_version_id": prompt_version_id,
                "run_result_id": run_result_id,
                "model": model_name,
            },
        ) as span:
            span.set_inputs(
                {
                    "input": input_content,
                    "prompt": prompt_text,
                }
            )
            span.set_outputs(
                {
                    "output": output,
                }
            )
            trace_id = span.trace_id

        return trace_id

    def log_feedback(
        self,
        trace_id: str,
        is_good: bool,
        reason: Optional[str] = None,
        correction: Optional[str] = None,
    ) -> None:
        """
        Log human feedback as an MLflow assessment on an existing trace.
        """
        rationale_parts = []
        if reason:
            rationale_parts.append(reason)
        if correction:
            rationale_parts.append(f"Correction: {correction}")
        rationale = "; ".join(rationale_parts) if rationale_parts else None

        mlflow.log_feedback(
            trace_id=trace_id,
            name="output_quality",
            value=is_good,
            rationale=rationale,
            source=AssessmentSource(
                source_type=AssessmentSourceType.HUMAN,
                source_id="saqal_user",
            ),
        )
