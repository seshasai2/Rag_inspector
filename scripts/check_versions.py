#!/usr/bin/env python3
"""Fail if package versions diverge from the root VERSION file."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    checks = [
        (ROOT / "backend" / "pyproject.toml", rf'version\s*=\s*"{re.escape(version)}"'),
        (ROOT / "sdk" / "pyproject.toml", rf'version\s*=\s*"{re.escape(version)}"'),
        (ROOT / "frontend" / "package.json", rf'"version"\s*:\s*"{re.escape(version)}"'),
        (ROOT / "sdk" / "raginspector" / "__init__.py", rf'__version__\s*=\s*"{re.escape(version)}"'),
    ]
    ok = True
    for path, pattern in checks:
        text = path.read_text(encoding="utf-8")
        if not re.search(pattern, text):
            print(f"FAIL: {path.relative_to(ROOT)} does not match VERSION={version}")
            ok = False
        else:
            print(f"OK:   {path.relative_to(ROOT)}")
    if not ok:
        return 1
    print(f"All packages at {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
