"""Diff viewer component for prompt comparisons."""

import streamlit as st
from typing import Optional

from core.prompt_manager import generate_diff


def render_diff_viewer(
    old_prompt: str,
    new_prompt: str,
    show_legend: bool = True,
) -> None:
    """
    Render a diff view between two prompts.

    Args:
        old_prompt: The original prompt text
        new_prompt: The new prompt text
        show_legend: Whether to show the color legend
    """
    if show_legend:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                '<span style="background-color: #d4edda; padding: 2px 6px; border-radius: 3px;">+ Added</span>',
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                '<span style="background-color: #f8d7da; padding: 2px 6px; border-radius: 3px;">- Removed</span>',
                unsafe_allow_html=True,
            )
        with col3:
            st.markdown(
                '<span style="padding: 2px 6px;">Unchanged</span>',
                unsafe_allow_html=True,
            )
        st.markdown("")

    # Generate diff
    diff_lines = generate_diff(old_prompt, new_prompt)

    # Build HTML for diff display
    html_parts = ['<div style="font-family: monospace; white-space: pre-wrap; line-height: 1.6;">']

    for line in diff_lines:
        text = line["text"].replace("<", "&lt;").replace(">", "&gt;")
        if line["type"] == "added":
            html_parts.append(
                f'<div style="background-color: #d4edda; padding: 2px 4px; margin: 1px 0;"><span style="color: #155724;">+ {text}</span></div>'
            )
        elif line["type"] == "removed":
            html_parts.append(
                f'<div style="background-color: #f8d7da; padding: 2px 4px; margin: 1px 0;"><span style="color: #721c24;">- {text}</span></div>'
            )
        else:
            html_parts.append(
                f'<div style="padding: 2px 4px; margin: 1px 0;"><span style="color: #666;">  {text}</span></div>'
            )

    html_parts.append("</div>")

    st.markdown("".join(html_parts), unsafe_allow_html=True)


def render_side_by_side_diff(
    old_prompt: str,
    new_prompt: str,
    old_label: str = "Before",
    new_label: str = "After",
) -> None:
    """
    Render prompts side by side for comparison.

    Args:
        old_prompt: The original prompt text
        new_prompt: The new prompt text
        old_label: Label for the old prompt column
        new_label: Label for the new prompt column
    """
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**{old_label}**")
        st.code(old_prompt, language=None)

    with col2:
        st.markdown(f"**{new_label}**")
        st.code(new_prompt, language=None)


def render_changes_summary(
    analysis: str,
    changes: list[str],
) -> None:
    """
    Render a summary of changes made.

    Args:
        analysis: GEPA's analysis of what was wrong
        changes: List of specific changes made
    """
    if analysis:
        st.markdown("**Analysis**")
        st.markdown(analysis)

    if changes:
        st.markdown("**Changes Made**")
        for change in changes:
            st.markdown(f"- {change}")
