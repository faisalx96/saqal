# Technical Specification: Saqal: A Prompt Refinement Workbench

**Interactive Human-in-the-Loop Prompt Optimization with GEPA**

Version 1.0 | December 2025

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Product Overview](#2-product-overview)
3. [System Architecture](#3-system-architecture)
4. [Data Model](#4-data-model)
5. [GEPA Integration](#5-gepa-integration)
6. [User Interface Specification](#6-user-interface-specification)
7. [API Contracts](#7-api-contracts)
8. [Implementation Plan](#8-implementation-plan)
9. [Testing Strategy](#9-testing-strategy)
10. [Deployment](#10-deployment)
11. [Appendices](#11-appendices)

---

## 1. Executive Summary

### 1.1 Purpose

This document provides the complete technical specification for the **Prompt Refinement Workbench**, an interactive tool that enables users to iteratively improve LLM prompts through human-in-the-loop feedback. The system leverages **GEPA (Genetic-Pareto)**, a state-of-the-art prompt optimization algorithm, to automatically propose prompt improvements based on user feedback.

### 1.2 Problem Statement

Prompt engineering is currently a manual, tedious process. Users must:

- Run prompts on test inputs manually
- Evaluate outputs subjectively
- Guess at what changes might improve results
- Repeat indefinitely with no systematic approach

Existing tools either automate everything (removing human judgment) or require users to manually edit prompts (providing no guidance). There is no tool that combines human feedback with intelligent, transparent prompt adaptation.

### 1.3 Solution Overview

The Prompt Refinement Workbench bridges this gap by:

1. Allowing users to mark outputs as good/bad with optional explanations
2. Using GEPA to automatically propose prompt improvements based on feedback
3. Showing transparent diffs of what changed and why
4. Enabling users to accept, edit, or reject proposed changes
5. Providing side-by-side comparison of before/after performance
6. Maintaining full version history for audit and rollback

### 1.4 Target Users

**Primary:** Individual prompt engineers and developers who want to systematically improve prompts for any LLM task (classification, extraction, generation, etc.) without writing code or defining programmatic metrics.

### 1.5 Key Differentiators

| Feature | Existing Tools | This Product |
|---------|----------------|--------------|
| Feedback type | Programmatic metrics or production signals | Direct human judgment (good/bad + why) |
| Adaptation | Automated black-box or manual editing | AI-proposed with human approval |
| Transparency | Limited visibility into changes | Full diff view with explanations |
| Workflow | Batch/offline optimization | Live, interactive refinement sessions |
| Task flexibility | Often task-specific | Any prompt task (classification, extraction, generation, etc.) |

---

## 2. Product Overview

### 2.1 Core Workflow

The user workflow consists of five main stages:

```
Setup → Review Batch → Adapt → Compare → Iterate
```

#### 2.1.1 Stage 1: Setup

User provides:
- Task description (what the prompt should do)
- Initial prompt text
- Test inputs (CSV, JSON, or pasted text)
- Optional: expected outputs (ground truth)
- Model configuration (provider, model name, temperature)

#### 2.1.2 Stage 2: Review Batch

System runs the prompt on a batch of inputs (default: 10). User reviews each output and provides feedback:
- Good/Bad toggle (required)
- "Why is this wrong?" (encouraged but optional)
- "What should it be?" (optional correction)

#### 2.1.3 Stage 3: Adapt

User clicks "Adapt Prompt". System:
1. Aggregates feedback from the batch
2. Sends feedback to GEPA optimization engine
3. GEPA proposes a new prompt version with explanation
4. UI displays diff view showing exact changes
5. User can Accept, Edit & Accept, or Reject the proposal

#### 2.1.4 Stage 4: Compare

After accepting a new prompt version, user can compare performance:
- Same inputs shown with old vs new outputs side-by-side
- User marks each: "New is better" / "Old is better" / "Same"
- Aggregate statistics shown
- User decides to keep new version or revert

#### 2.1.5 Stage 5: Iterate

User repeats stages 2-4 until satisfied with prompt performance. All versions are saved with full history.

### 2.2 Task Flexibility

The system is designed to work with **any LLM task**:

| Task Type | Example Input | Example Output |
|-----------|---------------|----------------|
| Classification | Customer message text | complaint / question / praise / other |
| Extraction | Job posting HTML | JSON with title, salary, location |
| Generation | Topic + tone | Blog post paragraph |
| Summarization | Long document | 3-sentence summary |
| Judgment/Scoring | Essay + rubric | Score 1-10 with reasoning |
| Translation | English text | French translation |
| Code generation | Function description | Python code |

### 2.3 Constraints and Scope

**In Scope:**
- Single-user Streamlit application
- Local SQLite persistence
- OpenAI-compatible API providers (OpenRouter, OpenAI, local)
- Single-prompt optimization (not multi-step chains)
- Text inputs and outputs

**Out of Scope (v1):**
- Multi-user collaboration
- Image/audio inputs
- Multi-prompt pipeline optimization
- Fine-tuning integration
- Production deployment/serving

---

## 3. System Architecture

### 3.1 High-Level Architecture

```
┌────────────────────────────────────────────────────────────┐
│                     STREAMLIT UI                           │
│  ┌──────────┬──────────┬─────────┬───────────┬──────────┐  │
│  │  Setup   │  Review  │  Adapt  │  Compare  │  History │  │
│  └──────────┴──────────┴─────────┴───────────┴──────────┘  │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│                   CORE APPLICATION                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Session    │  │    Prompt    │  │    Run Result    │  │
│  │   Manager    │  │   Versions   │  │     Store        │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│                  GEPA ADAPTER LAYER                        │
│         Converts human feedback → GEPA format              │
│         Controls iteration (pause for approval)            │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│                     GEPA ENGINE                            │
│       (Reflection, Mutation, Pareto Selection)             │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│                   LLM PROVIDER                             │
│            (OpenRouter / OpenAI-compatible)                │
└────────────────────────────────────────────────────────────┘
```

### 3.2 Component Responsibilities

#### 3.2.1 Streamlit UI Layer

**Responsibilities:**
- Render all user interface pages
- Handle user input and form submissions
- Display prompt diffs and comparisons
- Manage navigation between pages
- Session state management for in-progress work

**Technology:** Streamlit 1.28+

#### 3.2.2 Core Application Layer

**Responsibilities:**
- Business logic for sessions, inputs, versions, and results
- Database operations (CRUD)
- Orchestration of the refinement workflow
- Export functionality

**Technology:** Python 3.11+, SQLModel, SQLite

#### 3.2.3 GEPA Adapter Layer

**Responsibilities:**
- Translate human feedback (good/bad + text) into GEPA-compatible format
- Wrap GEPA to run single iterations (pause for human approval)
- Extract mutation explanations for UI display
- Manage Pareto frontier candidates

**Technology:** gepa package (pip install gepa)

#### 3.2.4 LLM Provider Layer

**Responsibilities:**
- Execute prompts against LLM APIs
- Handle retries and rate limiting
- Normalize responses across providers

**Technology:** LiteLLM (OpenRouter/OpenAI-compatible)

### 3.3 Technology Stack

| Component | Technology | Version | Rationale |
|-----------|------------|---------|-----------|
| UI Framework | Streamlit | 1.28+ | Requirement from stakeholder; rapid prototyping |
| Language | Python | 3.11+ | GEPA compatibility; ecosystem |
| Database | SQLite | 3.x | Zero setup; file-based; sufficient for single-user |
| ORM | SQLModel | 0.0.14+ | Pydantic + SQLAlchemy; type safety |
| LLM Client | LiteLLM | 1.0+ | OpenRouter + any OpenAI-compatible; unified interface |
| Optimizer | gepa | latest | State-of-the-art; reflection-based; DSPy-compatible |
| Diffing | difflib | stdlib | Built-in Python; sufficient for text diffs |

### 3.4 Directory Structure

```
prompt-workbench/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Streamlit entry point
│   ├── pages/
│   │   ├── 1_setup.py          # Session setup page
│   │   ├── 2_review.py         # Batch review page
│   │   ├── 3_adapt.py          # Adaptation approval page
│   │   ├── 4_compare.py        # Before/after comparison
│   │   └── 5_history.py        # Version history & export
│   ├── components/
│   │   ├── feedback_card.py    # Reusable feedback UI component
│   │   ├── diff_viewer.py      # Prompt diff display
│   │   └── comparison_table.py # Side-by-side output comparison
│   └── state.py                # Streamlit session state helpers
├── core/
│   ├── __init__.py
│   ├── models.py               # SQLModel definitions
│   ├── database.py             # DB connection and operations
│   ├── session_manager.py      # Session CRUD operations
│   ├── prompt_manager.py       # Prompt version management
│   ├── run_manager.py          # Execute prompts, store results
│   └── export.py               # Export to JSON/Markdown
├── gepa_adapter/
│   ├── __init__.py
│   ├── adapter.py              # InteractiveGEPAAdapter class
│   ├── feedback_converter.py   # Human feedback → GEPA format
│   └── iteration_controller.py # Single-step iteration control
├── llm/
│   ├── __init__.py
│   ├── client.py               # LiteLLM wrapper
│   └── config.py               # Model configuration
├── tests/
│   ├── test_models.py
│   ├── test_gepa_adapter.py
│   └── test_llm_client.py
├── data/                        # SQLite DB stored here
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## 4. Data Model

### 4.1 Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────────┐       ┌─────────────┐
│   Session   │──1:N──│  PromptVersion  │──1:N──│  RunResult  │
└─────────────┘       └─────────────────┘       └─────────────┘
      │                       │                        │
      │ 1:N                   │                        │
      ▼                       │                        │
┌─────────────┐               │                        │
│    Input    │───────────────┼────────────────────────┘
└─────────────┘               │                  N:1
                              │
                    (self-reference: parent_version_id)
```

### 4.2 Entity Definitions

#### 4.2.1 Session

Represents a single prompt refinement project.

```python
class Session(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str                           # User-provided session name
    task_description: str               # What the prompt should do
    output_description: Optional[str]   # Expected output format
    model_provider: str                 # 'openrouter', 'openai', etc.
    model_name: str                     # 'gpt-4o-mini', 'claude-3-haiku', etc.
    model_temperature: float = 0.7
    batch_size: int = 10               # Inputs per review batch
    status: str = 'active'             # 'active', 'completed', 'archived'
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID string | Auto | Primary key, auto-generated |
| name | string | Yes | User-friendly session name |
| task_description | string | Yes | Natural language description of the task |
| output_description | string | No | Expected output format (e.g., "JSON with fields...") |
| model_provider | string | Yes | LLM provider identifier |
| model_name | string | Yes | Specific model to use |
| model_temperature | float | No | Sampling temperature, default 0.7 |
| batch_size | int | No | Number of inputs per batch, default 10 |
| status | string | No | Session status, default 'active' |
| created_at | datetime | Auto | Creation timestamp |
| updated_at | datetime | Auto | Last modification timestamp |

#### 4.2.2 Input

Represents a single test input for the prompt.

```python
class Input(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    session_id: str = Field(foreign_key='session.id')
    content: str                        # The input text (or JSON string)
    ground_truth: Optional[str]         # Expected output (if known)
    metadata: Optional[str]             # Additional context (JSON string)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID string | Auto | Primary key |
| session_id | UUID string | Yes | Foreign key to Session |
| content | string | Yes | Input text or JSON-serialized structured input |
| ground_truth | string | No | Expected output for comparison |
| metadata | string (JSON) | No | Additional context about this input |
| created_at | datetime | Auto | Creation timestamp |

#### 4.2.3 PromptVersion

Represents a version of the prompt, including lineage tracking.

```python
class PromptVersion(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    session_id: str = Field(foreign_key='session.id')
    version_number: int                 # Sequential version number
    prompt_text: str                    # The actual prompt template
    parent_version_id: Optional[str]    # ID of parent version (for lineage)
    mutation_explanation: Optional[str] # GEPA's explanation of changes
    status: str = 'proposed'            # 'proposed', 'accepted', 'rejected'
    pareto_rank: Optional[int]          # Rank in Pareto frontier
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID string | Auto | Primary key |
| session_id | UUID string | Yes | Foreign key to Session |
| version_number | int | Yes | Sequential version (1, 2, 3...) |
| prompt_text | string | Yes | Full prompt template with {input} placeholder |
| parent_version_id | UUID string | No | Link to parent version (null for v1) |
| mutation_explanation | string | No | GEPA's explanation of what changed |
| status | string | No | Workflow status of this version |
| pareto_rank | int | No | Position in Pareto frontier (if applicable) |
| created_at | datetime | Auto | Creation timestamp |

#### 4.2.4 RunResult

Represents the output from running a prompt on an input, plus human feedback.

```python
class RunResult(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    input_id: str = Field(foreign_key='input.id')
    prompt_version_id: str = Field(foreign_key='promptversion.id')
    output: str                         # Raw LLM output
    latency_ms: Optional[int]           # Response time in milliseconds
    tokens_used: Optional[int]          # Total tokens consumed
    human_feedback: Optional[str]       # 'good', 'bad', or null
    feedback_reason: Optional[str]      # Why it's wrong (user explanation)
    human_correction: Optional[str]     # What the output should have been
    comparison_result: Optional[str]    # 'better', 'worse', 'same' (for comparisons)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID string | Auto | Primary key |
| input_id | UUID string | Yes | Foreign key to Input |
| prompt_version_id | UUID string | Yes | Foreign key to PromptVersion |
| output | string | Yes | Raw output from LLM |
| latency_ms | int | No | Response latency in milliseconds |
| tokens_used | int | No | Token count for cost tracking |
| human_feedback | string | No | 'good' or 'bad' |
| feedback_reason | string | No | User's explanation of the issue |
| human_correction | string | No | What the correct output should be |
| comparison_result | string | No | Result when comparing versions |
| created_at | datetime | Auto | Creation timestamp |

### 4.3 Database Schema SQL

The following SQL creates the required tables. SQLModel will auto-generate this, but it's provided for reference:

```sql
CREATE TABLE session (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    task_description TEXT NOT NULL,
    output_description TEXT,
    model_provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_temperature REAL DEFAULT 0.7,
    batch_size INTEGER DEFAULT 10,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE input (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES session(id),
    content TEXT NOT NULL,
    ground_truth TEXT,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE promptversion (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES session(id),
    version_number INTEGER NOT NULL,
    prompt_text TEXT NOT NULL,
    parent_version_id TEXT REFERENCES promptversion(id),
    mutation_explanation TEXT,
    status TEXT DEFAULT 'proposed',
    pareto_rank INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE runresult (
    id TEXT PRIMARY KEY,
    input_id TEXT NOT NULL REFERENCES input(id),
    prompt_version_id TEXT NOT NULL REFERENCES promptversion(id),
    output TEXT NOT NULL,
    latency_ms INTEGER,
    tokens_used INTEGER,
    human_feedback TEXT,
    feedback_reason TEXT,
    human_correction TEXT,
    comparison_result TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_input_session ON input(session_id);
CREATE INDEX idx_promptversion_session ON promptversion(session_id);
CREATE INDEX idx_runresult_input ON runresult(input_id);
CREATE INDEX idx_runresult_version ON runresult(prompt_version_id);
```

---

## 5. GEPA Integration

### 5.1 What is GEPA?

GEPA (Genetic-Pareto) is a state-of-the-art prompt optimization algorithm from UC Berkeley, Stanford, and Databricks (paper: arXiv:2507.19457). Key features:

- **Reflective Mutation:** Uses LLM reflection to analyze failures and propose targeted prompt improvements
- **Pareto Selection:** Maintains diverse candidate pool to avoid local optima
- **Sample Efficient:** Achieves results with up to 35x fewer examples than RL methods
- **Textual Feedback:** Accepts natural language explanations, not just scalar scores

### 5.2 Integration Approach

We will **NOT** use DSPy. Instead, we use the standalone `gepa` package with a custom adapter.

**Rationale:**
- DSPy requires typed `Signatures` which conflict with our "any task" flexibility
- Standalone GEPA provides the optimization engine without framework overhead
- Custom adapter allows us to control the iteration loop (pause for human approval)

### 5.3 InteractiveGEPAAdapter

The adapter translates our domain model to GEPA's expected interfaces.

```python
# gepa_adapter/adapter.py

from gepa import GEPAAdapter, GEPAConfig
from typing import List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class FeedbackItem:
    input_content: str
    output: str
    is_good: bool
    reason: Optional[str] = None
    correction: Optional[str] = None

@dataclass
class MutationProposal:
    new_prompt: str
    explanation: str      # Human-readable summary
    analysis: str         # Detailed analysis of issues
    changes: List[str]    # Bullet points of changes

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
        llm_client,  # LiteLLM client
        reflection_model: str = 'gpt-4o'  # Model for GEPA reflection
    ):
        self.current_prompt = initial_prompt
        self.task_description = task_description
        self.llm_client = llm_client
        self.reflection_model = reflection_model
        self.pareto_frontier: List[str] = [initial_prompt]
        self.iteration_count = 0
    
    def run_prompt(self, prompt: str, input_content: str) -> str:
        """Execute prompt on a single input."""
        formatted = prompt.replace('{input}', input_content)
        response = self.llm_client.complete(formatted)
        return response.text
    
    def propose_mutation(
        self,
        feedback_batch: List[FeedbackItem]
    ) -> MutationProposal:
        """
        Given a batch of human feedback, propose an improved prompt.
        
        Returns:
            MutationProposal with new prompt and explanation
        
        NOTE: Does NOT automatically accept - waits for user decision.
        """
        # Convert feedback to GEPA format
        feedback_text = self._convert_feedback(feedback_batch)
        
        # Build and execute reflection prompt
        reflection_prompt = self._build_reflection_prompt(feedback_text)
        reflection_response = self.llm_client.complete(
            reflection_prompt,
            model=self.reflection_model
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
    
    def _convert_feedback(self, feedback_batch: List[FeedbackItem]) -> str:
        """Convert human feedback to GEPA-compatible text format."""
        good_examples = []
        bad_examples = []
        
        for item in feedback_batch:
            if item.is_good:
                good_examples.append(f'Input: "{item.input_content}"\nOutput: "{item.output}"')
            else:
                bad_entry = f'Input: "{item.input_content}"\nOutput: "{item.output}"'
                if item.reason:
                    bad_entry += f'\nWhy wrong: "{item.reason}"'
                if item.correction:
                    bad_entry += f'\nShould be: "{item.correction}"'
                bad_examples.append(bad_entry)
        
        return self._format_feedback_text(good_examples, bad_examples)
    
    def _format_feedback_text(self, good: List[str], bad: List[str]) -> str:
        """Format feedback into structured text."""
        sections = []
        
        if good:
            sections.append("GOOD OUTPUTS (keep doing this):\n\n" + "\n\n".join(good))
        
        if bad:
            sections.append("BAD OUTPUTS (fix these):\n\n" + "\n\n".join(bad))
        
        return "\n\n---\n\n".join(sections)
    
    def _build_reflection_prompt(self, feedback_text: str) -> str:
        """Build the reflection prompt for GEPA."""
        return f'''You are an expert prompt engineer.

TASK: {self.task_description}

CURRENT PROMPT:
"""
{self.current_prompt}
"""

FEEDBACK FROM HUMAN REVIEWER:
{feedback_text}

Analyze the feedback patterns and rewrite the prompt to fix the issues.

Respond in this exact format:

ANALYSIS:
[Your analysis of what's going wrong and why]

CHANGES:
- [Change 1]
- [Change 2]
- [Change 3]

NEW PROMPT:
"""
[The complete improved prompt]
"""'''
    
    def _parse_reflection(self, response: str) -> MutationProposal:
        """Parse GEPA reflection response into structured proposal."""
        # Extract sections using simple parsing
        analysis = ""
        changes = []
        new_prompt = ""
        
        # Parse ANALYSIS section
        if "ANALYSIS:" in response:
            analysis_start = response.index("ANALYSIS:") + len("ANALYSIS:")
            analysis_end = response.index("CHANGES:") if "CHANGES:" in response else len(response)
            analysis = response[analysis_start:analysis_end].strip()
        
        # Parse CHANGES section
        if "CHANGES:" in response:
            changes_start = response.index("CHANGES:") + len("CHANGES:")
            changes_end = response.index("NEW PROMPT:") if "NEW PROMPT:" in response else len(response)
            changes_text = response[changes_start:changes_end].strip()
            changes = [line.strip().lstrip("- ") for line in changes_text.split("\n") if line.strip().startswith("-")]
        
        # Parse NEW PROMPT section
        if "NEW PROMPT:" in response:
            prompt_section = response.split("NEW PROMPT:")[-1]
            # Extract content between triple quotes
            if '"""' in prompt_section:
                parts = prompt_section.split('"""')
                if len(parts) >= 2:
                    new_prompt = parts[1].strip()
        
        # Generate human-readable explanation
        explanation = f"Made {len(changes)} changes to address feedback issues."
        if changes:
            explanation = "; ".join(changes[:3])
            if len(changes) > 3:
                explanation += f"; and {len(changes) - 3} more changes"
        
        return MutationProposal(
            new_prompt=new_prompt or self.current_prompt,
            explanation=explanation,
            analysis=analysis,
            changes=changes
        )
```

### 5.4 Feedback Format Specification

Human feedback is converted to the following text format for GEPA:

```
GOOD OUTPUTS (keep doing this):

Input: "How do I reset my password?"
Output: "question"

Input: "Your product is amazing!"
Output: "praise"

---

BAD OUTPUTS (fix these):

Input: "Your app crashed and deleted my data"
Output: "question"
Why wrong: "This is clearly a complaint, not a question"
Should be: "complaint"

Input: "Can I get a refund?"
Output: "question"
Why wrong: "This is a complaint disguised as a question - they're unhappy"
Should be: "complaint"
```

### 5.5 Mutation Response Parsing

GEPA's reflection response is parsed to extract:

1. **Analysis:** The reasoning about what's wrong
2. **Changes:** Bullet points of specific modifications
3. **New Prompt:** The complete improved prompt text

The Changes section is formatted as a human-readable explanation for the UI diff view.

### 5.6 Pareto Frontier Management

GEPA maintains a Pareto frontier of candidate prompts. For the UI, we expose:

- Current best prompt (default selection)
- Alternative candidates (optional advanced view)
- Coverage metrics per candidate

In v1, we simplify by only showing the current best. The Pareto logic runs internally to ensure diversity in the search.

---

## 6. User Interface Specification

### 6.1 Navigation Structure

The application uses Streamlit's native page navigation with 5 main pages:

```
┌─────────────────────────────────────────────────────────────────┐
│  [Setup]  [Review]  [Adapt]  [Compare]  [History]              │
└─────────────────────────────────────────────────────────────────┘
```

Page visibility is context-dependent:
- **Setup:** Always visible
- **Review:** Visible after session created and inputs uploaded
- **Adapt:** Visible after batch has feedback
- **Compare:** Visible after a mutation is accepted
- **History:** Always visible (shows all sessions)

### 6.2 Page 1: Setup

#### 6.2.1 Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Prompt Refinement Workbench                                    │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  ┌─ New Session ───────────────────────────────────────────┐   │
│  │                                                         │   │
│  │  Session Name:                                          │   │
│  │  [________________________________]                     │   │
│  │                                                         │   │
│  │  What task is your prompt doing?                        │   │
│  │  [________________________________]                     │   │
│  │  (e.g., "Classify customer messages into categories")   │   │
│  │                                                         │   │
│  │  What should the output look like? (optional)           │   │
│  │  [________________________________]                     │   │
│  │  (e.g., "One of: complaint, question, praise, other")   │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─ Your Initial Prompt ───────────────────────────────────┐   │
│  │                                                         │   │
│  │  [                                                  ]   │   │
│  │  [  Use {input} as placeholder for the input        ]   │   │
│  │  [                                                  ]   │   │
│  │  [                                                  ]   │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─ Test Inputs ───────────────────────────────────────────┐   │
│  │                                                         │   │
│  │  Upload CSV/JSON: [Choose File]                         │   │
│  │                                                         │   │
│  │  Or paste inputs (one per line):                        │   │
│  │  [                                                  ]   │   │
│  │  [                                                  ]   │   │
│  │                                                         │   │
│  │  ☑ First row is header                                  │   │
│  │  Input column: [content ▼]                              │   │
│  │  Ground truth column (optional): [expected ▼]           │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─ Model Configuration ───────────────────────────────────┐   │
│  │                                                         │   │
│  │  Provider: [OpenRouter ▼]                               │   │
│  │  Model: [gpt-4o-mini ▼]                                 │   │
│  │  Temperature: [0.7____]                                 │   │
│  │  API Key: [________________________________] (saved)    │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [Create Session & Run First Batch →]                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 6.2.2 Behavior

1. **Validation:** Session name, task description, prompt text, and at least 1 input required
2. **Prompt must contain `{input}` placeholder**
3. **API key is stored in Streamlit session state** (not persisted to DB)
4. **On submit:** Create session, create inputs, create v1 prompt, run batch, navigate to Review

#### 6.2.3 Input Parsing

Support three input methods:

1. **CSV Upload:** Parse with pandas, user selects input column and optional ground truth column
2. **JSON Upload:** Expect array of objects or array of strings
3. **Paste:** Split by newlines, each line is one input

### 6.3 Page 2: Review Batch

#### 6.3.1 Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Review Batch - v1                              [3/10 reviewed] │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  ┌─ Input ─────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │  "Your app crashed and deleted my data"                 │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─ Output ────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │  question                                               │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─ Your Feedback ─────────────────────────────────────────┐   │
│  │                                                         │   │
│  │  Is this output correct?                                │   │
│  │  [👍 Good]  [👎 Bad]                                    │   │
│  │                                                         │   │
│  │  Why is this wrong? (helps improve the prompt)          │   │
│  │  [This is clearly a complaint, not a question_____]     │   │
│  │                                                         │   │
│  │  What should it be? (optional)                          │   │
│  │  [complaint_____________________________________]        │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [← Previous]                                      [Next →]    │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Batch Progress:  ✓ 2 good   ✗ 1 bad   ○ 7 pending            │
│                                                                 │
│  [Finish Review & Adapt Prompt →]                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 6.3.2 Behavior

1. Shows one input/output pair at a time
2. Good/Bad selection is required before moving to next
3. "Why is this wrong?" field shown only when Bad is selected
4. Progress bar updates in real-time
5. "Adapt Prompt" button enabled when at least 1 feedback exists
6. Navigation: Previous/Next cycle through batch

### 6.4 Page 3: Adapt

#### 6.4.1 Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Proposed Changes                                               │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  ┌─ Feedback Summary ──────────────────────────────────────┐   │
│  │                                                         │   │
│  │  ✓ 4 outputs marked good                                │   │
│  │  ✗ 6 outputs marked bad                                 │   │
│  │                                                         │   │
│  │  Common issues identified:                              │   │
│  │  • Complaints phrased as questions misclassified        │   │
│  │  • "Other" category used too broadly                    │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─ What GEPA Changed ─────────────────────────────────────┐   │
│  │                                                         │   │
│  │  Analysis:                                              │   │
│  │  The prompt lacks guidance on distinguishing complaints │   │
│  │  from questions. Users often express complaints in      │   │
│  │  question form (e.g., "Can I get a refund?").           │   │
│  │                                                         │   │
│  │  Changes:                                               │   │
│  │  • Added explicit guidelines for each category          │   │
│  │  • Clarified that complaints can be question-form       │   │
│  │  • Added examples of edge cases                         │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─ Diff View ─────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │    Classify the following customer message into:        │   │
│  │    complaint, question, praise, or other.               │   │
│  │                                                         │   │
│  │  + Guidelines:                                          │   │
│  │  + - "complaint" = frustration or dissatisfaction,      │   │
│  │  +   even if phrased as a question                      │   │
│  │  + - "question" = genuine info-seeking, neutral tone    │   │
│  │  + - "praise" = positive feedback or compliment         │   │
│  │  + - "other" = greetings, off-topic, unclear            │   │
│  │                                                         │   │
│  │    Message: {input}                                     │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [✓ Accept]    [✎ Edit & Accept]    [✗ Reject]                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 6.4.2 Diff View Formatting

Use unified diff format with color coding:
- **Green background / '+' prefix:** Added lines
- **Red background / '-' prefix:** Removed lines
- **No background:** Unchanged context lines

Implementation using Python's `difflib`:

```python
import difflib

def generate_diff(old_prompt: str, new_prompt: str) -> List[dict]:
    """Generate a structured diff for UI display."""
    differ = difflib.unified_diff(
        old_prompt.splitlines(keepends=True),
        new_prompt.splitlines(keepends=True),
        lineterm=''
    )
    
    result = []
    for line in differ:
        if line.startswith('+') and not line.startswith('+++'):
            result.append({'type': 'added', 'text': line[1:]})
        elif line.startswith('-') and not line.startswith('---'):
            result.append({'type': 'removed', 'text': line[1:]})
        elif line.startswith(' '):
            result.append({'type': 'unchanged', 'text': line[1:]})
    
    return result
```

#### 6.4.3 Behavior

1. **Accept:** Creates new PromptVersion with status='accepted', navigates to Compare
2. **Edit & Accept:** Opens editable text area with proposed prompt, then Accept flow
3. **Reject:** Creates new PromptVersion with status='rejected', returns to Review

### 6.5 Page 4: Compare

#### 6.5.1 Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Compare: v1 → v2                                               │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Same inputs, different prompt versions. Which is better?       │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ INPUT              │ v1 OUTPUT    │ v2 OUTPUT    │      │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ "Your app crashed  │ question     │ complaint    │      │   │
│  │  and deleted..."   │              │              │      │   │
│  │                    │              │              │      │   │
│  │     [v1 Better]  [Same]  [v2 Better ✓]                  │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ "Can I get a       │ question     │ complaint    │      │   │
│  │  refund?"          │              │              │      │   │
│  │                    │              │              │      │   │
│  │     [v1 Better]  [Same]  [v2 Better ✓]                  │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ "How do I reset    │ question     │ question     │      │   │
│  │  my password?"     │              │              │      │   │
│  │                    │              │              │      │   │
│  │     [v1 Better]  [Same ✓]  [v2 Better]                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│  Summary:                                                       │
│  • v2 better: 6 inputs                                          │
│  • Same: 3 inputs                                               │
│  • v1 better: 1 input                                           │
│                                                                 │
│  [Keep v2 & Continue →]           [Revert to v1]               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 6.5.2 Behavior

1. Re-runs current batch with both old and new prompt versions
2. Comparison is required for each row before proceeding
3. "Keep v2 & Continue": Sets v2 as current, navigates to Review for next batch
4. "Revert to v1": Discards v2, returns to Review with v1

### 6.6 Page 5: History & Export

#### 6.6.1 Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Session History                                                │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Session: Customer Classifier                                   │
│  Created: Dec 8, 2025                                           │
│  Inputs: 47   |   Versions: 5   |   Current: v4                 │
│                                                                 │
│  ┌─ Version Timeline ──────────────────────────────────────┐   │
│  │                                                         │   │
│  │   v1 ──●── v2 ──●── v3 ──●── v4 (current)              │   │
│  │              │                                          │   │
│  │           rejected                                      │   │
│  │            v2.1                                         │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─ Version Details ───────────────────────────────────────┐   │
│  │                                                         │   │
│  │  v4 (current) - Accepted                                │   │
│  │  Created: 2 hours ago                                   │   │
│  │                                                         │   │
│  │  Changes from v3:                                       │   │
│  │  "Added explicit handling for sarcastic messages..."    │   │
│  │                                                         │   │
│  │  Performance: 9/10 correct on last batch                │   │
│  │                                                         │   │
│  │  [View Full Prompt]  [Compare with v3]  [Revert to v4]  │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  [Export Prompt (Markdown)]  [Export Session (JSON)]           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 6.6.2 Export Formats

**Markdown Export (prompt only):**

```markdown
# Customer Classifier - v4

## Prompt

```
Classify the following customer message into:
complaint, question, praise, or other.

Guidelines:
- "complaint" = frustration or dissatisfaction...
...

Message: {input}
```

## Metadata
- Task: Classify customer messages into categories
- Version: 4
- Created: 2025-12-08
- Model: gpt-4o-mini
```

**JSON Export (full session):**

```json
{
  "session": {
    "id": "abc-123",
    "name": "Customer Classifier",
    "task_description": "Classify customer messages...",
    "created_at": "2025-12-08T10:00:00Z"
  },
  "versions": [
    {
      "version_number": 1,
      "prompt_text": "...",
      "status": "accepted",
      "mutation_explanation": null
    }
  ],
  "inputs": [...],
  "results": [...]
}
```

---

## 7. API Contracts

### 7.1 SessionManager

```python
class SessionManager:
    def create_session(
        self,
        name: str,
        task_description: str,
        output_description: Optional[str],
        model_provider: str,
        model_name: str,
        model_temperature: float = 0.7,
        batch_size: int = 10
    ) -> Session:
        """Create a new session. Returns the created Session object."""
        ...
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve a session by ID. Returns None if not found."""
        ...
    
    def list_sessions(
        self,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Session]:
        """List sessions, optionally filtered by status."""
        ...
    
    def update_session(
        self,
        session_id: str,
        **kwargs
    ) -> Session:
        """Update session fields. Returns updated Session."""
        ...
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all related data. Returns success."""
        ...
```

### 7.2 PromptManager

```python
class PromptManager:
    def create_version(
        self,
        session_id: str,
        prompt_text: str,
        parent_version_id: Optional[str] = None,
        mutation_explanation: Optional[str] = None,
        status: str = 'proposed'
    ) -> PromptVersion:
        """Create a new prompt version. Auto-increments version_number."""
        ...
    
    def get_current_version(self, session_id: str) -> Optional[PromptVersion]:
        """Get the latest accepted version for a session."""
        ...
    
    def get_version_history(
        self,
        session_id: str
    ) -> List[PromptVersion]:
        """Get all versions for a session, ordered by version_number."""
        ...
    
    def update_version_status(
        self,
        version_id: str,
        status: str  # 'proposed', 'accepted', 'rejected'
    ) -> PromptVersion:
        """Update the status of a version."""
        ...
    
    def get_diff(
        self,
        old_version_id: str,
        new_version_id: str
    ) -> List[dict]:
        """Generate structured diff between two versions."""
        ...
```

### 7.3 RunManager

```python
class RunManager:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
    
    def run_batch(
        self,
        prompt_version_id: str,
        input_ids: List[str],
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> List[RunResult]:
        """
        Run a prompt version on a batch of inputs.
        Calls on_progress(completed, total) after each completion.
        """
        ...
    
    def get_results_for_version(
        self,
        prompt_version_id: str
    ) -> List[RunResult]:
        """Get all results for a specific prompt version."""
        ...
    
    def update_feedback(
        self,
        result_id: str,
        human_feedback: str,  # 'good' or 'bad'
        feedback_reason: Optional[str] = None,
        human_correction: Optional[str] = None
    ) -> RunResult:
        """Update human feedback on a result."""
        ...
    
    def update_comparison(
        self,
        result_id: str,
        comparison_result: str  # 'better', 'worse', 'same'
    ) -> RunResult:
        """Update comparison result."""
        ...
```

### 7.4 LLMClient

```python
class LLMClient:
    def __init__(
        self,
        provider: str,
        api_key: str,
        default_model: str,
        default_temperature: float = 0.7
    ):
        """Initialize LLM client with provider configuration."""
        ...
    
    def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: int = 2048
    ) -> LLMResponse:
        """
        Execute a completion request.
        Returns LLMResponse with text, tokens, latency.
        """
        ...

@dataclass
class LLMResponse:
    text: str
    tokens_used: int
    latency_ms: int
    model: str
```

### 7.5 InputManager

```python
class InputManager:
    def create_inputs(
        self,
        session_id: str,
        inputs: List[dict]  # [{"content": "...", "ground_truth": "..."}]
    ) -> List[Input]:
        """Bulk create inputs for a session."""
        ...
    
    def get_inputs(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Input]:
        """Get inputs for a session with pagination."""
        ...
    
    def get_batch(
        self,
        session_id: str,
        batch_size: int,
        exclude_ids: List[str] = []
    ) -> List[Input]:
        """Get a batch of inputs, excluding already-processed ones."""
        ...
```

---

## 8. Implementation Plan

### 8.1 Phase Overview

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| 1. Foundation | 2 days | Database models, basic Streamlit skeleton, project structure |
| 2. Core Loop | 2 days | LLM client, batch execution, feedback collection UI |
| 3. GEPA Integration | 3 days | GEPA adapter, mutation proposal, diff view |
| 4. Comparison & History | 2 days | Side-by-side comparison, version timeline, export |
| 5. Polish | 1 day | Error handling, UX refinements, documentation |

**Total estimated duration: 10 working days**

### 8.2 Phase 1: Foundation (Days 1-2)

#### 8.2.1 Objectives
- Set up project structure and dependencies
- Implement database models with SQLModel
- Create basic Streamlit application with navigation
- Implement SessionManager and basic CRUD operations

#### 8.2.2 Tasks
1. Initialize project with pyproject.toml and requirements.txt
2. Create directory structure as specified in Section 3.4
3. Implement all SQLModel entities (Section 4)
4. Create database.py with connection management
5. Implement SessionManager class
6. Create Streamlit main.py with page navigation
7. Build Setup page UI (forms only, no backend wiring)

#### 8.2.3 Acceptance Criteria
- [ ] Can create and list sessions via SessionManager
- [ ] Database persists between application restarts
- [ ] Setup page renders correctly with all form fields
- [ ] Navigation between pages works

### 8.3 Phase 2: Core Loop (Days 3-4)

#### 8.3.1 Objectives
- Implement LLM client with LiteLLM
- Build input upload and parsing
- Execute prompts on batches
- Collect and store human feedback

#### 8.3.2 Tasks
1. Implement LLMClient class with OpenRouter support
2. Add input parsing (CSV, JSON, plain text)
3. Implement PromptManager for version CRUD
4. Implement RunManager for batch execution
5. Wire Setup page to create session + inputs + v1 prompt
6. Build Review page with feedback card component
7. Implement feedback storage and retrieval

#### 8.3.3 Acceptance Criteria
- [ ] Can upload inputs via CSV, JSON, or paste
- [ ] LLM client successfully calls OpenRouter API
- [ ] Batch execution runs and stores results
- [ ] Feedback can be submitted and persisted

### 8.4 Phase 3: GEPA Integration (Days 5-7)

#### 8.4.1 Objectives
- Integrate GEPA package
- Build InteractiveGEPAAdapter
- Implement mutation proposal flow
- Create diff viewer component

#### 8.4.2 Tasks
1. Install and configure gepa package
2. Implement FeedbackConverter (human feedback → GEPA format)
3. Implement InteractiveGEPAAdapter with single-iteration control
4. Build reflection prompt template
5. Implement response parsing for mutations
6. Create diff_viewer.py component using difflib
7. Build Adapt page with proposal display
8. Wire Accept/Edit/Reject buttons to state changes

#### 8.4.3 Acceptance Criteria
- [ ] GEPA proposes sensible prompt improvements based on feedback
- [ ] Diff view clearly shows changes with color coding
- [ ] Accept creates new version with status='accepted'
- [ ] Reject creates new version with status='rejected'
- [ ] Edit allows modification before accepting

### 8.5 Phase 4: Comparison & History (Days 8-9)

#### 8.5.1 Objectives
- Build side-by-side comparison view
- Implement version timeline visualization
- Create export functionality

#### 8.5.2 Tasks
1. Implement comparison batch execution (old vs new)
2. Build comparison_table.py component
3. Build Compare page with voting UI
4. Implement version timeline visualization
5. Build History page with version details
6. Implement Markdown export
7. Implement JSON export

#### 8.5.3 Acceptance Criteria
- [ ] Same inputs shown with outputs from both versions
- [ ] Comparison votes are stored and summarized
- [ ] Version timeline displays lineage correctly
- [ ] Exports produce valid Markdown and JSON files

### 8.6 Phase 5: Polish (Day 10)

#### 8.6.1 Objectives
- Add comprehensive error handling
- Improve UX based on testing
- Write documentation

#### 8.6.2 Tasks
1. Add try/catch blocks and user-friendly error messages
2. Add loading spinners for LLM calls
3. Add confirmation dialogs for destructive actions
4. Test edge cases (empty inputs, API failures, etc.)
5. Write README with setup instructions
6. Add inline help text to UI

#### 8.6.3 Acceptance Criteria
- [ ] No unhandled exceptions in normal usage
- [ ] User sees feedback during long operations
- [ ] README is sufficient for new developer onboarding

---

## 9. Testing Strategy

### 9.1 Unit Tests

Unit tests cover individual components in isolation.

#### 9.1.1 Models (test_models.py)
- Session creation with all required fields
- Input creation with optional ground truth
- PromptVersion lineage (parent_version_id)
- RunResult feedback updates

#### 9.1.2 GEPA Adapter (test_gepa_adapter.py)
- FeedbackConverter produces correct format
- Reflection prompt includes all feedback items
- Response parsing extracts prompt and explanation
- Accept/reject update internal state correctly

#### 9.1.3 LLM Client (test_llm_client.py)
- Client initializes with correct provider config
- Complete returns LLMResponse with all fields
- Handles API errors gracefully
- Respects rate limits

### 9.2 Integration Tests

Integration tests verify component interactions.

- Session creation flows through to database
- Batch execution stores all results
- Feedback triggers GEPA and produces valid mutation
- Version acceptance updates all related state

### 9.3 End-to-End Tests

E2E tests simulate full user workflows.

- Create session → upload inputs → run batch → provide feedback → adapt → compare → export
- Test with real LLM API (use cheap model like gpt-4o-mini)
- Verify exported files are valid and complete

### 9.4 Test Data

Provide sample test data for development and testing:

**Sample inputs for classification task:**

| Input | Expected Output |
|-------|-----------------|
| Your app crashed and deleted my data | complaint |
| How do I reset my password? | question |
| This is the best app I've ever used! | praise |
| Can I get a refund? | complaint |
| What are your business hours? | question |
| The new update is terrible | complaint |
| Thanks for the quick response! | praise |
| Hello | other |
| I've been waiting 3 weeks for support | complaint |
| Do you offer student discounts? | question |

---

## 10. Deployment

### 10.1 Local Development

```bash
# Clone repository
git clone <repo-url>
cd prompt-workbench

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run application
streamlit run app/main.py
```

### 10.2 Requirements.txt

```
streamlit>=1.28.0
sqlmodel>=0.0.14
litellm>=1.0.0
gepa>=0.1.0
pydantic>=2.0.0
python-dotenv>=1.0.0
pandas>=2.0.0
```

### 10.3 Environment Variables

Create a `.env` file or set environment variables:

```bash
# Required
OPENROUTER_API_KEY=sk-or-...

# Optional
OPENAI_API_KEY=sk-...              # If using OpenAI directly
DATABASE_PATH=./data/workbench.db  # Default location
DEFAULT_MODEL=gpt-4o-mini
REFLECTION_MODEL=gpt-4o            # Model for GEPA reflection
```

### 10.4 Database Location

SQLite database is stored at `./data/workbench.db` by default. This can be configured via `DATABASE_PATH` environment variable. The data directory is created automatically if it doesn't exist.

---

## 11. Appendices

### 11.1 Appendix A: Sample Classification Task

**Task Description:**
Classify customer messages into: complaint, question, praise, other

**Initial Prompt (v1):**
```
Classify the following customer message into one of these categories:
complaint, question, praise, other

Message: {input}

Category:
```

**Sample Inputs:**

| Input | Expected Output |
|-------|-----------------|
| Your app crashed and deleted my data | complaint |
| How do I reset my password? | question |
| This is the best app I've ever used! | praise |
| Can I get a refund? | complaint |
| What are your business hours? | question |
| The new update is terrible | complaint |
| Thanks for the quick response! | praise |
| Hello | other |
| I've been waiting 3 weeks for support | complaint |
| Do you offer student discounts? | question |

### 11.2 Appendix B: Sample Extraction Task

**Task Description:**
Extract product information from e-commerce listings

**Initial Prompt (v1):**
```
Extract the following information from this product listing:
- Product name
- Price
- Brand

Return as JSON.

Listing: {input}
```

**Expected Output Format:**
```json
{
  "product_name": "Wireless Bluetooth Headphones",
  "price": "$49.99",
  "brand": "SoundMax"
}
```

### 11.3 Appendix C: GEPA Reflection Prompt Template

Full template used for GEPA reflection:

```
You are an expert prompt engineer analyzing a prompt that needs improvement.

TASK DESCRIPTION:
{task_description}

CURRENT PROMPT:
"""
{current_prompt}
"""

HUMAN FEEDBACK ON RECENT OUTPUTS:

=== GOOD OUTPUTS (the prompt got these right) ===
{good_examples}

=== BAD OUTPUTS (the prompt got these wrong) ===
{bad_examples}

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
"""
[The complete improved prompt]
"""
```

### 11.4 Appendix D: Error Handling Reference

| Error Type | User Message | Recovery Action |
|------------|--------------|-----------------|
| API rate limit | "Rate limit reached. Please wait a moment and try again." | Show retry button with countdown |
| API authentication | "Invalid API key. Please check your settings." | Navigate to settings |
| Network error | "Connection failed. Please check your internet." | Show retry button |
| Invalid input format | "Could not parse input file. Please check format." | Show format examples |
| Empty batch | "No inputs to process. Please add inputs first." | Navigate to setup |
| GEPA parse error | "Could not parse improvement suggestion. Using fallback." | Show raw response, allow manual edit |

### 11.5 Appendix E: Glossary

| Term | Definition |
|------|------------|
| Session | A prompt refinement project containing inputs, versions, and results |
| Prompt Version | A specific iteration of the prompt text |
| Batch | A subset of inputs processed together (default: 10) |
| Mutation | A proposed change to the prompt generated by GEPA |
| Pareto Frontier | Set of non-dominated prompt candidates maintained by GEPA |
| Ground Truth | The expected/correct output for an input |
| Feedback | Human judgment (good/bad) on an output with optional explanation |
| Reflection | GEPA's process of analyzing feedback to propose improvements |
| Diff | Visual representation of changes between prompt versions |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | December 2025 | - | Initial specification |

---

*— End of Document —*
