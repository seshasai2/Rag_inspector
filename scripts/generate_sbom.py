#!/usr/bin/env python3
"""Generate filesystem SBOMs (CycloneDX) for backend + frontend + SDK."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "sbom"
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def try_syft(target: Path, out: Path) -> bool:
    cmd = ["syft", str(target), "-o", f"cyclonedx-json={out}", "-q"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        return False
    return proc.returncode == 0 and out.exists()


def fallback_inventory(name: str, files: list[Path], out: Path) -> None:
    components = []
    for f in files:
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        components.append(
            {
                "type": "file",
                "name": str(f.relative_to(ROOT)).replace("\\", "/"),
                "version": VERSION,
                "description": f"Dependency lock / manifest ({len(text)} bytes)",
            }
        )
    doc = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "component": {"type": "application", "name": name, "version": VERSION},
            "tools": [{"name": "raginspector-generate_sbom", "version": VERSION}],
        },
        "components": components,
    }
    out.write_text(json.dumps(doc, indent=2), encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    targets = [
        ("backend", ROOT / "backend", [ROOT / "backend" / "requirements.txt"]),
        ("frontend", ROOT / "frontend", [ROOT / "frontend" / "package-lock.json"]),
        ("sdk", ROOT / "sdk", [ROOT / "sdk" / "pyproject.toml"]),
    ]
    for name, path, manifests in targets:
        out = OUT / f"{name}-cyclonedx.json"
        if try_syft(path, out):
            print(f"OK: syft SBOM -> {out.relative_to(ROOT)}")
        else:
            fallback_inventory(name, manifests, out)
            print(f"OK: fallback inventory SBOM -> {out.relative_to(ROOT)} (install syft for full graph)")
    meta = {
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": [str(p.relative_to(ROOT)).replace("\\", "/") for p in sorted(OUT.glob("*.json"))],
        "update_process": "docs/SUPPLY_CHAIN.md",
    }
    (OUT / "manifest.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("SBOM generation complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
