#!/usr/bin/env python3
"""
Post-deploy release validation against a running API/UI.
Fails non-zero if critical checks fail.

  API_URL=https://api.example.com FRONTEND_URL=https://app.example.com \
    python scripts/validate_release.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def fetch(url: str, headers: dict | None = None, timeout: int = 15) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return e.code, body
    except Exception as e:  # noqa: BLE001
        return 0, str(e)


def main() -> int:
    api = os.environ.get("API_URL", "http://127.0.0.1:8000").rstrip("/")
    fe = os.environ.get("FRONTEND_URL", "http://127.0.0.1:3000").rstrip("/")
    ops = (os.environ.get("OPS_SHARED_TOKEN") or "").strip()
    failed = 0

    checks = [
        ("API /live", f"{api}/live", None, {200}),
        ("API /api/v1/ops/ready", f"{api}/api/v1/ops/ready", None, {200}),
        ("Frontend /", f"{fe}/", None, {200, 304}),
    ]
    for name, url, _, ok in checks:
        status, body = fetch(url)
        if status not in ok:
            print(f"FAIL: {name} -> HTTP {status}: {body[:200]}")
            failed += 1
        else:
            print(f"OK:   {name} -> {status}")

    headers = {"X-Ops-Token": ops} if ops else {}
    status, body = fetch(f"{api}/api/v1/ops/metrics", headers=headers)
    if status != 200:
        print(f"FAIL: metrics -> HTTP {status}: {body[:200]}")
        failed += 1
    else:
        print("OK:   metrics scrape")

    # Ready body should mention ready status when JSON
    status, body = fetch(f"{api}/api/v1/ops/ready")
    if status == 200:
        try:
            data = json.loads(body)
            if data.get("status") not in ("ready", "healthy", None) and data.get("status") == "degraded":
                print(f"FAIL: readiness degraded: {data}")
                failed += 1
            else:
                print(f"OK:   readiness payload status={data.get('status')}")
        except json.JSONDecodeError:
            print("WARN: readiness body not JSON")

    if failed:
        print(f"\n{failed} critical check(s) failed — stop deployment")
        return 1
    print("\nRelease validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
