"""Convert legacy Postgres UUID PK/FK columns to VARCHAR(36).

Revision ID: 010_uuid_columns_to_varchar36
Revises: 009_fix_subscription_plan_enum
Create Date: 2026-07-13

Aligns the database with SQLAlchemy models, which store IDs as
``String(36)`` generated via ``str(uuid.uuid4())``.

SQLite path is a no-op (dev/test already use String via create_all).
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "010_uuid_columns_to_varchar36"
down_revision: Union[str, None] = "009_fix_subscription_plan_enum"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Preferred alteration order: leaf FK columns, then mid-level, then PKs.
_PREFERRED_ORDER = (
    # Leaf FKs → query_traces
    ("retrieved_chunks", "trace_id"),
    ("grounding_results", "trace_id"),
    ("analysis_jobs", "trace_id"),
    # Mid FKs → pipelines
    ("query_traces", "pipeline_id"),
    ("chunk_stats", "pipeline_id"),
    ("alert_rules", "pipeline_id"),
    ("fix_recommendations", "pipeline_id"),
    ("sla_thresholds", "pipeline_id"),
    # User FKs
    ("refresh_tokens", "user_id"),
    ("api_keys", "user_id"),
    ("pipelines", "user_id"),
    ("alert_rules", "user_id"),
    ("user_settings", "user_id"),
    ("fix_recommendations", "user_id"),
    ("organization_members", "user_id"),
    ("audit_logs", "user_id"),
    ("integration_webhooks", "user_id"),
    ("mfa_factors", "user_id"),
    ("mfa_recovery_codes", "user_id"),
    ("remembered_devices", "user_id"),
    ("weekly_executive_reports", "user_id"),
    ("sla_thresholds", "user_id"),
    ("report_history", "user_id"),
    ("invoice_records", "user_id"),
    # Leaf / mid PKs before parents
    ("retrieved_chunks", "id"),
    ("grounding_results", "id"),
    ("analysis_jobs", "id"),
    ("chunk_stats", "id"),
    ("alert_rules", "id"),
    ("query_traces", "id"),
    ("pipelines", "id"),
    ("api_keys", "id"),
    ("refresh_tokens", "id"),
    ("user_settings", "id"),
    ("users", "id"),
)


def _delete_rule_to_ondelete(rule: str) -> str | None:
    mapping = {
        "CASCADE": "CASCADE",
        "SET NULL": "SET NULL",
        "SET DEFAULT": "SET DEFAULT",
        "RESTRICT": "RESTRICT",
        "NO ACTION": None,
    }
    return mapping.get(rule.upper())


def _list_uuid_columns(conn) -> list[tuple[str, str]]:
    rows = conn.execute(
        sa.text(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND udt_name = 'uuid'
            ORDER BY table_name, column_name
            """
        )
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


def _list_foreign_keys(conn) -> list[dict]:
    """Return one dict per FK constraint (supports multi-column FKs)."""
    rows = conn.execute(
        sa.text(
            """
            SELECT
                tc.constraint_name,
                tc.table_name AS source_table,
                kcu.column_name AS source_column,
                kcu.ordinal_position,
                ccu.table_name AS target_table,
                ccu.column_name AS target_column,
                rc.delete_rule
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
             AND ccu.table_schema = tc.table_schema
            JOIN information_schema.referential_constraints AS rc
              ON rc.constraint_name = tc.constraint_name
             AND rc.constraint_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'public'
            ORDER BY tc.constraint_name, kcu.ordinal_position
            """
        )
    ).fetchall()

    grouped: dict[str, dict] = {}
    for row in rows:
        name = row.constraint_name
        if name not in grouped:
            grouped[name] = {
                "name": name,
                "source_table": row.source_table,
                "target_table": row.target_table,
                "source_columns": [],
                "target_columns": [],
                "delete_rule": row.delete_rule,
            }
        grouped[name]["source_columns"].append(row.source_column)
        grouped[name]["target_columns"].append(row.target_column)
    return list(grouped.values())


def _ordered_uuid_columns(columns: list[tuple[str, str]]) -> list[tuple[str, str]]:
    remaining = set(columns)
    ordered: list[tuple[str, str]] = []
    for item in _PREFERRED_ORDER:
        if item in remaining:
            ordered.append(item)
            remaining.remove(item)
    # Any unexpected uuid columns (stable alphabetical)
    ordered.extend(sorted(remaining))
    return ordered


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # Descriptive revision IDs (e.g. 011_org_member_invite_nullable_user)
    # exceed Alembic's default VARCHAR(32) for version_num.
    op.execute(
        sa.text(
            "ALTER TABLE alembic_version "
            "ALTER COLUMN version_num TYPE VARCHAR(128)"
        )
    )

    uuid_columns = _list_uuid_columns(bind)
    if not uuid_columns:
        return

    fks = _list_foreign_keys(bind)

    # Drop every FK so UUID → VARCHAR casts cannot violate type matching.
    for fk in fks:
        op.drop_constraint(fk["name"], fk["source_table"], type_="foreignkey")

    for table_name, column_name in _ordered_uuid_columns(uuid_columns):
        op.execute(
            sa.text(
                f'ALTER TABLE "{table_name}" '
                f'ALTER COLUMN "{column_name}" TYPE varchar(36) '
                f'USING "{column_name}"::text'
            )
        )

    # App generates IDs; remove Postgres UUID default if present.
    op.execute(sa.text("ALTER TABLE users ALTER COLUMN id DROP DEFAULT"))

    for fk in fks:
        kwargs = {}
        ondelete = _delete_rule_to_ondelete(fk["delete_rule"])
        if ondelete:
            kwargs["ondelete"] = ondelete
        op.create_foreign_key(
            fk["name"],
            fk["source_table"],
            fk["target_table"],
            fk["source_columns"],
            fk["target_columns"],
            **kwargs,
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # Convert varchar(36) ID columns that look like UUIDs back to uuid.
    # Only touch columns that were originally UUID in 001_initial.
    legacy_uuid_columns = [
        ("users", "id"),
        ("refresh_tokens", "id"),
        ("refresh_tokens", "user_id"),
        ("api_keys", "id"),
        ("api_keys", "user_id"),
        ("pipelines", "id"),
        ("pipelines", "user_id"),
        ("query_traces", "id"),
        ("query_traces", "pipeline_id"),
        ("retrieved_chunks", "id"),
        ("retrieved_chunks", "trace_id"),
        ("grounding_results", "id"),
        ("grounding_results", "trace_id"),
        ("chunk_stats", "id"),
        ("chunk_stats", "pipeline_id"),
        ("analysis_jobs", "id"),
        ("analysis_jobs", "trace_id"),
        ("alert_rules", "id"),
        ("alert_rules", "user_id"),
        ("alert_rules", "pipeline_id"),
        ("user_settings", "id"),
        ("user_settings", "user_id"),
    ]

    fks = _list_foreign_keys(bind)
    for fk in fks:
        op.drop_constraint(fk["name"], fk["source_table"], type_="foreignkey")

    # Reverse order for downgrade (parents before children for types? actually
    # all FKs dropped so any order works; reverse preferred for symmetry).
    for table_name, column_name in reversed(legacy_uuid_columns):
        op.execute(
            sa.text(
                f'ALTER TABLE "{table_name}" '
                f'ALTER COLUMN "{column_name}" TYPE uuid '
                f'USING "{column_name}"::uuid'
            )
        )

    op.execute(
        sa.text(
            "ALTER TABLE users ALTER COLUMN id SET DEFAULT gen_random_uuid()"
        )
    )

    for fk in fks:
        kwargs = {}
        ondelete = _delete_rule_to_ondelete(fk["delete_rule"])
        if ondelete:
            kwargs["ondelete"] = ondelete
        op.create_foreign_key(
            fk["name"],
            fk["source_table"],
            fk["target_table"],
            fk["source_columns"],
            fk["target_columns"],
            **kwargs,
        )
