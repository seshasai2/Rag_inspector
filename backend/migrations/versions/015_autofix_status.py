"""Add apply/dismiss/trust fields to fix_recommendations (Phase 10.2).

Revision ID: 015_autofix_status
Revises: 014_knowledge_gaps
Create Date: 2026-07-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "015_autofix_status"
down_revision: Union[str, None] = "014_knowledge_gaps"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "fix_recommendations",
        sa.Column("status", sa.String(length=50), nullable=False, server_default="open"),
    )
    op.add_column("fix_recommendations", sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("fix_recommendations", sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("fix_recommendations", sa.Column("trust_score_before", sa.Float(), nullable=True))
    op.add_column("fix_recommendations", sa.Column("trust_score_after", sa.Float(), nullable=True))
    op.create_index("ix_fix_recommendations_status", "fix_recommendations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_fix_recommendations_status", table_name="fix_recommendations")
    op.drop_column("fix_recommendations", "trust_score_after")
    op.drop_column("fix_recommendations", "trust_score_before")
    op.drop_column("fix_recommendations", "dismissed_at")
    op.drop_column("fix_recommendations", "applied_at")
    op.drop_column("fix_recommendations", "status")
