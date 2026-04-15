"""
test_prereq.py — tests
Unit tests for app/core/graph/prereq.py
"""

import pytest
import networkx as nx

from app.core.graph.prereq import find_prereq_path, get_prereq_depth


def _build_mock_graph() -> nx.DiGraph:
    """
    Builds a small mock graph for testing.

    Prerequisite chain:
        10-100 --prereq--> 10-200 --prereq--> 10-300
                           10-201 --prereq--> 10-300

    Semantic edge (should be ignored by prereq traversal):
        10-100 --semantic--> 10-201

    Node 10-999 is isolated (no edges).
    """
    g = nx.DiGraph()
    courses = [
        {"id": "10-100", "name": "Course A"},
        {"id": "10-200", "name": "Course B"},
        {"id": "10-201", "name": "Course C"},
        {"id": "10-300", "name": "Course D"},
        {"id": "10-999", "name": "Unrelated"},
    ]
    for c in courses:
        g.add_node(c["id"], **c)

    # prereq edges: source is the prereq, target is the course that requires it
    g.add_edge("10-100", "10-200", type="prereq")
    g.add_edge("10-200", "10-300", type="prereq")
    g.add_edge("10-201", "10-300", type="prereq")
    # semantic edge — must not appear in prereq subgraph
    g.add_edge("10-100", "10-201", type="semantic", weight=0.75)
    return g


class TestFindPrereqPath:
    def test_all_prereq_nodes_present(self):
        g = _build_mock_graph()
        sub = find_prereq_path(g, "10-300")
        assert "10-300" in sub
        assert "10-200" in sub
        assert "10-201" in sub
        assert "10-100" in sub

    def test_target_included_in_subgraph(self):
        g = _build_mock_graph()
        sub = find_prereq_path(g, "10-300")
        assert "10-300" in sub

    def test_unrelated_node_absent(self):
        g = _build_mock_graph()
        sub = find_prereq_path(g, "10-300")
        assert "10-999" not in sub

    def test_semantic_edge_absent_from_subgraph(self):
        g = _build_mock_graph()
        sub = find_prereq_path(g, "10-300")
        # The semantic edge 10-100 -> 10-201 should not appear
        assert not sub.has_edge("10-100", "10-201")

    def test_prereq_edges_present_in_subgraph(self):
        g = _build_mock_graph()
        sub = find_prereq_path(g, "10-300")
        assert sub.has_edge("10-100", "10-200")
        assert sub.has_edge("10-200", "10-300")
        assert sub.has_edge("10-201", "10-300")

    def test_leaf_target_returns_single_node(self):
        """A course with no prerequisites returns only itself."""
        g = _build_mock_graph()
        sub = find_prereq_path(g, "10-100")
        assert set(sub.nodes()) == {"10-100"}
        assert sub.number_of_edges() == 0

    def test_unknown_target_raises_value_error(self):
        g = _build_mock_graph()
        with pytest.raises(ValueError, match="Course 99-999 not found in graph"):
            find_prereq_path(g, "99-999")


class TestGetPrereqDepth:
    def test_target_is_depth_zero(self):
        g = _build_mock_graph()
        depths = get_prereq_depth(g, "10-300")
        assert depths["10-300"] == 0

    def test_direct_prereqs_are_depth_one(self):
        g = _build_mock_graph()
        depths = get_prereq_depth(g, "10-300")
        assert depths["10-200"] == 1
        assert depths["10-201"] == 1

    def test_transitive_prereq_is_depth_two(self):
        g = _build_mock_graph()
        depths = get_prereq_depth(g, "10-300")
        assert depths["10-100"] == 2

    def test_all_nodes_have_depth_entry(self):
        g = _build_mock_graph()
        depths = get_prereq_depth(g, "10-300")
        for node in ["10-100", "10-200", "10-201", "10-300"]:
            assert node in depths

    def test_unrelated_node_absent_from_depth(self):
        g = _build_mock_graph()
        depths = get_prereq_depth(g, "10-300")
        assert "10-999" not in depths

    def test_leaf_target_depth_is_only_zero(self):
        g = _build_mock_graph()
        depths = get_prereq_depth(g, "10-100")
        assert depths == {"10-100": 0}

    def test_unknown_target_raises_value_error(self):
        g = _build_mock_graph()
        with pytest.raises(ValueError):
            get_prereq_depth(g, "99-999")
