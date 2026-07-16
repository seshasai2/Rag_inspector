"""Add pipeline Hallucination Cost settings.

Revision ID: 012_pipeline_hallucination_cost
Revises: 011_org_member_invite_nullable_user
Create Date: 2026-07-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "012_pipeline_hallucination_cost"
down_revision: Union[str, None] = "011_org_member_invite_nullable_user"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("pipelines") as batch:
            batch.add_column(
                sa.Column(
                    "queries_per_month",
                    sa.Integer(),
                    nullable=False,
                    server_default="10000",
                )
            )
            batch.add_column(
                sa.Column(
                    "cost_per_wrong_answer_usd",
                    sa.Float(),
                    nullable=False,
                    server_default="5.0",
                )
            )
        return

    op.add_column(
        "pipelines",
        sa.Column(
            "queries_per_month",
            sa.Integer(),
            nullable=False,
            server_default="10000",
        ),
    )
    op.add_column(
        "pipelines",
        sa.Column(
            "cost_per_wrong_answer_usd",
            sa.Float(),
            nullable=False,
            server_default="5.0",
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("pipelines") as batch:
            batch.drop_column("cost_per_wrong_answer_usd")
            batch.drop_column("queries_per_month")
        return

    op.drop_column("pipelines", "cost_per_wrong_answer_usd")
    op.drop_column("pipelines", "queries_per_month")
