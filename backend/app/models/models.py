import enum
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy import (
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TypeDecorator,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship

from app.db.session import Base

# ID strategy (canonical): String(36) storing ``str(uuid.uuid4())``.
# Migration ``010_uuid_columns_to_varchar36`` converts legacy Postgres UUID
# columns from ``001_initial`` to VARCHAR(36) so FKs match models.


def utcnow():
    return datetime.now(timezone.utc)


class FloatArrayCompat(TypeDecorator):
    """Postgres ARRAY(Float); SQLite stores JSON text for unit-test create_all."""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(Float()))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return list(value) if not isinstance(value, str) else json.loads(value)
        if isinstance(value, str):
            return value
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return list(value)
        if isinstance(value, str):
            return json.loads(value)
        return list(value)


class UserRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    engineer = "engineer"
    analyst = "analyst"
    developer = "developer"
    viewer = "viewer"


class SubscriptionPlan(str, enum.Enum):
    """Billing tiers. DB enum name: ``subscriptionplan``.

    Legacy migration ``001_initial`` used ``saas``; revision
    ``009_fix_subscription_plan_enum`` maps ``saas`` → ``pro``.
    """

    free = "free"
    starter = "starter"
    pro = "pro"
    enterprise = "enterprise"


class SubscriptionStatus(str, enum.Enum):
    active = "active"
    cancelled = "cancelled"
    past_due = "past_due"
    trialing = "trialing"


class FailureType(str, enum.Enum):
    retrieval_miss = "retrieval_miss"
    retrieval_irrelevant = "retrieval_irrelevant"
    hallucination = "hallucination"
    coverage_gap = "coverage_gap"
    chunking_issue = "chunking_issue"
    none = "none"


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.owner, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    subscription_plan = Column(
        SAEnum(
            SubscriptionPlan,
            name="subscriptionplan",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=SubscriptionPlan.free,
        nullable=False,
    )
    subscription_status = Column(SAEnum(SubscriptionStatus), nullable=True)
    razorpay_customer_id = Column(String(255), nullable=True)
    razorpay_subscription_id = Column(String(255), nullable=True)
    subscription_current_period_end = Column(DateTime(timezone=True), nullable=True)
    traces_this_month = Column(Integer, default=0, nullable=False)
    traces_reset_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    onboarding_completed = Column(Boolean, default=False, nullable=False)
    slack_webhook_url = Column(String(512), nullable=True)  # NEW: PRD v2.0 Slack alerts
    slack_alert_enabled = Column(Boolean, default=False, nullable=False)  # NEW
    email_verified = Column(Boolean, default=False, nullable=False)  # NEW: Email verification
    email_verification_token = Column(String(255), nullable=True)  # NEW
    email_verification_sent_at = Column(DateTime(timezone=True), nullable=True)  # NEW
    password_reset_token = Column(String(255), nullable=True)  # NEW
    password_reset_sent_at = Column(DateTime(timezone=True), nullable=True)  # NEW
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    organization = relationship(
        "Organization", back_populates="users", foreign_keys=[organization_id]
    )
    organization_memberships = relationship(
        "OrganizationMember",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="OrganizationMember.user_id",
    )
    pipelines = relationship("Pipeline", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    alert_rules = relationship("AlertRule", back_populates="user", cascade="all, delete-orphan")
    settings = relationship(
        "UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    fix_recommendations = relationship(
        "FixRecommendation", back_populates="user", cascade="all, delete-orphan"
    )  # NEW


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship("User", back_populates="refresh_tokens")


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    allowed_domains = Column(Text, nullable=True)
    sso_required = Column(Boolean, default=False, nullable=False)
    mfa_required = Column(Boolean, default=False, nullable=False)
    saml_metadata_xml = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    users = relationship("User", back_populates="organization", foreign_keys="User.organization_id")
    members = relationship(
        "OrganizationMember", back_populates="organization", cascade="all, delete-orphan"
    )


class OrganizationMember(Base):
    __tablename__ = "organization_members"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    role = Column(SAEnum(UserRole), default=UserRole.owner, nullable=False)
    invited_email = Column(String(255), nullable=True, index=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    organization = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="organization_memberships", foreign_keys=[user_id])


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    key_prefix = Column(String(20), nullable=False)
    name = Column(String(255), nullable=False)
    scopes = Column(Text, nullable=True)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship("User", back_populates="api_keys")


class Pipeline(Base):
    __tablename__ = "pipelines"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    queries_per_month = Column(Integer, default=10000, nullable=False)
    cost_per_wrong_answer_usd = Column(Float, default=5.0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="pipelines")
    query_traces = relationship(
        "QueryTrace", back_populates="pipeline", cascade="all, delete-orphan"
    )
    chunk_stats = relationship("ChunkStat", back_populates="pipeline", cascade="all, delete-orphan")
    knowledge_gaps = relationship(
        "KnowledgeGap", back_populates="pipeline", cascade="all, delete-orphan"
    )
    documents = relationship("Document", back_populates="pipeline", cascade="all, delete-orphan")
    monitoring_config = relationship(
        "MonitoringConfig",
        back_populates="pipeline",
        uselist=False,
        cascade="all, delete-orphan",
    )
    monitoring_runs = relationship(
        "MonitoringRun",
        back_populates="pipeline",
        cascade="all, delete-orphan",
    )
    regression_snapshots = relationship(
        "RegressionSnapshot",
        back_populates="pipeline",
        cascade="all, delete-orphan",
    )


class QueryTrace(Base):
    __tablename__ = "query_traces"
    __table_args__ = (
        # Default queries list: WHERE pipeline_id IN (…) ORDER BY traced_at DESC
        Index("ix_query_traces_pipeline_id_traced_at", "pipeline_id", "traced_at"),
        # Failure-type filter on queries list
        Index("ix_query_traces_pipeline_id_failure_type", "pipeline_id", "failure_type"),
        # Hallucination filter on queries list
        Index("ix_query_traces_pipeline_id_is_hallucination", "pipeline_id", "is_hallucination"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_id = Column(
        String(36), ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    query_text = Column(Text, nullable=False)
    query_embedding = Column(FloatArrayCompat, nullable=True)
    answer_text = Column(Text, nullable=True)
    raw_context = Column(Text, nullable=True)
    faithfulness_score = Column(Float, nullable=True)
    answer_relevance_score = Column(Float, nullable=True)
    context_precision_score = Column(Float, nullable=True)
    context_recall_score = Column(Float, nullable=True)
    grounded_fraction = Column(Float, nullable=True)
    trustworthiness_score = Column(Float, nullable=True)  # NEW: PRD v2.0
    is_hallucination = Column(Boolean, nullable=True)
    failure_type = Column(SAEnum(FailureType), default=FailureType.none, nullable=True)
    failure_explanation = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    embed_latency_ms = Column(Float, nullable=True)
    retrieve_latency_ms = Column(Float, nullable=True)
    generate_latency_ms = Column(Float, nullable=True)
    rank_latency_ms = Column(Float, nullable=True)
    session_id = Column(String(64), nullable=True, index=True)
    request_id = Column(String(64), nullable=True)
    client_metadata_json = Column(Text, nullable=True)  # tags, custom metadata, model info from SDK
    analysis_latencies_json = Column(Text, nullable=True)  # worker stage timings JSON
    analysis_status = Column(String(20), default="pending", nullable=False)
    traced_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    pipeline = relationship("Pipeline", back_populates="query_traces")
    retrieved_chunks = relationship(
        "RetrievedChunk", back_populates="trace", cascade="all, delete-orphan"
    )
    grounding_results = relationship(
        "GroundingResult", back_populates="trace", cascade="all, delete-orphan"
    )
    analysis_job = relationship(
        "AnalysisJob", back_populates="trace", uselist=False, cascade="all, delete-orphan"
    )


class RetrievedChunk(Base):
    __tablename__ = "retrieved_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trace_id = Column(
        String(36), ForeignKey("query_traces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_id = Column(String(255), nullable=False, index=True)
    chunk_text = Column(Text, nullable=False)
    similarity_score = Column(Float, nullable=True)
    bm25_score = Column(Float, nullable=True)
    rank = Column(Integer, nullable=True)
    was_cited = Column(Boolean, default=False, nullable=False)
    metadata_json = Column(Text, nullable=True)  # JSON stored as text for SQLite compat

    trace = relationship("QueryTrace", back_populates="retrieved_chunks")


class GroundingResult(Base):
    __tablename__ = "grounding_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trace_id = Column(
        String(36), ForeignKey("query_traces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sentence_text = Column(Text, nullable=False)
    sentence_index = Column(Integer, nullable=False)
    is_grounded = Column(Boolean, nullable=False)
    supporting_chunk_id = Column(String(255), nullable=True)
    confidence_score = Column(Float, nullable=True)

    trace = relationship("QueryTrace", back_populates="grounding_results")


class ChunkStat(Base):
    __tablename__ = "chunk_stats"
    __table_args__ = (
        # Flagged-only chunks list + summary counts
        Index("ix_chunk_stats_pipeline_id_is_flagged", "pipeline_id", "is_flagged"),
        # Default chunks list: WHERE pipeline_id … ORDER BY retrieval_count DESC
        Index("ix_chunk_stats_pipeline_id_retrieval_count", "pipeline_id", "retrieval_count"),
        # Flag/unflag and per-chunk lookups (pipeline_id + chunk_id)
        Index("ix_chunk_stats_pipeline_id_chunk_id", "pipeline_id", "chunk_id"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chunk_id = Column(String(255), nullable=False, index=True)
    pipeline_id = Column(
        String(36), ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text = Column(Text, nullable=False)
    retrieval_count = Column(Integer, default=0, nullable=False)
    citation_count = Column(Integer, default=0, nullable=False)
    citation_rate = Column(Float, default=0.0, nullable=False)
    is_flagged = Column(Boolean, default=False, nullable=False)
    last_retrieved_at = Column(DateTime(timezone=True), nullable=True)

    pipeline = relationship("Pipeline", back_populates="chunk_stats")


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trace_id = Column(
        String(36), ForeignKey("query_traces.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    status = Column(SAEnum(JobStatus), default=JobStatus.pending, nullable=False)
    celery_task_id = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    trace = relationship("QueryTrace", back_populates="analysis_job")


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    pipeline_id = Column(String(36), ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=True)
    metric = Column(String(50), nullable=False)
    threshold = Column(Float, nullable=False)
    direction = Column(String(10), nullable=False)  # "below" or "above"
    notify_email = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship("User", back_populates="alert_rules")


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    ollama_url = Column(String(255), default="http://localhost:11434", nullable=False)
    ollama_model = Column(String(100), default="llama3.2:3b", nullable=False)
    grounding_threshold = Column(Float, default=0.5, nullable=False)
    faithfulness_alert_threshold = Column(Float, default=0.7, nullable=False)
    enable_email_alerts = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="settings")


class FixRecommendation(Base):  # NEW: PRD v2.0 / Phase 10.2 actions
    __tablename__ = "fix_recommendations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pipeline_id = Column(
        String(36), ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=True, index=True
    )
    recommendation_type = Column(
        String(50), nullable=False
    )  # coverage_gap / chunking / hybrid_search / re_embed
    topic_description = Column(Text, nullable=False)
    affected_query_count = Column(Integer, default=0, nullable=False)
    sample_queries = Column(Text, nullable=True)  # JSON array as text
    generated_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    # Phase 10.2 — apply / dismiss / trust verify
    status = Column(String(50), default="open", nullable=False, index=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)
    dismissed_at = Column(DateTime(timezone=True), nullable=True)
    trust_score_before = Column(Float, nullable=True)
    trust_score_after = Column(Float, nullable=True)

    user = relationship("User", back_populates="fix_recommendations")
    pipeline = relationship("Pipeline")


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider = Column(String(50), nullable=False, index=True)
    provider_event_id = Column(String(255), unique=True, nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    processed_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action = Column(String(100), nullable=False, index=True)
    target_type = Column(String(100), nullable=True)
    target_id = Column(String(255), nullable=True)
    metadata_json = Column(Text, nullable=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class IntegrationWebhook(Base):
    __tablename__ = "integration_webhooks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    provider = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    webhook_url = Column(String(1024), nullable=False)
    signing_secret_hash = Column(String(255), nullable=True)
    events = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class SSOConnection(Base):
    __tablename__ = "sso_connections"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider = Column(String(50), nullable=False, index=True)
    issuer_url = Column(String(512), nullable=True)
    client_id = Column(String(255), nullable=True)
    client_secret_ref = Column(String(255), nullable=True)
    enabled = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class MFAFactor(Base):
    __tablename__ = "mfa_factors"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    factor_type = Column(String(50), nullable=False)
    secret_ref = Column(String(255), nullable=True)
    enabled = Column(Boolean, default=False, nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class MFARecoveryCode(Base):
    __tablename__ = "mfa_recovery_codes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code_hash = Column(String(255), nullable=False, index=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class RememberedDevice(Base):
    __tablename__ = "remembered_devices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_hash = Column(String(255), nullable=False, index=True)
    user_agent = Column(String(512), nullable=True)
    ip_address = Column(String(64), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class IPAllowlistEntry(Base):
    __tablename__ = "ip_allowlist_entries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cidr = Column(String(64), nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class WeeklyExecutiveReport(Base):
    __tablename__ = "weekly_executive_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    recipient_email = Column(String(255), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class SLAThreshold(Base):
    __tablename__ = "sla_thresholds"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    pipeline_id = Column(
        String(36), ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=True, index=True
    )
    trust_score_min = Column(Float, default=85.0, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    webhook_id = Column(
        String(36),
        ForeignKey("integration_webhooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type = Column(String(100), nullable=False, index=True)
    payload_json = Column(Text, nullable=False)
    status = Column(String(30), default="pending", nullable=False, index=True)
    attempts = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class ReportHistory(Base):
    __tablename__ = "report_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    report_type = Column(String(100), nullable=False)
    format = Column(String(20), nullable=False)
    payload_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class InvoiceRecord(Base):
    __tablename__ = "invoice_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    provider_invoice_id = Column(String(255), nullable=True, index=True)
    amount = Column(Float, nullable=False, default=0)
    currency = Column(String(10), nullable=False, default="INR")
    tax_amount = Column(Float, nullable=False, default=0)
    status = Column(String(50), nullable=False, default="draft")
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class KnowledgeGap(Base):
    """Clustered coverage gaps (PRD v3 / Phase 10.1)."""

    __tablename__ = "knowledge_gaps"
    __table_args__ = (Index("idx_gaps_pipeline", "pipeline_id", "status", "priority"),)

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_id = Column(
        String(36), ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_label = Column(String(500), nullable=False)
    representative_query = Column(Text, nullable=True)
    query_count = Column(Integer, default=1, nullable=False)
    failure_rate = Column(Float, nullable=True)
    affected_users_estimate = Column(Integer, default=0, nullable=False)
    estimated_monthly_cost_usd = Column(Float, nullable=True)
    priority = Column(String(50), default="medium", nullable=False)
    suggested_document_topic = Column(Text, nullable=True)
    auto_fix_draft = Column(Text, nullable=True)
    fix_format = Column(String(50), default="markdown", nullable=False)
    status = Column(String(50), default="open", nullable=False)
    fixed_at = Column(DateTime(timezone=True), nullable=True)
    trust_improvement_after_fix = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    pipeline = relationship("Pipeline", back_populates="knowledge_gaps")


class Document(Base):
    """Tracked knowledge-base documents + freshness (Phase 10.3)."""

    __tablename__ = "documents"
    __table_args__ = (
        Index("idx_documents_pipeline", "pipeline_id"),
        Index("idx_documents_freshness", "pipeline_id", "freshness_status"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_id = Column(
        String(36), ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = Column(String(500), nullable=False)
    source_url = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=True)
    document_type = Column(String(100), nullable=True)
    last_modified_at = Column(DateTime(timezone=True), nullable=True)
    ingested_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    days_since_modified = Column(Integer, nullable=True)
    freshness_status = Column(String(50), default="fresh", nullable=False)
    freshness_alert_sent = Column(Boolean, default=False, nullable=False)
    topic_labels = Column(Text, nullable=True)  # JSON array as text
    coverage_score = Column(Float, nullable=True)
    chunk_count = Column(Integer, default=0, nullable=False)
    stale_chunk_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    pipeline = relationship("Pipeline", back_populates="documents")


class MonitoringConfig(Base):
    """Continuous monitoring schedule per pipeline (Phase 10.4)."""

    __tablename__ = "monitoring_configs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_id = Column(
        String(36),
        ForeignKey("pipelines.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    is_enabled = Column(Boolean, default=False, nullable=False)
    interval_minutes = Column(Integer, default=60, nullable=False)
    probe_queries = Column(Text, nullable=False, default="[]")  # JSON list
    alert_trust_threshold = Column(Float, default=70.0, nullable=False)
    alert_hallucination_threshold = Column(Float, default=0.10, nullable=False)
    alert_channels = Column(Text, nullable=False, default="[]")  # JSON list
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    pipeline = relationship("Pipeline", back_populates="monitoring_config")
    runs = relationship("MonitoringRun", back_populates="config", cascade="all, delete-orphan")


class MonitoringRun(Base):
    """One monitoring probe evaluation (Phase 10.4)."""

    __tablename__ = "monitoring_runs"
    __table_args__ = (Index("idx_monitoring_runs_pipeline", "pipeline_id", "run_at"),)

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_id = Column(
        String(36), ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    config_id = Column(
        String(36),
        ForeignKey("monitoring_configs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    trust_score = Column(Float, nullable=True)
    hallucination_rate = Column(Float, nullable=True)
    probes_run = Column(Integer, default=0, nullable=False)
    probes_failed = Column(Integer, default=0, nullable=False)
    alerts_triggered = Column(Text, nullable=True)  # JSON
    regression_detected = Column(Boolean, default=False, nullable=False)
    run_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    pipeline = relationship("Pipeline", back_populates="monitoring_runs")
    config = relationship("MonitoringConfig", back_populates="runs")


class RegressionSnapshot(Base):
    """Point-in-time quality metrics for pre-deploy checks (Phase 10.5)."""

    __tablename__ = "regression_snapshots"
    __table_args__ = (Index("idx_snapshots_pipeline", "pipeline_id", "snapshot_at"),)

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_id = Column(
        String(36), ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    snapshot_label = Column(String(255), nullable=True)
    trust_score = Column(Float, nullable=False)
    faithfulness_avg = Column(Float, nullable=True)
    context_precision_avg = Column(Float, nullable=True)
    hallucination_rate = Column(Float, nullable=True)
    trace_count = Column(Integer, default=0, nullable=False)
    snapshot_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    pipeline = relationship("Pipeline", back_populates="regression_snapshots")
