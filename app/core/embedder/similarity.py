"""
similarity.py — app/core/embedder
Computes cosine similarity between course embeddings.
"""

import numpy as np


def compute_similarity_matrix(embeddings: np.ndarray) -> np.ndarray:
    """
    Accepts an (N, D) embedding matrix.
    Returns an (N, N) cosine similarity matrix with values in [0, 1].

    Cosine similarity is computed as the dot product of L2-normalized vectors,
    then clipped to [0, 1] to discard negative similarities.

    Args:
        embeddings: An (N, D) numpy matrix of course embeddings.

    Returns:
        An (N, N) float32 numpy matrix of pairwise cosine similarities.
    """
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1e-10, norms)  # Avoid division by zero
    normalized = embeddings / norms
    similarity = np.dot(normalized, normalized.T).astype(np.float32)
    return np.clip(similarity, 0.0, 1.0)


def get_top_k_similar(
    course_idx: int,
    similarity_matrix: np.ndarray,
    k: int
) -> list[int]:
    """
    Returns the indices of the k most similar courses to course_idx,
    excluding course_idx itself. Results are sorted by descending similarity.

    Args:
        course_idx: The index of the query course in the similarity matrix.
        similarity_matrix: An (N, N) cosine similarity matrix.
        k: Number of similar courses to return.

    Returns:
        A list of up to k integer indices sorted by descending similarity.
    """
    row = similarity_matrix[course_idx].copy()
    row[course_idx] = -1.0  # Exclude self

    n = row.shape[0]
    k = min(k, n - 1)

    top_indices = np.argpartition(row, -k)[-k:]
    top_indices = top_indices[np.argsort(row[top_indices])[::-1]]

    return top_indices.tolist()
