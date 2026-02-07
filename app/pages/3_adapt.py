"""Adapt page for viewing and approving GEPA-proposed prompt changes."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

from app.state import (
    init_state,
    get_current_session_id,
    get_batch_input_ids,
    get_api_key,
    get_state,
    set_state,
)
from app.components.diff_viewer import (
    render_diff_viewer,
    render_changes_summary,
)
from core.database import init_db
from core.session_manager import SessionManager
from core.input_manager import InputManager
from core.prompt_manager import PromptManager
from core.run_manager import RunManager
from llm.client import LLMClient
from gepa_adapter.adapter import InteractiveGEPAAdapter, MutationProposal
from gepa_adapter.feedback_converter import FeedbackItem
from memory.mlflow_config import init_mlflow, get_or_create_experiment
from memory.judge_manager import JudgeManager

# Initialize
init_state()
init_db()

st.title("Adapt Prompt")

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
    st.error("No prompt version found.")
    st.stop()

# Get API key
api_key = get_api_key()
if not api_key:
    st.error("API key not found. Please go to Setup and enter your API key.")
    st.stop()

# Initialize managers
llm_client = LLMClient(
    provider=session.model_provider,
    api_key=api_key,
    default_model=session.model_name,
    default_temperature=session.model_temperature,
)
run_manager = RunManager(llm_client)

# Get feedback from current batch
batch_input_ids = get_batch_input_ids()
results = run_manager.get_results_for_version(current_version.id)

# Filter to results with feedback
feedback_results = [r for r in results if r.human_feedback is not None]

if not feedback_results:
    st.warning("No feedback provided yet. Please review some outputs first.")
    st.page_link("pages/2_review.py", label="Go to Review")
    st.stop()

# Build feedback summary
good_count = sum(1 for r in feedback_results if r.human_feedback == "good")
bad_count = sum(1 for r in feedback_results if r.human_feedback == "bad")

st.markdown(f"**Session:** {session.name}")
st.markdown(f"**Current Version:** v{current_version.version_number}")

# Feedback summary
st.header("Feedback Summary")

col1, col2 = st.columns(2)
with col1:
    st.metric("Good outputs", good_count)
with col2:
    st.metric("Bad outputs", bad_count)

# Show common issues
bad_feedback = [r for r in feedback_results if r.human_feedback == "bad" and r.feedback_reason]
if bad_feedback:
    st.markdown("**Common issues identified:**")
    for r in bad_feedback[:5]:
        st.markdown(f"- {r.feedback_reason}")

st.markdown("---")

# Check for existing proposal or generate new one
proposal_key = f"proposal_{current_version.id}"
proposal = get_state(proposal_key)

if proposal is None:
    # Generate new proposal
    st.header("Generating Improvements...")

    # Step 1: Align judge with MemAlign to extract accumulated principles
    accumulated_principles = ""
    init_mlflow()
    if not session.mlflow_experiment_id:
        experiment_id = get_or_create_experiment(session.id, session.name)
        session_manager.update_session(session.id, mlflow_experiment_id=experiment_id)
        session = session_manager.get_session(session_id)

    if session.mlflow_experiment_id:
        with st.spinner("Aligning judge with accumulated feedback..."):
            try:
                judge_mgr = JudgeManager(
                    model_name=session.model_name,
                    provider=session.model_provider,
                )
                alignment = judge_mgr.align(
                    experiment_id=session.mlflow_experiment_id
                )
                accumulated_principles = alignment.distilled_principles

                # Store for auto-judge use on Review page
                set_state("judge_manager", judge_mgr)
                set_state("alignment_done", True)
                set_state("distilled_principles", accumulated_principles)

                if alignment.trace_count > 0:
                    st.success(
                        f"Aligned with {alignment.trace_count} traces. "
                        f"Extracted principles for prompt improvement."
                    )
            except Exception as e:
                st.warning(f"Memory alignment skipped: {e}")

    # Step 2: Build feedback items and generate GEPA proposal
    with st.spinner("GEPA is analyzing feedback and proposing improvements..."):
        feedback_items = []
        for result in feedback_results:
            input_obj = input_manager.get_input(result.input_id)
            if input_obj:
                feedback_items.append(
                    FeedbackItem(
                        input_content=input_obj.content,
                        output=result.output,
                        is_good=result.human_feedback == "good",
                        reason=result.feedback_reason,
                        correction=result.human_correction,
                    )
                )

        # Create GEPA adapter with accumulated principles from MemAlign
        gepa = InteractiveGEPAAdapter(
            initial_prompt=current_version.prompt_text,
            task_description=session.task_description,
            llm_client=llm_client,
            accumulated_principles=accumulated_principles,
        )

        try:
            proposal = gepa.propose_mutation(feedback_items)
            set_state(proposal_key, proposal)
        except Exception as e:
            st.error(f"Error generating proposal: {str(e)}")
            st.stop()

    st.rerun()

# Display proposal
st.header("Proposed Changes")

# Show what GEPA changed
render_changes_summary(
    analysis=proposal.analysis,
    changes=proposal.changes,
)

st.markdown("---")

# Show diff view
st.header("Diff View")

render_diff_viewer(
    old_prompt=current_version.prompt_text,
    new_prompt=proposal.new_prompt,
)

# Edit mode
edited_prompt_key = f"edited_prompt_{current_version.id}"
show_editor = get_state(f"show_editor_{current_version.id}", False)

if show_editor:
    st.markdown("---")
    st.header("Edit Prompt")

    edited_prompt = st.text_area(
        "Edit the proposed prompt",
        value=get_state(edited_prompt_key, proposal.new_prompt),
        height=300,
        key=f"edit_area_{current_version.id}",
    )
    set_state(edited_prompt_key, edited_prompt)

# Action buttons
st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("Accept", type="primary", use_container_width=True):
        # Get the prompt to use (edited or original proposal)
        final_prompt = get_state(edited_prompt_key, proposal.new_prompt)

        # Create new version
        new_version = prompt_manager.create_version(
            session_id=session_id,
            prompt_text=final_prompt,
            parent_version_id=current_version.id,
            mutation_explanation=proposal.explanation,
            status="accepted",
        )

        st.success(f"Created v{new_version.version_number}!")

        # Clear proposal state
        set_state(proposal_key, None)
        set_state(edited_prompt_key, None)
        set_state(f"show_editor_{current_version.id}", False)

        # Set up comparison
        set_state("old_version_id", current_version.id)
        set_state("new_version_id", new_version.id)
        set_state("comparison_mode", True)

        st.page_link("pages/4_compare.py", label="Go to Compare")

with col2:
    if st.button("Edit & Accept", use_container_width=True):
        set_state(f"show_editor_{current_version.id}", True)
        st.rerun()

with col3:
    if st.button("Reject", use_container_width=True):
        # Create rejected version for history
        rejected_version = prompt_manager.create_version(
            session_id=session_id,
            prompt_text=proposal.new_prompt,
            parent_version_id=current_version.id,
            mutation_explanation=proposal.explanation,
            status="rejected",
        )

        st.warning(f"Rejected proposal (saved as v{rejected_version.version_number} for history)")

        # Clear proposal state
        set_state(proposal_key, None)
        set_state(edited_prompt_key, None)
        set_state(f"show_editor_{current_version.id}", False)

        # Go back to review
        st.page_link("pages/2_review.py", label="Back to Review")

# Show current prompt for reference
with st.expander("View Current Prompt"):
    st.code(current_version.prompt_text)
