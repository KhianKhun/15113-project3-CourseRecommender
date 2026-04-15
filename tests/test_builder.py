"""
test_builder.py — tests
Unit tests for app/core/graph/builder.py
"""

import numpy as np
import networkx as nx
import pytest

from app.core.graph.builder import build_graph


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
        "prerequisites": ["15-122"],
        "department": "ML",
        "units": 12,
        "source": "official",
    },
]


def _identity_similarity(n: int) -> np.ndarray:
    """Returns an (N, N) identity-like similarity matrix (only self-similarity = 1)."""
    return np.eye(n, dtype=np.float32)


def _high_similarity(n: int) -> np.ndarray:
    """Returns an (N, N) matrix where all pairs have similarity 0.9."""
    mat = np.full((n, n), 0.9, dtype=np.float32)
    np.fill_diagonal(mat, 1.0)
    return mat


class TestBuildGraph:
    def test_nodes_created_for_all_courses(self):
        sim = _identity_similarity(3)
        G = build_graph(SAMPLE_COURSES, sim)
        assert set(G.nodes()) == {"15-112", "15-122", "10-301"}

    def test_node_stores_course_dict(self):
        sim = _identity_similarity(3)
        G = build_graph(SAMPLE_COURSES, sim)
        node_data = G.nodes["15-112"]
        assert node_data["name"] == "Fundamentals of Programming"
        assert node_data["department"] == "CS"

    def test_prereq_edges_added(self):
        sim = _identity_similarity(3)
        G = build_graph(SAMPLE_COURSES, sim)
        assert G.has_edge("15-112", "15-122")
        assert G.edges["15-112", "15-122"]["type"] == "prereq"

    def test_no_semantic_edges_below_threshold(self):
        sim = _identity_similarity(3)
        G = build_graph(SAMPLE_COURSES, sim, similarity_threshold=0.3)
        semantic_edges = [
            (u, v) for u, v, d in G.edges(data=True) if d.get("type") == "semantic"
        ]
        assert semantic_edges == []

    def test_semantic_edges_added_above_threshold(self):
        sim = _high_similarity(3)
        G = build_graph(SAMPLE_COURSES, sim, similarity_threshold=0.3)
        semantic_edges = [
            (u, v) for u, v, d in G.edges(data=True) if d.get("type") == "semantic"
        ]
        assert len(semantic_edges) > 0

    def test_semantic_edge_has_weight(self):
        sim = _high_similarity(3)
        G = build_graph(SAMPLE_COURSES, sim, similarity_threshold=0.3)
        for u, v, data in G.edges(data=True):
            if data.get("type") == "semantic":
                assert "weight" in data
                assert 0.0 <= data["weight"] <= 1.0
                break

    def test_returns_digraph(self):
        sim = _identity_similarity(3)
        G = build_graph(SAMPLE_COURSES, sim)
        assert isinstance(G, nx.DiGraph)

    def test_missing_prereq_not_in_graph(self):
        courses_with_missing_prereq = [
            {
                "id": "10-601",
                "name": "Machine Learning",
                "description": "Advanced ML.",
                "prerequisites": ["99-999"],  # Does not exist
                "department": "ML",
                "units": 12,
                "source": "official",
            }
        ]
        sim = np.eye(1, dtype=np.float32)
        G = build_graph(courses_with_missing_prereq, sim)
        # Edge to missing prereq should not be added
        assert not G.has_edge("99-999", "10-601")
