# CMU Course Recommender & Visualization

A locally run course visualization and recommendation tool. It builds a semantic space and prerequisite graph from CMU course descriptions, and supports interactive exploration and recommendations.

## Project Features

1. Semantic Graph
- Generates vector representations from course descriptions and visualizes them in 2D/3D projections.
- Supports course search, course selection, dynamic highlighting, and recommendations.
- Supports `Hidden Course`: hides only graph points and recommendation list items, without changing scoring logic.

2. Prerequisite Path
- Lets users select a single target course and view its prerequisite subgraph and depth levels.
- Helps users quickly understand what they need to take beforehand.

3. Recommendation System
- Combines semantic similarity, structural prerequisite score (`prereq score`), and PageRank score.
- Supports multi-course input scenarios.

4. Startup Acceleration Cache
- Uses `.npy` cache files for graph construction, PageRank, and prerequisite structural scores.
- Reduces repeated startup computation.

## How to Use

### In the UI
1. Open `Semantic Graph`:
- Choose 2D/3D, max displayed nodes, and highlighted course count.
- Search and select courses to view highlighted nodes and recommendations.

2. Open `Hidden Course`:
- Use the same search + selection interaction as course search.
- Hidden courses persist across tabs and affect display only (not algorithmic computation).

3. Open `Prerequisite Path`:
- Select one course and view its prerequisite dependency graph and depth summary.

### Command Line (Data-related)
- Scrape/update course data:
```bash
python -m data_pipeline.scraper
```
- Validate course data:
```bash
python -m data_pipeline.validator
```

## Feature I’m Most Proud Of

The `Hidden Course` design and the clean separation between display and computation:
- Users can hide courses from the graph and recommendation list.
- Center calculation, recommendation scoring, and ranking logic remain unchanged.
- This keeps algorithm behavior stable while improving interaction control.

Another feature I am especially proud of is a custom structural-similarity algorithm inspired by neural-network-style message passing:
- It propagates influence along prerequisite chains in both directions:
  - upstream (what this course depends on),
  - downstream (what future courses this course unlocks).
- Influence decays with graph distance using a controlled decay function (with a floor), so nearby courses have stronger impact while distant courses still contribute.
- It also supports different directional weights for upstream vs. downstream influence.
- The final result is a cached course-to-course prerequisite score matrix that captures both prerequisite and future-course context, and this structural signal is combined with cosine similarity and PageRank in recommendation scoring.

## Run Locally

### 1. Prepare Environment
- Python 3.10+ (recommended)
- Install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Startup Commands (Copy & Run)
```bash
cd 15113-project3-CourseRecommender
pip install -r requirements.txt
streamlit run app/app.py
```

### 3. Start the App
```bash
streamlit run app/app.py
```

On first run, embedding/model setup may take some time. Later runs are faster due to caching.

### 4. Optional: Run Tests
```bash
python -m pytest -q
```

## Secret / Key Handling

- This project currently does not rely on OpenAI or other paid external APIs for core functionality, so no API key is required.
- The text embedding model is handled via local cache through `sentence-transformers` (first run may download model files).
- If keys are introduced in the future, store them in environment variables or `.env` files, and never commit them to the repository.

## Project Structure (Simplified)

```text
app/
  app.py
  core/
  ui/
data/
data_pipeline/
tests/
SPEC/
```
