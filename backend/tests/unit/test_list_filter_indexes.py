"""Phase 6.1 — list-filter composite indexes are declared on models."""
from __future__ import annotations

from app.models.models import ChunkStat, Pipeline, QueryTrace


def _index_names(model) -> set[str]:
    return {idx.name for idx in model.__table__.indexes if idx.name}


def test_query_trace_list_indexes_declared():
    names = _index_names(QueryTrace)
    assert "ix_query_traces_pipeline_id_traced_at" in names
    assert "ix_query_traces_pipeline_id_failure_type" in names
    assert "ix_query_traces_pipeline_id_is_hallucination" in names


def test_chunk_stat_list_indexes_declared():
    names = _index_names(ChunkStat)
    assert "ix_chunk_stats_pipeline_id_is_flagged" in names
    assert "ix_chunk_stats_pipeline_id_retrieval_count" in names
    assert "ix_chunk_stats_pipeline_id_chunk_id" in names


def test_pipeline_user_id_indexed_for_ownership_scope():
    cols = {c.name for c in Pipeline.__table__.columns if c.index or c.primary_key}
    # Column(index=True) creates ix_pipelines_user_id
    assert any(
        idx.name == "ix_pipelines_user_id" or "user_id" in idx.columns.keys()
        for idx in Pipeline.__table__.indexes
    ) or Pipeline.__table__.c.user_id.index
