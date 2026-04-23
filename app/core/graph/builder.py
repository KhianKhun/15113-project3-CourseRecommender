"""
builder.py - app/core/graph
Constructs the directed course graph with semantic and prerequisite edges.
"""

import networkx as nx
import numpy as np

from app.core.config import (
    DEFAULT_SIMILARITY_THRESHOLD,
    GRAPH_EDGE_MATRIX_PATH,
    PAGERANK_PREREQ_WEIGHT,
)

_EDGE_TYPE_NONE = 0.0
_EDGE_TYPE_SEMANTIC = 1.0
_EDGE_TYPE_PREREQ = 2.0


def _compute_edge_tensor(
    courses: list[dict],
    similarity_matrix: np.ndarray,
    similarity_threshold: float,
    prereq_weight: float,
) -> np.ndarray:
    """
    Build a 2 x N x N tensor for final graph edges.

    tensor[0]: edge weights
    tensor[1]: edge type code (0 none, 1 semantic, 2 prereq)
    """
    n = len(courses)
    edge_weight = np.zeros((n, n), dtype=np.float32)
    edge_type = np.zeros((n, n), dtype=np.float32)

    i_arr, j_arr = np.where(np.triu(similarity_matrix > similarity_threshold, k=1))
    if i_arr.size > 0:
        sim_vals = similarity_matrix[i_arr, j_arr].astype(np.float32)
        edge_weight[i_arr, j_arr] = sim_vals
        edge_weight[j_arr, i_arr] = sim_vals
        edge_type[i_arr, j_arr] = _EDGE_TYPE_SEMANTIC
        edge_type[j_arr, i_arr] = _EDGE_TYPE_SEMANTIC

    id_to_idx = {course["id"]: i for i, course in enumerate(courses)}
    for course in courses:
        dst = id_to_idx[course["id"]]
        for prereq_id in course.get("prerequisites", []):
            src = id_to_idx.get(prereq_id)
            if src is None:
                continue
            # Prereq edges override semantic edges for the same direction.
            edge_weight[src, dst] = float(prereq_weight)
            edge_type[src, dst] = _EDGE_TYPE_PREREQ

    return np.stack((edge_weight, edge_type), axis=0)


def _load_or_compute_edge_tensor(
    courses: list[dict],
    similarity_matrix: np.ndarray,
    similarity_threshold: float,
    prereq_weight: float,
) -> np.ndarray:
    """
    Load cached graph-edge tensor when safe; otherwise compute and persist.

    Cache is intentionally limited to default startup settings so tests or
    custom thresholds always produce fresh results.
    """
    n = len(courses)
    can_use_cache = similarity_threshold == DEFAULT_SIMILARITY_THRESHOLD

    if can_use_cache and GRAPH_EDGE_MATRIX_PATH.exists():
        try:
            cached = np.load(GRAPH_EDGE_MATRIX_PATH)
            if cached.shape == (2, n, n):
                return cached.astype(np.float32, copy=False)
        except OSError:
            pass

    edge_tensor = _compute_edge_tensor(
        courses=courses,
        similarity_matrix=similarity_matrix,
        similarity_threshold=similarity_threshold,
        prereq_weight=prereq_weight,
    )

    if can_use_cache:
        try:
            GRAPH_EDGE_MATRIX_PATH.parent.mkdir(parents=True, exist_ok=True)
            np.save(GRAPH_EDGE_MATRIX_PATH, edge_tensor)
        except OSError:
            pass

    return edge_tensor


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
    graph = nx.DiGraph()
    for course in courses:
        graph.add_node(course["id"], **course)

    edge_tensor = _load_or_compute_edge_tensor(
        courses=courses,
        similarity_matrix=similarity_matrix,
        similarity_threshold=similarity_threshold,
        prereq_weight=prereq_weight,
    )
    edge_weight = edge_tensor[0]
    edge_type = edge_tensor[1]
    course_ids = [c["id"] for c in courses]

    src_idx, dst_idx = np.where(edge_type > _EDGE_TYPE_NONE)
    edges = []
    for src, dst in zip(src_idx, dst_idx):
        edge_kind = "prereq" if edge_type[src, dst] == _EDGE_TYPE_PREREQ else "semantic"
        edges.append(
            (
                course_ids[src],
                course_ids[dst],
                {"weight": float(edge_weight[src, dst]), "type": edge_kind},
            )
        )
    graph.add_edges_from(edges)

    return graph
