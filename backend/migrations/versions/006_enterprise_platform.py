"""Add enterprise platform models

Revision ID: 006_enterprise_platform
Revises: 005_organizations
Create Date: 2026-06-21
"""
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "006_enterprise_platform"
down_revision: Union[str, None] = "005_organizations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for value in ["admin", "engineer", "analyst"]:
            op.execute(f"ALTER TYPE userrole ADD VALUE IF NOT EXISTS '{value}'")

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("target_type", sa.String(100), nullable=True),
        sa.Column("target_id", sa.String(255), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_organization_id", "audit_logs", ["organization_id"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])

    op.create_table(
        "integration_webhooks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("webhook_url", sa.String(1024), nullable=False),
        sa.Column("events", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_integration_webhooks_organization_id", "integration_webhooks", ["organization_id"])
    op.create_index("ix_integration_webhooks_provider", "integration_webhooks", ["provider"])
    op.create_index("ix_integration_webhooks_user_id", "integration_webhooks", ["user_id"])

    op.create_table(
        "sso_connections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("issuer_url", sa.String(512), nullable=True),
        sa.Column("client_id", sa.String(255), nullable=True),
        sa.Column("client_secret_ref", sa.String(255), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sso_connections_organization_id", "sso_connections", ["organization_id"])
    op.create_index("ix_sso_connections_provider", "sso_connections", ["provider"])

    op.create_table(
        "mfa_factors",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("factor_type", sa.String(50), nullable=False),
        sa.Column("secret_ref", sa.String(255), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_mfa_factors_user_id", "mfa_factors", ["user_id"])

    op.create_table(
        "weekly_executive_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("recipient_email", sa.String(255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_weekly_executive_reports_organization_id", "weekly_executive_reports", ["organization_id"])
    op.create_index("ix_weekly_executive_reports_user_id", "weekly_executive_reports", ["user_id"])

    op.create_table(
        "sla_thresholds",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("pipeline_id", sa.String(36), sa.ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=True),
        sa.Column("trust_score_min", sa.Float(), nullable=False, server_default="85"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sla_thresholds_organization_id", "sla_thresholds", ["organization_id"])
    op.create_index("ix_sla_thresholds_pipeline_id", "sla_thresholds", ["pipeline_id"])
    op.create_index("ix_sla_thresholds_user_id", "sla_thresholds", ["user_id"])


def downgrade() -> None:
    for table in ["sla_thresholds", "weekly_executive_reports", "mfa_factors", "sso_connections", "integration_webhooks", "audit_logs"]:
        op.drop_table(table)
