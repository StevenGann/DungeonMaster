"""
DungeonMaster configuration loader.

Reads YAML from a file (default: config/default.yaml or DUNGEONMASTER_CONFIG)
and resolves environment variable placeholders. Any string value containing
${VAR_NAME} is replaced with os.environ.get("VAR_NAME", "${VAR_NAME}").

Secrets (API keys, tokens) can be loaded from:
  1. secrets.json in the project root (preferred for local development)
  2. Environment variables (fallback, used in production/Docker)

VAULT_PATH can override vault.path after loading.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

import yaml


logger = logging.getLogger(__name__)


def _find_project_root() -> Path:
    """Find the project root by looking for pyproject.toml or config directory."""
    base = Path.cwd()
    if (base / "pyproject.toml").exists():
        return base
    if (base / "config").exists():
        return base
    if (base / "..").resolve() != base and (base / ".." / "pyproject.toml").exists():
        return (base / "..").resolve()
    return base


def _load_secrets(secrets_path: Path | None = None) -> dict[str, str]:
    """
    Load secrets from secrets.json file.

    Looks for secrets.json in the project root unless a specific path is provided.
    Returns an empty dict if the file doesn't exist or is invalid.

    Expected format:
    {
        "DISCORD_BOT_TOKEN": "your-discord-token",
        "ANTHROPIC_API_KEY": "your-claude-api-key"
    }
    """
    if secrets_path is None:
        secrets_path = _find_project_root() / "secrets.json"

    if not secrets_path.exists():
        logger.debug("No secrets.json found at %s", secrets_path)
        return {}

    try:
        with open(secrets_path, encoding="utf-8") as f:
            secrets = json.load(f)
        if not isinstance(secrets, dict):
            logger.warning("secrets.json must contain a JSON object, got %s", type(secrets).__name__)
            return {}
        logger.info("Loaded secrets from %s", secrets_path)
        return {str(k): str(v) for k, v in secrets.items()}
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse secrets.json: %s", e)
        return {}
    except Exception as e:
        logger.warning("Failed to load secrets.json: %s", e)
        return {}


def _resolve_env(value: Any, secrets: dict[str, str] | None = None) -> Any:
    """
    Recursively resolve ${VAR} placeholders in strings.

    Resolution order:
    1. secrets dict (from secrets.json)
    2. Environment variables
    3. Keep original placeholder if not found
    """
    if secrets is None:
        secrets = {}

    if isinstance(value, str):
        pattern = re.compile(r"\$\{([^}]+)\}")

        def resolve_placeholder(m: re.Match) -> str:
            var_name = m.group(1)
            # First check secrets, then environment
            if var_name in secrets:
                return secrets[var_name]
            return os.environ.get(var_name, m.group(0))

        return pattern.sub(resolve_placeholder, value)
    if isinstance(value, dict):
        return {k: _resolve_env(v, secrets) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env(v, secrets) for v in value]
    return value


def _default_config_dict(secrets: dict[str, str] | None = None) -> dict[str, Any]:
    """Minimal default config when no file is present."""
    if secrets is None:
        secrets = {}

    discord_token = secrets.get("DISCORD_BOT_TOKEN", "")
    if not discord_token:
        discord_token = os.environ.get("DISCORD_BOT_TOKEN", "")

    anthropic_key = secrets.get("ANTHROPIC_API_KEY", "")
    if not anthropic_key:
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")

    return {
        "vault": {"path": "data"},
        "ai": {
            "ollama": {
                "base_url": "http://localhost:11434",
                "narrative_model": "llama3.2",
                "embedding_model": "nomic-embed-text",
            },
            "claude": {
                "api_key": anthropic_key,
                "ruling_model": "claude-3-5-sonnet-20241022",
            },
        },
        "rag": {"chunk_size": 512, "chunk_overlap": 64, "top_k": 5},
        "discord": {
            "token": discord_token,
            "dm_only": True,
        },
    }


def load_config(path: str | Path | None = None, secrets_path: str | Path | None = None) -> dict[str, Any]:
    """
    Load configuration from a YAML file with secrets and environment variable substitution.

    Secrets are loaded from secrets.json (if present) and take precedence over
    environment variables for ${VAR} placeholder resolution.

    Args:
        path: Path to YAML config file. If None, looks for DUNGEONMASTER_CONFIG
              env var, then config/default.yaml relative to project root.
        secrets_path: Path to secrets.json. If None, looks in project root.

    Returns:
        Configuration dictionary with all placeholders resolved.
    """
    # Load secrets first
    secrets = _load_secrets(Path(secrets_path) if secrets_path else None)

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
        config = _default_config_dict(secrets)
    else:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        config = _resolve_env(raw, secrets)

    # VAULT_PATH env var overrides config
    if os.environ.get("VAULT_PATH"):
        config.setdefault("vault", {})["path"] = os.environ["VAULT_PATH"]
    return config
