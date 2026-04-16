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

# Scoring weights for node ranking
SIMILARITY_WEIGHT = 0.85       # α in the scoring formula
PAGERANK_WEIGHT = 0.15         # (1 - α)