#!/usr/bin/env python3
"""Validate Helm chart structure and required templates (no cluster required)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHART = ROOT / "infrastructure" / "helm" / "raginspector"
REQUIRED = [
    "Chart.yaml",
    "values.yaml",
    "values-development.yaml",
    "values-staging.yaml",
    "values-production.yaml",
    "templates/_helpers.tpl",
    "templates/backend.yaml",
    "templates/frontend.yaml",
    "templates/worker.yaml",
    "templates/beat.yaml",
    "templates/ingress.yaml",
    "templates/networkpolicy.yaml",
    "templates/hpa.yaml",
    "templates/pdb.yaml",
    "templates/configmap.yaml",
    "templates/secret.yaml",
    "templates/serviceaccount.yaml",
    "templates/migration-job.yaml",
    "templates/validate-job.yaml",
]


def main() -> int:
    missing = [p for p in REQUIRED if not (CHART / p).exists()]
    if missing:
        print("Missing chart files:")
        for m in missing:
            print(f"  - {m}")
        return 1
    print(f"OK: chart structure ({len(REQUIRED)} required paths)")

    try:
        helm = subprocess.run(["helm", "version", "--short"], capture_output=True, text=True)
    except FileNotFoundError:
        print("WARN: helm CLI not installed — skipping helm lint/template")
        return 0
    if helm.returncode != 0:
        print("WARN: helm CLI not usable — skipping helm lint/template")
        return 0

    lint = subprocess.run(
        ["helm", "lint", str(CHART), "-f", str(CHART / "values-production.yaml")],
        capture_output=True,
        text=True,
    )
    print(lint.stdout)
    if lint.stderr:
        print(lint.stderr)
    if lint.returncode != 0:
        return lint.returncode

    for name, values in [
        ("development", "values-development.yaml"),
        ("staging", "values-staging.yaml"),
        ("production", "values-production.yaml"),
    ]:
        out = ROOT / "artifacts" / f"helm-render-{name}.yaml"
        out.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "helm",
            "template",
            "raginspector",
            str(CHART),
            "-f",
            str(CHART / values),
            "--namespace",
            "raginspector",
        ]
        if name == "development":
            cmd += [
                "--set",
                "secret.stringData.SECRET_KEY=ci-dev-secret-key-min-32-characters!!",
            ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            print(f"helm template FAILED for {name}:\n{proc.stderr}")
            return proc.returncode
        out.write_text(proc.stdout, encoding="utf-8")
        print(f"OK: rendered {name} -> {out.relative_to(ROOT)} ({len(proc.stdout.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
