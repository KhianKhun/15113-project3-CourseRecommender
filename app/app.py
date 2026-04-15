"""
app.py — CMU Course Graph
Main Streamlit entry point. Bootstraps shared data once into session_state,
then routes to the two tab views.

Launch: streamlit run app/app.py
"""

import streamlit as st

from app.core.data_loader import load_courses
from app.core.embedder.model import get_embeddings
from app.core.embedder.similarity import compute_similarity_matrix
from app.core.graph.builder import build_graph
from app.core.graph.pagerank import compute_pagerank
from app.core.reduction.pca import reduce_dimensions
from app.ui.semantic_view import render_semantic_view
from app.ui.prereq_view import render_prereq_view


st.set_page_config(
    page_title="CMU Course Graph",
    page_icon="\U0001f393",
    layout="wide",
)

if "initialized" not in st.session_state:
    with st.spinner("Loading course data and building graph..."):
        courses = load_courses()
        embeddings = get_embeddings(courses)
        similarity_matrix = compute_similarity_matrix(embeddings)
        graph = build_graph(courses, similarity_matrix)
        pagerank_scores = compute_pagerank(graph)
        coords_2d, var_2d = reduce_dimensions(embeddings, 2)
        coords_3d, var_3d = reduce_dimensions(embeddings, 3)

        st.session_state.courses = courses
        st.session_state.embeddings = embeddings
        st.session_state.similarity_matrix = similarity_matrix
        st.session_state.graph = graph
        st.session_state.pagerank_scores = pagerank_scores
        st.session_state.coords_2d = coords_2d
        st.session_state.coords_3d = coords_3d
        st.session_state.var_2d = var_2d
        st.session_state.var_3d = var_3d
        st.session_state.initialized = True

tab1, tab2 = st.tabs(["Semantic Graph", "Prerequisite Path"])

with tab1:
    render_semantic_view()

with tab2:
    render_prereq_view()
