"""SQLModel entity definitions for Saqal."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlmodel import Field, SQLModel


class Session(SQLModel, table=True):
    """Represents a single prompt refinement project."""

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str = Field(index=True)
    task_description: str
    output_description: Optional[str] = None
    model_provider: str
    model_name: str
    model_temperature: float = 0.7
    batch_size: int = 10
    status: str = Field(default="active", index=True)  # 'active', 'completed', 'archived'
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Input(SQLModel, table=True):
    """Represents a single test input for the prompt."""

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    session_id: str = Field(foreign_key="session.id", index=True)
    content: str
    ground_truth: Optional[str] = None
    input_metadata: Optional[str] = None  # JSON string for additional context
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PromptVersion(SQLModel, table=True):
    """Represents a version of the prompt, including lineage tracking."""

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    session_id: str = Field(foreign_key="session.id", index=True)
    version_number: int
    prompt_text: str
    parent_version_id: Optional[str] = Field(default=None, foreign_key="promptversion.id")
    mutation_explanation: Optional[str] = None
    status: str = Field(default="proposed")  # 'proposed', 'accepted', 'rejected'
    pareto_rank: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RunResult(SQLModel, table=True):
    """Represents the output from running a prompt on an input, plus human feedback."""

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    input_id: str = Field(foreign_key="input.id", index=True)
    prompt_version_id: str = Field(foreign_key="promptversion.id", index=True)
    output: str
    latency_ms: Optional[int] = None
    tokens_used: Optional[int] = None
    human_feedback: Optional[str] = None  # 'good', 'bad', or null
    feedback_reason: Optional[str] = None
    human_correction: Optional[str] = None
    comparison_result: Optional[str] = None  # 'better', 'worse', 'same'
    created_at: datetime = Field(default_factory=datetime.utcnow)
