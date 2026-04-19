"""
builder.py — app/core/graph
Constructs the directed course graph with semantic and prerequisite edges.
"""

import networkx as nx
import numpy as np

from app.core.config import PAGERANK_PREREQ_WEIGHT


def build_graph(
    courses: list[dict],
    similarity_matrix: np.ndarray,
    similarity_threshold: float = 0.3,
    prereq_weight: float = PAGERANK_PREREQ_WEIGHT,
) -> nx.DiGraph:
    """
    Builds a directed graph where each node stores the full course dict
    as its attribute payload.

    Semantic edges: added when cosine similarity exceeds similarity_threshold.
        Edge attribute: weight=<similarity value>, type="semantic".

    Prerequisite edges: added per the prerequisites field.
        Edge attribute: weight=prereq_weight, type="prereq".

    Args:
        courses: The merged course list from data_loader.load_courses().
        similarity_matrix: An (N, N) cosine similarity matrix from
            similarity.compute_similarity_matrix().
        similarity_threshold: Minimum cosine similarity to add a semantic edge.
        prereq_weight: Edge weight assigned to prerequisite edges. Higher values
            give prerequisite relationships more influence in PageRank.

    Returns:
        A nx.DiGraph with one node per course (keyed by course id) and edges
        for both semantic similarity and prerequisite relationships.
    """
    G = nx.DiGraph()

    # Add all nodes
    for course in courses:
        G.add_node(course["id"], **course)

    n = len(courses)
    course_ids = [c["id"] for c in courses]

    # Add semantic edges via numpy: find all (i,j) pairs above threshold in one pass
    i_arr, j_arr = np.where(np.triu(similarity_matrix > similarity_threshold, k=1))
    sim_vals = similarity_matrix[i_arr, j_arr]
    forward = [
        (course_ids[i], course_ids[j], {"weight": float(w), "type": "semantic"})
        for i, j, w in zip(i_arr, j_arr, sim_vals)
    ]
    backward = [
        (course_ids[j], course_ids[i], {"weight": float(w), "type": "semantic"})
        for i, j, w in zip(i_arr, j_arr, sim_vals)
    ]
    G.add_edges_from(forward)
    G.add_edges_from(backward)

    # Add prerequisite edges
    for course in courses:
        for prereq_id in course.get("prerequisites", []):
            if prereq_id in G:
                G.add_edge(prereq_id, course["id"], weight=prereq_weight, type="prereq")

    return G
