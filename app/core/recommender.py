"""
recommender.py — app/core
Generates course recommendations based on semantic similarity and PageRank.
"""

import logging
import numpy as np

from app.core.embedder.similarity import get_top_k_similar

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
        4. Rank remaining candidates by pagerank_score (descending).
        5. Return the top_n results.

    Each returned dict is a full course dict with one additional field:
        score: float — the pagerank score used for ranking.

    Args:
        input_course_ids: Course ids the user is already interested in.
        courses: The full merged course list from data_loader.load_courses().
        similarity_matrix: An (N, N) cosine similarity matrix.
        pagerank_scores: A dict mapping course_id -> normalized PageRank score.
        top_n: Maximum number of recommendations to return.

    Returns:
        A list of up to top_n course dicts, each augmented with a 'score' field,
        sorted by descending PageRank score.
    """
    if not input_course_ids:
        return []

    id_to_idx = {c["id"]: i for i, c in enumerate(courses)}
    id_to_course = {c["id"]: c for c in courses}

    input_set = set(input_course_ids)
    candidate_ids: set[str] = set()

    for cid in input_course_ids:
        if cid not in id_to_idx:
            logger.warning("Course id %r not found in courses list; skipping.", cid)
            continue
        idx = id_to_idx[cid]
        neighbor_indices = get_top_k_similar(idx, similarity_matrix, k=_K_NEIGHBORS)
        for ni in neighbor_indices:
            neighbor_id = courses[ni]["id"]
            if neighbor_id not in input_set:
                candidate_ids.add(neighbor_id)

    ranked = sorted(
        candidate_ids,
        key=lambda cid: pagerank_scores.get(cid, 0.0),
        reverse=True
    )

    results = []
    for cid in ranked[:top_n]:
        course = dict(id_to_course[cid])
        course["score"] = pagerank_scores.get(cid, 0.0)
        results.append(course)

    return results
