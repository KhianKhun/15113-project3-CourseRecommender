"""
tooltip.py — app/ui/components
Formats hover tooltip text for graph nodes and renders course cards.
"""

import streamlit as st


def format_tooltip(course: dict, pagerank_score: float) -> str:
    """
    Returns a formatted string for Plotly hovertemplate.

    Format:
        10-301 — Introduction to Machine Learning
        Department: ML  |  Units: 12
        Importance: 0.842
        Prerequisites: 21-241, 36-218

        This course provides a broad introduction to...
        (description truncated to 200 characters)

    Args:
        course: A full course dict from the merged course list.
        pagerank_score: The normalized PageRank score for this course.

    Returns:
        A formatted string suitable for use in a Plotly hovertemplate.
    """
    prereqs = ", ".join(course["prerequisites"]) if course.get("prerequisites") else "None"
    desc = course.get("description", "")
    if len(desc) > 200:
        desc = desc[:200] + "..."
    return (
        f"{course['id']} \u2014 {course['name']}<br>"
        f"Department: {course['department']}  |  Units: {course['units']}<br>"
        f"Importance: {pagerank_score:.3f}<br>"
        f"Prerequisites: {prereqs}<br><br>"
        f"{desc}"
    )


def render_course_card(course: dict, score: float | None = None) -> None:
    """
    Renders a styled course detail card using Streamlit's container/markdown.

    Args:
        course: A full course dict from the merged course list.
        score: Optional PageRank score to display. If None, score is omitted.

    Returns:
        None. Renders directly to the active Streamlit container.
    """
    with st.container():
        st.markdown(f"### {course['id']}: {course['name']}")
        col1, col2, col3 = st.columns(3)
        col1.metric("Department", course["department"])
        col2.metric("Units", course["units"])
        if score is not None:
            col3.metric("PageRank Score", f"{score:.4f}")
        else:
            col3.metric("Source", course.get("source", "—"))

        st.markdown(f"**Description:** {course['description']}")

        if course.get("prerequisites"):
            prereqs_str = ", ".join(course["prerequisites"])
            st.markdown(f"**Prerequisites:** {prereqs_str}")
        else:
            st.markdown("**Prerequisites:** None")


def render_recommendation_list(recommendations: list[dict]) -> None:
    """
    Renders a compact list of course recommendations.

    Args:
        recommendations: A list of course dicts each augmented with a 'score'
            field, as returned by recommender.recommend().

    Returns:
        None. Renders directly to the active Streamlit container.
    """
    if not recommendations:
        st.info("No recommendations found. Try selecting more courses.")
        return

    for course in recommendations:
        score = course.get("score", 0.0)
        st.markdown(f"**{course['id']}** — {course['name']} `score: {score:.3f}`")
