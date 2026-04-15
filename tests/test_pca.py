"""
test_pca.py — tests
Unit tests for app/core/reduction/pca.py
"""

import numpy as np
import pytest

from app.core.reduction.pca import reduce_dimensions


def _random_embeddings(n: int = 20, d: int = 64, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.standard_normal((n, d)).astype(np.float32)


class TestReduceDimensions:
    def test_2d_output_shape(self):
        emb = _random_embeddings()
        coords, _ = reduce_dimensions(emb, n_components=2)
        assert coords.shape == (20, 2)

    def test_3d_output_shape(self):
        emb = _random_embeddings()
        coords, _ = reduce_dimensions(emb, n_components=3)
        assert coords.shape == (20, 3)

    def test_explained_variance_in_range(self):
        emb = _random_embeddings()
        _, variance = reduce_dimensions(emb, n_components=2)
        assert 0.0 <= variance <= 1.0

    def test_returns_float32(self):
        emb = _random_embeddings()
        coords, _ = reduce_dimensions(emb, n_components=2)
        assert coords.dtype == np.float32

    def test_raises_on_invalid_n_components(self):
        emb = _random_embeddings()
        with pytest.raises(ValueError):
            reduce_dimensions(emb, n_components=4)

    def test_raises_on_n_components_1(self):
        emb = _random_embeddings()
        with pytest.raises(ValueError):
            reduce_dimensions(emb, n_components=1)

    def test_3d_variance_ge_2d_variance(self):
        emb = _random_embeddings()
        _, var2 = reduce_dimensions(emb, n_components=2)
        _, var3 = reduce_dimensions(emb, n_components=3)
        assert var3 >= var2 - 1e-6  # 3D captures at least as much variance
