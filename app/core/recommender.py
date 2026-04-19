"""
recommender.py — app/core
Generates course recommendations using cosine similarity, structural similarity,
and PageRank as a three-signal score (direct sum, no normalization).
"""

import logging
from collections import deque

import numpy as np

from app.core.config import (
    COSINE_WEIGHT, STRUCTURAL_WEIGHT, PAGERANK_WEIGHT,
    STRUCTURAL_COSINE_THRESHOLD, STRUCTURAL_PAGERANK_THRESHOLD,
    DECAY_ALPHA, DECAY_K,
    UPSTREAM_WEIGHT, DOWNSTREAM_WEIGHT,
)

logger = logging.getLogger(__name__)


def _decay_weight(d: int) -> float:
    return max(DECAY_ALPHA, 1 - DECAY_K * d)


def _weighted_neighborhood(
    course_id: str,
    courses_by_id: dict,
    reverse_index: dict,
) -> dict[str, float]:
    """
    BFS in both upstream (prerequisites) and downstream directions from course_id.
    Returns a dict mapping neighbor_id -> weight, decaying with BFS depth.
    course_id itself is never included.
    """
    neighborhood: dict[str, float] = {}
    visited: set[str] = {course_id}
    queue: deque = deque([(course_id, 0)])

    while queue:
        node, d = queue.popleft()
        upstream = courses_by_id.get(node, {}).get("prerequisites", [])
        downstream = reverse_index.get(node, [])

        for neighbor, dir_weight in [
            *((n, UPSTREAM_WEIGHT) for n in upstream),
            *((n, DOWNSTREAM_WEIGHT) for n in downstream),
        ]:
            w = _decay_weight(d + 1) * dir_weight
            if neighbor not in visited:
                neighborhood[neighbor] = w
                visited.add(neighbor)
                queue.append((neighbor, d + 1))
            elif neighbor in neighborhood:
                neighborhood[neighbor] = max(neighborhood[neighbor], w)

    return neighborhood


def _weighted_jaccard(n_a: dict[str, float], n_b: dict[str, float]) -> float:
    """Weighted Jaccard similarity between two neighborhood dicts."""
    all_nodes = set(n_a) | set(n_b)
    if not all_nodes:
        return 0.0
    numerator = sum(min(n_a.get(v, 0.0), n_b.get(v, 0.0)) for v in all_nodes)
    denominator = sum(max(n_a.get(v, 0.0), n_b.get(v, 0.0)) for v in all_nodes)
    return numerator / denominator if denominator > 0.0 else 0.0


def recommend(
    input_course_ids: list[str],
    courses: list[dict],
    embeddings: np.ndarray,
    pagerank_scores: dict[str, float],
    top_n: int = 5,
) -> tuple[list[dict], dict[str, float]]:
    """
    Scores all courses using three signals and returns the top-N recommendations.

    Scoring formula (weighted sum, no min-max normalization):
        score = COSINE_WEIGHT * cosine_sim + STRUCTURAL_WEIGHT * structural_sim + PAGERANK_WEIGHT * pagerank_score

    cosine_sim: mean cosine similarity to all input courses (numpy batch computation).
    structural_sim: mean weighted-Jaccard of prerequisite neighborhoods against
        each input course, computed on-demand via BFS for all 4000 courses.
    pagerank_score: normalized PageRank from the pre-built graph.

    Args:
        input_course_ids: Course ids the user is already interested in.
        courses: The full merged course list from data_loader.load_courses().
        embeddings: (N, D) L2-normalized embedding matrix.
        pagerank_scores: Dict mapping course_id -> normalized PageRank score.
        top_n: Maximum number of recommendations to return.

    Returns:
        A tuple of:
        - list of up to top_n course dicts, each augmented with a 'score' field
        - dict mapping every non-input course_id -> blended score (for graph display)
    """
    if not input_course_ids:
        return [], {}

    id_to_idx = {c["id"]: i for i, c in enumerate(courses)}
    id_to_course = {c["id"]: c for c in courses}
    input_set = set(input_course_ids)

    input_indices: list[int] = []
    for cid in input_course_ids:
        if cid not in id_to_idx:
            logger.warning("Course id %r not found in courses list; skipping.", cid)
            continue
        input_indices.append(id_to_idx[cid])

    if not input_indices:
        return [], {}

    n = len(courses)
    input_idx_arr = np.array(input_indices)

    # --- Cosine signal (numpy batch) ---
    # embeddings are L2-normalized, so dot product = cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1e-10, norms)
    normalized = embeddings / norms

    input_embs = normalized[input_idx_arr]              # (N_inputs, D)
    cosine_mat = np.clip(
        np.dot(normalized, input_embs.T).astype(np.float32), 0.0, 1.0
    )                                                   # (N, N_inputs)
    cosine_scores = cosine_mat.mean(axis=1)             # (N,)

    # --- PageRank signal ---
    pagerank_arr = np.array(
        [pagerank_scores.get(c["id"], 0.0) for c in courses], dtype=np.float32
    )

    # --- Structural signal (BFS on-demand) ---
    courses_by_id = {c["id"]: c for c in courses}
    reverse_index: dict[str, list[str]] = {}
    for c in courses:
        for p in c["prerequisites"]:
            reverse_index.setdefault(p, []).append(c["id"])

    input_neighborhoods = [
        _weighted_neighborhood(courses[idx]["id"], courses_by_id, reverse_index)
        for idx in input_indices
    ]

    structural_scores = np.zeros(n, dtype=np.float32)
    for i, c in enumerate(courses):
        if c["id"] in input_set:
            continue
        if (
            cosine_scores[i] <= STRUCTURAL_COSINE_THRESHOLD
            or pagerank_arr[i] <= STRUCTURAL_PAGERANK_THRESHOLD
        ):
            continue
        nbr = _weighted_neighborhood(c["id"], courses_by_id, reverse_index)
        if nbr:
            vals = [_weighted_jaccard(nbr, inp_nbr) for inp_nbr in input_neighborhoods]
            structural_scores[i] = float(np.mean(vals))

    # --- Final score: weighted sum (no min-max normalization) ---
    final_scores = (
        COSINE_WEIGHT     * cosine_scores
        + STRUCTURAL_WEIGHT * structural_scores
        + PAGERANK_WEIGHT   * pagerank_arr
    )

    # Mask out input courses
    for idx in input_indices:
        final_scores[idx] = -1.0

    # All non-input scores and breakdowns for graph display
    all_scores: dict[str, float] = {}
    all_breakdowns: dict[str, tuple[float, float, float]] = {}
    for i, c in enumerate(courses):
        if c["id"] in input_set:
            continue
        all_scores[c["id"]] = float(final_scores[i])
        all_breakdowns[c["id"]] = (
            float(cosine_scores[i]),
            float(structural_scores[i]),
            float(pagerank_arr[i]),
        )

    # Top-N results
    top_indices = np.argsort(final_scores)[::-1][:top_n]
    results = []
    for idx in top_indices:
        cid = courses[idx]["id"]
        if cid in input_set:
            continue
        course = dict(id_to_course[cid])
        course["score"] = float(final_scores[idx])
        results.append(course)

    return results, all_scores, all_breakdowns
