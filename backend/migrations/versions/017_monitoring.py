"""Create monitoring_configs + monitoring_runs (Phase 10.4).

Revision ID: 017_monitoring
Revises: 016_documents
Create Date: 2026-07-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "017_monitoring"
down_revision: Union[str, None] = "016_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "monitoring_configs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "pipeline_id",
            sa.String(length=36),
            sa.ForeignKey("pipelines.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("interval_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("probe_queries", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("alert_trust_threshold", sa.Float(), nullable=False, server_default="70.0"),
        sa.Column("alert_hallucination_threshold", sa.Float(), nullable=False, server_default="0.10"),
        sa.Column("alert_channels", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_monitoring_configs_pipeline_id", "monitoring_configs", ["pipeline_id"], unique=True)

    op.create_table(
        "monitoring_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "pipeline_id",
            sa.String(length=36),
            sa.ForeignKey("pipelines.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "config_id",
            sa.String(length=36),
            sa.ForeignKey("monitoring_configs.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("trust_score", sa.Float(), nullable=True),
        sa.Column("hallucination_rate", sa.Float(), nullable=True),
        sa.Column("probes_run", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("probes_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("alerts_triggered", sa.Text(), nullable=True),
        sa.Column("regression_detected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_monitoring_runs_pipeline_id", "monitoring_runs", ["pipeline_id"])
    op.create_index("ix_monitoring_runs_config_id", "monitoring_runs", ["config_id"])
    op.create_index("idx_monitoring_runs_pipeline", "monitoring_runs", ["pipeline_id", "run_at"])


def downgrade() -> None:
    op.drop_index("idx_monitoring_runs_pipeline", table_name="monitoring_runs")
    op.drop_index("ix_monitoring_runs_config_id", table_name="monitoring_runs")
    op.drop_index("ix_monitoring_runs_pipeline_id", table_name="monitoring_runs")
    op.drop_table("monitoring_runs")
    op.drop_index("ix_monitoring_configs_pipeline_id", table_name="monitoring_configs")
    op.drop_table("monitoring_configs")
