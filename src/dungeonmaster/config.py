"""
DungeonMaster configuration loader.

Reads YAML from a file (default: config/default.yaml or DUNGEONMASTER_CONFIG)
and resolves environment variable placeholders. Any string value containing
${VAR_NAME} is replaced with os.environ.get("VAR_NAME", "${VAR_NAME}").
VAULT_PATH can override vault.path after loading.
"""

import os
import re
from pathlib import Path
from typing import Any

import yaml


def _resolve_env(value: Any) -> Any:
    """Recursively resolve ${VAR} placeholders in strings; leave other types unchanged."""
    if isinstance(value, str):
        pattern = re.compile(r"\$\{([^}]+)\}")
        return pattern.sub(
            lambda m: os.environ.get(m.group(1), m.group(0)),
            value,
        )
    if isinstance(value, dict):
        return {k: _resolve_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env(v) for v in value]
    return value


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """
    Load configuration from a YAML file with environment variable substitution.

    If path is None, looks for DUNGEONMASTER_CONFIG env var, then config/default.yaml
    relative to the project root (directory containing pyproject.toml or 'config').
    """
    if path is None:
        path = os.environ.get("DUNGEONMASTER_CONFIG")
        if path:
            path = Path(path)
        else:
            # Default: config/default.yaml next to cwd or repo root
            base = Path.cwd()
            if (base / "config" / "default.yaml").exists():
                path = base / "config" / "default.yaml"
            elif (base / ".." / "config" / "default.yaml").resolve().exists():
                path = (base / ".." / "config" / "default.yaml").resolve()
            else:
                path = base / "config" / "default.yaml"
    path = Path(path)
    if not path.exists():
        config = _default_config_dict()
    else:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        config = _resolve_env(raw)
    if os.environ.get("VAULT_PATH"):
        config.setdefault("vault", {})["path"] = os.environ["VAULT_PATH"]
    return config


def _default_config_dict() -> dict[str, Any]:
    """Minimal default config when no file is present."""
    return {
        "vault": {"path": "data"},
        "ai": {
            "ollama": {
                "base_url": "http://localhost:11434",
                "narrative_model": "llama3.2",
                "embedding_model": "nomic-embed-text",
            },
            "claude": {
                "api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
                "ruling_model": "claude-3-5-sonnet-20241022",
            },
        },
        "rag": {"chunk_size": 512, "chunk_overlap": 64, "top_k": 5},
        "discord": {"token": os.environ.get("DISCORD_BOT_TOKEN", ""), "dm_only": True},
    }
