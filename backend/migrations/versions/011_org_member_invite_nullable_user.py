"""Allow pending org invites without a resolved user_id.

Revision ID: 011_org_member_invite_nullable_user
Revises: 010_uuid_columns_to_varchar36
Create Date: 2026-07-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "011_org_member_invite_nullable_user"
down_revision: Union[str, None] = "010_uuid_columns_to_varchar36"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("organization_members") as batch:
            batch.alter_column("user_id", existing_type=sa.String(36), nullable=True)
        return

    op.alter_column(
        "organization_members",
        "user_id",
        existing_type=sa.String(length=36),
        nullable=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    # Pending invites (NULL user_id) cannot survive a NOT NULL downgrade.
    op.execute(
        sa.text("DELETE FROM organization_members WHERE user_id IS NULL")
    )
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("organization_members") as batch:
            batch.alter_column("user_id", existing_type=sa.String(36), nullable=False)
        return

    op.alter_column(
        "organization_members",
        "user_id",
        existing_type=sa.String(length=36),
        nullable=False,
    )
