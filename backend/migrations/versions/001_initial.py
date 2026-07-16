"""Initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")

    op.create_table('users',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('role', sa.Enum('owner', 'developer', 'viewer', name='userrole'), nullable=False, server_default='owner'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('subscription_plan', sa.Enum('free', 'saas', 'enterprise', name='subscriptionplan'), nullable=False, server_default='free'),
        sa.Column('subscription_status', sa.Enum('active', 'cancelled', 'past_due', 'trialing', name='subscriptionstatus'), nullable=True),
        sa.Column('razorpay_customer_id', sa.String(255), nullable=True),
        sa.Column('razorpay_subscription_id', sa.String(255), nullable=True),
        sa.Column('subscription_current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('traces_this_month', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('traces_reset_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('onboarding_completed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    op.create_table('refresh_tokens',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('token_hash', sa.String(255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_refresh_tokens_token_hash', 'refresh_tokens', ['token_hash'], unique=True)

    op.create_table('api_keys',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('key_hash', sa.String(255), nullable=False),
        sa.Column('key_prefix', sa.String(20), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_api_keys_key_hash', 'api_keys', ['key_hash'], unique=True)

    op.create_table('pipelines',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('query_traces',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('pipeline_id', sa.String(36), nullable=False),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('query_embedding', postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column('answer_text', sa.Text(), nullable=True),
        sa.Column('raw_context', sa.Text(), nullable=True),
        sa.Column('faithfulness_score', sa.Float(), nullable=True),
        sa.Column('answer_relevance_score', sa.Float(), nullable=True),
        sa.Column('context_precision_score', sa.Float(), nullable=True),
        sa.Column('context_recall_score', sa.Float(), nullable=True),
        sa.Column('grounded_fraction', sa.Float(), nullable=True),
        sa.Column('is_hallucination', sa.Boolean(), nullable=True),
        sa.Column('failure_type', sa.Enum('retrieval_miss','retrieval_irrelevant','hallucination','coverage_gap','chunking_issue','none', name='failuretype'), nullable=True),
        sa.Column('failure_explanation', sa.Text(), nullable=True),
        sa.Column('recommendation', sa.Text(), nullable=True),
        sa.Column('embed_latency_ms', sa.Float(), nullable=True),
        sa.Column('retrieve_latency_ms', sa.Float(), nullable=True),
        sa.Column('generate_latency_ms', sa.Float(), nullable=True),
        sa.Column('analysis_status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('traced_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['pipeline_id'], ['pipelines.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_query_traces_pipeline_id', 'query_traces', ['pipeline_id'])
    op.create_index('ix_query_traces_traced_at', 'query_traces', ['traced_at'])

    op.create_table('retrieved_chunks',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('trace_id', sa.String(36), nullable=False),
        sa.Column('chunk_id', sa.String(255), nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('similarity_score', sa.Float(), nullable=True),
        sa.Column('bm25_score', sa.Float(), nullable=True),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.Column('was_cited', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['trace_id'], ['query_traces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_retrieved_chunks_trace_id', 'retrieved_chunks', ['trace_id'])
    op.create_index('ix_retrieved_chunks_chunk_id', 'retrieved_chunks', ['chunk_id'])

    op.create_table('grounding_results',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('trace_id', sa.String(36), nullable=False),
        sa.Column('sentence_text', sa.Text(), nullable=False),
        sa.Column('sentence_index', sa.Integer(), nullable=False),
        sa.Column('is_grounded', sa.Boolean(), nullable=False),
        sa.Column('supporting_chunk_id', sa.String(255), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['trace_id'], ['query_traces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_grounding_results_trace_id', 'grounding_results', ['trace_id'])

    op.create_table('chunk_stats',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('chunk_id', sa.String(255), nullable=False),
        sa.Column('pipeline_id', sa.String(36), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('retrieval_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('citation_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('citation_rate', sa.Float(), nullable=False, server_default='0'),
        sa.Column('is_flagged', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_retrieved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['pipeline_id'], ['pipelines.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_chunk_stats_chunk_id', 'chunk_stats', ['chunk_id'])
    op.create_index('ix_chunk_stats_pipeline_id', 'chunk_stats', ['pipeline_id'])

    op.create_table('analysis_jobs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('trace_id', sa.String(36), nullable=False),
        sa.Column('status', sa.Enum('pending','running','completed','failed', name='jobstatus'), nullable=False, server_default='pending'),
        sa.Column('celery_task_id', sa.String(255), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['trace_id'], ['query_traces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trace_id'),
    )

    op.create_table('alert_rules',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('pipeline_id', sa.String(36), nullable=True),
        sa.Column('metric', sa.String(50), nullable=False),
        sa.Column('threshold', sa.Float(), nullable=False),
        sa.Column('direction', sa.String(10), nullable=False),
        sa.Column('notify_email', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pipeline_id'], ['pipelines.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('user_settings',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('ollama_url', sa.String(255), nullable=False, server_default='http://localhost:11434'),
        sa.Column('ollama_model', sa.String(100), nullable=False, server_default='llama3.2:3b'),
        sa.Column('grounding_threshold', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('faithfulness_alert_threshold', sa.Float(), nullable=False, server_default='0.7'),
        sa.Column('enable_email_alerts', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )


def downgrade() -> None:
    op.drop_table('user_settings')
    op.drop_table('alert_rules')
    op.drop_table('analysis_jobs')
    op.drop_table('chunk_stats')
    op.drop_table('grounding_results')
    op.drop_table('retrieved_chunks')
    op.drop_table('query_traces')
    op.drop_table('pipelines')
    op.drop_table('api_keys')
    op.drop_table('refresh_tokens')
    op.drop_table('users')
