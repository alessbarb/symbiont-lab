"""Provisional intervention families before dimensions or competences (§11-§12, §93)."""

from __future__ import annotations

import ast
from pathlib import Path

from symbiont.actuation.action import MotorCommand
from symbiont.actuation.intervention import (
    InterventionSignatureRegistry,
    opaque_channel_ref,
)

from .acquisition_support import SURFACE, A, B


def _command(index: int, channels: dict[str, float], *, competence_id=None) -> MotorCommand:
    return MotorCommand.from_mapping(
        command_id=f"command.{index}",
        commitment_id=f"commitment.{index}",
        controller_id="controller.test",
        competence_id=competence_id,
        surface_fingerprint=SURFACE.contract_fingerprint,
        channels=channels,
        issued_at_tick=index,
    )


def _signature(registry, index, channels, **kwargs):
    return registry.signature_for_command(
        command=_command(index, channels, **kwargs), controller_id="controller.test", tick=index
    )


def test_same_motor_pattern_reuses_signature():
    registry = InterventionSignatureRegistry()
    first = _signature(registry, 1, {A: 0.3})
    second = _signature(registry, 2, {A: 0.8})  # same family, other intensity
    third = _signature(registry, 3, {A: 0.6, B: 0.25})
    fourth = _signature(registry, 4, {A: 0.9, B: 0.4})  # same relative profile
    assert first.signature_id == second.signature_id
    assert third.signature_id == fourth.signature_id
    assert registry.attempt_support(first.signature_id) == 2
    assert registry.intensity_coverage(first.signature_id) == 0.5


def test_different_pattern_creates_distinct_signature():
    registry = InterventionSignatureRegistry()
    only_a = _signature(registry, 1, {A: 0.5})
    only_b = _signature(registry, 2, {B: 0.5})
    a_dominant = _signature(registry, 3, {A: 0.8, B: 0.2})
    b_dominant = _signature(registry, 4, {A: 0.2, B: 0.8})
    ids = {
        only_a.signature_id,
        only_b.signature_id,
        a_dominant.signature_id,
        b_dominant.signature_id,
    }
    assert len(ids) == 4


def test_signature_identity_is_semantically_opaque():
    registry = InterventionSignatureRegistry()
    signature = _signature(registry, 1, {A: 0.5, B: 0.5})
    assert signature.signature_id.startswith("intervention.signature.")
    assert all(ref.startswith("channel.") for ref in signature.channel_refs)
    rendered = repr(signature)
    assert A not in rendered and B not in rendered
    assert "actuator" not in rendered


def test_signature_can_span_multiple_channels():
    registry = InterventionSignatureRegistry()
    signature = _signature(registry, 1, {A: 0.5, B: 0.4})
    assert signature.dimensionality == 2
    assert signature.channel_refs == tuple(sorted((opaque_channel_ref(A), opaque_channel_ref(B))))


def test_signature_can_reference_temporal_pattern():
    registry = InterventionSignatureRegistry()
    _signature(registry, 1, {A: 0.5})
    _signature(registry, 2, {B: 0.5})
    temporal = registry.signature_for_sequence(
        command_refs=("command.1", "command.2"),
        controller_seed_ref="seed.x",
    )
    reverse = registry.signature_for_sequence(
        command_refs=("command.2", "command.1"),
        controller_seed_ref="seed.x",
    )
    assert temporal.temporal_pattern_ref is not None
    assert temporal.temporal_pattern_ref.startswith("temporal.")
    assert temporal.dimensionality == 2
    assert temporal.signature_id != reverse.signature_id
    pattern_temporal, steps = registry.signature_for_pattern_sequence(
        ({A: 0.5}, {B: 0.5}), controller_seed_ref="seed.x"
    )
    assert pattern_temporal.signature_id == temporal.signature_id
    assert len(steps) == 2


def test_signature_does_not_require_action_dimension():
    source = Path("symbiont/src/symbiont/actuation/intervention.py").read_text(encoding="utf-8")
    imported = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert "dimension" not in imported and "competence" not in imported
    registry = InterventionSignatureRegistry()
    assert _signature(registry, 1, {A: 0.5}).signature_id


def test_signature_does_not_require_motor_competence():
    registry = InterventionSignatureRegistry()
    signature = _signature(registry, 1, {A: 0.5}, competence_id=None)
    assert registry.get(signature.signature_id) == signature


def test_signature_registry_roundtrip_and_bound():
    registry = InterventionSignatureRegistry(capacity=2)
    _signature(registry, 1, {A: 0.5})
    _signature(registry, 2, {A: 0.5})
    _signature(registry, 3, {B: 0.5})
    _signature(registry, 4, {A: 0.5, B: 0.5})
    assert len(registry.items) == 2
    restored = InterventionSignatureRegistry.restore(registry.checkpoint())
    assert restored.checkpoint() == registry.checkpoint()


def test_completed_commitment_becomes_a_temporal_intervention_family():
    from .acquisition_support import act, fresh_acquisition

    acquisition = fresh_acquisition()
    act(acquisition, 0, {A: 0.5}, {"signal.a": 0.4})
    temporal = acquisition.record_commitment_pattern(
        commitment_id="commitment.0", controller_seed_ref="competence.c", tick=2
    )
    assert temporal is not None and temporal.temporal_pattern_ref is not None
    assert acquisition.signatures.attempt_support(temporal.signature_id) == 1
    assert (
        acquisition.record_commitment_pattern(
            commitment_id="commitment.unknown", controller_seed_ref="competence.c", tick=3
        )
        is None
    )


def test_untried_neighbour_families_raise_causal_information_gain():
    from .acquisition_support import act, fresh_acquisition, rest

    lonely = fresh_acquisition()
    compared = fresh_acquisition()
    for acquisition in (lonely, compared):
        for tick in range(0, 8, 2):
            rest(acquisition, tick, {})
        for tick in range(10, 26, 2):
            act(acquisition, tick, {A: 0.5}, {"signal.a": 0.4})
    for tick in range(30, 36, 2):
        act(compared, tick, {A: 0.5, B: 0.5}, {"signal.ab": 0.4})
    channel = (opaque_channel_ref(A),)
    assert compared.causal_information_gain(channel) < lonely.causal_information_gain(channel)
