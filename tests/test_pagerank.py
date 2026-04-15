"""
test_pagerank.py — tests
Unit tests for app/core/graph/pagerank.py
"""

import numpy as np
import pytest

from app.core.graph.builder import build_graph
from app.core.graph.pagerank import compute_pagerank


SAMPLE_COURSES = [
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
        "description": "Data structures.",
        "prerequisites": ["15-112"],
        "department": "CS",
        "units": 10,
        "source": "official",
    },
    {
        "id": "15-213",
        "name": "Introduction to Computer Systems",
        "description": "Systems programming.",
        "prerequisites": ["15-122"],
        "department": "CS",
        "units": 12,
        "source": "official",
    },
]


def _build(courses, threshold=0.0):
    n = len(courses)
    sim = np.full((n, n), 0.5, dtype=np.float32)
    np.fill_diagonal(sim, 1.0)
    return build_graph(courses, sim, similarity_threshold=threshold)


class TestComputePagerank:
    def test_returns_dict_for_all_nodes(self):
        G = _build(SAMPLE_COURSES)
        scores = compute_pagerank(G)
        assert set(scores.keys()) == {"15-112", "15-122", "15-213"}

    def test_scores_normalized_to_0_1(self):
        G = _build(SAMPLE_COURSES)
        scores = compute_pagerank(G)
        for cid, score in scores.items():
            assert 0.0 <= score <= 1.0, f"Score out of range for {cid}: {score}"

    def test_max_score_is_1(self):
        G = _build(SAMPLE_COURSES)
        scores = compute_pagerank(G)
        assert abs(max(scores.values()) - 1.0) < 1e-6

    def test_scores_are_floats(self):
        G = _build(SAMPLE_COURSES)
        scores = compute_pagerank(G)
        for score in scores.values():
            assert isinstance(score, float)

    def test_single_node_graph(self):
        single = [SAMPLE_COURSES[0]]
        n = 1
        sim = np.ones((n, n), dtype=np.float32)
        G = build_graph(single, sim)
        scores = compute_pagerank(G)
        assert "15-112" in scores
        assert abs(scores["15-112"] - 1.0) < 1e-6
