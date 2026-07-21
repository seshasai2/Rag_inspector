#!/usr/bin/env python3
"""CLI: seed demo user, org, pipelines, traces, and Phase 10 assets.

Usage (from backend/):

    python scripts/seed_demo.py
    python scripts/seed_demo.py --force

Or via Compose:

    docker compose run --rm backend python scripts/seed_demo.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow ``python scripts/seed_demo.py`` without installing the package
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed RAGInspector demo dataset")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Refresh demo pipeline traces and Phase 10 assets even if already present",
    )
    args = parser.parse_args()

    from sqlalchemy.orm import Session

    from app.db.session import sync_engine
    from app.services.demo_seed import DEMO_EMAIL, DEMO_PASSWORD, seed_demo_data

    with Session(sync_engine) as session:
        result = seed_demo_data(session, force=args.force)

    print(result.message)
    print(f"  email:    {result.email}")
    print(f"  password: {result.password}")
    print(f"  api_key:  {result.api_key}")
    print(f"  user_id:  {result.user_id}")
    print(f"  org_id:   {result.organization_id}")
    print(f"  pipeline: {result.pipeline_id}")
    if result.trace_count:
        print(f"  traces:   {result.trace_count}")
    print()
    print("Log in at the frontend, then open Dashboard / Queries / Chunks / Knowledge Gaps.")
    print(f"(Credentials are also in docs/SEED.md — {DEMO_EMAIL} / {DEMO_PASSWORD})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
