"""
pca.py — app/core/reduction
Reduces high-dimensional course embeddings to 2D or 3D for visualization.
"""

import numpy as np
from sklearn.decomposition import PCA


def reduce_dimensions(
    embeddings: np.ndarray,
    n_components: int
) -> tuple[np.ndarray, float]:
    """
    Applies PCA to the embedding matrix.

    Returns (reduced_coordinates, explained_variance_ratio_sum).
    reduced_coordinates has shape (N, n_components).

    Args:
        embeddings: An (N, D) numpy embedding matrix.
        n_components: Number of output dimensions. Must be 2 or 3.

    Returns:
        A tuple of:
            reduced_coordinates: (N, n_components) float32 numpy array.
            explained_variance_ratio_sum: float, sum of explained variance
                ratios for the selected components (value in [0, 1]).

    Raises:
        ValueError: If n_components is not 2 or 3.
    """
    if n_components not in (2, 3):
        raise ValueError(f"n_components must be 2 or 3, got {n_components}")

    pca = PCA(n_components=n_components, random_state=42)
    reduced = pca.fit_transform(embeddings).astype(np.float32)
    explained = round(float(np.sum(pca.explained_variance_ratio_)), 4)

    return reduced, explained
