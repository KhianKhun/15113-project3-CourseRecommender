# REFLECTION.md
# CMU Course Graph — Design Reflections

This file records design decisions, trade-offs, and lessons learned throughout
the project. It is updated incrementally as each segment is implemented.

---

## Data Pipeline (Segment 1)

**scraper.py:** The CMU course catalog API endpoint is a placeholder. In a real
deployment this would be replaced with the actual catalog URL or a local HTML
scraper using BeautifulSoup. The polite crawl delay (0.3s) prevents rate limiting.

**parser.py:** Handles two common raw field naming conventions (`course_id`/`id`,
`title`/`name`, `desc`/`description`) to be robust against slight API changes.

**validator.py:** Validates at parse time rather than at load time to catch data
quality issues early in the pipeline, before embeddings are computed.

---

## Core Layer (Segment 2)

**data_loader.py:** The fixed ordering (official sorted by id, then user sorted by id)
is critical — `embeddings.npy` row indices must correspond exactly to this order.
Any change to this ordering would invalidate cached embeddings.

**embedder/model.py:** Uses the row-count match heuristic to decide whether to reuse
cached embeddings. This is sufficient for the expected usage pattern (adding user
courses one at a time), but a hash-based check would be more robust in production.

**graph/builder.py:** Semantic edges are added bidirectionally, making the graph
undirected with respect to semantic similarity. Prerequisite edges are directional
(prereq → course), reflecting the dependency direction.

**graph/pagerank.py:** PageRank is normalized by dividing by the max score rather
than by the sum. This preserves the relative ranking while keeping the scale in
[0, 1], making the metric directly comparable to the similarity threshold.

**reduction/pca.py:** PCA is seeded (`random_state=42`) for reproducibility. The
explained variance ratio sum is surfaced to the user so they can judge whether
2D or 3D is capturing enough structure.

---

## Recommender & Prereq (Segment 3)

**recommender.py:** Uses PageRank as the final ranking signal after semantic
neighbor collection. This is a deliberate trade-off: semantic similarity finds
related courses, but PageRank promotes courses that are prerequisites for many
other courses — i.e., foundational courses the user is likely to benefit from.

**prereq.py:** Uses reverse BFS from the target node to collect all ancestors.
The returned subgraph includes only `type="prereq"` edges, stripping semantic
edges that are not relevant to the prerequisite view.

---

## UI Layer (Segment 4)

**app.py:** `@st.cache_resource` is used for the full data pipeline. This means
the pipeline only runs once per server lifetime, not once per user session.
For a multi-user deployment, this is the correct choice.

**semantic_view.py:** PCA is recomputed on every render within the session because
the number of components can change (2D vs 3D toggle). If performance is a concern,
both 2D and 3D projections could be precomputed.

**prereq_view.py:** Falls back to `nx.spring_layout` if the prerequisite subgraph
contains a cycle (which can happen if `courses.json` has circular dependencies).
This is a defensive choice; ideally the data pipeline would catch circular prereqs.

---
