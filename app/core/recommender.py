"""
recommender.py — app/core
Generates course recommendations using cosine similarity, structural similarity,
and PageRank as a three-signal blended score.
"""

import logging
from collections import deque

import numpy as np

from app.core.embedder.similarity import get_top_k_similar
from app.core.config import (
    COSINE_WEIGHT, STRUCTURAL_WEIGHT, PAGERANK_WEIGHT,
    DECAY_ALPHA, DECAY_K,
    UPSTREAM_WEIGHT, DOWNSTREAM_WEIGHT,
)

logger = logging.getLogger(__name__)

_K_NEIGHBORS = 20


def _decay_weight(d: int) -> float:
    """Returns the decay weight for a node at BFS depth d from the source course."""
    return max(DECAY_ALPHA, 1 - DECAY_K * d)


def _weighted_neighborhood(
    course_id: str,
    courses_by_id: dict,
    reverse_index: dict,
) -> dict[str, float]:
    """
    BFS in both upstream (prerequisites) and downstream directions from course_id.
    Returns a dict mapping neighbor_id -> weight, where weight decays with BFS depth.
    course_id itself is never included in its own neighborhood.
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
                # multi-path: keep the strongest signal
                neighborhood[neighbor] = max(neighborhood[neighbor], w)

    return neighborhood


def _weighted_jaccard(n_a: dict[str, float], n_b: dict[str, float]) -> float:
    """Weighted Jaccard similarity between two neighborhood dicts. Returns 0.0 if both empty."""
    all_nodes = set(n_a) | set(n_b)
    if not all_nodes:
        return 0.0
    numerator = sum(min(n_a.get(v, 0.0), n_b.get(v, 0.0)) for v in all_nodes)
    denominator = sum(max(n_a.get(v, 0.0), n_b.get(v, 0.0)) for v in all_nodes)
    return numerator / denominator if denominator > 0.0 else 0.0


def _structural_sim_pair(
    id_a: str,
    id_b: str,
    courses_by_id: dict,
    reverse_index: dict,
) -> float:
    """
    Weighted Jaccard similarity between the prerequisite neighborhoods of id_a and id_b.
    Returns 0.0 if both neighborhoods are empty.
    """
    n_a = _weighted_neighborhood(id_a, courses_by_id, reverse_index)
    n_b = _weighted_neighborhood(id_b, courses_by_id, reverse_index)
    return _weighted_jaccard(n_a, n_b)


def recommend(
    input_course_ids: list[str],
    courses: list[dict],
    similarity_matrix: np.ndarray,
    pagerank_scores: dict[str, float],
    top_n: int = 5,
) -> list[dict]:
    """
    Given a list of course ids the user is interested in, returns a ranked
    list of recommended courses.

    Scoring formula:
        score = COSINE_WEIGHT     * cosine_sim
              + STRUCTURAL_WEIGHT * structural_sim
              + PAGERANK_WEIGHT   * pagerank_score

    cosine_sim is the mean cosine similarity between the candidate and all inputs.
    structural_sim is the mean weighted-Jaccard prereq-neighborhood similarity.
    pagerank_score is the normalized PageRank score.

    Args:
        input_course_ids: Course ids the user is already interested in.
        courses: The full merged course list from data_loader.load_courses().
        similarity_matrix: An (N, N) cosine similarity matrix.
        pagerank_scores: A dict mapping course_id -> normalized PageRank score.
        top_n: Maximum number of recommendations to return.

    Returns:
        A list of up to top_n course dicts, each augmented with a 'score' field,
        sorted by descending blended score.
    """
    if not input_course_ids:
        return []

    id_to_idx = {c["id"]: i for i, c in enumerate(courses)}
    id_to_course = {c["id"]: c for c in courses}

    courses_by_id = {c["id"]: c for c in courses}
    reverse_index: dict[str, list[str]] = {}
    for c in courses:
        for p in c["prerequisites"]:
            reverse_index.setdefault(p, []).append(c["id"])

    input_set = set(input_course_ids)
    input_indices: list[int] = []
    valid_input_ids: list[str] = []
    for cid in input_course_ids:
        if cid not in id_to_idx:
            logger.warning("Course id %r not found in courses list; skipping.", cid)
            continue
        input_indices.append(id_to_idx[cid])
        valid_input_ids.append(cid)

    if not input_indices:
        return []

    candidate_ids: set[str] = set()
    for idx in input_indices:
        for ni in get_top_k_similar(idx, similarity_matrix, k=_K_NEIGHBORS):
            neighbor_id = courses[ni]["id"]
            if neighbor_id not in input_set:
                candidate_ids.add(neighbor_id)

    neighborhood_cache: dict[str, dict[str, float]] = {}

    def get_neighborhood(cid: str) -> dict[str, float]:
        if cid not in neighborhood_cache:
            neighborhood_cache[cid] = _weighted_neighborhood(cid, courses_by_id, reverse_index)
        return neighborhood_cache[cid]

    def blended_score(cid: str) -> float:
        cidx = id_to_idx.get(cid)
        if cidx is None:
            return 0.0

        cosine_sim = float(np.mean(similarity_matrix[cidx, input_indices]))

        n_cid = get_neighborhood(cid)
        struct_sims = [
            _weighted_jaccard(n_cid, get_neighborhood(input_id))
            for input_id in valid_input_ids
        ]
        structural_sim = float(np.mean(struct_sims))

        pr = pagerank_scores.get(cid)
        if pr is None:
            logger.warning(
                "Course id %r missing from pagerank_scores; treating PageRank as 0.0.", cid
            )
            pr = 0.0

        return COSINE_WEIGHT * cosine_sim + STRUCTURAL_WEIGHT * structural_sim + PAGERANK_WEIGHT * pr

    ranked = sorted(candidate_ids, key=blended_score, reverse=True)

    results = []
    for cid in ranked[:top_n]:
        course = dict(id_to_course[cid])
        course["score"] = blended_score(cid)
        results.append(course)

    return results
