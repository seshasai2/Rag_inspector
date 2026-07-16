"""Create documents table (Phase 10.3).

Revision ID: 016_documents
Revises: 015_autofix_status
Create Date: 2026-07-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "016_documents"
down_revision: Union[str, None] = "015_autofix_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("pipeline_id", sa.String(length=36), sa.ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("document_type", sa.String(length=100), nullable=True),
        sa.Column("last_modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("days_since_modified", sa.Integer(), nullable=True),
        sa.Column("freshness_status", sa.String(length=50), nullable=False, server_default="fresh"),
        sa.Column("freshness_alert_sent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("topic_labels", sa.Text(), nullable=True),
        sa.Column("coverage_score", sa.Float(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stale_chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_documents_pipeline", "documents", ["pipeline_id"])
    op.create_index("idx_documents_freshness", "documents", ["pipeline_id", "freshness_status"])


def downgrade() -> None:
    op.drop_index("idx_documents_freshness", table_name="documents")
    op.drop_index("idx_documents_pipeline", table_name="documents")
    op.drop_table("documents")
