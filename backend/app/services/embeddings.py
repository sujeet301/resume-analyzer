from functools import lru_cache
from typing import Sequence
import numpy as np
from app.core.config import settings

_model = None
_model_error = None

def _load_model():
    global _model, _model_error
    if _model is not None:
        return _model
    if _model_error is not None:
        raise RuntimeError(_model_error)
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(settings.embedding_model)
        return _model
    except Exception as exc:
        _model_error = f"Could not load embedding model '{settings.embedding_model}': {exc}"
        raise RuntimeError(_model_error)

def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    if not texts:
        return []
    model = _load_model()
    vectors = model.encode(list(texts), normalize_embeddings=True, convert_to_numpy=True)
    return vectors.astype(float).tolist()

def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    va, vb = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / denom) if denom else 0.0
