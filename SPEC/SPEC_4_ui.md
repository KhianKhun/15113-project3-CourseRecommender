# SPEC_4_ui.md
# CMU Course Graph — Segment 4: UI Layer
# Before starting, read SPEC_0_convention.md in full.
# This session is responsible for all files under `app/ui/` and `app/app.py`.
# Do not create or modify any files outside of these.

---

## Overview

This segment implements the Streamlit-based user interface. The UI layer
has one strict rule: it contains no business logic. Every analytical
computation is delegated to `app/core/`. The UI layer only does three
things: read from `st.session_state`, render components, and pass user
inputs to core functions.

The app has two views, accessible via Streamlit tabs:
- Tab 1: Semantic Graph — course semantic similarity visualization
- Tab 2: Prerequisite Path — directed prerequisite tree for a target course

---

## Startup and Session State

### app/app.py

This is the Streamlit entry point. Its only responsibilities are:

1. Page configuration (title, layout)
2. One-time startup computation, cached in `st.session_state`
3. Tab routing to `semantic_view.py` and `prereq_view.py`

The startup block runs once per session. Use the following pattern:

```python
if "initialized" not in st.session_state:
    with st.spinner("Loading course data and building graph..."):
        courses = load_courses()
        embeddings = get_embeddings(courses)
        similarity_matrix = compute_similarity_matrix(embeddings)
        graph = build_graph(courses, similarity_matrix)
        pagerank_scores = compute_pagerank(graph)
        coords_2d, var_2d = reduce_dimensions(embeddings, 2)
        coords_3d, var_3d = reduce_dimensions(embeddings, 3)

        st.session_state.courses = courses
        st.session_state.embeddings = embeddings
        st.session_state.similarity_matrix = similarity_matrix
        st.session_state.graph = graph
        st.session_state.pagerank_scores = pagerank_scores
        st.session_state.coords_2d = coords_2d
        st.session_state.coords_3d = coords_3d
        st.session_state.var_2d = var_2d
        st.session_state.var_3d = var_3d
        st.session_state.initialized = True

tab1, tab2 = st.tabs(["Semantic Graph", "Prerequisite Path"])
with tab1:
    render_semantic_view()
with tab2:
    render_prereq_view()
```

After a user adds a new course, reset `st.session_state.initialized` to
`False` and call `st.rerun()` to trigger a full recomputation. This is
the correct and intentional behavior as described in SPEC_2.

`app.py` must not contain any rendering logic beyond the spinner and tab
routing shown above.

---

## app/ui/semantic_view.py

### Responsibility

Render the semantic graph visualization tab. This is the primary view
of the application.

### Layout

The view is divided into two columns:
- Left column (width ratio 1): control panel
- Right column (width ratio 3): graph visualization

### Control panel (controls.py handles individual components)

The following controls appear in the left column, in this order:

**Dimension selector**: a radio button with options "2D" and "3D".
Default is "2D". Changing this switches the visualization without
any other state changes.

**Node count slider**: labeled "Max nodes to display". Range 10 to
100, default value read from `DEFAULT_TOP_K_NODES` in config.py.
This controls how many of the top-PageRank nodes are shown.

**Course search**: a text input labeled "Search or select courses".
As the user types, filter the course list by id or name (case-insensitive
substring match) and show matching results as a multiselect widget below
the search input. Selected courses are stored as a list in
`st.session_state.selected_courses`. These courses are highlighted in
the graph.

**Add custom course**: an expander labeled "Add a custom course".
Inside the expander: text inputs for course id, name, department, units
(number input), and a text area for description. A "Prerequisites" text
input that accepts a comma-separated list of course ids. A submit button
labeled "Add to graph". On submit, call `save_user_course()` and
`data_loader`, reset `st.session_state.initialized`, and call
`st.rerun()`.

**Recommendation panel**: below the controls, if
`st.session_state.selected_courses` is not empty, show a section labeled
"Recommended for you". Call `recommend()` with the selected course ids
and display the top 5 results as a compact list showing course id, name,
and score.

### Graph rendering (graph_plot.py handles the Plotly figure)

Pass the following to `render_graph_plot()` in `graph_plot.py`:
- `coords`: either `coords_2d` or `coords_3d` from session state,
  depending on dimension selector
- `courses`: from session state
- `pagerank_scores`: from session state
- `n_components`: 2 or 3
- `top_k`: current slider value
- `selected_ids`: current selected course ids
- `explained_variance`: corresponding `var_2d` or `var_3d`

Display the returned Plotly figure with `st.plotly_chart(fig,
use_container_width=True)`.

Below the chart, display a single line of metadata in small grey text:
`f"Showing top {top_k} courses by PageRank · {n_components}D projection
· {explained_variance:.1%} variance explained"`

---

## app/ui/prereq_view.py

### Responsibility

Render the prerequisite path visualization tab.

### Layout

Single column layout, no sidebar needed.

At the top, a selectbox labeled "Select a target course" showing all
course ids and names in the format "10-301 — Introduction to Machine
Learning". Sorted alphabetically by id.

Below the selectbox, when a course is selected:

1. Call `find_prereq_path(graph, target_id)` to get the prerequisite
   subgraph.
2. Call `get_prereq_depth(graph, target_id)` to get depth values.
3. If the subgraph has only one node (the target itself, no
   prerequisites), display the message "This course has no
   prerequisites." and stop.
4. Otherwise, render the prerequisite graph using `render_prereq_plot()`
   from `graph_plot.py`.
5. Below the graph, display a plain text summary:
   `f"{target_id} requires {len(subgraph.nodes) - 1} prerequisite
   course(s) across {max(depth_values)} level(s)."`

---

## app/ui/components/graph_plot.py

### Responsibility

All Plotly figure construction lives here. This file exposes two
functions: one for the semantic graph, one for the prerequisite graph.
No Streamlit calls are made inside this file — it only builds and
returns Plotly figures.

### render_graph_plot()

```python
def render_graph_plot(
    coords: np.ndarray,
    courses: list[dict],
    pagerank_scores: dict[str, float],
    n_components: int,
    top_k: int,
    selected_ids: list[str],
    explained_variance: float
) -> go.Figure:
```

**Node selection**: select the top `top_k` courses by PageRank score.
These are the only nodes rendered. Use `get_top_n_by_pagerank()` to
get their ids, then find their indices in `courses`.

**Anchor nodes**: the top `DEFAULT_ANCHOR_COUNT` nodes by PageRank are
"anchor" nodes. Read `DEFAULT_ANCHOR_COUNT` from config.py.

**Node sizing**: node size is proportional to PageRank score. Scale
sizes to the range [8, 24] pixels so that differences are visible but
no node is too large or too small.

**Node coloring**: three visual states, applied in priority order:
- Selected (course id in `selected_ids`): bright yellow, size +4 bonus
- Anchor (top DEFAULT_ANCHOR_COUNT by PageRank): coral/orange color
- Default: color mapped by `department` field using a fixed color dict
  defined at the top of this file. Assign one distinct color per
  department. Unknown departments get a neutral grey.

**Node labels**: anchor nodes always display their course id as a
visible text label. Non-anchor nodes display no label by default.
All nodes display a hover tooltip (see tooltip.py).

**Edges**: do not render all edges — only render edges where both
endpoints are in the current top_k node set. Render semantic edges
as thin grey lines with 30% opacity. Do not render prerequisite edges
in this view (they belong in the prereq view).

**2D figure**: use `go.Scatter` with `mode="markers+text"`. Set
`textposition="top center"` for labels.

**3D figure**: use `go.Scatter3d` with `mode="markers+text"`. Enable
the default Plotly 3D camera controls (drag to rotate, scroll to zoom)
— these work out of the box with no extra configuration needed.

**Layout**: set `showlegend=False`, transparent background
(`paper_bgcolor="rgba(0,0,0,0)"`, `plot_bgcolor="rgba(0,0,0,0)"`),
and hide axis tick marks and grid lines for a clean look.

### render_prereq_plot()

```python
def render_prereq_plot(
    subgraph: nx.DiGraph,
    depth_values: dict[str, int],
    target_id: str
) -> go.Figure:
```

**Layout**: position nodes using depth values. All nodes at the same
depth share the same y-coordinate (depth 0 at the top, deeper levels
lower). Nodes at the same depth are spread evenly along the x-axis.

**Node coloring**: target course (depth 0) is bright coral. Direct
prerequisites (depth 1) are medium orange. Deeper prerequisites are
progressively lighter. Use a simple linear interpolation between two
colors based on depth / max_depth.

**Edges**: render as arrows using Plotly's `add_annotation` with
`arrowhead=2`. Draw one annotation per edge. Arrow direction follows
the prerequisite direction (prereq → course, pointing upward toward
depth 0).

**Labels**: all nodes display their course id as a visible label.
On hover, display the full course name.

**Figure size**: set a fixed height of 500px. Width is handled by
`use_container_width=True` in the Streamlit call.

---

## app/ui/components/controls.py

### Responsibility

Reusable Streamlit control components used by semantic_view.py.
Each function renders one logical control and returns its current value.

```python
def dimension_selector() -> int:
    """Renders 2D/3D radio. Returns 2 or 3."""

def node_count_slider() -> int:
    """Renders node count slider. Returns current int value."""

def course_search(courses: list[dict]) -> list[str]:
    """
    Renders search input and multiselect.
    Returns list of selected course ids.
    """

def add_course_form(courses: list[dict]) -> dict | None:
    """
    Renders the add custom course expander.
    Returns a validated course dict if submitted, None otherwise.
    """
```

These functions are called by `semantic_view.py`. They must not write
to `st.session_state` directly — they return values and let the caller
decide what to do with them.

---

## app/ui/components/tooltip.py

### Responsibility

Format the hover tooltip text for graph nodes.

```python
def format_tooltip(course: dict, pagerank_score: float) -> str:
    """
    Returns a formatted string for Plotly hovertemplate.
    Format:
        10-301 — Introduction to Machine Learning
        Department: ML  |  Units: 12
        Importance: 0.842
        Prerequisites: 21-241, 36-218
        
        This course provides a broad introduction to...
        (description truncated to 200 characters)
    """
```

If the description exceeds 200 characters, truncate it and append "...".
If `prerequisites` is an empty list, show "None" instead of an empty
value. This function is called by `graph_plot.py` when building node
hover data.

---

## Window and Layout Behavior

Set the Streamlit page layout to `"wide"` in `st.set_page_config()`.
This maximizes the space available for the graph visualization.

Set a minimum usable width by adding the following to a
`.streamlit/config.toml` file (create this file in the project root):

```toml
[server]
headless = true

[theme]
base = "dark"
```

The dark theme provides better contrast for the graph visualization.
Streamlit handles scroll behavior natively when content exceeds the
viewport — no custom CSS is needed.

---

## Dependencies

Add the following to `requirements.txt`:

```
streamlit
plotly
```

---

## Testing notes

The UI layer does not have unit tests. Instead, manual testing should
verify the following scenarios before submission:

1. App launches without error on a fresh session.
2. Switching between 2D and 3D updates the graph without page reload.
3. Moving the node count slider updates the graph in real time.
4. Searching for a course highlights it in the graph.
5. Adding a custom course triggers recomputation and the new node
   appears in the graph.
6. Selecting a target course in the prereq tab renders a correct tree.
7. Selecting a course with no prerequisites shows the correct message.
8. The explained variance percentage is displayed below the graph.