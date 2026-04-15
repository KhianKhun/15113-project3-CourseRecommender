"""
pagerank.py — app/core/graph
Computes and normalizes PageRank scores for all course nodes.
"""

import networkx as nx


def compute_pagerank(graph: nx.DiGraph) -> dict[str, float]:
    """
    Accepts the graph returned by build_graph().
    Returns a dict mapping course_id -> pagerank_score,
    with scores normalized to [0, 1].

    Uses NetworkX's built-in PageRank implementation with default alpha=0.85.
    Normalization divides all scores by the maximum score, so the highest-ranked
    course always has score 1.0.

    Args:
        graph: The directed course graph from builder.build_graph().

    Returns:
        A dict mapping course id strings to float scores in [0, 1].
    """
    raw_scores = nx.pagerank(graph, alpha=0.85, weight="weight")

    max_score = max(raw_scores.values()) if raw_scores else 1.0
    if max_score == 0.0:
        max_score = 1.0

    return {node: score / max_score for node, score in raw_scores.items()}


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
