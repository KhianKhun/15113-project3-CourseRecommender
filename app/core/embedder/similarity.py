"""
similarity.py — app/core/embedder
Computes cosine similarity between course embeddings.
"""

import numpy as np


def compute_similarity_matrix(embeddings: np.ndarray) -> np.ndarray:
    """
    Accepts an (N, D) embedding matrix (expected to be L2-normalized).
    Returns an (N, N) cosine similarity matrix with values clipped to [0, 1].

    Since embeddings from model.py are L2-normalized, cosine similarity = dot product.

    Args:
        embeddings: An (N, D) numpy matrix of L2-normalized course embeddings.

    Returns:
        An (N, N) float32 numpy matrix of pairwise cosine similarities.
    """
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1e-10, norms)
    normalized = embeddings / norms
    return np.clip(np.dot(normalized, normalized.T).astype(np.float32), 0.0, 1.0)
