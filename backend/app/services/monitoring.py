"""Monitoring probe evaluation (Phase 10.4).

Probes are query strings used to score recent pipeline health (Trust Score +
hallucination rate). Full re-ingest of each probe is intentionally not done in
the beat loop — that would block workers; instead we evaluate live metrics and
match probe text against recent failing traces.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.models import MonitoringConfig, MonitoringRun, QueryTrace
from app.services.trust_scorer import TRUST_SCORE_WINDOW, compute_trust_score


def _parse_json_list(raw: str | None) -> list:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def dumps_json(value: Any) -> str:
    return json.dumps(value)


def hallucination_rate(traces: list) -> float:
    if not traces:
        return 0.0
    flags = [bool(t.is_hallucination) for t in traces]
    return sum(1 for f in flags if f) / len(flags)


def count_probe_failures(traces: list, probe_queries: list[str]) -> tuple[int, int]:
    """Return (probes_run, probes_failed) using keyword overlap with recent failures."""
    probes = [str(q).strip() for q in probe_queries if str(q).strip()]
    if not probes:
        probes = ["*"]
    failed_traces = [
        t
        for t in traces
        if t.is_hallucination
        or (
            t.failure_type
            and str(getattr(t.failure_type, "value", t.failure_type)) not in ("none", "None", "")
        )
    ]
    probes_failed = 0
    for probe in probes:
        if probe == "*":
            if failed_traces:
                probes_failed += 1
            continue
        tokens = [tok for tok in probe.lower().split() if len(tok) > 2]
        matched_fail = False
        for t in failed_traces:
            text = (t.query_text or "").lower()
            if tokens and any(tok in text for tok in tokens):
                matched_fail = True
                break
            if not tokens and probe.lower() in text:
                matched_fail = True
                break
        if matched_fail:
            probes_failed += 1
    return len(probes), probes_failed


def build_alerts(
    *,
    trust: float,
    hall_rate: float,
    trust_threshold: float,
    hall_threshold: float,
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    if trust < trust_threshold:
        alerts.append(
            {
                "type": "trust_score",
                "value": trust,
                "threshold": trust_threshold,
                "direction": "below",
            }
        )
    if hall_rate > hall_threshold:
        alerts.append(
            {
                "type": "hallucination_rate",
                "value": hall_rate,
                "threshold": hall_threshold,
                "direction": "above",
            }
        )
    return alerts


def evaluate_pipeline_monitoring(
    db: Session,
    config: MonitoringConfig,
    *,
    now: datetime | None = None,
) -> MonitoringRun:
    """Compute metrics, persist a MonitoringRun, advance next_run_at."""
    now = now or datetime.now(timezone.utc)
    traces = (
        db.query(QueryTrace)
        .filter(QueryTrace.pipeline_id == config.pipeline_id)
        .order_by(QueryTrace.traced_at.desc())
        .limit(TRUST_SCORE_WINDOW)
        .all()
    )
    trust = float(compute_trust_score(traces)) if traces else 0.0
    hall = hallucination_rate(traces)
    probes = _parse_json_list(config.probe_queries)
    probes_run, probes_failed = count_probe_failures(traces, probes)
    alerts = build_alerts(
        trust=trust,
        hall_rate=hall,
        trust_threshold=float(config.alert_trust_threshold),
        hall_threshold=float(config.alert_hallucination_threshold),
    )

    # Simple regression: trust dropped >5 vs previous run
    prev = (
        db.query(MonitoringRun)
        .filter(MonitoringRun.pipeline_id == config.pipeline_id)
        .order_by(MonitoringRun.run_at.desc())
        .first()
    )
    regression = bool(prev and prev.trust_score is not None and (prev.trust_score - trust) >= 5.0)

    run = MonitoringRun(
        pipeline_id=config.pipeline_id,
        config_id=config.id,
        trust_score=trust,
        hallucination_rate=round(hall, 4),
        probes_run=probes_run,
        probes_failed=probes_failed,
        alerts_triggered=dumps_json(alerts) if alerts else "[]",
        regression_detected=regression,
        run_at=now,
    )
    db.add(run)

    interval = max(1, int(config.interval_minutes or 60))
    config.last_run_at = now
    config.next_run_at = now + timedelta(minutes=interval)
    db.flush()
    return run
