#!/usr/bin/env python3
"""Fail if any Alembic revision lacks a downgrade() callable."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ROOT / "backend" / "migrations" / "versions"


def has_downgrade(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "downgrade":
            return True
    return False


def main() -> int:
    files = sorted(p for p in VERSIONS.glob("*.py") if p.name != "__init__.py")
    if not files:
        print(f"No migrations found under {VERSIONS}")
        return 1
    failed = [p.name for p in files if not has_downgrade(p)]
    if failed:
        print("Migrations missing downgrade():")
        for name in failed:
            print(f"  - {name}")
        return 1
    print(f"OK: {len(files)} migrations define downgrade()")
    return 0


if __name__ == "__main__":
    sys.exit(main())
