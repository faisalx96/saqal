"""Reusable feedback card UI component."""

import streamlit as st
from typing import Optional, Callable


def render_feedback_card(
    input_content: str,
    output: str,
    ground_truth: Optional[str] = None,
    current_feedback: Optional[str] = None,
    feedback_reason: Optional[str] = None,
    human_correction: Optional[str] = None,
    on_feedback: Optional[Callable[[str, Optional[str], Optional[str]], None]] = None,
    card_key: str = "feedback",
) -> dict:
    """
    Render a feedback card for reviewing an input/output pair.

    Args:
        input_content: The input text
        output: The LLM output
        ground_truth: Expected output (if available)
        current_feedback: Current feedback value ('good', 'bad', or None)
        feedback_reason: Current feedback reason
        human_correction: Current human correction
        on_feedback: Callback when feedback is submitted
        card_key: Unique key for the component

    Returns:
        Dict with feedback values if submitted
    """
    result = {
        "feedback": current_feedback,
        "reason": feedback_reason,
        "correction": human_correction,
    }

    # Input display
    st.markdown("**Input**")
    st.info(input_content)

    # Output display
    st.markdown("**Output**")
    st.success(output)

    # Ground truth if available
    if ground_truth:
        st.markdown("**Expected (Ground Truth)**")
        st.warning(ground_truth)

    st.markdown("---")
    st.markdown("**Your Feedback**")

    # Feedback buttons
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        good_selected = current_feedback == "good"
        if st.button(
            "Good" if not good_selected else "Good",
            key=f"{card_key}_good",
            type="primary" if good_selected else "secondary",
            use_container_width=True,
        ):
            result["feedback"] = "good"
            result["reason"] = None
            result["correction"] = None

    with col2:
        bad_selected = current_feedback == "bad"
        if st.button(
            "Bad" if not bad_selected else "Bad",
            key=f"{card_key}_bad",
            type="primary" if bad_selected else "secondary",
            use_container_width=True,
        ):
            result["feedback"] = "bad"

    # Show reason/correction fields if bad
    if result["feedback"] == "bad" or current_feedback == "bad":
        reason = st.text_area(
            "Why is this wrong? (helps improve the prompt)",
            value=feedback_reason or "",
            key=f"{card_key}_reason",
            placeholder="e.g., This is clearly a complaint, not a question",
        )
        result["reason"] = reason if reason else None

        correction = st.text_input(
            "What should it be? (optional)",
            value=human_correction or "",
            key=f"{card_key}_correction",
            placeholder="e.g., complaint",
        )
        result["correction"] = correction if correction else None

    return result


def render_feedback_summary(good: int, bad: int, pending: int) -> None:
    """Render a summary of feedback progress."""
    total = good + bad + pending

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Good", good)
    with col2:
        st.metric("Bad", bad)
    with col3:
        st.metric("Pending", pending)
    with col4:
        if total > 0:
            progress = (good + bad) / total
            st.metric("Progress", f"{progress:.0%}")

    # Progress bar
    if total > 0:
        st.progress((good + bad) / total)
