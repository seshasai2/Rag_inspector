#!/usr/bin/env python3
"""Create or update a cron-job.org keep-alive job for /health.

Requires env CRON_JOB_ORG_API_KEY (Bearer token from cron-job.org → Settings).
Docs: https://docs.cron-job.org/rest-api.html
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.cron-job.org"
JOB_TITLE = "raginspector-api-keepalive"


def _request(method: str, path: str, token: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{API}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode() or "{}"
            return resp.status, json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode() or "{}"
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"raw": body}
        return exc.code, parsed


def every_n_minutes_schedule(n: int) -> dict:
    """Build a cron-job.org schedule that fires every n minutes."""
    if n < 1 or n > 30:
        raise ValueError("interval minutes must be 1..30")
    minutes = list(range(0, 60, n))
    return {
        "timezone": "UTC",
        "expiresAt": 0,
        "hours": [-1],
        "mdays": [-1],
        "months": [-1],
        "wdays": [-1],
        "minutes": minutes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        default="https://raginspector-api.onrender.com/health",
        help="Health URL to ping",
    )
    parser.add_argument(
        "--every-minutes",
        type=int,
        default=7,
        help="Ping interval in minutes (default 7, staggered vs GitHub */5)",
    )
    parser.add_argument(
        "--title",
        default=JOB_TITLE,
        help="Job title used for idempotent create/update",
    )
    args = parser.parse_args()

    token = (os.environ.get("CRON_JOB_ORG_API_KEY") or "").strip()
    if not token:
        print(
            "ERROR: Set CRON_JOB_ORG_API_KEY (cron-job.org → Settings → API keys).",
            file=sys.stderr,
        )
        return 1

    status, listing = _request("GET", "/jobs", token)
    if status != 200:
        print(f"ERROR: list jobs failed http={status}: {listing}", file=sys.stderr)
        return 1

    jobs = listing.get("jobs") or []
    existing = next((j for j in jobs if j.get("title") == args.title), None)

    job_body = {
        "job": {
            "url": args.url,
            "title": args.title,
            "enabled": True,
            "saveResponses": True,
            "requestMethod": 0,  # GET
            "schedule": every_n_minutes_schedule(args.every_minutes),
        }
    }

    if existing and existing.get("jobId") is not None:
        job_id = existing["jobId"]
        status, body = _request("PATCH", f"/jobs/{job_id}", token, job_body)
        action = "updated"
    else:
        status, body = _request("PUT", "/jobs", token, job_body)
        action = "created"

    print(f"{action} http={status}")
    print(json.dumps(body, indent=2))
    if status not in {200, 201}:
        return 1
    print(f"OK — cron-job.org will GET {args.url} every {args.every_minutes} minutes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
