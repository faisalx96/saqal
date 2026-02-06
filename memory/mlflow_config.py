"""MLflow configuration and initialization for Saqal memory layer."""

import os
from pathlib import Path
from typing import Optional

import mlflow

# Default MLflow tracking URI - local file store alongside SQLite DB
DEFAULT_MLFLOW_DIR = Path(__file__).parent.parent / "data" / "mlruns"


def init_mlflow(tracking_uri: Optional[str] = None) -> None:
    """
    Initialize MLflow tracking.

    Sets the tracking URI and configures the environment for
    OpenRouter compatibility if needed.
    """
    uri = tracking_uri or os.getenv(
        "MLFLOW_TRACKING_URI",
        DEFAULT_MLFLOW_DIR.as_uri(),
    )
    mlflow.set_tracking_uri(uri)

    # For OpenRouter compatibility: MLflow's "openai:/" model format
    # uses OPENAI_API_BASE to route requests. When the Saqal user is
    # using OpenRouter, we must set this env var so MLflow's judge
    # calls go through OpenRouter too.
    provider = os.getenv("LLM_PROVIDER", "openrouter")
    if provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if api_key:
            os.environ.setdefault("OPENAI_API_KEY", api_key)
            os.environ.setdefault(
                "OPENAI_API_BASE", "https://openrouter.ai/api/v1"
            )


def get_mlflow_model_uri(model_name: str, provider: str = "openrouter") -> str:
    """
    Convert a Saqal model name to MLflow model URI format.

    MLflow uses "openai:/<model>" format. For OpenRouter models that
    include a slash (e.g., "openai/gpt-4o-mini"), we keep the full name.
    """
    return f"openai:/{model_name}"


def get_or_create_experiment(session_id: str, session_name: str) -> str:
    """
    Get or create an MLflow experiment for a Saqal session.

    Returns the experiment_id.
    """
    experiment_name = f"saqal/{session_name}_{session_id[:8]}"
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if experiment:
        return experiment.experiment_id
    return mlflow.create_experiment(experiment_name)
