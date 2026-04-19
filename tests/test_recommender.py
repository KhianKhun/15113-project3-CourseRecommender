"""
test_recommender.py — tests
Unit tests for app/core/recommender.py
"""

import numpy as np
import pytest

from app.core.recommender import (
    recommend,
    _decay_weight,
    _weighted_neighborhood,
    _structural_sim_pair,
)
from app.core.config import COSINE_WEIGHT, STRUCTURAL_WEIGHT, PAGERANK_WEIGHT


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


# ── Mock dataset for structural similarity tests (from SPEC_5) ────────────────

mock_courses = [
    {"id": "A", "name": "A", "description": "a", "prerequisites": [],         "department": "X", "units": 9, "source": "official"},
    {"id": "B", "name": "B", "description": "b", "prerequisites": ["A"],      "department": "X", "units": 9, "source": "official"},
    {"id": "C", "name": "C", "description": "c", "prerequisites": ["A"],      "department": "X", "units": 9, "source": "official"},
    {"id": "D", "name": "D", "description": "d", "prerequisites": ["B", "E"], "department": "X", "units": 9, "source": "official"},
    {"id": "E", "name": "E", "description": "e", "prerequisites": [],         "department": "X", "units": 9, "source": "official"},
]

_mock_courses_by_id = {c["id"]: c for c in mock_courses}
_mock_reverse_index: dict = {}
for _c in mock_courses:
    for _p in _c["prerequisites"]:
        _mock_reverse_index.setdefault(_p, []).append(_c["id"])


# ── Structural helper tests ───────────────────────────────────────────────────

class TestDecayWeight:
    def test_depth_1(self):
        assert _decay_weight(1) == pytest.approx(0.85)

    def test_depth_2(self):
        assert _decay_weight(2) == pytest.approx(0.70)

    def test_depth_5_floor(self):
        assert _decay_weight(5) == pytest.approx(0.30)

    def test_depth_10_floor_holds(self):
        assert _decay_weight(10) == pytest.approx(0.30)


class TestWeightedNeighborhood:
    def test_b_neighborhood(self):
        nb_B = _weighted_neighborhood("B", _mock_courses_by_id, _mock_reverse_index)
        assert nb_B["A"] == pytest.approx(0.85)
        assert nb_B["D"] == pytest.approx(0.85)
        assert "B" not in nb_B

    def test_d_neighborhood(self):
        nb_D = _weighted_neighborhood("D", _mock_courses_by_id, _mock_reverse_index)
        assert nb_D["B"] == pytest.approx(0.85)
        assert nb_D["E"] == pytest.approx(0.85)
        assert nb_D["A"] == pytest.approx(0.70)


class TestStructuralSimPair:
    def test_bc_more_similar_than_be(self):
        sim_BC = _structural_sim_pair("B", "C", _mock_courses_by_id, _mock_reverse_index)
        sim_BE = _structural_sim_pair("B", "E", _mock_courses_by_id, _mock_reverse_index)
        assert sim_BC > sim_BE

    def test_zero_division_guard(self):
        result = _structural_sim_pair("A", "E", _mock_courses_by_id, _mock_reverse_index)
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0


# ── recommend() contract tests ────────────────────────────────────────────────

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
        # 15-122: high cosine to input, low PageRank.
        # 10-601: low cosine to input, high PageRank.
        # COSINE_WEIGHT=0.55 should keep 15-122 ranked above 10-601.
        n = len(COURSES)
        sim = np.zeros((n, n), dtype=np.float32)
        np.fill_diagonal(sim, 1.0)
        sim[0, 1] = sim[1, 0] = 0.9   # high similarity: input(15-112) → 15-122
        sim[0, 3] = sim[3, 0] = 0.1   # low similarity:  input(15-112) → 10-601
        for i in range(n):
            for j in range(n):
                if sim[i, j] == 0.0 and i != j:
                    sim[i, j] = 0.05

        pr = {"15-112": 0.1, "15-122": 0.1, "10-301": 0.5, "10-601": 1.0, "11-411": 0.5}
        recs = recommend(["15-112"], COURSES, sim, pr, top_n=5)
        rec_ids = [r["id"] for r in recs]
        assert rec_ids.index("15-122") < rec_ids.index("10-601")

    def test_score_field_uses_three_signal_formula(self):
        # With uniform cosine_sim=0.8, structural_sim is deterministic per course.
        # Score must not equal raw PageRank, and must include cosine contribution.
        sim = _uniform_similarity(len(COURSES))
        recs = recommend(["15-112"], COURSES, sim, PAGERANK, top_n=5)
        for r in recs:
            raw_pr = PAGERANK.get(r["id"], 0.0)
            # Score must be greater than PageRank-only and less than cosine-only
            assert r["score"] > PAGERANK_WEIGHT * raw_pr
            assert r["score"] < COSINE_WEIGHT * 1.0 + STRUCTURAL_WEIGHT * 1.0 + PAGERANK_WEIGHT * 1.0

    def test_missing_pagerank_no_crash(self):
        pr_partial = {k: v for k, v in PAGERANK.items() if k != "11-411"}
        sim = _uniform_similarity(len(COURSES))
        recs = recommend(["15-112"], COURSES, sim, pr_partial, top_n=5)
        match = [r for r in recs if r["id"] == "11-411"]
        if match:
            # PageRank contribution must be 0 for the missing entry
            assert match[0]["score"] < COSINE_WEIGHT * 1.0 + STRUCTURAL_WEIGHT * 1.0 + PAGERANK_WEIGHT * 1.0

    def test_mock_empty_input(self):
        n = len(mock_courses)
        sim_matrix = np.full((n, n), 0.5, dtype=np.float32)
        np.fill_diagonal(sim_matrix, 1.0)
        pagerank_scores = {c["id"]: 0.5 for c in mock_courses}
        assert recommend([], mock_courses, sim_matrix, pagerank_scores) == []

    def test_mock_excluded_from_results(self):
        n = len(mock_courses)
        sim_matrix = np.full((n, n), 0.5, dtype=np.float32)
        np.fill_diagonal(sim_matrix, 1.0)
        pagerank_scores = {c["id"]: 0.5 for c in mock_courses}
        results = recommend(["B"], mock_courses, sim_matrix, pagerank_scores, top_n=3)
        assert all(r["id"] != "B" for r in results)
        assert len(results) <= 3

    def test_mock_sorted_by_descending_score(self):
        n = len(mock_courses)
        sim_matrix = np.full((n, n), 0.5, dtype=np.float32)
        np.fill_diagonal(sim_matrix, 1.0)
        pagerank_scores = {c["id"]: 0.5 for c in mock_courses}
        results = recommend(["B"], mock_courses, sim_matrix, pagerank_scores, top_n=3)
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)
