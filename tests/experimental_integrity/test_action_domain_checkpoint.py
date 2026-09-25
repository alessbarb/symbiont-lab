from __future__ import annotations

from pathlib import Path

from symbiont.core.runtime import OrganismRuntime

from symbiont.actuation.surface import derive_actuator_constitution


def test_checkpoint_writes_single_canonical_action_domain() -> None:
    surface = derive_actuator_constitution(
        1,
        physical_contract="canonical-checkpoint",
    )
    runtime = OrganismRuntime(
        organism_id="symbiont.checkpoint",
        actuation_enabled=True,
        actuator_constitution=surface,
    )
    actuation = runtime.checkpoint()["actuation"]
    assert "action_domain" in actuation
    assert "proposer" not in actuation
    assert "sensorimotor" not in actuation
    assert "action_commitment" not in actuation
    assert "sensorimotor_v2" not in actuation


def test_runtime_source_keeps_legacy_keys_read_only() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / "src" / "symbiont" / "core" / "orchestration" / "runtime.py").read_text(
        encoding="utf-8"
    )
    build = source.split("def _build_checkpoint_payload", 1)[1].split("def state_hash", 1)[0]
    assert '"proposer":' not in build
    assert '"sensorimotor":' not in build
    assert '"action_commitment":' not in build
