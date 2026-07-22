#!/usr/bin/env python3
"""Create an UptimeRobot free monitor via the agentic (no API key) flow.

Owner must click the activation email to finish setup.
Docs: https://uptimerobot.com/quick-monitor-setup/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.uptimerobot.com"


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as resp:
        return json.loads(resp.read().decode())


def _post_json(url: str, payload: dict) -> tuple[int, dict | str]:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode()
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, body


def solve_pow(nonce: str, difficulty: int) -> int:
    counter = 0
    while True:
        digest = hashlib.sha256(f"{nonce}|{counter}".encode()).digest()
        leading_zeros = 0
        for byte in digest:
            if byte == 0:
                leading_zeros += 8
            else:
                leading_zeros += 8 - byte.bit_length()
                break
        if leading_zeros >= difficulty:
            return counter
        counter += 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--email",
        required=True,
        help="Inbox that receives the UptimeRobot activation + downtime alerts",
    )
    parser.add_argument(
        "--url",
        default="https://raginspector-api.onrender.com/health",
        help="Health URL to monitor (default: production /health)",
    )
    args = parser.parse_args()

    query = urllib.parse.urlencode({"email": args.email, "url": args.url})
    challenge = _get_json(f"{API}/agentic/agent-monitor/challenge?{query}")
    print("challenge:", json.dumps(challenge))

    nonce = challenge["nonce"]
    difficulty = int(challenge["difficulty"])
    counter = solve_pow(nonce, difficulty)
    print(f"solved counter={counter} difficulty={difficulty}")

    status, body = _post_json(
        f"{API}/agentic/agent-monitor",
        {
            "email": args.email,
            "url": args.url,
            "nonce": nonce,
            "timestamp": challenge["timestamp"],
            "counter": counter,
            "signature": challenge["signature"],
        },
    )
    print(f"submit http={status}")
    print(json.dumps(body, indent=2) if isinstance(body, dict) else body)

    if status != 200:
        return 1

    deep = (
        "https://uptimerobot.com/quick-start?"
        + urllib.parse.urlencode({"url": args.url, "email": args.email})
    )
    print()
    print("NEXT STEP (required):")
    print(f"  1. Check inbox for {args.email} (UptimeRobot activation email).")
    print("  2. Open the link and click Activate.")
    print(f"  Or open: {deep}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
