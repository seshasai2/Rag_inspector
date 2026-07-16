"""Add webhook event idempotency table

Revision ID: 004_webhook_events
Revises: 003_email_verification
Create Date: 2026-06-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004_webhook_events"
down_revision: Union[str, None] = "003_email_verification"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "webhook_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_event_id"),
    )
    op.create_index(op.f("ix_webhook_events_event_type"), "webhook_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_webhook_events_provider"), "webhook_events", ["provider"], unique=False)
    op.create_index(op.f("ix_webhook_events_provider_event_id"), "webhook_events", ["provider_event_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_webhook_events_provider_event_id"), table_name="webhook_events")
    op.drop_index(op.f("ix_webhook_events_provider"), table_name="webhook_events")
    op.drop_index(op.f("ix_webhook_events_event_type"), table_name="webhook_events")
    op.drop_table("webhook_events")
