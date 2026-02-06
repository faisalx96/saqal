"""Export functionality for Saqal."""

import json
from datetime import datetime
from typing import Optional

from .models import Session, Input, PromptVersion, RunResult
from .session_manager import SessionManager
from .input_manager import InputManager
from .prompt_manager import PromptManager
from .run_manager import RunManager


def export_prompt_markdown(
    session: Session,
    version: PromptVersion,
) -> str:
    """Export a prompt version as Markdown."""
    return f"""# {session.name} - v{version.version_number}

## Prompt

```
{version.prompt_text}
```

## Metadata
- Task: {session.task_description}
- Version: {version.version_number}
- Created: {version.created_at.strftime('%Y-%m-%d')}
- Model: {session.model_name}
- Provider: {session.model_provider}
- Temperature: {session.model_temperature}
"""


def export_session_json(
    session_id: str,
    session_manager: SessionManager,
    input_manager: InputManager,
    prompt_manager: PromptManager,
    run_manager: Optional[RunManager] = None,
) -> str:
    """Export a full session as JSON."""
    session = session_manager.get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    inputs = input_manager.get_inputs(session_id)
    versions = prompt_manager.get_version_history(session_id)

    # Get results for each version if run_manager is provided
    results_by_version = {}
    if run_manager:
        for version in versions:
            results_by_version[version.id] = run_manager.get_results_for_version(version.id)

    export_data = {
        "session": {
            "id": session.id,
            "name": session.name,
            "task_description": session.task_description,
            "output_description": session.output_description,
            "model_provider": session.model_provider,
            "model_name": session.model_name,
            "model_temperature": session.model_temperature,
            "batch_size": session.batch_size,
            "status": session.status,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        },
        "versions": [
            {
                "id": v.id,
                "version_number": v.version_number,
                "prompt_text": v.prompt_text,
                "parent_version_id": v.parent_version_id,
                "mutation_explanation": v.mutation_explanation,
                "status": v.status,
                "pareto_rank": v.pareto_rank,
                "created_at": v.created_at.isoformat(),
            }
            for v in versions
        ],
        "inputs": [
            {
                "id": inp.id,
                "content": inp.content,
                "ground_truth": inp.ground_truth,
                "metadata": inp.input_metadata,
                "created_at": inp.created_at.isoformat(),
            }
            for inp in inputs
        ],
        "results": [],
    }

    # Add results if available
    if run_manager:
        for version_id, results in results_by_version.items():
            for result in results:
                export_data["results"].append({
                    "id": result.id,
                    "input_id": result.input_id,
                    "prompt_version_id": result.prompt_version_id,
                    "output": result.output,
                    "latency_ms": result.latency_ms,
                    "tokens_used": result.tokens_used,
                    "human_feedback": result.human_feedback,
                    "feedback_reason": result.feedback_reason,
                    "human_correction": result.human_correction,
                    "comparison_result": result.comparison_result,
                    "created_at": result.created_at.isoformat(),
                })

    return json.dumps(export_data, indent=2)
