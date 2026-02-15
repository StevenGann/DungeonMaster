"""Tests for config loading and env substitution."""

import os
from pathlib import Path

import pytest

from dungeonmaster.config import load_config, _resolve_env


def test_resolve_env_string():
    assert _resolve_env("hello") == "hello"
    os.environ["TEST_VAR"] = "world"
    try:
        assert _resolve_env("${TEST_VAR}") == "world"
        assert _resolve_env("pre-${TEST_VAR}-suf") == "pre-world-suf"
    finally:
        os.environ.pop("TEST_VAR", None)


def test_resolve_env_missing_var():
    assert _resolve_env("${NONEXISTENT}") == "${NONEXISTENT}"


def test_resolve_env_nested():
    os.environ["NESTED_TEST_VAR"] = "nested_value"
    try:
        out = _resolve_env({"a": "x", "b": ["${NESTED_TEST_VAR}"], "c": {"d": "y"}})
        assert out["a"] == "x"
        assert out["b"][0] == "nested_value"
        assert out["c"]["d"] == "y"
    finally:
        os.environ.pop("NESTED_TEST_VAR", None)


def test_load_config_default(tmp_path: Path):
    os.chdir(tmp_path)
    (tmp_path / "config").mkdir(exist_ok=True)
    (tmp_path / "config" / "default.yaml").write_text("vault:\n  path: mydata\n")
    cfg = load_config()
    assert cfg.get("vault", {}).get("path") == "mydata"


def test_load_config_env_override(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VAULT_PATH", "/custom/vault")
    cfg = load_config()
    assert cfg.get("vault", {}).get("path") == "/custom/vault"
