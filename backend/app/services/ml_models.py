"""
Central lazy cache for heavy ML models (NLI + embeddings).

Strategy (Phase 6.3):
- **Lazy:** first analysis call loads the model into process memory.
- **Warm:** Celery workers optionally preload on ``worker_process_init`` so the
  first user trace does not pay cold-start latency.

See ``docs/COLD_START.md``.
"""

from __future__ import annotations

import threading
from typing import Any, Optional

import structlog

from app.core.config import settings

logger = structlog.get_logger()

_lock = threading.Lock()
_embedding_model: Any = None
_nli_cross_encoder: Any = None
_embedding_load_attempted = False
_nli_load_attempted = False


def embedding_model_name() -> str:
    return settings.EMBEDDING_MODEL_NAME


def nli_model_name() -> str:
    return settings.NLI_MODEL_NAME


def get_embedding_model() -> Optional[Any]:
    """Lazy-load SentenceTransformer used by RAGAS / context recall / fix clusters."""
    global _embedding_model, _embedding_load_attempted
    if _embedding_model is not None or _embedding_load_attempted:
        return _embedding_model
    with _lock:
        if _embedding_model is not None or _embedding_load_attempted:
            return _embedding_model
        _embedding_load_attempted = True
        try:
            from sentence_transformers import SentenceTransformer

            name = embedding_model_name()
            logger.info("Loading embedding model (lazy)", model=name)
            _embedding_model = SentenceTransformer(name)
            logger.info("Embedding model ready", model=name)
        except Exception as e:
            logger.error("Failed to load embedding model", error=str(e))
            _embedding_model = None
    return _embedding_model


def get_nli_cross_encoder() -> Optional[Any]:
    """Lazy-load CrossEncoder used by grounding verification."""
    global _nli_cross_encoder, _nli_load_attempted
    if _nli_cross_encoder is not None or _nli_load_attempted:
        return _nli_cross_encoder
    with _lock:
        if _nli_cross_encoder is not None or _nli_load_attempted:
            return _nli_cross_encoder
        _nli_load_attempted = True
        try:
            from sentence_transformers import CrossEncoder

            name = nli_model_name()
            logger.info("Loading NLI cross-encoder (lazy)", model=name)
            _nli_cross_encoder = CrossEncoder(name)
            logger.info("NLI cross-encoder ready", model=name)
        except Exception as e:
            logger.error("Failed to load NLI cross-encoder", error=str(e))
            _nli_cross_encoder = None
    return _nli_cross_encoder


# Back-compat alias used by older call sites
get_cross_encoder = get_nli_cross_encoder


def model_cache_status() -> dict[str, Any]:
    return {
        "embedding_loaded": _embedding_model is not None,
        "nli_loaded": _nli_cross_encoder is not None,
        "embedding_model": embedding_model_name(),
        "nli_model": nli_model_name(),
        "warm_on_worker_start": bool(settings.WARM_ML_MODELS_ON_WORKER_START),
    }


def warm_ml_models(*, embedding: bool = True, nli: bool = True) -> dict[str, Any]:
    """
    Eagerly load models into this process (warm cache path).

    Safe to call multiple times; subsequent calls are no-ops once loaded.
    Failures are logged; callers should still run analysis with keyword fallbacks.
    """
    logger.info("Warming ML model cache", embedding=embedding, nli=nli)
    if embedding:
        get_embedding_model()
    if nli:
        get_nli_cross_encoder()
    status = model_cache_status()
    logger.info("ML model cache warm complete", **status)
    return status


def reset_ml_model_cache_for_tests() -> None:
    """Clear process cache (unit tests only)."""
    global _embedding_model, _nli_cross_encoder
    global _embedding_load_attempted, _nli_load_attempted
    with _lock:
        _embedding_model = None
        _nli_cross_encoder = None
        _embedding_load_attempted = False
        _nli_load_attempted = False
