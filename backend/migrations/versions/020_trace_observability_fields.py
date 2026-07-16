"""Add QueryTrace observability fields (rank latency, session, metadata).

Revision ID: 020_trace_observability_fields
Revises: 019_retrieved_chunks_metadata_json
Create Date: 2026-07-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "020_trace_observability_fields"
down_revision: Union[str, None] = "019_retrieved_chunks_metadata_json"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLUMNS: tuple[tuple[str, sa.Column], ...] = (
    ("rank_latency_ms", sa.Column("rank_latency_ms", sa.Float(), nullable=True)),
    ("session_id", sa.Column("session_id", sa.String(length=64), nullable=True)),
    ("request_id", sa.Column("request_id", sa.String(length=64), nullable=True)),
    ("client_metadata_json", sa.Column("client_metadata_json", sa.Text(), nullable=True)),
    ("analysis_latencies_json", sa.Column("analysis_latencies_json", sa.Text(), nullable=True)),
)


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("query_traces")}

    for name, column in _COLUMNS:
        if name not in cols:
            op.add_column("query_traces", column)

    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("query_traces")}
    indexes = {ix["name"] for ix in insp.get_indexes("query_traces")}
    if "session_id" in cols and "ix_query_traces_session_id" not in indexes:
        op.create_index("ix_query_traces_session_id", "query_traces", ["session_id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    indexes = {ix["name"] for ix in insp.get_indexes("query_traces")}
    if "ix_query_traces_session_id" in indexes:
        op.drop_index("ix_query_traces_session_id", table_name="query_traces")

    cols = {c["name"] for c in insp.get_columns("query_traces")}
    for name, _ in reversed(_COLUMNS):
        if name in cols:
            op.drop_column("query_traces", name)
