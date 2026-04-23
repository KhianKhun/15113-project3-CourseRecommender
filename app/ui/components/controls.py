"""
controls.py — app/ui/components
Reusable Streamlit control components used by semantic_view.py.
Each function renders one logical control and returns its current value.
Functions must not write to st.session_state — they return values to the caller.
"""

import streamlit as st

from app.core.config import DEFAULT_TOP_K_NODES, DEFAULT_ANCHOR_COUNT


def dimension_selector() -> int:
    """
    Renders a 2D/3D radio button.

    Returns:
        2 or 3 as an integer.
    """
    choice = st.radio("Dimensions", options=["2D", "3D"], horizontal=True)
    return 2 if choice == "2D" else 3


def node_count_slider() -> int:
    """
    Renders a node count slider labeled "Max nodes to display".
    Range 10 to 100, default from DEFAULT_TOP_K_NODES.

    Returns:
        The selected integer value.
    """
    return st.slider(
        "Max nodes to display",
        min_value=10,
        max_value=150,
        value=DEFAULT_TOP_K_NODES,
        step=5,
    )


def highlight_count_slider() -> int:
    """
    Renders the highlight count slider.
    Returns current int value (1 to 20).
    Default is DEFAULT_ANCHOR_COUNT from config.py.
    """
    return st.slider(
        "Highlighted courses to show",
        min_value=1,
        max_value=20,
        value=DEFAULT_ANCHOR_COUNT,
        step=1,
        key="top_n_highlight",
    )


def course_search(courses: list[dict]) -> list[str]:
    """
    Renders a text search input and a multiselect of matching courses.
    Filters by case-insensitive substring match on course id or name.
    Previously selected courses are always kept in the options list so
    that changing the search query does not drop existing selections.

    Args:
        courses: The full course list from data_loader.load_courses().

    Returns:
        A list of selected course id strings.
    """
    # Build label → id map from ALL courses (not just filtered) so previously
    # selected labels can always be resolved.
    all_label_to_id = {f"{c['id']} \u2014 {c['name']}": c["id"] for c in courses}

    query = st.text_input("Search or select courses", key="course_search_query")

    if query:
        filtered_labels = [
            label for label in all_label_to_id
            if query.lower() in label.lower()
        ]
    else:
        filtered_labels = list(all_label_to_id.keys())

    # Always include currently selected labels so Streamlit does not drop them
    # when the filter changes.
    preserved = st.session_state.get("course_search_multiselect", [])
    preserved_set = set(filtered_labels)
    for label in preserved:
        if label not in preserved_set:
            filtered_labels.insert(0, label)

    st.markdown(
        """
        <style>
        [data-testid="stMultiSelect"] [data-baseweb="select"] > div:first-child {
            max-height: 80px;
            overflow-y: auto;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    selected = st.multiselect(
        "Matching courses",
        options=filtered_labels,
        label_visibility="collapsed",
        key="course_search_multiselect",
    )
    return [all_label_to_id[s] for s in selected if s in all_label_to_id]


def hidden_course_search(courses: list[dict]) -> list[str]:
    """
    Renders a text search input and a multiselect for hidden courses.
    Interaction matches course_search(), but stores values under separate keys.

    Args:
        courses: The full course list from data_loader.load_courses().

    Returns:
        A list of hidden course id strings.
    """
    all_label_to_id = {f"{c['id']} — {c['name']}": c["id"] for c in courses}
    query = st.text_input("Search courses to hide", key="hidden_course_query")

    if query:
        filtered_labels = [
            label for label in all_label_to_id
            if query.lower() in label.lower()
        ]
    else:
        filtered_labels = list(all_label_to_id.keys())

    preserved = st.session_state.get("hidden_course_multiselect", [])
    preserved_set = set(filtered_labels)
    for label in preserved:
        if label not in preserved_set:
            filtered_labels.insert(0, label)

    st.markdown(
        """
        <style>
        [data-testid="stMultiSelect"] [data-baseweb="select"] > div:first-child {
            max-height: 80px;
            overflow-y: auto;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    selected = st.multiselect(
        "Hidden courses",
        options=filtered_labels,
        label_visibility="collapsed",
        key="hidden_course_multiselect",
    )
    return [all_label_to_id[s] for s in selected if s in all_label_to_id]
