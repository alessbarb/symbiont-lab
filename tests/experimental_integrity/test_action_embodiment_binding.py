from __future__ import annotations

from pathlib import Path


def test_physics3d_binds_action_authority_to_canonical_episode() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / "src" / "symbiont_lab" / "physics3d" / "runtime.py").read_text(
        encoding="utf-8"
    )
    assert "bind_action_embodiment(" in source
    assert "new_episode=not restored_same_episode" in source


def test_runtime_new_episode_withdraws_previous_execution_authority() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / "src" / "symbiont" / "core" / "orchestration" / "runtime.py").read_text(
        encoding="utf-8"
    )
    assert "self._action_domain.begin_embodiment(" in source
    assert "restored action authority belongs to another embodiment" in source
