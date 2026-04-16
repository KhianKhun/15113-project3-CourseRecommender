# SPEC_3.1_recommender_patch.md
# CMU Course Graph — Patch for Segment 3: Recommender Scoring Fix
# This file SUPERSEDES the ranking step (Step 3) of the recommend() function
# described in SPEC_3_recommender_prereq.md.
# Read SPEC_0 → SPEC_3 → this file in order before implementing.
# This session is responsible for exactly one file: app/core/recommender.py
# Do not create or modify any files outside of this file,
# except to add constants to app/core/config.py as specified below.

---

## What Changed and Why

SPEC_3 ranked recommendation candidates purely by PageRank score.
PageRank measures global centrality in the course graph — how "important"
a course is across the entire curriculum. This caused a systematic failure:
niche or domain-specific input courses (e.g., a pure math course like 21-235)
would produce recommendations dominated by globally central courses (e.g.,
10-606) that happen to sit at the intersection of many edges, regardless of
whether they are semantically close to the user's input.

The fix is to blend two signals: semantic similarity (local relevance to the
user's input) and PageRank (global importance as a tie-breaker). Similarity
takes the dominant weight so that results are anchored to the user's actual
intent.

This fix is consistent with the scoring logic introduced in SPEC_4.1 for
node ranking in the UI visualization. Both use the same α = SIMILARITY_WEIGHT
from config.py to ensure the recommender and the graph display agree on what
"relevance" means.

---

## config.py additions

Add the following two constants to app/core/config.py. Do not modify any
existing constants. These are the single source of truth for scoring weights
and must be imported by recommender.py — do not hardcode numeric values.

```python
# Scoring weights for recommendation and node ranking
SIMILARITY_WEIGHT = 0.7    # α: weight given to semantic similarity
PAGERANK_WEIGHT = 0.3      # (1 - α): weight given to PageRank
```

Note: SPEC_4.1 defines the same constants for the UI layer's node ranking.
Both segments must import from the same config.py. Do not redefine these
values in recommender.py.

---

## Revised recommend() — Step 3: Rank by Blended Score

Replace the original Step 3 ("rank by PageRank") with the following logic.
Steps 1, 2, and 4 are unchanged from SPEC_3.

### Interface contract (unchanged from SPEC_3)

```python
def recommend(
    input_course_ids: list[str],
    courses: list[dict],
    similarity_matrix: np.ndarray,
    pagerank_scores: dict[str, float],
    top_n: int = 5
) -> list[dict]:
```

The function signature does not change. similarity_matrix was already a
parameter in SPEC_3 (used in Step 2 to collect neighbors). It is now also
used in Step 3 for scoring.

### Revised Step 3: blended scoring

For each candidate index collected in Step 2, compute a blended score:
blended_score(candidate) =
SIMILARITY_WEIGHT × mean_similarity(candidate, input_indices)

PAGERANK_WEIGHT   × pagerank_score(candidate)


Where mean_similarity is the arithmetic mean of
similarity_matrix[candidate_idx][input_idx] over all indices in
input_indices (the set built in Step 1). If input_indices has only one
element, mean_similarity reduces to a single similarity value.

pagerank_score(candidate) is retrieved from pagerank_scores by course id.
If a candidate id is missing from pagerank_scores, treat its PageRank as 0.0
and log a warning — do not crash.

Sort all candidates by descending blended_score.

### Step 4: return top_n (revised field name)

Retrieve the full course dict for each top candidate from courses.
Attach the field score: float containing the blended_score (not the raw
PageRank score). This change means the score displayed in the UI now
reflects combined relevance, not just centrality.

If top_n exceeds the number of available candidates, return all available
candidates without raising an error (unchanged from SPEC_3).

---

## Edge Cases (unchanged from SPEC_3)

If input_course_ids is empty, return an empty list immediately.
No scoring computation should occur for an empty input.

---

## What Is Not Changed

The function signature of recommend() is identical to SPEC_3. Steps 1 and 2
(index resolution and neighbor collection) are unchanged. prereq.py is not
touched by this patch. No other file in app/core/ is modified except the
config.py constants above.

---

## Testing notes for tests/test_recommender.py

Add the following test cases to the existing test file.

First, a blended score dominance test: construct a scenario where candidate A
has high similarity but low PageRank, and candidate B has low similarity but
high PageRank. Verify that candidate A ranks above candidate B when
SIMILARITY_WEIGHT = 0.7.

Second, a score field verification test: verify that the score field in each
returned dict is not equal to the raw PageRank score, confirming that blending
is actually applied and stored.

Third, a missing PageRank graceful fallback test: include a candidate whose id
is absent from pagerank_scores. Verify no exception is raised and the candidate
receives a PageRank contribution of 0.0.