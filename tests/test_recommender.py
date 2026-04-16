"""
test_recommender.py — tests
Unit tests for app/core/recommender.py
"""

import numpy as np
import pytest

from app.core.recommender import recommend
from app.core.config import SIMILARITY_WEIGHT, PAGERANK_WEIGHT


COURSES = [
    {
        "id": "15-112",
        "name": "Fundamentals of Programming",
        "description": "Intro to programming.",
        "prerequisites": [],
        "department": "CS",
        "units": 12,
        "source": "official",
    },
    {
        "id": "15-122",
        "name": "Principles of Imperative Computation",
        "description": "Data structures and algorithms.",
        "prerequisites": ["15-112"],
        "department": "CS",
        "units": 10,
        "source": "official",
    },
    {
        "id": "10-301",
        "name": "Introduction to Machine Learning",
        "description": "Machine learning and statistics.",
        "prerequisites": [],
        "department": "ML",
        "units": 12,
        "source": "official",
    },
    {
        "id": "10-601",
        "name": "Machine Learning",
        "description": "Advanced machine learning topics.",
        "prerequisites": ["10-301"],
        "department": "ML",
        "units": 12,
        "source": "official",
    },
    {
        "id": "11-411",
        "name": "Natural Language Processing",
        "description": "NLP techniques and models.",
        "prerequisites": ["10-301"],
        "department": "LTI",
        "units": 12,
        "source": "official",
    },
]

PAGERANK = {
    "15-112": 0.3,
    "15-122": 0.5,
    "10-301": 0.7,
    "10-601": 1.0,
    "11-411": 0.8,
}


def _uniform_similarity(n: int) -> np.ndarray:
    """All pairs have similarity 0.8 (excluding self)."""
    mat = np.full((n, n), 0.8, dtype=np.float32)
    np.fill_diagonal(mat, 1.0)
    return mat


class TestRecommend:
    def test_returns_list(self):
        sim = _uniform_similarity(len(COURSES))
        recs = recommend(["15-112"], COURSES, sim, PAGERANK)
        assert isinstance(recs, list)

    def test_excludes_input_courses(self):
        sim = _uniform_similarity(len(COURSES))
        recs = recommend(["15-112"], COURSES, sim, PAGERANK)
        rec_ids = {r["id"] for r in recs}
        assert "15-112" not in rec_ids

    def test_respects_top_n(self):
        sim = _uniform_similarity(len(COURSES))
        recs = recommend(["15-112"], COURSES, sim, PAGERANK, top_n=2)
        assert len(recs) <= 2

    def test_each_result_has_score_field(self):
        sim = _uniform_similarity(len(COURSES))
        recs = recommend(["15-112"], COURSES, sim, PAGERANK)
        for r in recs:
            assert "score" in r
            assert isinstance(r["score"], float)

    def test_sorted_by_descending_score(self):
        sim = _uniform_similarity(len(COURSES))
        recs = recommend(["15-112"], COURSES, sim, PAGERANK, top_n=5)
        scores = [r["score"] for r in recs]
        assert scores == sorted(scores, reverse=True)

    def test_unknown_input_id_ignored(self):
        sim = _uniform_similarity(len(COURSES))
        recs = recommend(["99-999"], COURSES, sim, PAGERANK)
        assert recs == []

    def test_empty_input_returns_empty(self):
        sim = _uniform_similarity(len(COURSES))
        recs = recommend([], COURSES, sim, PAGERANK)
        assert recs == []

    def test_blended_score_dominance(self):
        # Candidate A (15-122): high similarity to input, low PageRank.
        # Candidate B (10-601): low similarity to input, high PageRank.
        # With SIMILARITY_WEIGHT=0.7, A should rank above B.
        n = len(COURSES)
        # input = 15-112 (idx 0), A = 15-122 (idx 1), B = 10-601 (idx 3)
        sim = np.zeros((n, n), dtype=np.float32)
        np.fill_diagonal(sim, 1.0)
        sim[0, 1] = sim[1, 0] = 0.9   # high similarity: input → A
        sim[0, 3] = sim[3, 0] = 0.1   # low similarity:  input → B
        # fill remaining pairs so neighbors are found
        for i in range(n):
            for j in range(n):
                if sim[i, j] == 0.0 and i != j:
                    sim[i, j] = 0.05

        pr = {"15-112": 0.1, "15-122": 0.1, "10-301": 0.5, "10-601": 1.0, "11-411": 0.5}
        recs = recommend(["15-112"], COURSES, sim, pr, top_n=5)
        rec_ids = [r["id"] for r in recs]
        assert rec_ids.index("15-122") < rec_ids.index("10-601")

    def test_score_field_is_blended_not_pagerank(self):
        # Score must differ from raw PageRank when similarity != 1.0.
        sim = _uniform_similarity(len(COURSES))  # similarity = 0.8 for all pairs
        recs = recommend(["15-112"], COURSES, sim, PAGERANK, top_n=5)
        for r in recs:
            raw_pr = PAGERANK.get(r["id"], 0.0)
            expected_blended = SIMILARITY_WEIGHT * 0.8 + PAGERANK_WEIGHT * raw_pr
            assert abs(r["score"] - expected_blended) < 1e-5, (
                f"{r['id']}: score {r['score']:.5f} != blended {expected_blended:.5f}"
            )

    def test_missing_pagerank_no_crash(self):
        # 11-411 is absent from pagerank_scores; recommend must not raise.
        pr_partial = {k: v for k, v in PAGERANK.items() if k != "11-411"}
        sim = _uniform_similarity(len(COURSES))
        recs = recommend(["15-112"], COURSES, sim, pr_partial, top_n=5)
        # 11-411 should appear with PageRank contribution = 0.0
        match = [r for r in recs if r["id"] == "11-411"]
        if match:
            expected = SIMILARITY_WEIGHT * 0.8 + PAGERANK_WEIGHT * 0.0
            assert abs(match[0]["score"] - expected) < 1e-5
