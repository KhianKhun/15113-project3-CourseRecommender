"""
prereq.py — app/core/graph
Extracts the transitive prerequisite subgraph for a target course.
"""

from collections import deque

import networkx as nx


def find_prereq_path(
    graph: nx.DiGraph,
    target_id: str
) -> nx.DiGraph:
    """
    Returns a subgraph containing all prerequisite courses required to reach
    target_id, as a directed subgraph.

    Performs a reverse BFS from target_id following only edges of
    type="prereq" in the reverse direction, collecting all ancestor nodes.
    The target node itself is included in the returned subgraph.

    Args:
        graph: The directed course graph from builder.build_graph().
        target_id: The course id to find prerequisites for.

    Returns:
        A nx.DiGraph subgraph containing target_id and all its transitive
        prerequisites, with only the prerequisite edges between them.

    Raises:
        ValueError: If target_id is not present in the graph.
    """
    if target_id not in graph:
        raise ValueError(f"Course {target_id} not found in graph")

    # BFS walking incoming prereq edges from target back to roots
    visited: set[str] = set()
    queue: deque[str] = deque([target_id])

    while queue:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        for source, _, data in graph.in_edges(node, data=True):
            if data.get("type") == "prereq" and source not in visited:
                queue.append(source)

    # Build a prereq-only subgraph over the visited nodes
    prereq_edges = [
        (u, v) for u, v, data in graph.edges(data=True)
        if data.get("type") == "prereq" and u in visited and v in visited
    ]
    subgraph = nx.DiGraph()
    for node in visited:
        subgraph.add_node(node, **graph.nodes[node])
    subgraph.add_edges_from(prereq_edges)
    return subgraph


def get_prereq_depth(
    graph: nx.DiGraph,
    target_id: str
) -> dict[str, int]:
    """
    Returns a dict mapping each course id in the prerequisite subgraph
    to its depth level, where target_id is at depth 0, its direct
    prerequisites are at depth 1, their prerequisites at depth 2, and
    so on. Used by the UI to assign vertical positions in the prereq
    visualization.

    Performs a BFS over the subgraph returned by find_prereq_path,
    traversing edges in reverse (from target toward roots) and tracking
    the distance from target_id.

    Args:
        graph: The directed course graph from builder.build_graph().
        target_id: The course id to measure depth from.

    Returns:
        A dict mapping course id strings to integer depth values.

    Raises:
        ValueError: If target_id is not present in the graph.
    """
    prereq_subgraph = find_prereq_path(graph, target_id)

    depth: dict[str, int] = {target_id: 0}
    queue: deque[str] = deque([target_id])

    while queue:
        node = queue.popleft()
        current_depth = depth[node]
        for source, _ in prereq_subgraph.in_edges(node):
            if source not in depth:
                depth[source] = current_depth + 1
                queue.append(source)

    return depth
