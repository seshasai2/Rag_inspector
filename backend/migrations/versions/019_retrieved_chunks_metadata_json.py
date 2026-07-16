"""Rename retrieved_chunks.metadata → metadata_json for model alignment.

Revision ID: 019_retrieved_chunks_metadata_json
Revises: 018_regression_snapshots
Create Date: 2026-07-14

Fresh installs already get ``metadata_json`` from updated ``001_initial``.
This revision upgrades databases that already applied the JSONB ``metadata`` column.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "019_retrieved_chunks_metadata_json"
down_revision: Union[str, None] = "018_regression_snapshots"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("retrieved_chunks")}
    if "metadata_json" in cols:
        return
    if "metadata" in cols:
        if bind.dialect.name == "postgresql":
            op.execute(
                sa.text(
                    "ALTER TABLE retrieved_chunks "
                    "RENAME COLUMN metadata TO metadata_json"
                )
            )
            op.execute(
                sa.text(
                    "ALTER TABLE retrieved_chunks "
                    "ALTER COLUMN metadata_json TYPE TEXT "
                    "USING metadata_json::text"
                )
            )
        else:
            with op.batch_alter_table("retrieved_chunks") as batch:
                batch.alter_column("metadata", new_column_name="metadata_json")
    else:
        op.add_column(
            "retrieved_chunks",
            sa.Column("metadata_json", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("retrieved_chunks")}
    if "metadata_json" not in cols:
        return
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                "ALTER TABLE retrieved_chunks "
                "ALTER COLUMN metadata_json TYPE JSONB "
                "USING CASE WHEN metadata_json IS NULL THEN NULL "
                "ELSE metadata_json::jsonb END"
            )
        )
        op.execute(
            sa.text(
                "ALTER TABLE retrieved_chunks "
                "RENAME COLUMN metadata_json TO metadata"
            )
        )
    else:
        with op.batch_alter_table("retrieved_chunks") as batch:
            batch.alter_column("metadata_json", new_column_name="metadata")
