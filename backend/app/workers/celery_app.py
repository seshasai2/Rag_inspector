from celery import Celery
from celery.schedules import crontab
from celery.signals import task_postrun, task_prerun, worker_process_init
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.core.config import settings, validate_production_settings
from app.core.logging import setup_logging
from app.core.sentry_init import init_sentry

celery_app = Celery(
    "raginspector",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks", "app.workers.freshness_worker", "app.workers.monitoring_worker"],
)


@worker_process_init.connect
def _init_worker_process(**kwargs):
    """Logging, Sentry, prod validation, and optional ML warm (Phases 8.3 / 8.6 / 8.7)."""
    setup_logging()
    init_sentry(celery=True)
    validate_production_settings()
    if not settings.WARM_ML_MODELS_ON_WORKER_START:
        return
    try:
        from app.services.ml_models import warm_ml_models

        warm_ml_models()
    except Exception:
        # Analysis still runs with keyword / lexical fallbacks if warm fails.
        pass


@task_prerun.connect
def _bind_task_log_context(task_id=None, task=None, **kwargs):
    clear_contextvars()
    bind_contextvars(celery_task_id=task_id)
    headers = getattr(getattr(task, "request", None), "headers", None) or {}
    if isinstance(headers, dict):
        request_id = headers.get("request_id")
        if request_id:
            bind_contextvars(request_id=request_id)


@task_postrun.connect
def _clear_task_log_context(**kwargs):
    clear_contextvars()


celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_timeout=5,
    broker_transport_options={
        "socket_timeout": 5,
        "socket_connect_timeout": 5,
    },
    result_backend_transport_options={
        "socket_timeout": 5,
        "socket_connect_timeout": 5,
    },
    task_routes={
        "app.workers.tasks.run_analysis": {"queue": "analysis"},
        "app.workers.tasks.reset_monthly_traces": {"queue": "celery"},
        "app.workers.tasks.update_chunk_citation_rates": {"queue": "celery"},
        "app.workers.tasks.deliver_webhook": {"queue": "celery"},
        "app.workers.tasks.send_weekly_executive_reports": {"queue": "celery"},
        "app.workers.freshness_worker.check_document_freshness": {"queue": "celery"},
        "app.workers.monitoring_worker.run_monitoring_probes": {"queue": "celery"},
    },
    beat_schedule={
        "reset-monthly-traces": {
            "task": "app.workers.tasks.reset_monthly_traces",
            "schedule": crontab(0, 0, day_of_month="1"),
        },
        "update-citation-rates": {
            "task": "app.workers.tasks.update_chunk_citation_rates",
            "schedule": crontab(minute="*/30"),
        },
        "send-weekly-executive-reports": {
            "task": "app.workers.tasks.send_weekly_executive_reports",
            "schedule": crontab(minute=0, hour=9, day_of_week="mon"),
        },
        "check-document-freshness-daily": {
            "task": "app.workers.freshness_worker.check_document_freshness",
            "schedule": crontab(minute=15, hour=3),
        },
        "run-monitoring-probes": {
            "task": "app.workers.monitoring_worker.run_monitoring_probes",
            "schedule": 60.0,  # every minute; configs filter on next_run_at
        },
    },
)
