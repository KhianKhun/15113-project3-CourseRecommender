# SPEC_3_recommender_prereq.md
# CMU Course Graph — Segment 3: Recommender and Prerequisite Path
# Before starting, read SPEC_0_convention.md in full.
# This session is responsible for exactly two files:
#   - app/core/recommender.py
#   - app/core/graph/prereq.py
# Do not create or modify any files outside of these two.

---

## Overview

This segment implements two self-contained analytical features that sit on
top of the graph and similarity structures built in Segment 2. Both files
are pure Python with no UI dependencies. They consume outputs from
Segment 2's modules and return structured results for the UI layer to
render.

Assume the following are already implemented and available for import:
- `app.core.data_loader.get_course_by_id`
- `app.core.embedder.similarity.get_top_k_similar`
- `app.core.graph.pagerank.get_top_n_by_pagerank`

Do not reimplement any logic from these modules. Import and use them
directly.

---

## app/core/recommender.py

### Responsibility

Given a list of course ids the user is interested in, produce a ranked
list of courses they have not yet seen but are likely to find relevant.

### Interface (as defined in SPEC_0)

```python
def recommend(
    input_course_ids: list[str],
    courses: list[dict],
    similarity_matrix: np.ndarray,
    pagerank_scores: dict[str, float],
    top_n: int = 5
) -> list[dict]:
```

### Algorithm

The recommendation logic proceeds in four steps.

Step 1: resolve indices. For each course id in `input_course_ids`, find
its integer index in `courses`. If an id is not found in `courses`, log
a warning and skip it. Build a set of input indices for fast lookup.

Step 2: collect neighbors. For each input course index, call
`get_top_k_similar` with a fixed k of 20. This gives a pool of candidate
courses. Collect all candidate indices into a single set, removing any
index that corresponds to a course already in `input_course_ids`.

Step 3: rank by PageRank. For each candidate index, look up its course id
and retrieve its PageRank score from `pagerank_scores`. Sort all candidates
by descending PageRank score.

Step 4: return top_n. Take the top `top_n` candidates, retrieve their full
course dicts from `courses`, attach the field `score: float` containing
their PageRank score, and return the list.

### Edge cases

If `input_course_ids` is empty, return an empty list immediately without
any computation. If `top_n` is greater than the number of available
candidates after filtering, return all available candidates rather than
raising an error.

---

## app/core/graph/prereq.py

### Responsibility

Given a target course, find all courses that must be completed before it
can be taken, and return them as a subgraph that the UI can visualize as
a directed prerequisite tree.

### Interface (as defined in SPEC_0)

```python
def find_prereq_path(
    graph: nx.DiGraph,
    target_id: str
) -> nx.DiGraph:
```

### Algorithm

This is a reverse BFS (breadth-first search) traversal over the prerequisite
edges of the graph.

Step 1: validate. If `target_id` is not a node in `graph`, raise
`ValueError` with the message f"Course {target_id} not found in graph".

Step 2: collect prerequisite nodes. Initialize a queue with `target_id`
and a visited set. While the queue is not empty, pop a node, add it to
visited, then iterate over its incoming edges. For each incoming edge,
check whether it has `type="prereq"`. If so, and if the source node has
not been visited, add it to the queue. Continue until the queue is empty.

Step 3: build subgraph. Call `graph.subgraph(visited)` to extract the
subgraph containing only the visited nodes and the edges between them.
Return this subgraph.

Note that the returned subgraph includes `target_id` itself as a node,
so the UI can render it as the destination of all paths.

### Additional helper

Also implement the following helper in this file:

```python
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
    """
```

This is a simple BFS over the prerequisite subgraph returned by
`find_prereq_path`, tracking distance from `target_id` by traversing
edges in reverse. The depth values are used by `prereq_view.py` to
lay out nodes in a top-down tree structure where deeper prerequisites
appear lower in the visualization.

---

## Dependencies

This segment introduces no new dependencies beyond what is already in
`requirements.txt` from Segment 2. Both files use only `networkx`,
`numpy`, and imports from `app.core`.

---

## Testing notes for tests/

`test_recommender.py`: construct a small mock courses list and similarity
matrix (5-10 courses is sufficient), call `recommend()`, and verify that:
- returned courses are not in the input list
- returned list length does not exceed top_n
- results are sorted by descending score
- empty input returns empty list

`test_prereq.py` (add this file): construct a small mock DiGraph with a
few prerequisite edges, call `find_prereq_path()`, and verify that:
- all prerequisite nodes are present in the returned subgraph
- non-prerequisite nodes are absent
- ValueError is raised for an unknown target_id
- `get_prereq_depth()` returns correct depth values for a known graph