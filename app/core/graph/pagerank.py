"""
pagerank.py — app/core/graph
Computes and normalizes PageRank scores for all course nodes.
"""

import networkx as nx
import numpy as np

from app.core.config import PAGERANK_ALPHA, PAGERANK_MATRIX_PATH


def compute_pagerank(graph: nx.DiGraph, alpha: float = PAGERANK_ALPHA) -> dict[str, float]:
    """
    Accepts the graph returned by build_graph().
    Returns a dict mapping course_id -> pagerank_score,
    with scores normalized to [0, 1].

    Normalization divides all scores by the maximum score, so the highest-ranked
    course always has score 1.0.

    Args:
        graph: The directed course graph from builder.build_graph().
        alpha: PageRank damping factor (teleportation probability = 1 - alpha).

    Returns:
        A dict mapping course id strings to float scores in [0, 1].
    """
    node_ids = sorted(graph.nodes())
    n = len(node_ids)
    can_use_cache = alpha == PAGERANK_ALPHA

    if can_use_cache and PAGERANK_MATRIX_PATH.exists():
        try:
            cached = np.load(PAGERANK_MATRIX_PATH)
            if cached.shape == (n, 1):
                return {
                    node_id: float(cached[i, 0])
                    for i, node_id in enumerate(node_ids)
                }
        except OSError:
            pass

    raw_scores = nx.pagerank(graph, alpha=alpha, weight="weight")
    max_score = max(raw_scores.values()) if raw_scores else 1.0
    if max_score == 0.0:
        max_score = 1.0

    normalized = {node: score / max_score for node, score in raw_scores.items()}

    if can_use_cache:
        try:
            score_matrix = np.array(
                [[float(normalized.get(node_id, 0.0))] for node_id in node_ids],
                dtype=np.float32,
            )
            PAGERANK_MATRIX_PATH.parent.mkdir(parents=True, exist_ok=True)
            np.save(PAGERANK_MATRIX_PATH, score_matrix)
        except OSError:
            pass

    return normalized


def get_top_n_by_pagerank(pagerank_scores: dict[str, float], n: int) -> list[str]:
    """
    Returns the top n course ids sorted by descending PageRank score.

    Used by the UI to determine anchor nodes.

    Args:
        pagerank_scores: A dict mapping course_id -> normalized PageRank score.
        n: Number of top course ids to return.

    Returns:
        A list of up to n course id strings, sorted by descending PageRank score.
    """
    sorted_ids = sorted(pagerank_scores, key=lambda cid: pagerank_scores[cid], reverse=True)
    return sorted_ids[:n]
