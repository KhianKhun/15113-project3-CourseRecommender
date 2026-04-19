from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = ROOT_DIR / "data"

COURSES_PATH = DATA_DIR / "courses.json"
USER_COURSES_PATH = DATA_DIR / "user_courses.json"
EMBEDDINGS_PATH = DATA_DIR / "embeddings.npy"

# Model configuration
EMBEDDING_MODEL_NAME   = "allenai/specter2_base"
EMBEDDING_ADAPTER_NAME = "allenai/specter2"

# Graph configuration
DEFAULT_SIMILARITY_THRESHOLD = 0.3
DEFAULT_TOP_K_NODES = 30
DEFAULT_ANCHOR_COUNT = 10

# PageRank configuration
PAGERANK_ALPHA        = 0.75   # damping factor (teleportation probability = 1 - alpha)
PAGERANK_PREREQ_WEIGHT = 0.5   # edge weight assigned to prerequisite edges (semantic edges use cosine similarity value)

# PCA configuration
DEFAULT_N_COMPONENTS = 2

# Recommendation scoring weights used by recommender.py (three-signal formula, must sum to 1.0)
# score = COSINE_WEIGHT * cosine_sim + STRUCTURAL_WEIGHT * structural_sim + PAGERANK_WEIGHT * pagerank
COSINE_WEIGHT     = 0.70
STRUCTURAL_WEIGHT = 0.20
PAGERANK_WEIGHT   = 0.10

# Prerequisite depth decay parameters
DECAY_ALPHA = 0.25   # floor weight for distant nodes
DECAY_K     = 0.20   # slope of linear decay per hop

# Structural similarity direction multipliers
UPSTREAM_WEIGHT   = 1.0   # prerequisite direction (A is required before B)
DOWNSTREAM_WEIGHT = 0.6   # downstream direction (B unlocks C)