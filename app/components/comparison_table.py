"""Comparison table component for version comparisons."""

import streamlit as st
from typing import Optional, Callable
from dataclasses import dataclass


@dataclass
class ComparisonRow:
    """A single row in the comparison table."""

    input_id: str
    input_content: str
    old_output: str
    new_output: str
    old_result_id: str
    new_result_id: str
    comparison_result: Optional[str] = None  # 'better', 'worse', 'same'


def render_comparison_table(
    rows: list[ComparisonRow],
    old_version_label: str = "v1",
    new_version_label: str = "v2",
    on_comparison: Optional[Callable[[str, str], None]] = None,
) -> dict[str, str]:
    """
    Render a comparison table for two prompt versions.

    Args:
        rows: List of comparison rows
        old_version_label: Label for the old version
        new_version_label: Label for the new version
        on_comparison: Callback when a comparison is made

    Returns:
        Dict mapping result_id to comparison result
    """
    results = {}

    for idx, row in enumerate(rows):
        with st.container():
            st.markdown(f"**Input {idx + 1}**")
            st.info(row.input_content)

            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"**{old_version_label} Output**")
                st.text_area(
                    label=f"{old_version_label} Output",
                    value=row.old_output,
                    key=f"old_output_{row.input_id}",
                    height=100,
                    disabled=True,
                    label_visibility="collapsed",
                )

            with col2:
                st.markdown(f"**{new_version_label} Output**")
                st.text_area(
                    label=f"{new_version_label} Output",
                    value=row.new_output,
                    key=f"new_output_{row.input_id}",
                    height=100,
                    disabled=True,
                    label_visibility="collapsed",
                )

            # Comparison buttons
            st.markdown("**Which is better?**")
            btn_col1, btn_col2, btn_col3 = st.columns(3)

            current = row.comparison_result

            with btn_col1:
                v1_selected = current == "worse"  # v1 better means new is worse
                if st.button(
                    f"{old_version_label} Better",
                    key=f"v1_better_{row.input_id}",
                    type="primary" if v1_selected else "secondary",
                    use_container_width=True,
                ):
                    results[row.new_result_id] = "worse"

            with btn_col2:
                same_selected = current == "same"
                if st.button(
                    "Same",
                    key=f"same_{row.input_id}",
                    type="primary" if same_selected else "secondary",
                    use_container_width=True,
                ):
                    results[row.new_result_id] = "same"

            with btn_col3:
                v2_selected = current == "better"
                if st.button(
                    f"{new_version_label} Better",
                    key=f"v2_better_{row.input_id}",
                    type="primary" if v2_selected else "secondary",
                    use_container_width=True,
                ):
                    results[row.new_result_id] = "better"

            # Show current selection
            if current:
                if current == "better":
                    st.success(f"Selected: {new_version_label} is better")
                elif current == "worse":
                    st.warning(f"Selected: {old_version_label} is better")
                else:
                    st.info("Selected: Same")

            st.markdown("---")

    return results


def render_comparison_summary(
    better: int,
    worse: int,
    same: int,
    old_version_label: str = "v1",
    new_version_label: str = "v2",
) -> None:
    """
    Render a summary of comparison results.

    Args:
        better: Number of times new version was better
        worse: Number of times old version was better
        same: Number of times they were the same
        old_version_label: Label for the old version
        new_version_label: Label for the new version
    """
    total = better + worse + same

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(f"{new_version_label} Better", better)
    with col2:
        st.metric("Same", same)
    with col3:
        st.metric(f"{old_version_label} Better", worse)
    with col4:
        if total > 0:
            net_improvement = better - worse
            delta = f"+{net_improvement}" if net_improvement >= 0 else str(net_improvement)
            st.metric("Net Change", delta)

    # Visual summary
    if total > 0:
        st.markdown("**Summary**")
        if better > worse:
            st.success(
                f"{new_version_label} is better overall! ({better} improvements vs {worse} regressions)"
            )
        elif worse > better:
            st.warning(
                f"{old_version_label} was better overall. ({worse} regressions vs {better} improvements)"
            )
        else:
            st.info("Both versions performed similarly.")
