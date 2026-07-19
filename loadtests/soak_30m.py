#!/usr/bin/env python3
"""30-minute soak: health + authenticated metrics; sample docker stats via stdin file companion."""
from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

API = "http://127.0.0.1:18000"
EMAIL = "demo@example.com"
PASSWORD = "DemoPass123!"
DURATION_S = int(__import__("os").environ.get("SOAK_SECONDS", "1800"))
OUT = Path("loadtests/artifacts")
OUT.mkdir(parents=True, exist_ok=True)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def docker_stats_sample() -> list[dict]:
    try:
        raw = subprocess.check_output(
            [
                "docker",
                "stats",
                "--no-stream",
                "--format",
                "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}",
            ],
            text=True,
            timeout=30,
        )
    except Exception as exc:  # noqa: BLE001
        return [{"error": str(exc)}]
    rows = []
    for line in raw.splitlines():
        if "raginspector_" not in line:
            continue
        parts = line.split("\t")
        if len(parts) >= 5:
            rows.append(
                {
                    "name": parts[0],
                    "cpu": parts[1],
                    "mem": parts[2],
                    "net": parts[3],
                    "block": parts[4],
                }
            )
    return rows


def main() -> None:
    started = time.time()
    end = started + DURATION_S
    events = []
    stats_series = []
    totals = {"live_ok": 0, "live_fail": 0, "dash_ok": 0, "dash_fail": 0, "login_429": 0}
    token = None
    refresh = None

    with httpx.Client(timeout=30.0) as c:
        # obtain token once
        for _ in range(10):
            r = c.post(f"{API}/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
            if r.status_code == 200:
                body = r.json()
                token = body["access_token"]
                refresh = body["refresh_token"]
                break
            if r.status_code == 429:
                totals["login_429"] += 1
                time.sleep(15)
            else:
                time.sleep(2)
        if not token:
            (OUT / "soak_30m.json").write_text(
                json.dumps({"error": "no token", "totals": totals}, indent=2), encoding="utf-8"
            )
            return

        i = 0
        next_stats = 0.0
        while time.time() < end:
            i += 1
            # live
            try:
                r = c.get(f"{API}/live")
                if r.status_code == 200:
                    totals["live_ok"] += 1
                else:
                    totals["live_fail"] += 1
                    events.append({"ts": utc(), "type": "live_http", "status": r.status_code})
            except Exception as exc:  # noqa: BLE001
                totals["live_fail"] += 1
                events.append({"ts": utc(), "type": "live_exc", "error": type(exc).__name__})

            # dashboard
            try:
                r = c.get(
                    f"{API}/api/v1/metrics/dashboard",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if r.status_code == 200:
                    totals["dash_ok"] += 1
                elif r.status_code == 401 and refresh:
                    # try refresh once
                    rr = c.post(f"{API}/api/v1/auth/refresh", json={"refresh_token": refresh})
                    if rr.status_code == 200:
                        token = rr.json()["access_token"]
                        refresh = rr.json()["refresh_token"]
                        totals["dash_ok"] += 0  # retry next loop
                    else:
                        totals["dash_fail"] += 1
                        events.append({"ts": utc(), "type": "dash_auth", "status": r.status_code})
                else:
                    totals["dash_fail"] += 1
                    events.append({"ts": utc(), "type": "dash_http", "status": r.status_code})
            except Exception as exc:  # noqa: BLE001
                totals["dash_fail"] += 1
                events.append({"ts": utc(), "type": "dash_exc", "error": type(exc).__name__})

            elapsed = time.time() - started
            if elapsed >= next_stats:
                stats_series.append({"t_s": elapsed, "ts": utc(), "containers": docker_stats_sample()})
                next_stats += 60  # every 60s
                print(f"soak t={elapsed:.0f}s live_ok={totals['live_ok']} dash_ok={totals['dash_ok']} fail_live={totals['live_fail']} fail_dash={totals['dash_fail']}", flush=True)

            time.sleep(1.0)

    # container restart check
    try:
        insp = subprocess.check_output(
            [
                "docker",
                "inspect",
                "-f",
                "{{.Name}} restarts={{.RestartCount}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}n/a{{end}}",
                "raginspector_backend",
                "raginspector_worker",
                "raginspector_db",
                "raginspector_redis",
                "raginspector_frontend",
            ],
            text=True,
        )
    except Exception as exc:  # noqa: BLE001
        insp = str(exc)

    report = {
        "started_at": datetime.fromtimestamp(started, tz=timezone.utc).isoformat(),
        "ended_at": utc(),
        "duration_s_requested": DURATION_S,
        "duration_s_actual": time.time() - started,
        "totals": totals,
        "error_events_sample": events[:50],
        "error_events_count": len(events),
        "stats_series": stats_series,
        "container_inspect": insp,
    }
    (OUT / "soak_30m.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Wrote soak_30m.json", flush=True)


if __name__ == "__main__":
    main()
