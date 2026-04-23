"""
hidden_view.py - app/ui
Streamlit view for managing hidden courses in semantic graph rendering.
"""

import streamlit as st

from app.ui.components.controls import hidden_course_search


def render_hidden_course_view() -> None:
    """
    Renders the hidden-course management tab.

    Hidden courses only affect display in the semantic graph and recommendation
    list. They do not alter scoring, ranking, or center-point logic.
    """
    st.subheader("Hidden Course")
    hidden_ids = hidden_course_search(st.session_state.courses)
    st.session_state.hidden_course_ids = hidden_ids

    if hidden_ids:
        st.caption(f"{len(hidden_ids)} course(s) currently hidden from Semantic Graph.")
    else:
        st.caption("No hidden courses. All courses are visible in Semantic Graph.")
