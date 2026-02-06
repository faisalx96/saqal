"""Streamlit session state helpers for Saqal."""

import streamlit as st
from typing import Optional, Any


def init_state() -> None:
    """Initialize all session state variables."""
    defaults = {
        # Current session
        "current_session_id": None,
        "api_key": "",
        # Review state
        "current_batch_index": 0,
        "batch_input_ids": [],
        "batch_results": {},  # result_id -> RunResult
        # Adapt state
        "mutation_proposal": None,
        "edited_prompt": None,
        # Compare state
        "comparison_mode": False,
        "old_version_id": None,
        "new_version_id": None,
        # General
        "page_initialized": {},
    }

    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def get_state(key: str, default: Any = None) -> Any:
    """Get a value from session state."""
    init_state()
    return st.session_state.get(key, default)


def set_state(key: str, value: Any) -> None:
    """Set a value in session state."""
    init_state()
    st.session_state[key] = value


def clear_session() -> None:
    """Clear the current session state."""
    set_state("current_session_id", None)
    set_state("current_batch_index", 0)
    set_state("batch_input_ids", [])
    set_state("batch_results", {})
    set_state("mutation_proposal", None)
    set_state("edited_prompt", None)
    set_state("comparison_mode", False)
    set_state("old_version_id", None)
    set_state("new_version_id", None)


def get_current_session_id() -> Optional[str]:
    """Get the current session ID."""
    return get_state("current_session_id")


def set_current_session_id(session_id: str) -> None:
    """Set the current session ID."""
    set_state("current_session_id", session_id)


def get_api_key() -> str:
    """Get the stored API key."""
    return get_state("api_key", "")


def set_api_key(api_key: str) -> None:
    """Store the API key in session state."""
    set_state("api_key", api_key)


def get_batch_index() -> int:
    """Get the current batch review index."""
    return get_state("current_batch_index", 0)


def set_batch_index(index: int) -> None:
    """Set the current batch review index."""
    set_state("current_batch_index", index)


def get_batch_input_ids() -> list[str]:
    """Get the current batch input IDs."""
    return get_state("batch_input_ids", [])


def set_batch_input_ids(ids: list[str]) -> None:
    """Set the current batch input IDs."""
    set_state("batch_input_ids", ids)


def get_batch_results() -> dict:
    """Get the current batch results mapping."""
    return get_state("batch_results", {})


def set_batch_results(results: dict) -> None:
    """Set the current batch results mapping."""
    set_state("batch_results", results)


def is_page_initialized(page: str) -> bool:
    """Check if a page has been initialized."""
    initialized = get_state("page_initialized", {})
    return initialized.get(page, False)


def mark_page_initialized(page: str) -> None:
    """Mark a page as initialized."""
    initialized = get_state("page_initialized", {})
    initialized[page] = True
    set_state("page_initialized", initialized)


def resume_session(session_id: str) -> None:
    """
    Resume a session by loading its state.

    This clears current working state and sets up for the resumed session.
    The actual data loading happens in the Review page.
    """
    # Clear any existing working state
    set_state("current_batch_index", 0)
    set_state("batch_input_ids", [])
    set_state("batch_results", {})
    set_state("mutation_proposal", None)
    set_state("edited_prompt", None)
    set_state("comparison_mode", False)
    set_state("old_version_id", None)
    set_state("new_version_id", None)
    set_state("page_initialized", {})

    # Set the new session
    set_state("current_session_id", session_id)

    # Mark that this is a resumed session (Review page will handle loading)
    set_state("session_resumed", True)
