"""
graph_plot.py — app/ui/components
Builds and returns Plotly figures for the semantic graph and prerequisite tree.
No Streamlit calls are made here — only figure construction.
"""

import numpy as np
import networkx as nx
import plotly.graph_objects as go

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
_MAX_SIZE = 16
_SELECTED_SIZE_BONUS = 0


def _course_num(cid: str) -> int:
    """Convert 'xx-yyy' → integer xxyyy for tie-breaking (smaller = higher priority)."""
    return int(cid.replace("-", ""))


def render_graph_plot(
    coords: np.ndarray,
    courses: list[dict],
    pagerank_scores: dict[str, float],
    n_components: int,
    top_k: int,
    top_n_highlight: int,
    selected_ids: list[str],
    explained_variance: float,
    highlight_ids: list[str] | None = None,
    recommend_scores: dict[str, float] | None = None,
    score_breakdowns: dict[str, tuple[float, float, float]] | None = None,
    hidden_ids: list[str] | None = None,
) -> go.Figure:
    """
    Builds an interactive Plotly scatter plot for the semantic graph view.

    Node selection:
      - No selection: top K by PageRank (Mode A).
      - With selection (Mode B):
          1. Center = geometric center of selected courses in PCA space.
          2. Radius = distance from center to the farthest of the
             top_n_highlight highlighted/recommended courses.
          3. Display: selected (always) + top_n_highlight highlights (always)
             + fill remaining slots from courses inside the circle,
             ranked by recommend score, until top_k.

    Node coloring priority (highest first):
      1. Selected (yellow #FFD700).
      2. High relevance (#FF6B6B) — top_n_highlight recommended courses.
      3. Department color (default).

    Args:
        coords: (N, n_components) PCA coordinate array.
        courses: Full course list (row order matches coords).
        pagerank_scores: Dict mapping course_id -> normalized score in [0, 1].
        n_components: 2 or 3.
        top_k: Max number of nodes to display.
        top_n_highlight: Number of recommended courses that define the radius.
        selected_ids: Course ids highlighted yellow.
        explained_variance: PCA variance ratio sum (used in caption only).
        highlight_ids: Recommended course ids (define the circle radius).
        recommend_scores: Dict mapping course_id -> recommend() score. When
            provided, used for fill ordering and node sizing in Mode B.
            Falls back to PageRank for courses not in the dict.

    Returns:
        A Plotly Figure object ready for st.plotly_chart().
    """
    selected_set = set(selected_ids)
    hidden_set = set(hidden_ids or [])
    id_to_idx = {c["id"]: i for i, c in enumerate(courses)}
    center = None  # set in Mode B when input_indices exist

    if selected_ids:
        # Mode B:
        # 1. Center = geometric center of selected courses.
        # 2. Radius = farthest of the top_n_highlight highlighted courses from center.
        # 3. Collect all courses inside the circle.
        # 4. Fill display up to top_k by avg similarity to selected courses.
        input_indices = [id_to_idx[cid] for cid in selected_ids if cid in id_to_idx]

        if input_indices:
            center = coords[np.array(input_indices)].mean(axis=0)  # (n_components,)

            # Distance from center for every course.
            dists: dict[str, float] = {}
            for course in courses:
                cid = course["id"]
                if cid in id_to_idx:
                    dists[cid] = float(np.linalg.norm(coords[id_to_idx[cid]] - center))

            # Highlighted courses (up to top_n_highlight) sorted by distance.
            forced_highlights: list[str] = []
            if highlight_ids:
                hl_sorted = sorted(
                    (hid for hid in highlight_ids if hid in dists),
                    key=lambda hid: dists[hid],
                )
                forced_highlights = hl_sorted[:top_n_highlight]

            # Radius = distance to farthest forced highlight from center.
            # Fallback (no highlights): radius covers top_k nearest courses.
            if forced_highlights:
                radius = max(dists[hid] for hid in forced_highlights)
            else:
                sorted_dists = sorted(dists.values())
                radius = sorted_dists[min(top_k - 1, len(sorted_dists) - 1)]

            # Selected courses are always inside the circle.
            for sid in selected_ids:
                if sid in dists:
                    radius = max(radius, dists[sid])

            # All courses within the circle.
            in_circle = [cid for cid, d in dists.items() if d <= radius]

            def node_score(cid: str) -> float:
                """Blended recommend score if available, otherwise 0."""
                if recommend_scores:
                    return recommend_scores.get(cid, 0.0)
                return pagerank_scores.get(cid, 0.0)

            # Build display_set.
            display_set: list[str] = []
            seen: set[str] = set()
            all_course_ids = {c["id"] for c in courses}

            # 1. Selected courses (always, yellow).
            for sid in selected_ids:
                if sid in all_course_ids and sid not in seen:
                    display_set.append(sid)
                    seen.add(sid)

            # 2. Forced highlights (always, coral red).
            for hid in forced_highlights:
                if hid not in seen:
                    display_set.append(hid)
                    seen.add(hid)

            # 3. Fill from in-circle courses by recommend score until top_k.
            fill_candidates = sorted(
                [(cid, node_score(cid)) for cid in in_circle if cid not in seen],
                key=lambda x: x[1],
                reverse=True,
            )
            for cid, _ in fill_candidates:
                if len(display_set) >= top_k:
                    break
                display_set.append(cid)
                seen.add(cid)

            top_k_ids = display_set
            high_relevance_ids = set(forced_highlights) - selected_set
            node_scores = {cid: node_score(cid) for cid in top_k_ids}

        else:
            top_k_ids = get_top_n_by_pagerank(pagerank_scores, top_k)
            high_relevance_ids = (
                set(highlight_ids) - selected_set if highlight_ids
                else set(get_top_n_by_pagerank(pagerank_scores, top_n_highlight))
            )
            node_scores = {cid: pagerank_scores.get(cid, 0.0) for cid in top_k_ids}
    else:
        # Mode A: pure PageRank ordering
        top_k_ids = get_top_n_by_pagerank(pagerank_scores, top_k)
        high_relevance_ids = set(get_top_n_by_pagerank(pagerank_scores, top_n_highlight))
        node_scores = {cid: pagerank_scores.get(cid, 0.0) for cid in top_k_ids}

    # Normalize node_scores to [0, 1] for sizing.
    score_vals = list(node_scores.values())
    s_max = max(score_vals) if score_vals else 1.0
    s_min = min(score_vals) if score_vals else 0.0
    s_range = max(s_max - s_min, 1e-9)

    # Build per-node arrays
    xs, ys, zs = [], [], []
    sizes, colors, labels, tooltips = [], [], [], []
    id_to_course = {c["id"]: c for c in courses}

    visible_top_k_ids = [cid for cid in top_k_ids if cid not in hidden_set]

    for cid in visible_top_k_ids:
        if cid not in id_to_idx:
            continue
        idx = id_to_idx[cid]
        course = id_to_course[cid]
        display_score = node_scores.get(cid, 0.0)

        # Coordinates
        xs.append(float(coords[idx, 0]))
        ys.append(float(coords[idx, 1]))
        if n_components == 3:
            zs.append(float(coords[idx, 2]))

        # Size: scale node_scores to [_MIN_SIZE, _MAX_SIZE]; bonuses for special states.
        norm = (node_scores.get(cid, s_min) - s_min) / s_range
        base_size = _MIN_SIZE + norm * (_MAX_SIZE - _MIN_SIZE)
        if cid in selected_set:
            base_size += _SELECTED_SIZE_BONUS      # +6 for selected
        elif cid in high_relevance_ids:
            base_size += 2                          # +2 for high relevance
        sizes.append(base_size)

        # Color priority: selected > high relevance > dept
        if cid in selected_set:
            colors.append(_SELECTED_COLOR)          # bright yellow
        elif cid in high_relevance_ids:
            colors.append("#FF6B6B")                # coral red
        else:
            dept = course.get("department", "")
            colors.append(DEPT_COLORS.get(dept, DEPT_DEFAULT))

        # Label: selected and high-relevance nodes only
        if cid in selected_set or cid in high_relevance_ids:
            labels.append(cid)
        else:
            labels.append("")

        breakdown = score_breakdowns.get(cid) if score_breakdowns else None
        tooltips.append(format_tooltip(course, display_score, breakdown))

    fig = go.Figure()

    # Edges (semantic only, both endpoints must be in top_k)
    top_k_set = set(visible_top_k_ids)
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
        if center is not None:
            fig.add_trace(go.Scatter(
                x=[float(center[0])],
                y=[float(center[1])],
                mode="markers",
                marker=dict(
                    symbol="circle",
                    size=14,
                    color="rgba(255, 0, 0, 0.5)",
                    line=dict(width=3, color="rgba(255, 0, 0, 1.0)"),
                ),
                hovertext=["Geometric Center"],
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
        if center is not None:
            fig.add_trace(go.Scatter3d(
                x=[float(center[0])],
                y=[float(center[1])],
                z=[float(center[2])],
                mode="markers",
                marker=dict(
                    symbol="circle",
                    size=8,
                    color="rgba(255, 0, 0, 0.5)",
                    line=dict(width=3, color="rgba(255, 0, 0, 1.0)"),
                ),
                hovertext=["Geometric Center"],
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
