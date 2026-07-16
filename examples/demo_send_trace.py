#!/usr/bin/env python3
"""
Reproducible SDK demo (Phase 9.5).

Prereqs:
  1. Stack up + migrations: docker compose up -d && alembic upgrade head
  2. Seed demo (or create your own API key in Settings):
       docker compose run --rm backend python scripts/seed_demo.py
  3. Create an API key in the UI (Settings) OR set RAGINSPECTOR_API_KEY

Usage:
  pip install -e ./sdk
  set RAGINSPECTOR_API_KEY=ri-...
  python examples/demo_send_trace.py
"""
from __future__ import annotations

import os
import sys

try:
    from raginspector import RAGInspector
except ImportError:
    print("Install the SDK first: pip install -e ./sdk", file=sys.stderr)
    raise SystemExit(1)

API_KEY = os.environ.get("RAGINSPECTOR_API_KEY", "").strip()
BASE_URL = os.environ.get("RAGINSPECTOR_BASE_URL", "http://localhost:8000").rstrip("/")

if not API_KEY:
    print(
        "Set RAGINSPECTOR_API_KEY to a key from Settings → API keys "
        "(demo user: demo@example.com / DemoPass123!).",
        file=sys.stderr,
    )
    raise SystemExit(2)

inspector = RAGInspector(
    api_key=API_KEY,
    pipeline_name=os.environ.get("RAGINSPECTOR_PIPELINE", "demo-sdk-pipeline"),
    base_url=BASE_URL,
)

CHUNKS = [
    {
        "chunk_id": "doc-returns-01",
        "chunk_text": "Customers may return unused items within 30 days of purchase for a full refund.",
        "similarity_score": 0.91,
    },
    {
        "chunk_id": "doc-returns-02",
        "chunk_text": "Opened software and gift cards are not eligible for return.",
        "similarity_score": 0.72,
    },
]


@inspector.trace_retrieval
def retrieve(query: str) -> list[dict]:
    return CHUNKS


@inspector.trace_generation
def generate(query: str, context: list[dict]) -> str:
    # Intentionally mix grounded + ungrounded claims for a useful dashboard demo.
    return (
        "You can return unused items within 30 days for a full refund. "
        "We also offer free lifetime replacements on all accessories."
    )


def main() -> None:
    query = "What is the return policy?"
    answer = generate(query, retrieve(query))
    inspector.flush()
    print("Answer:", answer)
    print("Trace submitted. Open the dashboard → Queries.")
    print(f"API: {BASE_URL}")


if __name__ == "__main__":
    main()
