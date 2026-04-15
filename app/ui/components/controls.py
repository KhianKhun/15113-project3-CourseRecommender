"""
controls.py — app/ui/components
Reusable Streamlit control components used by semantic_view.py.
Each function renders one logical control and returns its current value.
Functions must not write to st.session_state — they return values to the caller.
"""

import streamlit as st

from app.core.config import DEFAULT_TOP_K_NODES


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
        max_value=100,
        value=DEFAULT_TOP_K_NODES,
        step=5,
    )


def course_search(courses: list[dict]) -> list[str]:
    """
    Renders a text search input and a multiselect of matching courses.
    Filters by case-insensitive substring match on course id or name.

    Args:
        courses: The full course list from data_loader.load_courses().

    Returns:
        A list of selected course id strings.
    """
    query = st.text_input("Search or select courses", key="course_search_query")

    if query:
        filtered = [
            c for c in courses
            if query.lower() in c["id"].lower() or query.lower() in c["name"].lower()
        ]
    else:
        filtered = courses

    options = [f"{c['id']} \u2014 {c['name']}" for c in filtered]
    id_map = {f"{c['id']} \u2014 {c['name']}": c["id"] for c in filtered}

    selected = st.multiselect(
        "Matching courses",
        options=options,
        label_visibility="collapsed",
        key="course_search_multiselect",
    )
    return [id_map[s] for s in selected]


def add_course_form(courses: list[dict]) -> dict | None:
    """
    Renders an expander with a form to add a custom course.
    Returns a validated course dict if the form was submitted, None otherwise.
    Does not write to session_state or call save_user_course — the caller handles that.

    Args:
        courses: The existing course list, used to warn on duplicate ids.

    Returns:
        A course dict ready for save_user_course(), or None if not submitted.
    """
    existing_ids = {c["id"] for c in courses}

    with st.expander("Add a custom course"):
        course_id = st.text_input("Course ID (format: XX-NNN, e.g. 99-123)")
        name = st.text_input("Course Name")
        department = st.text_input("Department (abbreviated)")
        units = st.number_input("Units", min_value=1, max_value=48, value=12, step=1)
        description = st.text_area("Description")
        prereqs_input = st.text_input(
            "Prerequisites (comma-separated course IDs, leave blank if none)"
        )
        submitted = st.button("Add to graph")

        if submitted:
            prereqs = [p.strip() for p in prereqs_input.split(",") if p.strip()]
            return {
                "id": course_id.strip(),
                "name": name.strip(),
                "department": department.strip(),
                "units": int(units),
                "description": description.strip(),
                "prerequisites": prereqs,
                "source": "user",
            }

    return None
