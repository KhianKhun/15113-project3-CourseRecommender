# SPEC_4.2_ui_patch.md
# CMU Course Graph — Patch for Segment 4: UI Layer
# This file SUPERSEDES the node coloring and label sections of SPEC_4.1.
# Read SPEC_0 → SPEC_4 → SPEC_4.1 → this file in order.

---

## What Changed

Two additions on top of SPEC_4.1:
1. The number of "high relevance" (coral red) nodes is now user-controlled
   via a slider, replacing the hardcoded top-20% logic.
2. Label visibility logic is now split into two modes depending on
   whether the user has selected any input courses.

---

## New Slider: Top N Highlighted Nodes

Add a second slider to the control panel in `semantic_view.py`,
directly below the existing node count slider:

```
Label:   "Highlighted courses to show"
Range:   1 to 20
Default: DEFAULT_ANCHOR_COUNT (read from config.py, currently 10)
Key:     "top_n_highlight"
```

The value from this slider is passed to `render_graph_plot()` as a
new parameter `top_n_highlight: int`.

This slider is always visible regardless of whether the user has
selected any input courses. When no courses are selected, it controls
how many top-PageRank anchor nodes receive labels (same as before).
When courses are selected, it controls how many top-scored nodes are
colored coral red and labeled.

---

## Revised Node Coloring and Label Logic

### Mode A: No input courses (selected_ids is empty)

Node ranking: pure PageRank descending, top K shown.

Coloring:
- All nodes: colored by department (default color dict)
- Top `top_n_highlight` nodes by PageRank: colored coral red `#FF6B6B`

Labels:
- Top `top_n_highlight` nodes by PageRank: course id label visible
- All other nodes: no label, tooltip on hover only

### Mode B: User has selected one or more courses (selected_ids not empty)

Node ranking: hybrid score (SPEC_4.1 formula), top K shown plus
selected courses always included.

Coloring (priority order, highest first):
- Selected nodes (in `selected_ids`): bright yellow `#FFD700`, size +6
- Top `top_n_highlight` nodes by hybrid score
  (excluding selected nodes): coral red `#FF6B6B`, size +2
- All other nodes: colored by department, base size

Labels:
- Selected nodes: course id label always visible
- Top `top_n_highlight` coral red nodes: course id label always visible
- All other nodes: no label, tooltip on hover only

---

## Revised render_graph_plot() Signature

```python
def render_graph_plot(
    coords: np.ndarray,
    courses: list[dict],
    pagerank_scores: dict[str, float],
    similarity_matrix: np.ndarray,
    n_components: int,
    top_k: int,
    top_n_highlight: int,              # NEW — user-controlled highlight count
    selected_ids: list[str],
    explained_variance: float
) -> go.Figure:
```

---

## Revised controls.py

Add the following function:

```python
def highlight_count_slider() -> int:
    """
    Renders the highlight count slider.
    Returns current int value (1 to 20).
    Default is DEFAULT_ANCHOR_COUNT from config.py.
    """
```

Called in `semantic_view.py` directly below `node_count_slider()`.

---

## Unchanged from SPEC_4.1

Everything else in SPEC_4.1 remains unchanged including the scoring
formula, fallback logic, similarity_matrix parameter, and config.py
additions.