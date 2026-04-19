"""
model.py — app/core/embedder
Loads or computes sentence embeddings for all courses using all-MiniLM-L6-v2.
"""

import numpy as np
import streamlit as st
from sentence_transformers import SentenceTransformer

from app.core.config import EMBEDDING_MODEL_NAME, EMBEDDING_DIM, EMBEDDINGS_PATH


@st.cache_resource
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def get_embeddings(courses: list[dict]) -> np.ndarray:
    """
    Accepts the list returned by load_courses().

    If embeddings.npy exists with matching shape (N, EMBEDDING_DIM), loads and
    returns it directly. Otherwise recomputes, saves to embeddings.npy, and returns
    the resulting matrix of shape (N, EMBEDDING_DIM).

    Embeddings are L2-normalized so cosine similarity equals dot product.

    Args:
        courses: The merged course list from data_loader.load_courses().

    Returns:
        An (N, EMBEDDING_DIM) numpy float32 matrix where N == len(courses).
    """
    n = len(courses)

    if EMBEDDINGS_PATH.exists():
        cached = np.load(EMBEDDINGS_PATH)
        if cached.shape == (n, EMBEDDING_DIM):
            return cached

    model = _get_model()
    descriptions = [c["description"] for c in courses]

    embeddings = model.encode(
        descriptions,
        batch_size=32,
        normalize_embeddings=True,
        show_progress_bar=False,
    ).astype(np.float32)

    EMBEDDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.save(EMBEDDINGS_PATH, embeddings)

    return embeddings
