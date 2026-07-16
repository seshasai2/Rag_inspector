"""Create knowledge_gaps table (Phase 10.1).

Revision ID: 014_knowledge_gaps
Revises: 013_list_filter_indexes
Create Date: 2026-07-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "014_knowledge_gaps"
down_revision: Union[str, None] = "013_list_filter_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_gaps",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("pipeline_id", sa.String(length=36), sa.ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic_label", sa.String(length=500), nullable=False),
        sa.Column("representative_query", sa.Text(), nullable=True),
        sa.Column("query_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("failure_rate", sa.Float(), nullable=True),
        sa.Column("affected_users_estimate", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_monthly_cost_usd", sa.Float(), nullable=True),
        sa.Column("priority", sa.String(length=50), nullable=False, server_default="medium"),
        sa.Column("suggested_document_topic", sa.Text(), nullable=True),
        sa.Column("auto_fix_draft", sa.Text(), nullable=True),
        sa.Column("fix_format", sa.String(length=50), nullable=False, server_default="markdown"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="open"),
        sa.Column("fixed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trust_improvement_after_fix", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_knowledge_gaps_pipeline_id", "knowledge_gaps", ["pipeline_id"])
    op.create_index("idx_gaps_pipeline", "knowledge_gaps", ["pipeline_id", "status", "priority"])


def downgrade() -> None:
    op.drop_index("idx_gaps_pipeline", table_name="knowledge_gaps")
    op.drop_index("ix_knowledge_gaps_pipeline_id", table_name="knowledge_gaps")
    op.drop_table("knowledge_gaps")
