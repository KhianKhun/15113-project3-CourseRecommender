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
    STRUCTURAL_MATRIX_PATH,
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


def compute_structural_matrix(courses: list[dict]) -> np.ndarray:
    """
    Precomputes the N×N weighted-Jaccard structural similarity matrix for all courses.

    Loads from STRUCTURAL_MATRIX_PATH if cached and row count matches.
    Otherwise runs BFS for every course, computes all pairwise Jaccard scores,
    saves the result, and returns it.

    Args:
        courses: The full merged course list from data_loader.load_courses().

    Returns:
        A symmetric (N, N) float32 matrix where entry [i, j] is the weighted-Jaccard
        structural similarity between courses[i] and courses[j].
    """
    n = len(courses)

    if STRUCTURAL_MATRIX_PATH.exists():
        cached = np.load(STRUCTURAL_MATRIX_PATH)
        if cached.shape == (n, n):
            return cached

    courses_by_id = {c["id"]: c for c in courses}
    reverse_index: dict[str, list[str]] = {}
    for c in courses:
        for p in c["prerequisites"]:
            reverse_index.setdefault(p, []).append(c["id"])

    neighborhoods = [
        _weighted_neighborhood(c["id"], courses_by_id, reverse_index)
        for c in courses
    ]

    matrix = np.zeros((n, n), dtype=np.float32)
    for i in range(n):
        for j in range(i + 1, n):
            sim = _weighted_jaccard(neighborhoods[i], neighborhoods[j])
            matrix[i, j] = sim
            matrix[j, i] = sim

    STRUCTURAL_MATRIX_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.save(STRUCTURAL_MATRIX_PATH, matrix)

    return matrix


def recommend(
    input_course_ids: list[str],
    courses: list[dict],
    similarity_matrix: np.ndarray,
    structural_matrix: np.ndarray,
    pagerank_scores: dict[str, float],
    top_n: int = 5,
) -> list[dict]:
    """
    Given a list of course ids the user is interested in, returns a ranked
    list of recommended courses.

    Scoring formula:
        score = COSINE_WEIGHT     * norm(cosine_sim)
              + STRUCTURAL_WEIGHT * norm(structural_sim)
              + PAGERANK_WEIGHT   * norm(pagerank_score)

    Each signal is min-max normalized within the candidate set before blending,
    so relative differences are preserved even when raw values cluster in a narrow range
    (e.g. specter2 cosine similarities concentrated around 0.88-0.93).

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

    def _minmax(values: list[float]) -> list[float]:
        lo, hi = min(values), max(values)
        if hi == lo:
            return [0.0] * len(values)
        return [(v - lo) / (hi - lo) for v in values]

    # Compute raw signals for all candidates
    candidates = list(candidate_ids)
    raw_cosine: list[float] = []
    raw_structural: list[float] = []
    raw_pagerank: list[float] = []

    for cid in candidates:
        cidx = id_to_idx.get(cid)

        cosine_sim = float(np.mean(similarity_matrix[cidx, input_indices])) if cidx is not None else 0.0
        structural_sim = float(np.mean(structural_matrix[cidx, input_indices])) if cidx is not None else 0.0

        pr = pagerank_scores.get(cid)
        if pr is None:
            logger.warning(
                "Course id %r missing from pagerank_scores; treating PageRank as 0.0.", cid
            )
            pr = 0.0

        raw_cosine.append(cosine_sim)
        raw_structural.append(structural_sim)
        raw_pagerank.append(pr)

    # Normalize each signal within the candidate set before blending
    norm_cosine     = _minmax(raw_cosine)
    norm_structural = _minmax(raw_structural)
    norm_pagerank   = _minmax(raw_pagerank)

    scored = [
        (
            cid,
            COSINE_WEIGHT     * norm_cosine[i]
            + STRUCTURAL_WEIGHT * norm_structural[i]
            + PAGERANK_WEIGHT   * norm_pagerank[i],
        )
        for i, cid in enumerate(candidates)
    ]
    scored.sort(key=lambda x: x[1], reverse=True)

    results = []
    for cid, score in scored[:top_n]:
        course = dict(id_to_course[cid])
        course["score"] = score
        results.append(course)

    return results
