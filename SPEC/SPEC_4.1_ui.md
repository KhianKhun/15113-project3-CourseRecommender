# SPEC_4.1_ui_patch.md
# CMU Course Graph — Patch for Segment 4: UI Layer
# This file SUPERSEDES the node selection and coloring sections of SPEC_4_ui.md.
# Read SPEC_0 → SPEC_4 → this file in order.

---

## What Changed

SPEC_4 used PageRank as the sole criterion for selecting which K nodes
to display, with a fixed set of "anchor" nodes always highlighted in
orange. This patch replaces that logic with a user-input-driven
selection: when the user has selected courses, nodes are ranked by
average cosine similarity to those courses. PageRank is retained only
as a fallback (no input) and as a secondary tie-breaker.

The orange anchor nodes concept is removed entirely.

---

## Revised Node Selection Logic

### When user has selected one or more courses (selected_ids is not empty)

For each candidate course (all courses in the dataset), compute its
relevance score as follows:

```
score(candidate) = α × mean_similarity(candidate, selected_ids)
                 + (1 - α) × pagerank_score(candidate)
```

Where:
- `mean_similarity(candidate, selected_ids)` is the average of
  `similarity_matrix[candidate_idx][input_idx]` over all input courses
- `pagerank_score(candidate)` is the normalized PageRank score from
  `pagerank_scores` dict
- `α = 0.7` (hardcoded in config.py as `SIMILARITY_WEIGHT = 0.7`)

Filter out courses that are in `selected_ids` themselves — they are
shown as highlighted nodes but are not ranked against themselves.

Sort all remaining courses by descending score. Take the top K.
Add the selected courses back in (they are always shown regardless
of K). Final node set = top K scored courses + selected courses.

### When user has not selected any courses (selected_ids is empty)

Fall back to pure PageRank ordering: show the top K courses by
descending `pagerank_scores` value. This is the initial state of
the app when no input has been provided.

---

## Revised Node Coloring

Three visual states, applied in priority order (highest first):

**Selected** (course id in `selected_ids`):
- Color: bright yellow (`#FFD700`)
- Size: base_size + 6 bonus
- Label: always visible (course id shown as text label)

**High relevance** (top 20% of the scored K nodes by score,
only applies when selected_ids is not empty):
- Color: `#FF6B6B` (coral red)
- Size: base_size + 2 bonus
- Label: visible if score is in top DEFAULT_ANCHOR_COUNT by PageRank

**Default** (all other displayed nodes):
- Color: mapped by `department` field using the department color dict
- Size: proportional to PageRank score, scaled to range [8, 24]
- Label: visible only if course is in top DEFAULT_ANCHOR_COUNT
  by PageRank (this ensures some labels always show as landmarks
  even when no courses are selected)

---

## Revised render_graph_plot() Signature

The function signature in `graph_plot.py` needs one new parameter:

```python
def render_graph_plot(
    coords: np.ndarray,
    courses: list[dict],
    pagerank_scores: dict[str, float],
    similarity_matrix: np.ndarray,      # NEW — needed for score computation
    n_components: int,
    top_k: int,
    selected_ids: list[str],
    explained_variance: float
) -> go.Figure:
```

The node selection and scoring logic described above is implemented
inside this function. Do not put it in `semantic_view.py` — keep all
figure construction logic inside `graph_plot.py`.

---

## Revised semantic_view.py call site

Update the call to `render_graph_plot()` in `semantic_view.py` to
pass `similarity_matrix` from session state:

```python
fig = render_graph_plot(
    coords=coords,
    courses=st.session_state.courses,
    pagerank_scores=st.session_state.pagerank_scores,
    similarity_matrix=st.session_state.similarity_matrix,   # NEW
    n_components=n_components,
    top_k=top_k,
    selected_ids=st.session_state.get("selected_courses", []),
    explained_variance=explained_variance
)
```

---

## config.py additions

Add the following constants to `app/core/config.py`:

```python
# Scoring weights for node ranking
SIMILARITY_WEIGHT = 0.7       # α in the scoring formula
PAGERANK_WEIGHT = 0.3         # (1 - α)
```

---

## Unchanged from SPEC_4

Everything else in SPEC_4 remains unchanged:
- Control panel layout and components
- Edge rendering logic
- 2D/3D switching
- Tooltip format
- Prerequisite view
- Startup caching strategy
- Window and layout behavior