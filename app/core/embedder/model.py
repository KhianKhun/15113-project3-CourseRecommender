"""
model.py — app/core/embedder
Loads or computes sentence embeddings for all courses.
"""

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import EMBEDDINGS_PATH, EMBEDDING_MODEL_NAME

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Returns the cached sentence-transformer model, loading it on first call."""
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def get_embeddings(courses: list[dict]) -> np.ndarray:
    """
    Accepts the list returned by load_courses().

    If embeddings.npy exists and its row count matches len(courses),
    loads and returns it directly.
    Otherwise recomputes embeddings, saves to embeddings.npy, and returns
    the resulting matrix of shape (N, D).

    Args:
        courses: The merged course list from data_loader.load_courses().

    Returns:
        An (N, D) numpy float32 matrix where N == len(courses) and D is
        the embedding dimension (384 for all-MiniLM-L6-v2).
    """
    n = len(courses)

    if EMBEDDINGS_PATH.exists():
        cached = np.load(EMBEDDINGS_PATH)
        if cached.shape[0] == n:
            return cached

    descriptions = [c["description"] for c in courses]
    model = _get_model()
    embeddings = model.encode(descriptions, show_progress_bar=True, convert_to_numpy=True)
    embeddings = embeddings.astype(np.float32)

    EMBEDDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.save(EMBEDDINGS_PATH, embeddings)

    return embeddings
