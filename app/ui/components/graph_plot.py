"""
graph_plot.py — app/ui/components
Builds and returns Plotly figures for the semantic graph and prerequisite tree.
No Streamlit calls are made here — only figure construction.
"""

import numpy as np
import networkx as nx
import plotly.graph_objects as go

from app.core.config import DEFAULT_ANCHOR_COUNT
from app.core.graph.pagerank import get_top_n_by_pagerank
from app.ui.components.tooltip import format_tooltip

# Department → color mapping. Unknown departments fall back to DEPT_DEFAULT.
DEPT_COLORS: dict[str, str] = {
    "CS": "#636EFA",
    "ML": "#EF553B",
    "ECE": "#00CC96",
    "MATH": "#AB63FA",
    "STATS": "#FFA15A",
    "IS": "#19D3F3",
    "BIO": "#FF6692",
    "PHYS": "#B6E880",
    "CHEM": "#FF97FF",
    "ECON": "#FECB52",
    "ARCH": "#72B7B2",
    "ART": "#E45756",
    "MUS": "#54A24B",
    "PHIL": "#4C78A8",
    "PSY": "#F58518",
    "HCI": "#79706E",
    "SDS": "#BAB0AC",
    "CIT": "#D67195",
    "INI": "#A2C8EC",
    "LTI": "#FFBF79",
}
DEPT_DEFAULT = "#AAAAAA"

# Visual constants
_SELECTED_COLOR = "#FFD700"   # bright yellow
_ANCHOR_COLOR = "#FF7F50"     # coral/orange
_MIN_SIZE = 8
_MAX_SIZE = 24
_SELECTED_SIZE_BONUS = 4


def render_graph_plot(
    coords: np.ndarray,
    courses: list[dict],
    pagerank_scores: dict[str, float],
    n_components: int,
    top_k: int,
    selected_ids: list[str],
    explained_variance: float,
) -> go.Figure:
    """
    Builds an interactive Plotly scatter plot for the semantic graph view.

    Selects the top top_k courses by PageRank, applies size/color/label rules,
    and renders either a 2D or 3D figure depending on n_components.

    Node sizing: proportional to PageRank, scaled to [_MIN_SIZE, _MAX_SIZE].
    Node coloring priority: selected (yellow) > anchor (coral) > dept color.
    Node labels: anchor nodes always show their course id; others are hidden.
    Edges: semantic edges only, rendered for pairs where both endpoints are in top_k.

    Args:
        coords: (N, n_components) coordinate array from reduce_dimensions().
        courses: The full course list (row order matches coords).
        pagerank_scores: Dict mapping course_id -> normalized score in [0, 1].
        n_components: 2 for 2D, 3 for 3D.
        top_k: Number of top-PageRank nodes to display.
        selected_ids: Course ids that should be highlighted yellow.
        explained_variance: Variance ratio sum from PCA (for display, not used here).

    Returns:
        A Plotly Figure object ready for st.plotly_chart().
    """
    top_k_ids = get_top_n_by_pagerank(pagerank_scores, top_k)
    anchor_ids = set(get_top_n_by_pagerank(pagerank_scores, DEFAULT_ANCHOR_COUNT))
    selected_set = set(selected_ids)

    id_to_idx = {c["id"]: i for i, c in enumerate(courses)}
    id_to_course = {c["id"]: c for c in courses}

    # Build per-node arrays
    xs, ys, zs = [], [], []
    sizes, colors, labels, tooltips = [], [], [], []

    max_score = max(pagerank_scores.values()) if pagerank_scores else 1.0
    min_score = min(pagerank_scores.values()) if pagerank_scores else 0.0
    score_range = max(max_score - min_score, 1e-9)

    for cid in top_k_ids:
        if cid not in id_to_idx:
            continue
        idx = id_to_idx[cid]
        course = id_to_course[cid]
        score = pagerank_scores.get(cid, 0.0)

        # Coordinates
        xs.append(float(coords[idx, 0]))
        ys.append(float(coords[idx, 1]))
        if n_components == 3:
            zs.append(float(coords[idx, 2]))

        # Size: scale [min_score, max_score] → [_MIN_SIZE, _MAX_SIZE]
        norm = (score - min_score) / score_range
        base_size = _MIN_SIZE + norm * (_MAX_SIZE - _MIN_SIZE)
        if cid in selected_set:
            base_size += _SELECTED_SIZE_BONUS
        sizes.append(base_size)

        # Color priority: selected > anchor > dept
        if cid in selected_set:
            colors.append(_SELECTED_COLOR)
        elif cid in anchor_ids:
            colors.append(_ANCHOR_COLOR)
        else:
            dept = course.get("department", "")
            colors.append(DEPT_COLORS.get(dept, DEPT_DEFAULT))

        # Label: show for anchor nodes only
        labels.append(cid if cid in anchor_ids else "")

        # Hover tooltip
        tooltips.append(format_tooltip(course, score))

    fig = go.Figure()

    # Edges (semantic only, both endpoints must be in top_k)
    top_k_set = set(top_k_ids)
    # We reconstruct approximate semantic connectivity via coords proximity;
    # without the graph object, we skip explicit edge rendering here.
    # (The graph is not passed into this function per SPEC4 interface contract.)

    if n_components == 2:
        fig.add_trace(go.Scatter(
            x=xs,
            y=ys,
            mode="markers+text",
            marker=dict(
                size=sizes,
                color=colors,
                opacity=0.9,
                line=dict(width=1, color="rgba(255,255,255,0.4)"),
            ),
            text=labels,
            textposition="top center",
            hovertext=tooltips,
            hoverinfo="text",
            showlegend=False,
        ))
        fig.update_layout(
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
            yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
            margin=dict(l=0, r=0, t=20, b=0),
            height=600,
        )
    else:
        fig.add_trace(go.Scatter3d(
            x=xs,
            y=ys,
            z=zs,
            mode="markers+text",
            marker=dict(
                size=[s * 0.6 for s in sizes],
                color=colors,
                opacity=0.85,
                line=dict(width=0.5, color="rgba(255,255,255,0.3)"),
            ),
            text=labels,
            textposition="top center",
            hovertext=tooltips,
            hoverinfo="text",
            showlegend=False,
        ))
        fig.update_layout(
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            scene=dict(
                xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
                yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
                zaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
                bgcolor="rgba(0,0,0,0)",
            ),
            margin=dict(l=0, r=0, t=20, b=0),
            height=600,
        )

    return fig


def render_prereq_plot(
    subgraph: nx.DiGraph,
    depth_values: dict[str, int],
    target_id: str,
) -> go.Figure:
    """
    Builds a hierarchical Plotly figure for the prerequisite tree.

    Nodes are positioned by depth level (depth 0 = target at top, deeper = lower).
    Nodes at the same depth are spread evenly along the x-axis.
    Colors interpolate from bright coral (depth 0) to light orange (deepest).
    Edges are rendered as arrows pointing upward (prereq → course).
    All nodes display their course id as a label; hover shows the full course name.

    Args:
        subgraph: Prerequisite subgraph from find_prereq_path().
        depth_values: Dict mapping course_id -> depth from get_prereq_depth().
        target_id: The root course id (placed at depth 0).

    Returns:
        A Plotly Figure with height=500.
    """
    max_depth = max(depth_values.values()) if depth_values else 0

    # Group nodes by depth
    depth_to_nodes: dict[int, list[str]] = {}
    for nid, d in depth_values.items():
        depth_to_nodes.setdefault(d, []).append(nid)

    # Compute (x, y) positions: depth 0 at top (y=0), deeper → lower y
    pos: dict[str, tuple[float, float]] = {}
    for depth, nodes in depth_to_nodes.items():
        y = -depth
        count = len(nodes)
        for i, nid in enumerate(sorted(nodes)):
            x = (i - (count - 1) / 2.0) / max(count, 1)
            pos[nid] = (x, y)

    def _depth_color(depth: int) -> str:
        """Interpolate from coral (#EF553B at depth 0) to light peach (#FFD6C8 at max)."""
        if max_depth == 0:
            return "#EF553B"
        t = depth / max_depth
        r = int(0xEF + t * (0xFF - 0xEF))
        g = int(0x55 + t * (0xD6 - 0x55))
        b = int(0x3B + t * (0xC8 - 0x3B))
        return f"#{r:02X}{g:02X}{b:02X}"

    fig = go.Figure()

    # Draw edges as arrows (annotation per edge)
    for u, v in subgraph.edges():
        if u not in pos or v not in pos:
            continue
        x0, y0 = pos[u]   # prereq (deeper, lower y)
        x1, y1 = pos[v]   # course (shallower, higher y)
        fig.add_annotation(
            x=x1, y=y1,        # arrowhead at the course
            ax=x0, ay=y0,      # tail at the prereq
            axref="x", ayref="y",
            xref="x", yref="y",
            arrowhead=2,
            arrowsize=1.2,
            arrowwidth=1.5,
            arrowcolor="#888888",
            showarrow=True,
            text="",
        )

    # Draw nodes
    node_x = [pos[n][0] for n in subgraph.nodes() if n in pos]
    node_y = [pos[n][1] for n in subgraph.nodes() if n in pos]
    node_ids = [n for n in subgraph.nodes() if n in pos]
    node_colors = [_depth_color(depth_values.get(n, 0)) for n in node_ids]
    node_hover = [
        f"<b>{n}</b><br>{subgraph.nodes[n].get('name', '')}"
        if subgraph.nodes[n]
        else f"<b>{n}</b>"
        for n in node_ids
    ]

    fig.add_trace(go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=node_ids,
        textposition="top center",
        hovertext=node_hover,
        hoverinfo="text",
        marker=dict(
            size=18,
            color=node_colors,
            line=dict(width=2, color="white"),
        ),
        showlegend=False,
    ))

    fig.update_layout(
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        margin=dict(l=20, r=20, t=20, b=20),
        height=500,
    )
    return fig
