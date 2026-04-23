"""
prereq.py — app/core/graph
Extracts the transitive prerequisite subgraph for a target course.
"""

from collections import deque

import networkx as nx
import numpy as np

from app.core.config import (
    DECAY_ALPHA,
    DECAY_K,
    DOWNSTREAM_WEIGHT,
    PREREQ_SCORE_MATRIX_PATH,
    UPSTREAM_WEIGHT,
)


def find_prereq_path(
    graph: nx.DiGraph,
    target_id: str
) -> nx.DiGraph:
    """
    Returns a subgraph containing all prerequisite courses required to reach
    target_id, as a directed subgraph.

    Performs a reverse BFS from target_id following only edges of
    type="prereq" in the reverse direction, collecting all ancestor nodes.
    The target node itself is included in the returned subgraph.

    Args:
        graph: The directed course graph from builder.build_graph().
        target_id: The course id to find prerequisites for.

    Returns:
        A nx.DiGraph subgraph containing target_id and all its transitive
        prerequisites, with only the prerequisite edges between them.

    Raises:
        ValueError: If target_id is not present in the graph.
    """
    if target_id not in graph:
        raise ValueError(f"Course {target_id} not found in graph")

    # BFS walking incoming prereq edges from target back to roots
    visited: set[str] = set()
    queue: deque[str] = deque([target_id])

    while queue:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        for source, _, data in graph.in_edges(node, data=True):
            if data.get("type") == "prereq" and source not in visited:
                queue.append(source)

    # Build a prereq-only subgraph over the visited nodes
    prereq_edges = [
        (u, v) for u, v, data in graph.edges(data=True)
        if data.get("type") == "prereq" and u in visited and v in visited
    ]
    subgraph = nx.DiGraph()
    for node in visited:
        subgraph.add_node(node, **graph.nodes[node])
    subgraph.add_edges_from(prereq_edges)
    return subgraph


def get_prereq_depth(
    graph: nx.DiGraph,
    target_id: str
) -> dict[str, int]:
    """
    Returns a dict mapping each course id in the prerequisite subgraph
    to its depth level, where target_id is at depth 0, its direct
    prerequisites are at depth 1, their prerequisites at depth 2, and
    so on. Used by the UI to assign vertical positions in the prereq
    visualization.

    Performs a BFS over the subgraph returned by find_prereq_path,
    traversing edges in reverse (from target toward roots) and tracking
    the distance from target_id.

    Args:
        graph: The directed course graph from builder.build_graph().
        target_id: The course id to measure depth from.

    Returns:
        A dict mapping course id strings to integer depth values.

    Raises:
        ValueError: If target_id is not present in the graph.
    """
    prereq_subgraph = find_prereq_path(graph, target_id)

    depth: dict[str, int] = {target_id: 0}
    queue: deque[str] = deque([target_id])

    while queue:
        node = queue.popleft()
        current_depth = depth[node]
        for source, _ in prereq_subgraph.in_edges(node):
            if source not in depth:
                depth[source] = current_depth + 1
                queue.append(source)

    return depth


def _decay_weight(depth: int) -> float:
    """Linear decay with floor for prerequisite proximity propagation."""
    return max(DECAY_ALPHA, 1 - DECAY_K * depth)


def _build_neighbor_indices(courses: list[dict]) -> tuple[list[list[int]], list[list[int]]]:
    """
    Build adjacency indices for prerequisite traversal.

    Returns:
        upstream_neighbors[i]: indices that are prerequisites of i
        downstream_neighbors[i]: indices that require i
    """
    id_to_idx = {course["id"]: idx for idx, course in enumerate(courses)}
    n = len(courses)
    upstream_neighbors = [[] for _ in range(n)]
    downstream_neighbors = [[] for _ in range(n)]

    for dst_idx, course in enumerate(courses):
        for prereq_id in course.get("prerequisites", []):
            src_idx = id_to_idx.get(prereq_id)
            if src_idx is None:
                continue
            upstream_neighbors[dst_idx].append(src_idx)
            downstream_neighbors[src_idx].append(dst_idx)

    return upstream_neighbors, downstream_neighbors


def _compute_prereq_scores(courses: list[dict]) -> np.ndarray:
    """
    Compute an N x N prerequisite proximity matrix.

    score[i, j] represents structural proximity between course i and j by
    traversing both prerequisite directions with depth decay.
    """
    n = len(courses)
    if n == 0:
        return np.zeros((0, 0), dtype=np.float32)

    upstream_neighbors, downstream_neighbors = _build_neighbor_indices(courses)
    scores = np.zeros((n, n), dtype=np.float32)

    for root_idx in range(n):
        visited = {root_idx}
        queue: deque[tuple[int, int]] = deque([(root_idx, 0)])
        while queue:
            node_idx, depth = queue.popleft()
            next_depth = depth + 1
            base = _decay_weight(next_depth)

            for neighbor_idx in upstream_neighbors[node_idx]:
                score = float(base * UPSTREAM_WEIGHT)
                if score > scores[root_idx, neighbor_idx]:
                    scores[root_idx, neighbor_idx] = score
                if neighbor_idx not in visited:
                    visited.add(neighbor_idx)
                    queue.append((neighbor_idx, next_depth))

            for neighbor_idx in downstream_neighbors[node_idx]:
                score = float(base * DOWNSTREAM_WEIGHT)
                if score > scores[root_idx, neighbor_idx]:
                    scores[root_idx, neighbor_idx] = score
                if neighbor_idx not in visited:
                    visited.add(neighbor_idx)
                    queue.append((neighbor_idx, next_depth))

    # Convert directional proximity to symmetric course-course score.
    return np.maximum(scores, scores.T)


def get_prereq_score_matrix(courses: list[dict]) -> np.ndarray:
    """
    Load or compute the cached NxN prerequisite score matrix.

    Cache key is the number of courses (N), matching the project's current
    assumption that N is stable for normal startup.
    """
    n = len(courses)
    if PREREQ_SCORE_MATRIX_PATH.exists():
        try:
            cached = np.load(PREREQ_SCORE_MATRIX_PATH)
            if cached.shape == (n, n):
                return cached.astype(np.float32, copy=False)
        except OSError:
            pass

    matrix = _compute_prereq_scores(courses)
    try:
        PREREQ_SCORE_MATRIX_PATH.parent.mkdir(parents=True, exist_ok=True)
        np.save(PREREQ_SCORE_MATRIX_PATH, matrix.astype(np.float32, copy=False))
    except OSError:
        pass
    return matrix
