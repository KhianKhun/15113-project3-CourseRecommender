CMU Course Graph — Patch: Structural Similarity Recommender Upgrade
Read SPEC_0 → SPEC_2 → SPEC_3 → this file in order.
This file SUPERSEDES the recommendation scoring section of SPEC_3.
Do NOT modify pagerank.py, builder.py, or any embedder files.

Overview
This patch replaces the original two-signal blended score in recommender.py
with a three-signal formula that adds a structural similarity term derived
from the prerequisite graph. The structural similarity is computed entirely from
the prerequisites field of each course dict — it requires no changes to the
graph builder or PageRank.
The only files changed by this patch are:

app/core/config.py — add hyperparameter constants
app/core/recommender.py — new scoring logic

Do not modify any other file.

New Scoring Formula
score = COSINE_WEIGHT     × cosine_sim
      + STRUCTURAL_WEIGHT × structural_sim
      + PAGERANK_WEIGHT   × pagerank_score
Constants defined in config.py:
pythonCOSINE_WEIGHT      = 0.55
STRUCTURAL_WEIGHT  = 0.30
PAGERANK_WEIGHT    = 0.15
cosine_sim is the mean cosine similarity between the candidate and all input
courses, exactly as before. pagerank_score is the normalized PageRank score,
exactly as before. structural_sim is the new term defined below.

Structural Similarity
Concept
For any course X, define its weighted neighborhood as the set of all courses
reachable from X by traversing prerequisite edges in either direction, where each
reachable course receives a weight that decays with distance from X.
The chain A → B → C → X → D → E → F (where → means "is prerequisite of")
produces the following weighted neighborhood for X:
C: depth=1, weight=0.85   (upstream)
B: depth=2, weight=0.70
A: depth=3, weight=0.55
D: depth=1, weight=0.85   (downstream)
E: depth=2, weight=0.70
F: depth=3, weight=0.55
Two courses are structurally similar if their weighted neighborhoods overlap
substantially — they share knowledge foundations, unlock similar future courses,
or both.
Depth Decay Function
weight(d) = max(DECAY_ALPHA, 1 - DECAY_K × d)
Where d is the number of hops from X to the neighbor (d=1 for direct
neighbors). This is a linear decay with a floor so distant nodes never
lose all influence.
Constants defined in config.py:
pythonDECAY_ALPHA = 0.30   # floor — distant nodes never drop below this
DECAY_K     = 0.15   # slope of linear decay per hop
Example values:
d=1: max(0.30, 1 - 0.15) = 0.85
d=2: max(0.30, 1 - 0.30) = 0.70
d=3: max(0.30, 1 - 0.45) = 0.55
d=4: max(0.30, 1 - 0.60) = 0.40
d=5: max(0.30, 1 - 0.75) = 0.30  ← floor
d=6+: 0.30
Building the Weighted Neighborhood via BFS
To compute weighted_neighborhood(course_id, courses_by_id, reverse_index):

Initialize a result dict neighborhood = {} and a BFS queue with
(course_id, depth=0). Also maintain a visited set starting with
course_id itself.
Pop (node, d). Traverse neighbors in both directions:

Upstream: iterate over courses_by_id[node]["prerequisites"]
Downstream: iterate over reverse_index.get(node, [])


For each neighbor n not yet in visited:

Compute w = max(DECAY_ALPHA, 1 - DECAY_K × (d + 1))
If n not in neighborhood: add it with weight w, enqueue (n, d+1),
add to visited
If n already in neighborhood: update to max(existing_weight, w)
(a node reachable by multiple paths keeps the strongest signal)


Continue until queue is empty. Return neighborhood.

Note: course_id itself is never added to its own neighborhood (it is in
visited from the start).
Weighted Jaccard Similarity
Given neighborhoods N_A and N_B (dicts mapping course_id → weight):
structural_sim(A, B) = Σ min(N_A[v], N_B[v])  for v in (N_A ∩ N_B)
                     / Σ max(N_A[v], N_B[v])  for v in (N_A ∪ N_B)
Nodes only in N_A contribute N_A[v] to the denominator and 0 to the
numerator, and vice versa for nodes only in N_B.
If both neighborhoods are empty, return 0.0 — do not divide by zero.
Computing structural_sim in recommend()
For a candidate course, structural_sim(candidate) is the mean of pairwise
structural similarities against each input course:
structural_sim(candidate) = mean of structural_sim(candidate_id, input_id)
                            for each input_id in input_course_ids

Implementation Notes for recommender.py

Build two lookup structures once at the top of recommend(), before the
main loop:

python   courses_by_id = {c["id"]: c for c in courses}

   reverse_index = {}  # prereq_id -> list of course_ids that require it
   for c in courses:
       for p in c["prerequisites"]:
           reverse_index.setdefault(p, []).append(c["id"])

Implement the following as module-level private helper functions:

_decay_weight(d: int) -> float
_weighted_neighborhood(course_id, courses_by_id, reverse_index) -> dict[str, float]
_structural_sim_pair(id_a, id_b, courses_by_id, reverse_index) -> float


Cache neighborhoods during recommend() to avoid recomputing the same
course multiple times:

python   neighborhood_cache = {}
   def get_neighborhood(cid):
       if cid not in neighborhood_cache:
           neighborhood_cache[cid] = _weighted_neighborhood(cid, courses_by_id, reverse_index)
       return neighborhood_cache[cid]

Import the new constants from app.core.config:

python   from app.core.config import (
       COSINE_WEIGHT, STRUCTURAL_WEIGHT, PAGERANK_WEIGHT,
       DECAY_ALPHA, DECAY_K
   )

The recommend() function signature does not change.


config.py Additions
Add the following block to app/core/config.py. Do not remove or modify
any existing constants.
python# Recommendation scoring weights (must sum to 1.0)
COSINE_WEIGHT      = 0.55
STRUCTURAL_WEIGHT  = 0.30
PAGERANK_WEIGHT    = 0.15

# Prerequisite depth decay parameters
DECAY_ALPHA = 0.30   # floor weight for distant nodes
DECAY_K     = 0.15   # slope of linear decay per hop

Test Cases for tests/test_recommender.py
Use this mock dataset for all structural tests:
pythonmock_courses = [
    {"id": "A", "name": "A", "description": "a", "prerequisites": [],         "department": "X", "units": 9, "source": "official"},
    {"id": "B", "name": "B", "description": "b", "prerequisites": ["A"],      "department": "X", "units": 9, "source": "official"},
    {"id": "C", "name": "C", "description": "c", "prerequisites": ["A"],      "department": "X", "units": 9, "source": "official"},
    {"id": "D", "name": "D", "description": "d", "prerequisites": ["B", "E"], "department": "X", "units": 9, "source": "official"},
    {"id": "E", "name": "E", "description": "e", "prerequisites": [],         "department": "X", "units": 9, "source": "official"},
]
courses_by_id = {c["id"]: c for c in mock_courses}
reverse_index = {}
for c in mock_courses:
    for p in c["prerequisites"]:
        reverse_index.setdefault(p, []).append(c["id"])
Test: _decay_weight shape
pythonassert _decay_weight(1) == pytest.approx(0.85)
assert _decay_weight(2) == pytest.approx(0.70)
assert _decay_weight(5) == pytest.approx(0.30)
assert _decay_weight(10) == pytest.approx(0.30)  # floor holds
Test: weighted neighborhood contents
python# B's neighborhood: upstream A (d=1, w=0.85), downstream D (d=1, w=0.85)
nb_B = _weighted_neighborhood("B", courses_by_id, reverse_index)
assert nb_B["A"] == pytest.approx(0.85)
assert nb_B["D"] == pytest.approx(0.85)
assert "B" not in nb_B  # self excluded

# D's neighborhood: upstream B(0.85), E(0.85), A(0.70 via B)
nb_D = _weighted_neighborhood("D", courses_by_id, reverse_index)
assert nb_D["B"] == pytest.approx(0.85)
assert nb_D["E"] == pytest.approx(0.85)
assert nb_D["A"] == pytest.approx(0.70)
Test: B and C are more similar to each other than B is to E
python# B and C both have A upstream and D downstream (C is also upstream of D via B)
# E has no shared neighbors with B except D downstream
sim_BC = _structural_sim_pair("B", "C", courses_by_id, reverse_index)
sim_BE = _structural_sim_pair("B", "E", courses_by_id, reverse_index)
assert sim_BC > sim_BE
Test: zero division guard
python# If both neighborhoods are empty, return 0.0 without raising
result = _structural_sim_pair("A", "E", courses_by_id, reverse_index)
# A has downstream B, C; E has downstream D — they share no neighbors in this mock
assert isinstance(result, float)
assert 0.0 <= result <= 1.0
Test: existing recommend() contracts unchanged
python# empty input
assert recommend([], mock_courses, sim_matrix, pagerank_scores) == []

# returned courses not in input
results = recommend(["B"], mock_courses, sim_matrix, pagerank_scores, top_n=3)
assert all(r["id"] != "B" for r in results)

# length does not exceed top_n
assert len(results) <= 3

# sorted by descending score
scores = [r["score"] for r in results]
assert scores == sorted(scores, reverse=True)

What This Patch Does NOT Change

pagerank.py — untouched
builder.py — untouched
embedder/model.py — untouched
embedder/similarity.py — untouched
data_loader.py — untouched
All UI files — untouched
The recommend() function signature — unchanged