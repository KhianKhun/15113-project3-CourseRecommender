# SPEC_2_core.md
# CMU Course Graph — Segment 2: Core Analysis Layer
# Before starting, read SPEC_0_convention.md in full.
# This session is responsible for all files under `app/core/`,
# except `recommender.py` and `graph/prereq.py` (those belong to Segment 3).
# Do not create or modify any files outside of `app/core/`.

---

## Overview

The core layer is the analytical engine of the application. It has no
knowledge of Streamlit or any UI framework — it is pure Python logic that
takes data in and returns structured results out. Every function in this
layer must be independently testable without launching the app.

The execution order when the app starts is:

1. `config.py` — path constants loaded by all modules
2. `data_loader.py` — load and merge course data
3. `embedder/model.py` — load or compute embeddings
4. `embedder/similarity.py` — compute cosine similarity matrix
5. `graph/builder.py` — build the NetworkX graph
6. `graph/pagerank.py` — compute PageRank scores
7. `reduction/pca.py` — reduce dimensions for visualization

These results are computed once at app startup and cached in Streamlit's
session state. They are not recomputed on every user interaction.

---

## app/core/config.py

Create this file exactly as specified in SPEC_0. No additional logic belongs
here — it is constants only.

```python
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = ROOT_DIR / "data"

COURSES_PATH = DATA_DIR / "courses.json"
USER_COURSES_PATH = DATA_DIR / "user_courses.json"
EMBEDDINGS_PATH = DATA_DIR / "embeddings.npy"

# Model configuration
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# Graph configuration
DEFAULT_SIMILARITY_THRESHOLD = 0.3
DEFAULT_TOP_K_NODES = 30
DEFAULT_ANCHOR_COUNT = 10

# PCA configuration
DEFAULT_N_COMPONENTS = 2
```

The constants `DEFAULT_TOP_K_NODES` and `DEFAULT_ANCHOR_COUNT` deserve
explanation. `DEFAULT_TOP_K_NODES` is the default number of nodes shown
in the visualization (user-adjustable via slider). `DEFAULT_ANCHOR_COUNT`
is the number of highest-PageRank nodes that are always highlighted as
anchors regardless of the current K value. These are defined here so the
UI layer can read them without hardcoding magic numbers.

---

## app/core/data_loader.py

### Responsibility

Load course data from disk and expose a stable, ordered list of course
dicts to the rest of the application. This is the single source of truth
for course ordering, which is critical because `embeddings.npy` row indices
must correspond exactly to positions in this list.

### Implementation details

`load_courses()` reads `COURSES_PATH` first, then attempts to read
`USER_COURSES_PATH`. If `USER_COURSES_PATH` does not exist, create it as
an empty JSON array `[]` and log a message. Merge the two lists with
official courses first, each group sorted by `id` alphabetically. Return
the merged list.

`save_user_course(course)` must validate the incoming dict against the
schema before writing. Required fields and their types are defined in
SPEC_0. If any field is missing or has the wrong type, raise `ValueError`
with a descriptive message identifying the bad field. If validation passes,
read the current contents of `USER_COURSES_PATH`, append the new course,
and write back. Do not overwrite the file with just the new entry.

Add a helper `get_course_by_id(course_id: str, courses: list[dict]) ->
dict | None` that returns the course dict for a given id, or None if not
found. This is used by multiple modules and should live here to avoid
duplication.

---

## app/core/embedder/model.py

### Responsibility

Manage the lifecycle of course embeddings: load from disk if available,
recompute if not, and expose the result as a numpy matrix.

### Implementation details

`get_embeddings(courses)` checks whether `EMBEDDINGS_PATH` exists and
whether the stored matrix has exactly `len(courses)` rows. If both
conditions are true, load and return the matrix directly. This check is
important: if the user adds a new course, `len(courses)` increases and
the cached matrix becomes stale, triggering a recompute.

When recomputing, extract the `description` field from each course dict
in order, pass the list of strings to the sentence-transformers model,
and save the resulting matrix to `EMBEDDINGS_PATH` using `np.save`.
Print a progress message before starting the computation since this can
take 10-30 seconds on first run.

The model should be loaded once and reused, not reloaded on every call.
Use a module-level variable to cache the loaded model instance.

### Handling user-added courses

When a user adds a new course through the UI, `load_courses()` will return
a longer list, causing `get_embeddings()` to detect a row count mismatch
and recompute all embeddings from scratch. This is intentional and correct
behavior, not a bug. The recomputation time is acceptable since it only
happens when the course list changes.

---

## app/core/embedder/similarity.py

### Responsibility

Compute and expose pairwise cosine similarity between all courses.

### Implementation details

`compute_similarity_matrix(embeddings)` normalizes each row of the
embedding matrix to unit length, then computes the dot product matrix.
This is equivalent to cosine similarity and can be done efficiently with
a single `np.dot` call after normalization. Do not use a loop. The
diagonal of the result will be 1.0 (each course is identical to itself)
— this is expected and correct.

`get_top_k_similar(course_idx, similarity_matrix, k)` extracts row
`course_idx` from the similarity matrix, sets the self-similarity entry
to -1 to exclude it, then uses `np.argsort` to find the top k indices.
Return indices sorted by descending similarity.

---

## app/core/graph/builder.py

### Responsibility

Construct the NetworkX directed graph that is the central data structure
of the application.

### Implementation details

`build_graph(courses, similarity_matrix, similarity_threshold)` proceeds
in three steps.

Step 1: add nodes. Iterate over `courses` and add each course as a node
using `course["id"]` as the node key. Store the full course dict as the
node's attribute payload under the key `"data"`, so any part of the app
can retrieve full course information from the graph without needing a
separate lookup.

Step 2: add semantic edges. Iterate over all pairs `(i, j)` where `i < j`
to avoid duplicate pairs. If `similarity_matrix[i][j]` exceeds
`similarity_threshold`, add an edge in both directions (since semantic
similarity is symmetric) with attributes `weight=similarity_matrix[i][j]`
and `type="semantic"`. Use the course id strings as node keys, not integer
indices.

Step 3: add prerequisite edges. For each course, iterate over its
`prerequisites` list. For each prerequisite id that exists as a node in
the graph, add a directed edge from the prerequisite to the course with
attribute `type="prereq"`. If a prerequisite id does not exist in the
graph, log a warning and skip it — do not crash.

### Important note on graph type

Use `nx.DiGraph`, not `nx.Graph`. Prerequisite edges are inherently
directional (prereq → course). Semantic edges are added in both directions
explicitly to preserve this type consistency.

---

## app/core/graph/pagerank.py

### Responsibility

Compute a PageRank importance score for every course node.

### Implementation details

`compute_pagerank(graph)` calls `nx.pagerank(graph, weight="weight")`,
which uses the `weight` edge attribute for the semantic edges. Prerequisite
edges have no `weight` attribute — NetworkX treats missing weight as 1.0
by default, which is acceptable.

After computing raw PageRank scores, normalize them to [0, 1] by dividing
by the maximum score. Return the normalized dict mapping course_id to score.

Also expose a helper `get_top_n_by_pagerank(pagerank_scores: dict[str,
float], n: int) -> list[str]` that returns the top n course ids sorted by
descending PageRank score. This is used by the UI to determine anchor nodes.

---

## app/core/reduction/pca.py

### Responsibility

Project the high-dimensional embedding space down to 2D or 3D for
visualization.

### Implementation details

`reduce_dimensions(embeddings, n_components)` raises `ValueError` if
`n_components` is not 2 or 3. Otherwise applies `sklearn.decomposition.PCA`
with `n_components=n_components` to the full embedding matrix. Return a
tuple of:
- the transformed coordinate matrix of shape `(N, n_components)` as a
  numpy array
- the sum of `pca.explained_variance_ratio_` as a single float, rounded
  to 4 decimal places

The coordinate matrix rows correspond to the same ordering as the input
embeddings, which corresponds to the ordering from `load_courses()`.

PCA is deterministic given the same input, so there is no need to set a
random seed. Do not cache the PCA result to disk — it is fast enough to
recompute at startup (under 1 second for typical course counts).

---

## Startup Caching Strategy

All of the above computations are triggered once at app startup and stored
in `st.session_state`. This is the UI layer's responsibility (Segment 4),
but the core layer must be designed to support it. Specifically:

Every function in this layer must be pure and stateless — given the same
inputs, always return the same outputs. No function should read from
`st.session_state` or import anything from `app/ui/`. The data flow is
strictly one-directional: `data_pipeline` → `data/` → `app/core` → `app/ui`.

---

## Dependencies

Add the following to `requirements.txt`:

```
sentence-transformers
networkx
numpy
scikit-learn
```

---

## Testing notes for tests/

Each of the following should have at least one test in `tests/`:

`test_builder.py`: verify that `build_graph` produces correct node count,
that semantic edges have a `weight` attribute, and that prerequisite edges
have `type="prereq"`.

`test_pagerank.py`: verify that all scores are in [0, 1] and that the
top node has score 1.0 after normalization.

`test_pca.py`: verify that output shape is `(N, n_components)` for both
2 and 3 components, and that `ValueError` is raised for invalid input.