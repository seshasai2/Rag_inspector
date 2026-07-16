"""Add security, delivery, report, and billing maturity tables

Revision ID: 007_security_delivery_billing
Revises: 006_enterprise_platform
Create Date: 2026-06-21
"""
from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = "007_security_delivery_billing"
down_revision: Union[str, None] = "006_enterprise_platform"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("api_keys", sa.Column("scopes", sa.Text(), nullable=True))
    op.add_column("api_keys", sa.Column("organization_id", sa.String(36), nullable=True))
    op.create_index("ix_api_keys_organization_id", "api_keys", ["organization_id"])
    op.create_foreign_key("fk_api_keys_organization_id", "api_keys", "organizations", ["organization_id"], ["id"], ondelete="CASCADE")
    op.add_column("pipelines", sa.Column("organization_id", sa.String(36), nullable=True))
    op.create_index("ix_pipelines_organization_id", "pipelines", ["organization_id"])
    op.create_foreign_key("fk_pipelines_organization_id", "pipelines", "organizations", ["organization_id"], ["id"], ondelete="CASCADE")
    op.add_column("user_settings", sa.Column("organization_id", sa.String(36), nullable=True))
    op.create_index("ix_user_settings_organization_id", "user_settings", ["organization_id"])
    op.create_foreign_key("fk_user_settings_organization_id", "user_settings", "organizations", ["organization_id"], ["id"], ondelete="CASCADE")
    op.add_column("integration_webhooks", sa.Column("signing_secret_hash", sa.String(255), nullable=True))

    op.create_table("mfa_recovery_codes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code_hash", sa.String(255), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_mfa_recovery_codes_user_id", "mfa_recovery_codes", ["user_id"])
    op.create_index("ix_mfa_recovery_codes_code_hash", "mfa_recovery_codes", ["code_hash"])

    op.create_table("remembered_devices",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_hash", sa.String(255), nullable=False),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_remembered_devices_user_id", "remembered_devices", ["user_id"])
    op.create_index("ix_remembered_devices_device_hash", "remembered_devices", ["device_hash"])

    op.create_table("ip_allowlist_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cidr", sa.String(64), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_ip_allowlist_entries_organization_id", "ip_allowlist_entries", ["organization_id"])

    op.create_table("webhook_deliveries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("webhook_id", sa.String(36), sa.ForeignKey("integration_webhooks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_webhook_deliveries_webhook_id", "webhook_deliveries", ["webhook_id"])
    op.create_index("ix_webhook_deliveries_event_type", "webhook_deliveries", ["event_type"])
    op.create_index("ix_webhook_deliveries_status", "webhook_deliveries", ["status"])

    op.create_table("report_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("report_type", sa.String(100), nullable=False),
        sa.Column("format", sa.String(20), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_report_history_user_id", "report_history", ["user_id"])
    op.create_index("ix_report_history_organization_id", "report_history", ["organization_id"])
    op.create_index("ix_report_history_created_at", "report_history", ["created_at"])

    op.create_table("invoice_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("provider_invoice_id", sa.String(255), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("tax_amount", sa.Float(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_invoice_records_user_id", "invoice_records", ["user_id"])
    op.create_index("ix_invoice_records_organization_id", "invoice_records", ["organization_id"])
    op.create_index("ix_invoice_records_provider_invoice_id", "invoice_records", ["provider_invoice_id"])


def downgrade() -> None:
    for table in ["invoice_records", "report_history", "webhook_deliveries", "ip_allowlist_entries", "remembered_devices", "mfa_recovery_codes"]:
        op.drop_table(table)
    op.drop_column("integration_webhooks", "signing_secret_hash")
    op.drop_constraint("fk_user_settings_organization_id", "user_settings", type_="foreignkey")
    op.drop_column("user_settings", "organization_id")
    op.drop_constraint("fk_pipelines_organization_id", "pipelines", type_="foreignkey")
    op.drop_column("pipelines", "organization_id")
    op.drop_constraint("fk_api_keys_organization_id", "api_keys", type_="foreignkey")
    op.drop_column("api_keys", "organization_id")
    op.drop_column("api_keys", "scopes")
