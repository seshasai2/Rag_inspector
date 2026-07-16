"""Add organization enterprise controls

Revision ID: 008_org_enterprise_controls
Revises: 007_security_delivery_billing
Create Date: 2026-06-21
"""
from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = "008_org_enterprise_controls"
down_revision: Union[str, None] = "007_security_delivery_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("allowed_domains", sa.Text(), nullable=True))
    op.add_column("organizations", sa.Column("sso_required", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("organizations", sa.Column("mfa_required", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("organizations", sa.Column("saml_metadata_xml", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("organizations", "saml_metadata_xml")
    op.drop_column("organizations", "mfa_required")
    op.drop_column("organizations", "sso_required")
    op.drop_column("organizations", "allowed_domains")
