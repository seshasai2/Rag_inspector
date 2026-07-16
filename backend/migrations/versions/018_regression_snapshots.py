"""Create regression_snapshots (Phase 10.5).

Revision ID: 018_regression_snapshots
Revises: 017_monitoring
Create Date: 2026-07-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "018_regression_snapshots"
down_revision: Union[str, None] = "017_monitoring"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "regression_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "pipeline_id",
            sa.String(length=36),
            sa.ForeignKey("pipelines.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("snapshot_label", sa.String(length=255), nullable=True),
        sa.Column("trust_score", sa.Float(), nullable=False),
        sa.Column("faithfulness_avg", sa.Float(), nullable=True),
        sa.Column("context_precision_avg", sa.Float(), nullable=True),
        sa.Column("hallucination_rate", sa.Float(), nullable=True),
        sa.Column("trace_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_regression_snapshots_pipeline_id", "regression_snapshots", ["pipeline_id"])
    op.create_index("idx_snapshots_pipeline", "regression_snapshots", ["pipeline_id", "snapshot_at"])


def downgrade() -> None:
    op.drop_index("idx_snapshots_pipeline", table_name="regression_snapshots")
    op.drop_index("ix_regression_snapshots_pipeline_id", table_name="regression_snapshots")
    op.drop_table("regression_snapshots")
