"""Setup page for creating new refinement sessions."""

import json
import streamlit as st
import pandas as pd
from io import StringIO

from app.state import (
    init_state,
    set_current_session_id,
    set_api_key,
    get_api_key,
    set_batch_input_ids,
    set_batch_results,
)
from core.database import init_db
from core.session_manager import SessionManager
from core.input_manager import InputManager
from core.prompt_manager import PromptManager
from core.run_manager import RunManager
from llm.client import LLMClient
from memory.mlflow_config import init_mlflow, get_or_create_experiment
from memory.trace_logger import TraceLogger

# Initialize
init_state()
init_db()

st.title("Setup New Session")

st.markdown("""
Create a new prompt refinement session. Provide your initial prompt, test inputs,
and model configuration to get started.
""")

# Session info section
st.header("Session Info")

session_name = st.text_input(
    "Session Name",
    placeholder="e.g., Customer Message Classifier",
    help="A descriptive name for this refinement session",
)

task_description = st.text_area(
    "What task is your prompt doing?",
    placeholder="e.g., Classify customer messages into categories: complaint, question, praise, other",
    help="Describe what your prompt should accomplish",
)

output_description = st.text_input(
    "What should the output look like? (optional)",
    placeholder="e.g., One of: complaint, question, praise, other",
    help="Describe the expected output format",
)

# Prompt section
st.header("Your Initial Prompt")

st.markdown("Use `{input}` as a placeholder for where the input should be inserted.")

prompt_text = st.text_area(
    "Prompt Text",
    height=200,
    placeholder="""Classify the following customer message into one of these categories:
complaint, question, praise, other

Message: {input}

Category:""",
    help="Your prompt template. Use {input} where the test input should go.",
)

# Validate prompt has {input}
if prompt_text and "{input}" not in prompt_text:
    st.warning("Your prompt should contain `{input}` as a placeholder for the input.")

# Test inputs section
st.header("Test Inputs")

input_method = st.radio(
    "How would you like to provide inputs?",
    ["Upload CSV/JSON", "Paste text"],
    horizontal=True,
)

inputs_data = []

if input_method == "Upload CSV/JSON":
    uploaded_file = st.file_uploader(
        "Upload file",
        type=["csv", "json"],
        help="CSV or JSON file with test inputs",
    )

    if uploaded_file:
        file_ext = uploaded_file.name.split(".")[-1].lower()

        if file_ext == "csv":
            df = pd.read_csv(uploaded_file)
            st.dataframe(df.head())

            columns = df.columns.tolist()
            input_col = st.selectbox(
                "Input column",
                columns,
                help="Column containing the input text",
            )
            ground_truth_col = st.selectbox(
                "Ground truth column (optional)",
                ["(none)"] + columns,
                help="Column containing expected outputs",
            )

            for _, row in df.iterrows():
                entry = {"content": str(row[input_col])}
                if ground_truth_col != "(none)":
                    entry["ground_truth"] = str(row[ground_truth_col])
                inputs_data.append(entry)

        elif file_ext == "json":
            data = json.load(uploaded_file)
            if isinstance(data, list):
                if data and isinstance(data[0], dict):
                    # List of objects
                    st.json(data[:3])
                    keys = list(data[0].keys()) if data else []
                    input_key = st.selectbox(
                        "Input key",
                        keys,
                        help="Key containing the input text",
                    )
                    ground_truth_key = st.selectbox(
                        "Ground truth key (optional)",
                        ["(none)"] + keys,
                        help="Key containing expected outputs",
                    )

                    for item in data:
                        entry = {"content": str(item.get(input_key, ""))}
                        if ground_truth_key != "(none)":
                            entry["ground_truth"] = str(item.get(ground_truth_key, ""))
                        inputs_data.append(entry)
                else:
                    # List of strings
                    st.json(data[:5])
                    for item in data:
                        inputs_data.append({"content": str(item)})

else:  # Paste text
    pasted_text = st.text_area(
        "Paste inputs (one per line)",
        height=200,
        placeholder="""Your app crashed and deleted my data
How do I reset my password?
This is the best app I've ever used!
Can I get a refund?""",
    )

    if pasted_text:
        lines = [line.strip() for line in pasted_text.split("\n") if line.strip()]
        for line in lines:
            inputs_data.append({"content": line})

if inputs_data:
    st.success(f"Found {len(inputs_data)} inputs")

# Model configuration
st.header("Model Configuration")

col1, col2 = st.columns(2)

with col1:
    provider = st.selectbox(
        "Provider",
        ["openrouter", "openai"],
        help="LLM provider to use",
    )

with col2:
    model_options = {
        "openrouter": [
            "openai/gpt-4o-mini",
            "openai/gpt-4o",
            "anthropic/claude-3-haiku",
            "anthropic/claude-3-sonnet",
            "google/gemini-pro",
        ],
        "openai": [
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ],
    }
    model_name = st.selectbox(
        "Model",
        model_options.get(provider, ["gpt-4o-mini"]),
        help="Model to use for running prompts",
    )

col3, col4 = st.columns(2)

with col3:
    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=2.0,
        value=0.7,
        step=0.1,
        help="Sampling temperature (higher = more creative)",
    )

with col4:
    batch_size = st.number_input(
        "Batch Size",
        min_value=1,
        max_value=50,
        value=10,
        help="Number of inputs to review per batch",
    )

# API Key
api_key = st.text_input(
    "API Key",
    type="password",
    value=get_api_key(),
    help="Your API key (stored in session only, not persisted)",
)

if api_key:
    set_api_key(api_key)

# Validation
can_submit = all([
    session_name,
    task_description,
    prompt_text,
    "{input}" in prompt_text,
    len(inputs_data) > 0,
    api_key,
])

# Submit button
st.markdown("---")

if st.button(
    "Create Session & Run First Batch",
    type="primary",
    disabled=not can_submit,
    use_container_width=True,
):
    if not can_submit:
        st.error("Please fill in all required fields.")
    else:
        with st.spinner("Creating session..."):
            try:
                # Create session
                session_manager = SessionManager()
                session = session_manager.create_session(
                    name=session_name,
                    task_description=task_description,
                    output_description=output_description or None,
                    model_provider=provider,
                    model_name=model_name,
                    model_temperature=temperature,
                    batch_size=batch_size,
                )

                # Create inputs
                input_manager = InputManager()
                created_inputs = input_manager.create_inputs(
                    session_id=session.id,
                    inputs=inputs_data,
                )

                # Create initial prompt version (v1)
                prompt_manager = PromptManager()
                version = prompt_manager.create_version(
                    session_id=session.id,
                    prompt_text=prompt_text,
                    status="accepted",  # v1 is auto-accepted
                )

                # Create MLflow experiment for this session
                init_mlflow()
                experiment_id = get_or_create_experiment(session.id, session.name)
                session_manager.update_session(
                    session.id, mlflow_experiment_id=experiment_id
                )

                st.success(f"Created session with {len(created_inputs)} inputs!")

                # Get first batch
                batch_inputs = input_manager.get_batch(
                    session_id=session.id,
                    batch_size=batch_size,
                )
                batch_ids = [inp.id for inp in batch_inputs]

                # Run first batch
                st.info("Running prompt on first batch...")
                progress_bar = st.progress(0)
                status_text = st.empty()

                llm_client = LLMClient(
                    provider=provider,
                    api_key=api_key,
                    default_model=model_name,
                    default_temperature=temperature,
                )

                trace_logger = TraceLogger(experiment_id=experiment_id)
                run_manager = RunManager(llm_client, trace_logger=trace_logger)

                def on_progress(completed, total):
                    progress_bar.progress(completed / total)
                    status_text.text(f"Processing {completed}/{total}...")

                results = run_manager.run_batch(
                    prompt_version_id=version.id,
                    input_ids=batch_ids,
                    on_progress=on_progress,
                )

                progress_bar.progress(1.0)
                status_text.text(f"Completed {len(results)} inputs!")

                # Store state for review page
                set_current_session_id(session.id)
                set_batch_input_ids(batch_ids)
                set_batch_results({r.id: r for r in results})

                st.success("Ready for review! Go to the Review page to provide feedback.")

                # Offer to navigate
                st.page_link("pages/2_review.py", label="Go to Review Page")

            except Exception as e:
                st.error(f"Error creating session: {str(e)}")
                raise e

# Show validation messages
if not can_submit:
    missing = []
    if not session_name:
        missing.append("Session name")
    if not task_description:
        missing.append("Task description")
    if not prompt_text:
        missing.append("Prompt text")
    elif "{input}" not in prompt_text:
        missing.append("Prompt must contain {input}")
    if len(inputs_data) == 0:
        missing.append("At least one test input")
    if not api_key:
        missing.append("API key")

    if missing:
        st.info(f"Please provide: {', '.join(missing)}")
