# PROMPT_LOG.md
# CMU Course Graph — Session Prompt Log

This file records the key prompts and decisions made during each Claude Code session.
Each entry should include: date, segment worked on, key decisions made, and any
interface contract changes.

---

## Session 1 — 2026-04-15

**Segment:** SPEC_0 scaffold (all segments)

**Work done:**
- Read SPEC_0_convention.md to establish project conventions.
- Created full directory structure and skeleton files for all four segments.
- Implemented all module interfaces as specified in SPEC_0 Module Interface Contracts.
- Created `data/courses.json` with 15 sample CMU courses across CS, ML, MATH, STAT, LTI, RI departments.
- Wrote unit tests for `builder.py`, `pagerank.py`, `recommender.py`, and `pca.py`.

**Interface contracts followed:**
- All function signatures match SPEC_0 exactly.
- All paths imported from `app/core/config.py`.
- No hardcoded path strings.

**Decisions:**
- `app/app.py` uses `@st.cache_resource` for all heavy data objects to avoid recomputation on every UI interaction.
- `prereq_view.py` uses a hierarchical BFS layout for the prerequisite tree visualization.
- Semantic edges are bidirectional in `builder.py`; prerequisite edges are directional (prereq → course).

**Interface changes:** None. All contracts unchanged from SPEC_0.

---
