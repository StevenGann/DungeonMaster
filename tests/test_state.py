"""Tests for SceneState and StateStore."""

from dungeonmaster.data.state import (
    SceneState,
    StateStore,
)


def test_scene_state_roundtrip(sample_scene: SceneState):
    d = sample_scene.to_dict()
    restored = SceneState.from_dict(d)
    assert restored.scene_id == sample_scene.scene_id
    assert restored.location.name == sample_scene.location.name
    assert len(restored.positions) == len(sample_scene.positions)
    assert restored.positions[0].entity_id == "player1"


def test_state_store_load_save_scene(state_store: StateStore, sample_scene: SceneState):
    state_store.save_scene(sample_scene)
    loaded = state_store.load_scene()
    assert loaded.scene_id == sample_scene.scene_id
    assert loaded.location.name == sample_scene.location.name


def test_state_store_load_scene_missing(state_store: StateStore):
    scene = state_store.load_scene()
    assert scene.scene_id == "default"
    assert scene.positions == []


def test_state_store_character(state_store: StateStore):
    assert state_store.load_character("alice") == ""
    state_store.save_character("alice", "# Alice\n\nHP: 10")
    assert "Alice" in state_store.load_character("alice")


def test_state_store_npc(state_store: StateStore):
    assert state_store.load_npc("barkeep") == ""
    state_store.save_npc("barkeep", "# Barkeep\n\nFriendly.")
    assert "Barkeep" in state_store.load_npc("barkeep")
