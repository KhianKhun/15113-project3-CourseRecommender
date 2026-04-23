from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = ROOT_DIR / "data"

COURSES_PATH      = DATA_DIR / "courses.json"
USER_COURSES_PATH = DATA_DIR / "user_courses.json"
EMBEDDINGS_PATH   = DATA_DIR / "embeddings.npy"
GRAPH_EDGE_MATRIX_PATH = DATA_DIR / "graph_edge_matrix.npy"
PAGERANK_MATRIX_PATH = DATA_DIR / "pagerank_scores.npy"
PREREQ_SCORE_MATRIX_PATH = DATA_DIR / "prereq_scores.npy"

# Model configuration
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM        = 384

# Graph configuration
DEFAULT_SIMILARITY_THRESHOLD = 0.3
DEFAULT_TOP_K_NODES = 30
DEFAULT_ANCHOR_COUNT = 10

# PageRank configuration
PAGERANK_ALPHA         = 0.75  # damping factor (teleportation probability = 1 - alpha)
PAGERANK_PREREQ_WEIGHT = 0.5   # edge weight for prerequisite edges

# PCA configuration
DEFAULT_N_COMPONENTS = 2

# Recommendation scoring weights (must sum to 1.0)
# score = COSINE_WEIGHT * cosine_sim + STRUCTURAL_WEIGHT * structural_sim + PAGERANK_WEIGHT * pagerank
COSINE_WEIGHT     = 0.70
STRUCTURAL_WEIGHT = 0.20
PAGERANK_WEIGHT   = 0.10

# Structural similarity filter thresholds (AND condition)
# Courses must meet BOTH to have structural similarity computed; others get 0.
STRUCTURAL_COSINE_THRESHOLD   = 0.2
STRUCTURAL_PAGERANK_THRESHOLD = 0.1

# Prerequisite depth decay parameters
DECAY_ALPHA = 0.25  # floor weight for distant nodes
DECAY_K     = 0.20  # slope of linear decay per hop

# Structural similarity direction multipliers
UPSTREAM_WEIGHT   = 1.0  # prerequisite direction (A is required before B)
DOWNSTREAM_WEIGHT = 0.6  # downstream direction (B unlocks C)
