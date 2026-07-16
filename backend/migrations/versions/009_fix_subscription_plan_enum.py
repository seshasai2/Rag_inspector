"""Align subscription_plan enum with application models.

Revision ID: 009_fix_subscription_plan_enum
Revises: 008_org_enterprise_controls
Create Date: 2026-07-13

Maps legacy Postgres enum value ``saas`` → ``pro`` and replaces
``subscriptionplan`` with ``free | starter | pro | enterprise``.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "009_fix_subscription_plan_enum"
down_revision: Union[str, None] = "008_org_enterprise_controls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            "CREATE TYPE subscriptionplan_new AS ENUM "
            "('free', 'starter', 'pro', 'enterprise')"
        )
        # Server default still typed as old enum — must drop before TYPE change.
        op.execute("ALTER TABLE users ALTER COLUMN subscription_plan DROP DEFAULT")
        op.execute(
            """
            ALTER TABLE users
            ALTER COLUMN subscription_plan
            TYPE subscriptionplan_new
            USING (
                CASE subscription_plan::text
                    WHEN 'saas' THEN 'pro'::subscriptionplan_new
                    WHEN 'starter' THEN 'starter'::subscriptionplan_new
                    WHEN 'pro' THEN 'pro'::subscriptionplan_new
                    WHEN 'enterprise' THEN 'enterprise'::subscriptionplan_new
                    ELSE 'free'::subscriptionplan_new
                END
            )
            """
        )
        op.execute("DROP TYPE subscriptionplan")
        op.execute("ALTER TYPE subscriptionplan_new RENAME TO subscriptionplan")
        op.execute(
            "ALTER TABLE users ALTER COLUMN subscription_plan "
            "SET DEFAULT 'free'::subscriptionplan"
        )
        return

    # SQLite / other dialects store enums as plain strings.
    op.execute(
        sa.text(
            "UPDATE users SET subscription_plan = 'pro' "
            "WHERE subscription_plan = 'saas'"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            "CREATE TYPE subscriptionplan_old AS ENUM "
            "('free', 'saas', 'enterprise')"
        )
        op.execute(
            """
            ALTER TABLE users
            ALTER COLUMN subscription_plan
            TYPE subscriptionplan_old
            USING (
                CASE subscription_plan::text
                    WHEN 'starter' THEN 'free'::subscriptionplan_old
                    WHEN 'pro' THEN 'saas'::subscriptionplan_old
                    WHEN 'saas' THEN 'saas'::subscriptionplan_old
                    WHEN 'enterprise' THEN 'enterprise'::subscriptionplan_old
                    ELSE 'free'::subscriptionplan_old
                END
            )
            """
        )
        op.execute("DROP TYPE subscriptionplan")
        op.execute("ALTER TYPE subscriptionplan_old RENAME TO subscriptionplan")
        return

    op.execute(
        sa.text(
            "UPDATE users SET subscription_plan = 'saas' "
            "WHERE subscription_plan = 'pro'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE users SET subscription_plan = 'free' "
            "WHERE subscription_plan = 'starter'"
        )
    )
