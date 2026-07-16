"""ML model lazy cache + warm path (Phase 6.3)."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock

from app.services import ml_models


def setup_function():
    ml_models.reset_ml_model_cache_for_tests()


def teardown_function():
    ml_models.reset_ml_model_cache_for_tests()


def test_lazy_embedding_loads_once():
    fake = MagicMock(name="emb")
    sys.modules["sentence_transformers"].SentenceTransformer = MagicMock(return_value=fake)
    a = ml_models.get_embedding_model()
    b = ml_models.get_embedding_model()
    assert a is fake
    assert b is fake
    assert sys.modules["sentence_transformers"].SentenceTransformer.call_count == 1


def test_lazy_nli_loads_once():
    fake = MagicMock(name="nli")
    sys.modules["sentence_transformers"].CrossEncoder = MagicMock(return_value=fake)
    a = ml_models.get_nli_cross_encoder()
    b = ml_models.get_cross_encoder()
    assert a is fake
    assert b is fake
    assert sys.modules["sentence_transformers"].CrossEncoder.call_count == 1


def test_warm_ml_models_loads_both():
    emb = MagicMock(name="emb")
    nli = MagicMock(name="nli")
    sys.modules["sentence_transformers"].SentenceTransformer = MagicMock(return_value=emb)
    sys.modules["sentence_transformers"].CrossEncoder = MagicMock(return_value=nli)
    status = ml_models.warm_ml_models()
    assert status["embedding_loaded"] is True
    assert status["nli_loaded"] is True


def test_failed_load_returns_none_and_does_not_retry_storm():
    sys.modules["sentence_transformers"].SentenceTransformer = MagicMock(
        side_effect=RuntimeError("no torch")
    )
    assert ml_models.get_embedding_model() is None
    assert ml_models.get_embedding_model() is None
    assert sys.modules["sentence_transformers"].SentenceTransformer.call_count == 1
