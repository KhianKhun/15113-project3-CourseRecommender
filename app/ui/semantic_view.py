"""
semantic_view.py — app/ui
Streamlit view for the semantic course graph and recommendation features.
Reads all shared data from st.session_state. Contains no business logic.
"""

import streamlit as st

from app.ui.components.controls import (
    dimension_selector,
    node_count_slider,
    highlight_count_slider,
    course_search,
    add_course_form,
)
from app.ui.components.graph_plot import render_graph_plot
from app.ui.components.tooltip import render_recommendation_list
from app.core.data_loader import save_user_course
from app.core.recommender import recommend


def render_semantic_view() -> None:
    """
    Renders the full semantic graph view tab.

    Layout: left column (controls, 1-unit wide) | right column (graph, 3-units wide).

    Left column contains:
    - Dimension selector (2D / 3D radio)
    - Node count slider
    - Course search + multiselect
    - Add custom course expander
    - Recommendation panel (when courses are selected)

    Right column contains:
    - Plotly scatter figure
    - Metadata caption below the figure

    Returns:
        None. Renders directly to Streamlit.
    """
    left_col, right_col = st.columns([1, 3])

    with left_col:
        with st.expander("Display settings", expanded=False):
            n_components = dimension_selector()
            top_k = node_count_slider()
            top_n_highlight = highlight_count_slider()
        selected_ids = course_search(st.session_state.courses)
        st.session_state.selected_courses = selected_ids

        new_course = add_course_form(st.session_state.courses)
        if new_course:
            try:
                save_user_course(new_course)
                st.session_state.initialized = False
                st.rerun()
            except ValueError as e:
                st.error(str(e))

        recs = []
        if st.session_state.get("selected_courses"):
            recs = recommend(
                input_course_ids=st.session_state.selected_courses,
                courses=st.session_state.courses,
                similarity_matrix=st.session_state.similarity_matrix,
                pagerank_scores=st.session_state.pagerank_scores,
                top_n=top_n_highlight,
            )
            st.markdown("---")
            st.subheader("Recommended for you")
            render_recommendation_list(recs)

    with right_col:
        if n_components == 2:
            coords = st.session_state.coords_2d
            explained_variance = st.session_state.var_2d
        else:
            coords = st.session_state.coords_3d
            explained_variance = st.session_state.var_3d

        fig = render_graph_plot(
            coords=coords,
            courses=st.session_state.courses,
            pagerank_scores=st.session_state.pagerank_scores,
            n_components=n_components,
            top_k=top_k,
            top_n_highlight=top_n_highlight,
            selected_ids=selected_ids,
            explained_variance=explained_variance,
            highlight_ids=[r["id"] for r in recs] if recs else None,
            similarity_matrix=st.session_state.similarity_matrix,
        )
        st.plotly_chart(fig, use_container_width=True)
        if selected_ids:
            st.caption(
                f"Showing top {top_k} courses related to selection \u00b7 "
                f"{n_components}D projection \u00b7 "
                f"{explained_variance:.1%} variance explained"
            )
        else:
            st.caption(
                f"Showing top {top_k} courses by PageRank \u00b7 "
                f"{n_components}D projection \u00b7 "
                f"{explained_variance:.1%} variance explained"
            )
