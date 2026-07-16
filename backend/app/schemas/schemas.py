from datetime import datetime
from typing import Annotated, List, Optional
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, field_validator


def _validate_app_email(value: str) -> str:
    """Normalize emails; deliverability is not checked at registration time."""
    try:
        result = validate_email(value, check_deliverability=False)
    except EmailNotValidError as exc:
        raise ValueError(str(exc)) from exc
    return result.normalized


AppEmail = Annotated[str, AfterValidator(_validate_app_email)]


# ---- Auth ----


class ForgotPasswordRequest(BaseModel):
    email: AppEmail


class ResendVerificationRequest(BaseModel):
    email: AppEmail


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=100)


class VerifyEmailRequest(BaseModel):
    token: str


class UserRegister(BaseModel):
    email: AppEmail
    password: str = Field(min_length=8, max_length=100)
    name: str = Field(min_length=1, max_length=255)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    email: AppEmail
    password: str
    mfa_code: Optional[str] = None
    device_token: Optional[str] = None


class MFALoginComplete(BaseModel):
    mfa_token: str
    code: str
    remember_device: bool = False


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    """Password login may return tokens or an MFA challenge (no access token)."""

    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    mfa_required: bool = False
    mfa_token: Optional[str] = None
    device_token: Optional[str] = None


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    """Logout payload: revoke refresh (and optionally denylist the access jti)."""

    refresh_token: str
    access_token: Optional[str] = None
    revoke_all_sessions: bool = False


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: Optional[UUID] = None
    email: str
    name: str
    role: str
    subscription_plan: str
    subscription_status: Optional[str] = None
    subscription_current_period_end: Optional[datetime] = None
    traces_this_month: int
    onboarding_completed: bool
    email_verified: bool = False  # NEW
    created_at: datetime


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    created_at: datetime


class OrganizationMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    user_id: UUID
    role: str
    invited_email: Optional[str] = None
    accepted_at: Optional[datetime] = None
    created_at: datetime


# ---- API Keys ----


class APIKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    scopes: List[str] = ["ingest:write", "metrics:read"]


class APIKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    key_prefix: str
    scopes: Optional[str] = None
    last_used_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime


class APIKeyCreated(APIKeyOut):
    raw_key: str  # Only returned once at creation


# ---- Pipelines ----


class PipelineCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    queries_per_month: Optional[int] = Field(None, ge=0, le=100_000_000)
    cost_per_wrong_answer_usd: Optional[float] = Field(None, ge=0.0, le=1_000_000.0)


class PipelineUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    queries_per_month: Optional[int] = Field(None, ge=0, le=100_000_000)
    cost_per_wrong_answer_usd: Optional[float] = Field(None, ge=0.0, le=1_000_000.0)


class PipelineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str] = None
    queries_per_month: int = 10_000
    cost_per_wrong_answer_usd: float = 5.0
    created_at: datetime


class PipelineStats(BaseModel):
    pipeline_id: UUID
    name: str
    total_queries: int
    hallucination_rate: float
    mean_faithfulness: float
    mean_context_precision: float
    mean_latency_ms: float
    failure_rate: float
    queries_last_7d: int
    trust_score: float = 0.0
    hallucination_cost_usd: float = 0.0


# ---- Ingest (SDK) ----


class ChunkPayload(BaseModel):
    chunk_id: str
    chunk_text: str
    similarity_score: Optional[float] = None
    rank: Optional[int] = None
    metadata: Optional[dict] = None


class TraceIngest(BaseModel):
    pipeline_name: str
    query_text: str
    query_embedding: Optional[List[float]] = None
    retrieved_chunks: List[ChunkPayload] = []
    raw_context: Optional[str] = None
    answer_text: Optional[str] = None
    embed_latency_ms: Optional[float] = None
    retrieve_latency_ms: Optional[float] = None
    generate_latency_ms: Optional[float] = None
    rank_latency_ms: Optional[float] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Optional[dict] = None  # stored as client_metadata_json
    stage_latencies: Optional[dict] = None  # client-side custom stage timings


class TraceIngestResponse(BaseModel):
    trace_id: UUID
    status: str
    message: str


# ---- Query Traces ----


class RetrievedChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chunk_id: str
    chunk_text: str
    similarity_score: Optional[float] = None
    bm25_score: Optional[float] = None
    rank: Optional[int] = None
    was_cited: bool
    metadata: Optional[dict] = None


class GroundingResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sentence_text: str
    sentence_index: int
    is_grounded: bool
    supporting_chunk_id: Optional[str] = None
    confidence_score: Optional[float] = None


class BM25ComparisonOut(BaseModel):
    bm25_better: bool = False
    top_vector_score: Optional[float] = None
    top_bm25_score: Optional[float] = None
    comparable: bool = False
    analysis: str = ""


class QueryTraceListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pipeline_id: UUID
    pipeline_name: Optional[str] = None
    query_text: str
    faithfulness_score: Optional[float] = None
    context_precision_score: Optional[float] = None
    grounded_fraction: Optional[float] = None
    trustworthiness_score: Optional[float] = None  # NEW
    is_hallucination: Optional[bool] = None
    failure_type: Optional[str] = None
    embed_latency_ms: Optional[float] = None
    retrieve_latency_ms: Optional[float] = None
    generate_latency_ms: Optional[float] = None
    rank_latency_ms: Optional[float] = None
    analysis_status: str
    traced_at: datetime


class QueryTraceDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pipeline_id: UUID
    pipeline_name: Optional[str] = None
    query_text: str
    answer_text: Optional[str] = None
    raw_context: Optional[str] = None
    query_embedding: Optional[List[float]] = None
    faithfulness_score: Optional[float] = None
    answer_relevance_score: Optional[float] = None
    context_precision_score: Optional[float] = None
    context_recall_score: Optional[float] = None
    grounded_fraction: Optional[float] = None
    trustworthiness_score: Optional[float] = None  # NEW
    is_hallucination: Optional[bool] = None
    failure_type: Optional[str] = None
    failure_explanation: Optional[str] = None
    recommendation: Optional[str] = None
    embed_latency_ms: Optional[float] = None
    retrieve_latency_ms: Optional[float] = None
    generate_latency_ms: Optional[float] = None
    rank_latency_ms: Optional[float] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    analysis_status: str
    traced_at: datetime
    retrieved_chunks: List[RetrievedChunkOut] = []
    grounding_results: List[GroundingResultOut] = []
    bm25_comparison: Optional[BM25ComparisonOut] = None


class PaginatedTraces(BaseModel):
    items: List[QueryTraceListItem]
    total: int
    page: int
    per_page: int
    pages: int


# ---- Chunks ----


class ChunkStatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chunk_id: str
    pipeline_id: UUID
    text: str
    retrieval_count: int
    citation_count: int
    citation_rate: float
    is_flagged: bool
    last_retrieved_at: Optional[datetime] = None


class PaginatedChunks(BaseModel):
    items: List[ChunkStatOut]
    total: int
    page: int
    per_page: int
    pages: int


# ---- Metrics ----


class DashboardMetrics(BaseModel):
    total_queries: int
    hallucination_rate: float
    mean_faithfulness: float
    mean_context_precision: float
    trustworthiness_score: float  # Aggregate Trust Score (spec formula, recent window)
    queries_today: int
    queries_this_week: int
    failure_type_counts: dict
    recent_failures: List[QueryTraceListItem]
    recent_recommendations: List[dict] = []  # NEW: fix recommendations
    # Week-over-week relative % change vs prior 7 days. None = insufficient baseline.
    queries_trend_pct: Optional[float] = None
    hallucination_rate_trend_pct: Optional[float] = None
    faithfulness_trend_pct: Optional[float] = None
    # Hallucination Cost hero (USD/month)
    hallucination_cost_usd: float = 0.0
    queries_per_month: int = 10_000
    cost_per_wrong_answer_usd: float = 5.0
    cost_pipeline_id: Optional[str] = None  # pipeline whose cost inputs are editable
    # BM25 vs vector aggregate (PRD F4)
    bm25_outperform_rate: Optional[float] = None
    bm25_traces_compared: int = 0
    bm25_summary: Optional[str] = None


class TimeseriesPoint(BaseModel):
    date: str
    value: float


class MetricsAggregate(BaseModel):
    faithfulness_timeseries: List[TimeseriesPoint]
    hallucination_timeseries: List[TimeseriesPoint]
    context_precision_timeseries: List[TimeseriesPoint]
    failure_distribution: dict
    latency_breakdown: List[dict]


# ---- Settings ----


class UserSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ollama_url: str
    ollama_model: str
    grounding_threshold: float
    faithfulness_alert_threshold: float
    enable_email_alerts: bool
    slack_webhook_url: Optional[str] = None  # NEW
    slack_alert_enabled: bool = False  # NEW


class UserSettingsUpdate(BaseModel):
    ollama_url: Optional[str] = None
    ollama_model: Optional[str] = None
    grounding_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    faithfulness_alert_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    enable_email_alerts: Optional[bool] = None
    slack_webhook_url: Optional[str] = None  # NEW
    slack_alert_enabled: Optional[bool] = None  # NEW


# ---- Billing ----


class CreateSubscriptionRequest(BaseModel):
    plan: str  # "starter_monthly", "starter_annual", "pro_monthly", "pro_annual", "enterprise_monthly", "enterprise_annual" (INR) or "starter_usd_monthly", "pro_usd_monthly", "enterprise_usd_monthly" (USD Global)


class SubscriptionOut(BaseModel):
    subscription_plan: str
    subscription_status: Optional[str] = None
    subscription_current_period_end: Optional[datetime] = None
    razorpay_subscription_id: Optional[str] = None


# ---- Alert Rules ----


class AlertRuleCreate(BaseModel):
    pipeline_id: Optional[UUID] = None
    metric: str
    threshold: float
    direction: str  # "below" or "above"
    notify_email: Optional[str] = None
    notify_slack: Optional[bool] = False  # NEW


class AlertRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pipeline_id: Optional[UUID] = None
    metric: str
    threshold: float
    direction: str
    notify_email: Optional[str] = None
    notify_slack: bool = False  # NEW
    is_active: bool
    created_at: datetime


# ---- Fix Recommendations (NEW: PRD v2.0) ----


class FixRecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    pipeline_id: Optional[UUID] = None
    recommendation_type: str
    topic_description: str
    affected_query_count: int
    sample_queries: Optional[str] = None
    generated_at: datetime
    status: str = "open"
    applied_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None
    trust_score_before: Optional[float] = None
    trust_score_after: Optional[float] = None


class PaginatedFixRecommendations(BaseModel):
    items: list[FixRecommendationOut]
    total: int
    page: int
    per_page: int
    pages: int


class TrustVerifyOut(BaseModel):
    recommendation_id: UUID
    status: str
    trust_score_before: Optional[float] = None
    trust_score_after: Optional[float] = None
    trust_delta: Optional[float] = None
    improved: bool = False


# ---- Knowledge Gaps (Phase 10.1 / PRD v3) ----


class KnowledgeGapOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pipeline_id: UUID
    topic_label: str
    representative_query: Optional[str] = None
    query_count: int
    failure_rate: Optional[float] = None
    affected_users_estimate: int = 0
    estimated_monthly_cost_usd: Optional[float] = None
    priority: str
    suggested_document_topic: Optional[str] = None
    auto_fix_draft: Optional[str] = None
    fix_format: str = "markdown"
    status: str
    fixed_at: Optional[datetime] = None
    trust_improvement_after_fix: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class KnowledgeGapStatusUpdate(BaseModel):
    status: str


class PaginatedKnowledgeGaps(BaseModel):
    items: list[KnowledgeGapOut]
    total: int
    page: int
    per_page: int
    pages: int


# ---- Documents (Phase 10.3) ----


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pipeline_id: UUID
    title: str
    source_url: Optional[str] = None
    content_hash: Optional[str] = None
    document_type: Optional[str] = None
    last_modified_at: Optional[datetime] = None
    ingested_at: datetime
    days_since_modified: Optional[int] = None
    freshness_status: str
    freshness_alert_sent: bool = False
    topic_labels: Optional[str] = None
    coverage_score: Optional[float] = None
    chunk_count: int = 0
    stale_chunk_count: int = 0
    created_at: datetime
    updated_at: datetime


class DocumentCreate(BaseModel):
    pipeline_id: UUID
    title: str
    source_url: Optional[str] = None
    document_type: Optional[str] = None
    last_modified_at: Optional[datetime] = None
    chunk_count: int = 0


class PaginatedDocuments(BaseModel):
    items: list[DocumentOut]
    total: int
    page: int
    per_page: int
    pages: int


# ---- Monitoring (Phase 10.4) ----


class MonitoringConfigOut(BaseModel):
    id: UUID
    pipeline_id: UUID
    is_enabled: bool
    interval_minutes: int
    probe_queries: list[str] = []
    alert_trust_threshold: float
    alert_hallucination_threshold: float
    alert_channels: list = []
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: datetime


class MonitoringConfigUpdate(BaseModel):
    is_enabled: bool = False
    interval_minutes: int = 60
    probe_queries: list[str] = []
    alert_trust_threshold: float = 70.0
    alert_hallucination_threshold: float = 0.10
    alert_channels: list = []


class MonitoringRunOut(BaseModel):
    id: UUID
    pipeline_id: UUID
    config_id: Optional[UUID] = None
    trust_score: Optional[float] = None
    hallucination_rate: Optional[float] = None
    probes_run: int = 0
    probes_failed: int = 0
    alerts_triggered: list = []
    regression_detected: bool = False
    run_at: datetime


class MonitoringRunNowOut(BaseModel):
    run_id: str
    pipeline_id: UUID


# ---- Regression (Phase 10.5) ----


class RegressionSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pipeline_id: UUID
    snapshot_label: Optional[str] = None
    trust_score: float
    faithfulness_avg: Optional[float] = None
    context_precision_avg: Optional[float] = None
    hallucination_rate: Optional[float] = None
    trace_count: int = 0
    snapshot_at: datetime


class RegressionSnapshotCreate(BaseModel):
    snapshot_label: Optional[str] = None


class RegressionCompareIn(BaseModel):
    pipeline_id: UUID
    baseline_snapshot_id: UUID
    compare_to: str = "current"  # "current" or snapshot UUID


class RegressionCompareOut(BaseModel):
    baseline: RegressionSnapshotOut
    current: RegressionSnapshotOut
    delta: dict


class PreDeployCheckIn(BaseModel):
    pipeline_id: UUID
    deploy_label: Optional[str] = None


class PreDeployCheckOut(BaseModel):
    passed: bool
    trust_score: float
    baseline_trust_score: float
    regression_risk: str
    blocking_issues: list[str] = []
    regression_severity: Optional[str] = None
    snapshot_id: Optional[str] = None
