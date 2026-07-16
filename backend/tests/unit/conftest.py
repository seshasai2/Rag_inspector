"""Unit-test fixtures: keep ML model loads out of the critical path suite."""

from __future__ import annotations

import sys
import types

import pytest

from app.services import ml_models as ml_models_mod


@pytest.fixture(autouse=True)
def _stub_heavy_ml_models(monkeypatch):
    """
    Block sentence-transformers / torch downloads during unit tests.
    Real loaders catch init failures and return None (keyword fallbacks).
    """
    ml_models_mod.reset_ml_model_cache_for_tests()

    fake_st = types.ModuleType("sentence_transformers")

    class CrossEncoder:  # noqa: N801 — mirrors library name
        def __init__(self, *args, **kwargs):
            raise RuntimeError("sentence-transformers blocked in unit tests")

    class SentenceTransformer:  # noqa: N801
        def __init__(self, *args, **kwargs):
            raise RuntimeError("sentence-transformers blocked in unit tests")

    fake_st.CrossEncoder = CrossEncoder
    fake_st.SentenceTransformer = SentenceTransformer
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_st)
