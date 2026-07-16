"""Index audit for traces/chunks list filters (Phase 6.1).

Revision ID: 013_list_filter_indexes
Revises: 012_pipeline_hallucination_cost
Create Date: 2026-07-13

Justifications: docs/INDEXES.md
"""
from typing import Sequence, Union

from alembic import op


revision: str = "013_list_filter_indexes"
down_revision: Union[str, None] = "012_pipeline_hallucination_cost"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ownership scope for every queries/chunks list
    op.create_index("ix_pipelines_user_id", "pipelines", ["user_id"], unique=False)

    # query_traces list filters (GET /queries)
    op.create_index(
        "ix_query_traces_pipeline_id_traced_at",
        "query_traces",
        ["pipeline_id", "traced_at"],
        unique=False,
    )
    op.create_index(
        "ix_query_traces_pipeline_id_failure_type",
        "query_traces",
        ["pipeline_id", "failure_type"],
        unique=False,
    )
    op.create_index(
        "ix_query_traces_pipeline_id_is_hallucination",
        "query_traces",
        ["pipeline_id", "is_hallucination"],
        unique=False,
    )

    # chunk_stats list filters (GET /chunks)
    op.create_index(
        "ix_chunk_stats_pipeline_id_is_flagged",
        "chunk_stats",
        ["pipeline_id", "is_flagged"],
        unique=False,
    )
    op.create_index(
        "ix_chunk_stats_pipeline_id_retrieval_count",
        "chunk_stats",
        ["pipeline_id", "retrieval_count"],
        unique=False,
    )
    op.create_index(
        "ix_chunk_stats_pipeline_id_chunk_id",
        "chunk_stats",
        ["pipeline_id", "chunk_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_chunk_stats_pipeline_id_chunk_id", table_name="chunk_stats")
    op.drop_index("ix_chunk_stats_pipeline_id_retrieval_count", table_name="chunk_stats")
    op.drop_index("ix_chunk_stats_pipeline_id_is_flagged", table_name="chunk_stats")
    op.drop_index("ix_query_traces_pipeline_id_is_hallucination", table_name="query_traces")
    op.drop_index("ix_query_traces_pipeline_id_failure_type", table_name="query_traces")
    op.drop_index("ix_query_traces_pipeline_id_traced_at", table_name="query_traces")
    op.drop_index("ix_pipelines_user_id", table_name="pipelines")
