"""
prereq_view.py — app/ui
Streamlit view for the prerequisite path visualization.
Reads all shared data from st.session_state. Contains no business logic.
"""

import streamlit as st

from app.core.graph.prereq import find_prereq_path, get_prereq_depth
from app.ui.components.graph_plot import render_prereq_plot


def render_prereq_view() -> None:
    """
    Renders the prerequisite path visualization tab.

    Layout: single column.

    Displays:
    - A selectbox to choose a target course (sorted alphabetically by id).
    - A Plotly prerequisite tree when a course with prerequisites is selected.
    - A plain-text summary of the prerequisite count and depth.
    - An info message when the selected course has no prerequisites.

    Returns:
        None. Renders directly to Streamlit.
    """
    courses = st.session_state.courses
    graph = st.session_state.graph

    sorted_courses = sorted(courses, key=lambda c: c["id"])
    options = [f"{c['id']} \u2014 {c['name']}" for c in sorted_courses]
    id_map = {f"{c['id']} \u2014 {c['name']}": c["id"] for c in sorted_courses}

    selected_label = st.selectbox("Select a target course", options=options)
    if not selected_label:
        return

    target_id = id_map[selected_label]

    try:
        subgraph = find_prereq_path(graph, target_id)
        depth_values = get_prereq_depth(graph, target_id)
    except ValueError as e:
        st.error(str(e))
        return

    if subgraph.number_of_nodes() <= 1:
        st.info("This course has no prerequisites.")
        return

    fig = render_prereq_plot(subgraph, depth_values, target_id)
    st.plotly_chart(fig, use_container_width=True)

    max_depth = max(depth_values.values()) if depth_values else 0
    st.text(
        f"{target_id} requires {len(subgraph.nodes) - 1} "
        f"prerequisite course(s) across {max_depth} level(s)."
    )
