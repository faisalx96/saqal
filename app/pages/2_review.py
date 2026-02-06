"""Review page for providing feedback on prompt outputs."""

import streamlit as st

from app.state import (
    init_state,
    get_current_session_id,
    get_batch_index,
    set_batch_index,
    get_batch_input_ids,
    set_batch_input_ids,
    get_batch_results,
    set_batch_results,
    get_api_key,
    set_api_key,
    get_state,
    set_state,
)
from app.components.feedback_card import render_feedback_card, render_feedback_summary
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

st.title("Review Batch")

# Check for active session
session_id = get_current_session_id()

if not session_id:
    st.warning("No active session. Please create a session first.")
    st.page_link("pages/1_setup.py", label="Go to Setup")
    st.stop()

# Load session data
session_manager = SessionManager()
input_manager = InputManager()
prompt_manager = PromptManager()

session = session_manager.get_session(session_id)
if not session:
    st.error("Session not found.")
    st.stop()

current_version = prompt_manager.get_current_version(session_id)
if not current_version:
    # Try to get any version (might be first version)
    versions = prompt_manager.get_version_history(session_id)
    if versions:
        current_version = versions[-1]
    else:
        st.error("No prompt version found.")
        st.stop()

# Header
st.markdown(f"**Session:** {session.name}")
st.markdown(f"**Version:** v{current_version.version_number}")

# Check for API key - show input if not set
api_key = get_api_key()
if not api_key:
    st.warning("API key required to run prompts.")
    api_key_input = st.text_input(
        "Enter your API Key",
        type="password",
        help="Your OpenRouter or OpenAI API key",
    )
    if api_key_input:
        set_api_key(api_key_input)
        st.rerun()
    st.stop()

# Initialize LLM client
llm_client = LLMClient(
    provider=session.model_provider,
    api_key=api_key,
    default_model=session.model_name,
    default_temperature=session.model_temperature,
)

# Initialize trace logger for MLflow memory
init_mlflow()
if not session.mlflow_experiment_id:
    experiment_id = get_or_create_experiment(session.id, session.name)
    session_manager.update_session(session.id, mlflow_experiment_id=experiment_id)
    session = session_manager.get_session(session_id)

trace_logger = None
if session.mlflow_experiment_id:
    try:
        trace_logger = TraceLogger(experiment_id=session.mlflow_experiment_id)
    except Exception:
        pass  # Tracing is optional

run_manager = RunManager(llm_client, trace_logger=trace_logger)

# Check if this is a resumed session
is_resumed = get_state("session_resumed", False)
if is_resumed:
    set_state("session_resumed", False)  # Clear the flag
    st.info(f"Resumed session: {session.name}")

# Get or initialize batch
batch_input_ids = get_batch_input_ids()

# For resumed sessions or empty batch, load inputs that need review
if not batch_input_ids:
    # Get all results for current version to find what's been done
    existing_results = run_manager.get_results_for_version(current_version.id)
    existing_input_ids = {r.input_id for r in existing_results}

    # Find inputs that haven't been run yet OR have pending feedback
    all_inputs = input_manager.get_inputs(session_id)

    # First, prioritize inputs with existing results that need feedback
    inputs_with_pending_feedback = [
        r.input_id for r in existing_results
        if r.human_feedback is None
    ]

    if inputs_with_pending_feedback:
        # Resume with inputs that have pending feedback
        batch_input_ids = inputs_with_pending_feedback[:session.batch_size]
    else:
        # Get new inputs that haven't been processed
        unprocessed_inputs = [
            inp.id for inp in all_inputs
            if inp.id not in existing_input_ids
        ]

        if unprocessed_inputs:
            batch_input_ids = unprocessed_inputs[:session.batch_size]
        else:
            # All inputs processed - show completed message or allow re-review
            completed_inputs = [inp.id for inp in all_inputs]
            if completed_inputs:
                st.success("All inputs have been reviewed!")
                st.markdown("You can:")
                st.markdown("- Go to **Adapt** to improve the prompt based on feedback")
                st.markdown("- Go to **History** to export or view versions")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Go to Adapt", type="primary", use_container_width=True):
                        st.switch_page("pages/3_adapt.py")
                with col2:
                    if st.button("Re-review All", use_container_width=True):
                        batch_input_ids = completed_inputs[:session.batch_size]
                        set_batch_input_ids(batch_input_ids)
                        st.rerun()
                st.stop()

    set_batch_input_ids(batch_input_ids)

if not batch_input_ids:
    st.info("No inputs available for review. Add inputs in Setup.")
    st.stop()

# Run prompts on any inputs that don't have results yet
existing_results = run_manager.get_results_for_version(current_version.id)
existing_input_ids = {r.input_id for r in existing_results}
needs_run = [iid for iid in batch_input_ids if iid not in existing_input_ids]

if needs_run:
    with st.spinner(f"Running prompt on {len(needs_run)} inputs..."):
        progress_bar = st.progress(0)

        def on_progress(completed, total):
            progress_bar.progress(completed / total)

        new_results = run_manager.run_batch(
            prompt_version_id=current_version.id,
            input_ids=needs_run,
            on_progress=on_progress,
        )
        # Refresh existing results
        existing_results = run_manager.get_results_for_version(current_version.id)

# Build results dict for this batch
batch_results_dict = {
    r.id: r for r in existing_results
    if r.input_id in batch_input_ids
}
set_batch_results(batch_results_dict)

# Build input_id -> result mapping
input_to_result = {}
for result in batch_results_dict.values():
    input_to_result[result.input_id] = result

# Navigation
current_index = get_batch_index()
total = len(batch_input_ids)

if current_index >= total:
    current_index = total - 1
    set_batch_index(current_index)
if current_index < 0:
    current_index = 0
    set_batch_index(current_index)

# Feedback summary
good_count = sum(1 for r in input_to_result.values() if r.human_feedback == "good")
bad_count = sum(1 for r in input_to_result.values() if r.human_feedback == "bad")
pending_count = sum(1 for r in input_to_result.values() if r.human_feedback is None)

render_feedback_summary(good_count, bad_count, pending_count)

# Run auto-judge suggestions if judge is aligned
judge_manager = get_state("judge_manager")
judge_suggestions = get_state("judge_suggestions", {})

if judge_manager and judge_manager.is_aligned:
    for result in batch_results_dict.values():
        if result.id not in judge_suggestions and result.human_feedback is None:
            input_obj = input_manager.get_input(result.input_id)
            if input_obj:
                suggestion = judge_manager.suggest(
                    input_content=input_obj.content,
                    output=result.output,
                )
                if suggestion:
                    judge_suggestions[result.id] = {
                        "is_good": suggestion.is_good,
                        "rationale": suggestion.rationale,
                    }
    set_state("judge_suggestions", judge_suggestions)

st.markdown("---")

# Current item
if batch_input_ids and current_index < len(batch_input_ids):
    current_input_id = batch_input_ids[current_index]
    current_input = input_manager.get_input(current_input_id)
    current_result = input_to_result.get(current_input_id)

    if current_input and current_result:
        st.markdown(f"### Item {current_index + 1} of {total}")

        # Get auto-judge suggestion for this result (if available)
        current_suggestion = judge_suggestions.get(current_result.id)

        # Render feedback card
        feedback_result = render_feedback_card(
            input_content=current_input.content,
            output=current_result.output,
            ground_truth=current_input.ground_truth,
            current_feedback=current_result.human_feedback,
            feedback_reason=current_result.feedback_reason,
            human_correction=current_result.human_correction,
            judge_suggestion=current_suggestion,
            card_key=f"feedback_{current_input_id}",
        )

        # Save feedback if changed
        if feedback_result["feedback"] and (
            feedback_result["feedback"] != current_result.human_feedback
            or feedback_result["reason"] != current_result.feedback_reason
            or feedback_result["correction"] != current_result.human_correction
        ):
            updated = run_manager.update_feedback(
                result_id=current_result.id,
                human_feedback=feedback_result["feedback"],
                feedback_reason=feedback_result["reason"],
                human_correction=feedback_result["correction"],
            )
            if updated:
                # Update local state
                batch_results_dict[updated.id] = updated
                set_batch_results(batch_results_dict)
                input_to_result[current_input_id] = updated
                st.rerun()
    elif current_input and not current_result:
        st.warning("Result not found for this input. Try refreshing.")
        if st.button("Refresh"):
            set_batch_results({})
            st.rerun()

# Navigation buttons
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    if st.button("Previous", disabled=current_index == 0, use_container_width=True):
        set_batch_index(current_index - 1)
        st.rerun()

with col2:
    # Show position
    st.markdown(
        f"<div style='text-align: center;'>{current_index + 1} / {total}</div>",
        unsafe_allow_html=True,
    )

with col3:
    if st.button(
        "Next",
        disabled=current_index >= total - 1,
        use_container_width=True,
    ):
        set_batch_index(current_index + 1)
        st.rerun()

# Adapt button
st.markdown("---")

has_feedback = good_count + bad_count > 0

if st.button(
    "Finish Review & Adapt Prompt",
    type="primary",
    disabled=not has_feedback,
    use_container_width=True,
):
    st.switch_page("pages/3_adapt.py")

if not has_feedback:
    st.info("Provide feedback on at least one item to adapt the prompt.")

# Quick jump
with st.expander("Quick Jump"):
    cols = st.columns(min(10, total))
    for i, input_id in enumerate(batch_input_ids):
        result = input_to_result.get(input_id)
        status = "⬜"
        if result:
            if result.human_feedback == "good":
                status = "✅"
            elif result.human_feedback == "bad":
                status = "❌"

        col_idx = i % len(cols)
        with cols[col_idx]:
            if st.button(f"{status} {i+1}", key=f"jump_{i}", use_container_width=True):
                set_batch_index(i)
                st.rerun()

# Load more inputs option
st.markdown("---")
with st.expander("Batch Options"):
    total_inputs = input_manager.count_inputs(session_id)
    reviewed_in_session = len(existing_input_ids)

    st.markdown(f"**Total inputs:** {total_inputs}")
    st.markdown(f"**Processed:** {reviewed_in_session}")
    st.markdown(f"**Current batch:** {len(batch_input_ids)}")

    if reviewed_in_session < total_inputs:
        remaining = total_inputs - reviewed_in_session
        if st.button(f"Load Next Batch ({min(remaining, session.batch_size)} inputs)"):
            # Clear current batch and load new one
            set_batch_input_ids([])
            set_batch_results({})
            set_batch_index(0)
            st.rerun()
