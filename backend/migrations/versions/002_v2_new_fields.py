"""v2.0: Add trustworthiness_score, fix_recommendations, slack fields

Revision ID: 002_v2_new_fields
Revises: 001_initial
Create Date: 2026-05-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = '002_v2_new_fields'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Add trustworthiness_score to query_traces
    op.add_column(
        'query_traces',
        sa.Column('trustworthiness_score', sa.Float(), nullable=True)
    )

    # Add Slack fields to users
    op.add_column(
        'users',
        sa.Column('slack_webhook_url', sa.String(512), nullable=True)
    )
    op.add_column(
        'users',
        sa.Column('slack_alert_enabled', sa.Boolean(), nullable=False, server_default='false')
    )

    # IDs are VARCHAR(36) from 001_initial (aligned with SQLAlchemy models).
    op.create_table(
        'fix_recommendations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36),
                  sa.ForeignKey('users.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('pipeline_id', sa.String(36),
                  sa.ForeignKey('pipelines.id', ondelete='CASCADE'),
                  nullable=True, index=True),
        sa.Column('recommendation_type', sa.String(50), nullable=False),
        sa.Column('topic_description', sa.Text(), nullable=False),
        sa.Column('affected_query_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sample_queries', sa.Text(), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column('query_traces', 'trustworthiness_score')
    op.drop_column('users', 'slack_webhook_url')
    op.drop_column('users', 'slack_alert_enabled')
    op.drop_table('fix_recommendations')
