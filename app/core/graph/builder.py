"""
builder.py — app/core/graph
Constructs the directed course graph with semantic and prerequisite edges.
"""

import networkx as nx
import numpy as np


def build_graph(
    courses: list[dict],
    similarity_matrix: np.ndarray,
    similarity_threshold: float = 0.3
) -> nx.DiGraph:
    """
    Builds a directed graph where each node stores the full course dict
    as its attribute payload.

    Semantic edges: added when cosine similarity exceeds similarity_threshold.
        Edge attribute: weight=<similarity value>, type="semantic".

    Prerequisite edges: added per the prerequisites field.
        Edge attribute: type="prereq".

    Args:
        courses: The merged course list from data_loader.load_courses().
        similarity_matrix: An (N, N) cosine similarity matrix from
            similarity.compute_similarity_matrix().
        similarity_threshold: Minimum cosine similarity to add a semantic edge.

    Returns:
        A nx.DiGraph with one node per course (keyed by course id) and edges
        for both semantic similarity and prerequisite relationships.
    """
    G = nx.DiGraph()

    # Add all nodes
    for course in courses:
        G.add_node(course["id"], **course)

    id_to_idx = {c["id"]: i for i, c in enumerate(courses)}
    n = len(courses)

    # Add semantic edges
    for i in range(n):
        for j in range(i + 1, n):
            sim = float(similarity_matrix[i, j])
            if sim > similarity_threshold:
                src_id = courses[i]["id"]
                dst_id = courses[j]["id"]
                G.add_edge(src_id, dst_id, weight=sim, type="semantic")
                G.add_edge(dst_id, src_id, weight=sim, type="semantic")

    # Add prerequisite edges
    for course in courses:
        for prereq_id in course.get("prerequisites", []):
            if prereq_id in G:
                G.add_edge(prereq_id, course["id"], type="prereq")

    return G
