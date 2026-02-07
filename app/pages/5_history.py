"""History page for viewing sessions, versions, and exporting."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

from app.state import (
    init_state,
    get_current_session_id,
    set_current_session_id,
    clear_session,
    get_api_key,
    resume_session,
)
from app.components.diff_viewer import render_side_by_side_diff
from core.database import init_db
from core.session_manager import SessionManager
from core.input_manager import InputManager
from core.prompt_manager import PromptManager
from core.run_manager import RunManager
from core.export import export_prompt_markdown, export_session_json
from llm.client import LLMClient

# Initialize
init_state()
init_db()

st.title("Session History")

# Initialize managers
session_manager = SessionManager()
input_manager = InputManager()
prompt_manager = PromptManager()

# Sidebar: Session list
st.sidebar.header("Sessions")

sessions = session_manager.list_sessions()

if not sessions:
    st.info("No sessions yet. Create one from the Setup page.")
    st.page_link("pages/1_setup.py", label="Go to Setup")
    st.stop()

# Session selector
current_session_id = get_current_session_id()
session_options = {s.id: f"{s.name} ({s.status})" for s in sessions}

selected_session_id = st.sidebar.selectbox(
    "Select Session",
    options=list(session_options.keys()),
    format_func=lambda x: session_options[x],
    index=list(session_options.keys()).index(current_session_id) if current_session_id in session_options else 0,
)

if selected_session_id != current_session_id:
    set_current_session_id(selected_session_id)

# Load selected session
session = session_manager.get_session(selected_session_id)
if not session:
    st.error("Session not found.")
    st.stop()

# Session overview
st.header(session.name)

col1, col2, col3, col4 = st.columns(4)

with col1:
    total_inputs = input_manager.count_inputs(session.id)
    st.metric("Inputs", total_inputs)

with col2:
    versions = prompt_manager.get_version_history(session.id)
    st.metric("Versions", len(versions))

with col3:
    current_version = prompt_manager.get_current_version(session.id)
    if current_version:
        st.metric("Current", f"v{current_version.version_number}")
    else:
        st.metric("Current", "v1")

with col4:
    st.metric("Status", session.status)

st.markdown(f"**Task:** {session.task_description}")
st.markdown(f"**Model:** {session.model_provider}/{session.model_name}")
st.markdown(f"**Created:** {session.created_at.strftime('%Y-%m-%d %H:%M')}")

st.markdown("---")

# Version timeline
st.header("Version Timeline")

if versions:
    # Simple timeline visualization
    timeline_parts = []
    for i, v in enumerate(versions):
        status_icon = ""
        if v.status == "accepted":
            status_icon = "✅"
        elif v.status == "rejected":
            status_icon = "❌"
        else:
            status_icon = "⏳"

        is_current = current_version and v.id == current_version.id
        label = f"v{v.version_number} {status_icon}"
        if is_current:
            label += " (current)"

        timeline_parts.append(label)

    st.markdown(" → ".join(timeline_parts))

    st.markdown("---")

    # Version details
    st.header("Version Details")

    selected_version_num = st.selectbox(
        "Select version to view",
        options=[v.version_number for v in versions],
        index=len(versions) - 1,  # Default to latest
    )

    selected_version = next((v for v in versions if v.version_number == selected_version_num), None)

    if selected_version:
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown(f"**Version {selected_version.version_number}**")
            st.markdown(f"Status: {selected_version.status}")
            st.markdown(f"Created: {selected_version.created_at.strftime('%Y-%m-%d %H:%M')}")

            if selected_version.mutation_explanation:
                st.markdown(f"**Changes:** {selected_version.mutation_explanation}")

        with col2:
            # Get performance stats if we have a run manager
            api_key = get_api_key()
            if api_key:
                llm_client = LLMClient(
                    provider=session.model_provider,
                    api_key=api_key,
                    default_model=session.model_name,
                    default_temperature=session.model_temperature,
                )
                run_manager = RunManager(llm_client)
                summary = run_manager.get_feedback_summary(selected_version.id)
                if summary["total"] > 0:
                    st.markdown("**Feedback:**")
                    st.markdown(f"- Good: {summary['good']}")
                    st.markdown(f"- Bad: {summary['bad']}")
                    accuracy = summary['good'] / (summary['good'] + summary['bad']) if (summary['good'] + summary['bad']) > 0 else 0
                    st.markdown(f"- Accuracy: {accuracy:.0%}")

        # Show prompt
        with st.expander("View Prompt"):
            st.code(selected_version.prompt_text)

        # Compare with parent
        if selected_version.parent_version_id:
            parent_version = prompt_manager.get_version(selected_version.parent_version_id)
            if parent_version:
                with st.expander(f"Compare with v{parent_version.version_number}"):
                    render_side_by_side_diff(
                        old_prompt=parent_version.prompt_text,
                        new_prompt=selected_version.prompt_text,
                        old_label=f"v{parent_version.version_number}",
                        new_label=f"v{selected_version.version_number}",
                    )

        # Revert option
        if selected_version.status == "accepted" and current_version and selected_version.id != current_version.id:
            if st.button(f"Revert to v{selected_version.version_number}"):
                # Create a new version that copies this one
                new_version = prompt_manager.create_version(
                    session_id=session.id,
                    prompt_text=selected_version.prompt_text,
                    parent_version_id=current_version.id,
                    mutation_explanation=f"Reverted to v{selected_version.version_number}",
                    status="accepted",
                )
                st.success(f"Created v{new_version.version_number} (revert to v{selected_version.version_number})")
                st.rerun()

st.markdown("---")

# Export section
st.header("Export")

col1, col2 = st.columns(2)

with col1:
    if current_version:
        markdown_export = export_prompt_markdown(session, current_version)
        st.download_button(
            "Export Prompt (Markdown)",
            data=markdown_export,
            file_name=f"{session.name.replace(' ', '_')}_v{current_version.version_number}.md",
            mime="text/markdown",
            use_container_width=True,
        )

with col2:
    api_key = get_api_key()
    run_manager_for_export = None
    if api_key:
        llm_client = LLMClient(
            provider=session.model_provider,
            api_key=api_key,
            default_model=session.model_name,
            default_temperature=session.model_temperature,
        )
        run_manager_for_export = RunManager(llm_client)

    json_export = export_session_json(
        session_id=session.id,
        session_manager=session_manager,
        input_manager=input_manager,
        prompt_manager=prompt_manager,
        run_manager=run_manager_for_export,
    )
    st.download_button(
        "Export Session (JSON)",
        data=json_export,
        file_name=f"{session.name.replace(' ', '_')}_export.json",
        mime="application/json",
        use_container_width=True,
    )

st.markdown("---")

# Session actions
st.header("Session Actions")

# Resume session button (prominent)
if st.button("Resume Session", type="primary", use_container_width=True):
    resume_session(session.id)
    st.switch_page("pages/2_review.py")

col1, col2, col3 = st.columns(3)

with col1:
    new_status = "completed" if session.status == "active" else "active"
    if st.button(
        f"Mark as {new_status.capitalize()}",
        use_container_width=True,
    ):
        session_manager.update_session(session.id, status=new_status)
        st.success(f"Session marked as {new_status}")
        st.rerun()

with col2:
    if st.button("Delete Session", type="secondary", use_container_width=True):
        if st.session_state.get("confirm_delete"):
            session_manager.delete_session(session.id)
            clear_session()
            st.success("Session deleted")
            st.rerun()
        else:
            st.session_state["confirm_delete"] = True
            st.warning("Click again to confirm deletion")

with col3:
    # Reset delete confirmation when other buttons clicked
    if st.session_state.get("confirm_delete"):
        if st.button("Cancel Delete", use_container_width=True):
            st.session_state["confirm_delete"] = False
            st.rerun()
