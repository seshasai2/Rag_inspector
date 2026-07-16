"""Add email verification and password reset columns

Revision ID: 003_email_verification
Revises: 002_v2_new_fields
Create Date: 2026-05-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = '003_email_verification'
down_revision: Union[str, None] = '002_v2_new_fields'
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false')
    )
    op.add_column(
        'users',
        sa.Column('email_verification_token', sa.String(255), nullable=True)
    )
    op.add_column(
        'users',
        sa.Column('email_verification_sent_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        'users',
        sa.Column('password_reset_token', sa.String(255), nullable=True)
    )
    op.add_column(
        'users',
        sa.Column('password_reset_sent_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'email_verification_token')
    op.drop_column('users', 'email_verification_sent_at')
    op.drop_column('users', 'password_reset_token')
    op.drop_column('users', 'password_reset_sent_at')