"""Pytest fixtures: temp vault, config, providers (mocked where needed)."""

import os
from pathlib import Path

import pytest

from dungeonmaster.data.vault import Vault
from dungeonmaster.data.state import StateStore, SceneState, Location, Position


@pytest.fixture
def tmp_vault_path(tmp_path: Path) -> Path:
    return tmp_path / "vault"


@pytest.fixture
def vault(tmp_vault_path: Path) -> Vault:
    v = Vault(tmp_vault_path)
    v.ensure_all_dirs()
    return v


@pytest.fixture
def state_store(vault: Vault) -> StateStore:
    return StateStore(vault)


@pytest.fixture
def sample_scene() -> SceneState:
    return SceneState(
        scene_id="test",
        location=Location(name="Tavern", description="A noisy tavern."),
        positions=[
            Position(entity_id="player1", entity_type="player", x=0, y=0, zone="main"),
        ],
        turn_order=["player1"],
        timestamp="2025-01-01T00:00:00Z",
    )
