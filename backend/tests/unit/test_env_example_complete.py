"""Ensure .env.example documents every Settings field (Phase 5.8)."""
from __future__ import annotations

from pathlib import Path

from app.core.config import Settings

# Repo root: backend/tests/unit -> ../../..
REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_EXAMPLE = REPO_ROOT / ".env.example"
GITIGNORE = REPO_ROOT / ".gitignore"


def test_env_example_exists_and_lists_all_settings_fields():
    assert ENV_EXAMPLE.is_file(), f"missing {ENV_EXAMPLE}"
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    missing = [name for name in Settings.model_fields if name not in text]
    assert missing == [], f".env.example missing Settings fields: {missing}"


def test_gitignore_allows_env_templates_not_dotenv():
    text = GITIGNORE.read_text(encoding="utf-8")
    assert ".env" in text
    assert "!.env.example" in text
    assert "!.env.production.example" in text
    assert "credentials.json" in text
