"""
model.py — app/core/embedder
Loads or computes sentence embeddings for all courses using SPECTER2.
"""

import numpy as np
import torch
from adapters import AutoAdapterModel
from transformers import AutoTokenizer

from app.core.config import EMBEDDING_ADAPTER_NAME, EMBEDDING_MODEL_NAME, EMBEDDINGS_PATH

_model: AutoAdapterModel | None = None
_tokenizer: AutoTokenizer | None = None

_BATCH_SIZE = 16
_MAX_LENGTH = 512


def _get_model() -> tuple[AutoAdapterModel, AutoTokenizer]:
    global _model, _tokenizer
    if _model is None:
        _tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL_NAME)
        _model = AutoAdapterModel.from_pretrained(EMBEDDING_MODEL_NAME)
        _model.load_adapter(EMBEDDING_ADAPTER_NAME, source="hf", set_active=True)
        _model.eval()
    return _model, _tokenizer


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
        the embedding dimension (768 for specter2).
    """
    n = len(courses)

    if EMBEDDINGS_PATH.exists():
        cached = np.load(EMBEDDINGS_PATH)
        if cached.shape[0] == n:
            return cached

    model, tokenizer = _get_model()
    descriptions = [c["description"] for c in courses]

    all_embeddings = []
    with torch.no_grad():
        for i in range(0, len(descriptions), _BATCH_SIZE):
            batch = descriptions[i : i + _BATCH_SIZE]
            inputs = tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=_MAX_LENGTH,
                return_tensors="pt",
                return_token_type_ids=False,
            )
            output = model(**inputs)
            batch_embeddings = output.last_hidden_state[:, 0, :].cpu().numpy()
            all_embeddings.append(batch_embeddings)

    embeddings = np.vstack(all_embeddings).astype(np.float32)

    EMBEDDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.save(EMBEDDINGS_PATH, embeddings)

    return embeddings
