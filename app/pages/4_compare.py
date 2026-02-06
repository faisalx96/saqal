"""Compare page for side-by-side version comparison."""

import streamlit as st

from app.state import (
    init_state,
    get_current_session_id,
    get_batch_input_ids,
    set_batch_input_ids,
    get_api_key,
    get_state,
    set_state,
    set_batch_results,
    set_batch_index,
)
from app.components.comparison_table import (
    ComparisonRow,
    render_comparison_table,
    render_comparison_summary,
)
from core.database import init_db
from core.session_manager import SessionManager
from core.input_manager import InputManager
from core.prompt_manager import PromptManager
from core.run_manager import RunManager
from llm.client import LLMClient

# Initialize
init_state()
init_db()

st.title("Compare Versions")

# Check for active session
session_id = get_current_session_id()

if not session_id:
    st.warning("No active session. Please create a session first.")
    st.page_link("pages/1_setup.py", label="Go to Setup")
    st.stop()

# Check for comparison mode
old_version_id = get_state("old_version_id")
new_version_id = get_state("new_version_id")

if not old_version_id or not new_version_id:
    st.warning("No versions to compare. Please complete a prompt adaptation first.")
    st.page_link("pages/3_adapt.py", label="Go to Adapt")
    st.stop()

# Load session data
session_manager = SessionManager()
input_manager = InputManager()
prompt_manager = PromptManager()

session = session_manager.get_session(session_id)
if not session:
    st.error("Session not found.")
    st.stop()

old_version = prompt_manager.get_version(old_version_id)
new_version = prompt_manager.get_version(new_version_id)

if not old_version or not new_version:
    st.error("Version not found.")
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

# Header
st.markdown(f"**Session:** {session.name}")
st.markdown(f"**Comparing:** v{old_version.version_number} → v{new_version.version_number}")

st.markdown("""
Compare the outputs from both prompt versions on the same inputs.
Mark which version produced better results for each input.
""")

# Get batch inputs
batch_input_ids = get_batch_input_ids()

if not batch_input_ids:
    # Get all inputs with results for old version
    old_results = run_manager.get_results_for_version(old_version_id)
    batch_input_ids = [r.input_id for r in old_results]
    set_batch_input_ids(batch_input_ids)

if not batch_input_ids:
    st.info("No inputs to compare.")
    st.stop()

# Run new version on batch if needed
new_results = run_manager.get_results_for_version(new_version_id)
new_result_input_ids = {r.input_id for r in new_results}
needs_run = [iid for iid in batch_input_ids if iid not in new_result_input_ids]

if needs_run:
    with st.spinner(f"Running v{new_version.version_number} on {len(needs_run)} inputs..."):
        progress_bar = st.progress(0)

        def on_progress(completed, total):
            progress_bar.progress(completed / total)

        new_run_results = run_manager.run_batch(
            prompt_version_id=new_version_id,
            input_ids=needs_run,
            on_progress=on_progress,
        )

        # Refresh results
        new_results = run_manager.get_results_for_version(new_version_id)

# Build comparison rows
old_results = run_manager.get_results_for_version(old_version_id)
old_result_map = {r.input_id: r for r in old_results}
new_result_map = {r.input_id: r for r in new_results}

comparison_rows = []
for input_id in batch_input_ids:
    input_obj = input_manager.get_input(input_id)
    old_result = old_result_map.get(input_id)
    new_result = new_result_map.get(input_id)

    if input_obj and old_result and new_result:
        comparison_rows.append(
            ComparisonRow(
                input_id=input_id,
                input_content=input_obj.content,
                old_output=old_result.output,
                new_output=new_result.output,
                old_result_id=old_result.id,
                new_result_id=new_result.id,
                comparison_result=new_result.comparison_result,
            )
        )

if not comparison_rows:
    st.warning("No results to compare.")
    st.stop()

# Count current comparisons
better_count = sum(1 for r in comparison_rows if r.comparison_result == "better")
worse_count = sum(1 for r in comparison_rows if r.comparison_result == "worse")
same_count = sum(1 for r in comparison_rows if r.comparison_result == "same")
pending_count = sum(1 for r in comparison_rows if r.comparison_result is None)

# Summary at top
st.markdown("---")
render_comparison_summary(
    better=better_count,
    worse=worse_count,
    same=same_count,
    old_version_label=f"v{old_version.version_number}",
    new_version_label=f"v{new_version.version_number}",
)

st.markdown("---")

# Render comparison table
comparison_results = render_comparison_table(
    rows=comparison_rows,
    old_version_label=f"v{old_version.version_number}",
    new_version_label=f"v{new_version.version_number}",
)

# Save any new comparisons
for result_id, comparison in comparison_results.items():
    if comparison:
        run_manager.update_comparison(result_id, comparison)
        st.rerun()

# Action buttons
st.markdown("---")

all_compared = pending_count == 0

col1, col2 = st.columns(2)

with col1:
    if st.button(
        f"Keep v{new_version.version_number} & Continue →",
        type="primary",
        use_container_width=True,
        disabled=not all_compared,
    ):
        # Clear comparison state
        set_state("old_version_id", None)
        set_state("new_version_id", None)
        set_state("comparison_mode", False)

        # Clear batch for next iteration
        set_batch_input_ids([])
        set_batch_results({})
        set_batch_index(0)

        st.success(f"Keeping v{new_version.version_number} as current version!")
        st.page_link("pages/2_review.py", label="Continue to Review")

with col2:
    if st.button(
        f"Revert to v{old_version.version_number}",
        use_container_width=True,
    ):
        # Update new version status to rejected
        prompt_manager.update_version_status(new_version_id, "rejected")

        # Clear comparison state
        set_state("old_version_id", None)
        set_state("new_version_id", None)
        set_state("comparison_mode", False)

        st.warning(f"Reverted to v{old_version.version_number}")
        st.page_link("pages/2_review.py", label="Back to Review")

if not all_compared:
    st.info(f"Please compare all {pending_count} remaining items before continuing.")

# Show prompt versions for reference
with st.expander("View Prompt Versions"):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**v{old_version.version_number}**")
        st.code(old_version.prompt_text)
    with col2:
        st.markdown(f"**v{new_version.version_number}**")
        st.code(new_version.prompt_text)
