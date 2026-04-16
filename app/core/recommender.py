"""
recommender.py — app/core
Generates course recommendations based on semantic similarity and PageRank.
"""

import logging
import numpy as np

from app.core.embedder.similarity import get_top_k_similar
from app.core.config import SIMILARITY_WEIGHT, PAGERANK_WEIGHT

logger = logging.getLogger(__name__)

_K_NEIGHBORS = 20


def recommend(
    input_course_ids: list[str],
    courses: list[dict],
    similarity_matrix: np.ndarray,
    pagerank_scores: dict[str, float],
    top_n: int = 5
) -> list[dict]:
    """
    Given a list of course ids the user is interested in, returns a ranked
    list of recommended courses.

    Logic:
        1. Resolve each input id to its index in courses; warn and skip unknowns.
        2. Collect top-20 semantic neighbors for each input course.
        3. Deduplicate the candidate set, removing courses already in input.
        4. Rank by blended score:
               SIMILARITY_WEIGHT * mean_similarity(candidate, inputs)
             + PAGERANK_WEIGHT   * pagerank_score(candidate)
           where mean_similarity is the arithmetic mean of
           similarity_matrix[candidate_idx][input_idx] over all input indices.
           Missing PageRank entries are treated as 0.0 with a warning.
        5. Return the top_n results.

    Each returned dict is a full course dict with one additional field:
        score: float — the blended score used for ranking.

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
    input_indices = []
    for cid in input_course_ids:
        if cid not in id_to_idx:
            logger.warning("Course id %r not found in courses list; skipping.", cid)
            continue
        input_indices.append(id_to_idx[cid])

    candidate_ids: set[str] = set()
    for idx in input_indices:
        neighbor_indices = get_top_k_similar(idx, similarity_matrix, k=_K_NEIGHBORS)
        for ni in neighbor_indices:
            neighbor_id = courses[ni]["id"]
            if neighbor_id not in input_set:
                candidate_ids.add(neighbor_id)

    def blended_score(cid: str) -> float:
        cidx = id_to_idx.get(cid)
        if cidx is None or not input_indices:
            return 0.0
        mean_sim = float(np.mean(similarity_matrix[cidx, input_indices]))
        pr = pagerank_scores.get(cid)
        if pr is None:
            logger.warning(
                "Course id %r missing from pagerank_scores; treating PageRank as 0.0.", cid
            )
            pr = 0.0
        return SIMILARITY_WEIGHT * mean_sim + PAGERANK_WEIGHT * pr

    ranked = sorted(candidate_ids, key=blended_score, reverse=True)

    results = []
    for cid in ranked[:top_n]:
        course = dict(id_to_course[cid])
        course["score"] = blended_score(cid)
        results.append(course)

    return results
