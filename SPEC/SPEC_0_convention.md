# SPEC_0_convention.md
# CMU Course Graph — Developer Convention Header
# This file MUST be pasted in full at the start of every new Claude Code session.

---

## Project Overview

This project is a locally-run CMU course semantic graph visualization tool built
with Streamlit. Users can explore semantic relationships between courses, view
prerequisite paths, and receive course recommendations based on semantic similarity.

The project is divided into two main blocks: `data_pipeline/` (a one-time data
acquisition tool) and `app/` (the main application). All data is stored in the
top-level `data/` directory, which is parallel to both blocks.

Launch command: `streamlit run app/app.py`

---

## Repository Structure

cmu-course-graph/
├── data/
│   ├── courses.json           ← Official CMU course data (read-only)
│   ├── embeddings.npy         ← Precomputed embedding matrix (read-only)
│   └── user_courses.json      ← User-defined courses (written at runtime)
│
├── data_pipeline/
│   ├── scraper.py
│   ├── parser.py
│   └── validator.py
│
├── app/
│   ├── core/
│   │   ├── config.py
│   │   ├── data_loader.py
│   │   ├── embedder/
│   │   │   ├── model.py
│   │   │   └── similarity.py
│   │   ├── graph/
│   │   │   ├── builder.py
│   │   │   ├── pagerank.py
│   │   │   └── prereq.py
│   │   ├── reduction/
│   │   │   └── pca.py
│   │   └── recommender.py
│   ├── ui/
│   │   ├── components/
│   │   │   ├── graph_plot.py
│   │   │   ├── controls.py
│   │   │   └── tooltip.py
│   │   ├── semantic_view.py
│   │   └── prereq_view.py
│   └── app.py
│
├── tests/
│   ├── test_builder.py
│   ├── test_pagerank.py
│   ├── test_recommender.py
│   └── test_pca.py
│
├── .gitignore
├── SPEC_0_convention.md
├── SPEC_1_data_pipeline.md
├── SPEC_2_core.md
├── SPEC_3_recommender_prereq.md
├── SPEC_4_ui.md
├── README.md
├── PROMPT_LOG.md
├── REFLECTION.md
└── requirements.txt

---

## Data Schema

This is the most critical convention in the project. All modules operate around
these two data structures. No module may alter this schema without explicitly
updating this file and notifying all active sessions.

### courses.json and user_courses.json

Both files share an identical schema: a JSON array where each element is a course
object. An example entry looks like this:

```json
[
  {
    "id": "10-301",
    "name": "Introduction to Machine Learning",
    "description": "This course provides a broad introduction to...",
    "prerequisites": ["21-241", "36-218"],
    "department": "ML",
    "units": 12,
    "source": "official"
  }
]
```

Field definitions:
- `id`: Course number string, globally unique, format "XX-NNN". Primary key
  across all modules.
- `name`: Full course title, string.
- `description`: Course description text, string. This is the sole input to
  the embedding model.
- `prerequisites`: List of prerequisite course ids. May be an empty list `[]`.
- `department`: Abbreviated department name, string. Used for node color grouping
  in visualizations.
- `units`: Credit units, integer.
- `source`: Origin tag. Must be exactly `"official"` or `"user"`. Used to
  distinguish between courses.json and user_courses.json entries.

### embeddings.npy

A numpy matrix of shape `(N, D)`, where N is the total number of courses and D
is the embedding dimension (typically 384 for the default model). Row order
strictly corresponds to the course list returned by `data_loader.load_courses()`.
This correspondence is the sole responsibility of `data_loader.py`. No other
module may assume or re-derive row ordering independently.

---

## Module Interface Contracts

The following function signatures are binding contracts. Any Claude Code session
implementing a module must follow these signatures exactly — same parameter names,
same return types. If a signature needs to change, stop, raise it in the current
session, and update this file before proceeding.

### app/core/config.py

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

All modules must import paths from this file. Hardcoded path strings are not
permitted anywhere in the codebase.

### app/core/data_loader.py

```python
def load_courses() -> list[dict]:
    """
    Load and merge courses.json and user_courses.json.
    Returns a list of course dicts with a fixed ordering:
    official courses first (sorted by id), then user courses (sorted by id).
    If user_courses.json does not exist, it is created as an empty array.
    """

def save_user_course(course: dict) -> None:
    """
    Append a new course to user_courses.json.
    Validates schema before writing. Raises ValueError if schema is invalid.
    """
```

### app/core/embedder/model.py

```python
def get_embeddings(courses: list[dict]) -> np.ndarray:
    """
    Accepts the list returned by load_courses().
    If embeddings.npy exists and its row count matches len(courses),
    loads and returns it directly.
    Otherwise recomputes embeddings, saves to embeddings.npy, and returns
    the resulting matrix of shape (N, D).
    """
```

### app/core/embedder/similarity.py

```python
def compute_similarity_matrix(embeddings: np.ndarray) -> np.ndarray:
    """
    Accepts an (N, D) embedding matrix.
    Returns an (N, N) cosine similarity matrix with values in [0, 1].
    """

def get_top_k_similar(
    course_idx: int,
    similarity_matrix: np.ndarray,
    k: int
) -> list[int]:
    """
    Returns the indices of the k most similar courses to course_idx,
    excluding course_idx itself. Results are sorted by descending similarity.
    """
```

### app/core/graph/builder.py

```python
def build_graph(
    courses: list[dict],
    similarity_matrix: np.ndarray,
    similarity_threshold: float = 0.3
) -> nx.DiGraph:
    """
    Builds a directed graph where each node stores the full course dict
    as its attribute payload.
    Semantic edges: added when cosine similarity exceeds similarity_threshold.
    Edge attribute: weight=<similarity value>, type="semantic".
    Prerequisite edges: added per the prerequisites field.
    Edge attribute: type="prereq".
    """
```

### app/core/graph/pagerank.py

```python
def compute_pagerank(graph: nx.DiGraph) -> dict[str, float]:
    """
    Accepts the graph returned by build_graph().
    Returns a dict mapping course_id -> pagerank_score,
    with scores normalized to [0, 1].
    """
```

### app/core/graph/prereq.py

```python
def find_prereq_path(
    graph: nx.DiGraph,
    target_id: str
) -> nx.DiGraph:
    """
    Returns a subgraph containing all prerequisite courses required to reach
    target_id, as a directed subgraph.
    Raises ValueError if target_id is not present in the graph.
    """
```

### app/core/reduction/pca.py

```python
def reduce_dimensions(
    embeddings: np.ndarray,
    n_components: int  # must be 2 or 3
) -> tuple[np.ndarray, float]:
    """
    Applies PCA to the embedding matrix.
    Returns (reduced_coordinates, explained_variance_ratio_sum).
    reduced_coordinates has shape (N, n_components).
    Raises ValueError if n_components is not 2 or 3.
    """
```

### app/core/recommender.py

```python
def recommend(
    input_course_ids: list[str],
    courses: list[dict],
    similarity_matrix: np.ndarray,
    pagerank_scores: dict[str, float],
    top_n: int = 5
) -> list[dict]:
    """
    Given a list of course ids the user is interested in, returns a ranked
    list of recommended courses.
    Logic: collect semantic neighbors of all input courses, deduplicate,
    filter out courses already in input_course_ids, rank by pagerank_score,
    return top_n results.
    Each returned dict is a full course dict with one additional field:
    score: float (the pagerank score used for ranking).
    """
```

---

## Naming Conventions

Variables and functions use snake_case. Classes use PascalCase. Constants use
FULL_CAPS. Every function must have a docstring describing its inputs, outputs,
and core logic. All file paths must be imported from `app/core/config.py`.
Hardcoded strings for file paths are strictly forbidden.

---

## Line Count Limits

These limits exist to keep each file readable within a single Claude Code context
window and to enforce single-responsibility design.

The `ui/` layer: no `.py` file may exceed 300 lines (comments and blank lines
excluded). The `core/` layer: no `.py` file may exceed 500 lines. The
`data_pipeline/` layer: no `.py` file may exceed 400 lines. If a file approaches
its limit, split it into smaller files with clearly separated responsibilities
before continuing.

---

## Segment Ownership

Each Claude Code session is responsible for exactly one segment. A session must
not modify files owned by another segment. If a change to another segment's file
seems necessary, stop and raise it explicitly in the current session before
taking any action.

Segment 1 (SPEC_1): all files under `data_pipeline/`.
Segment 2 (SPEC_2): all files under `app/core/`, including `config.py`.
Segment 3 (SPEC_3): `app/core/recommender.py` and `app/core/graph/prereq.py`.
Segment 4 (SPEC_4): all files under `app/ui/` and `app/app.py`.

---

## .gitignore Contents

__pycache__/
*.pyc
*.pyo
.pytest_cache/
venv/
.venv/
.streamlit/
.DS_Store
data/embeddings.npy
*.env