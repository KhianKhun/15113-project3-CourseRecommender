"""
test_recommender.py — tests
Unit tests for app/core/recommender.py
"""

import numpy as np
import pytest

from app.core.recommender import recommend


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
