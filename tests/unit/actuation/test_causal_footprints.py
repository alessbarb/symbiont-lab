"""Causal footprints from pulses (Factorized Effect Representation v1 §4.2, §13.4)."""

from __future__ import annotations

from symbiont.actuation.evidence import CausalEvidence
from symbiont.actuation.footprint import (
    AtomEstimate,
    FootprintRegistry,
    atom_estimates,
    footprint_id,
    pulses_from,
    quiet_runs,
)

CAUSED = "effect.atom.caused"
DRIFT = "effect.atom.drift"
CHANNELS = {"sig.a": ("channel.a",), "sig.b": ("channel.b",)}


def _item(tick, *, commitment=None, signature=None, atoms=()):
    active = commitment is not None
    return CausalEvidence(
        evidence_id=f"causal.{tick}",
        attempt_id=f"attempt.{tick}" if active else None,
        intervention_signature_id=signature,
        commitment_id=commitment,
        competence_id=None,
        effect_id=None,
        context_ref=None,
        observation_tick=tick,
        action_ref=f"command.{tick}" if active else None,
        effect_atoms=tuple(sorted(atoms)),
    )


def _history(pulse_count=8):
    evidence, tick = [], 0
    for index in range(pulse_count):
        for step in range(6):  # a 6-window pulse; the caused change at onset only
            atoms = (CAUSED,) if step == 0 else ()
            evidence.append(_item(tick, commitment=f"c{index}", signature="sig.a", atoms=atoms))
            tick += 1
        for step in range(4):  # a quiet run; the body drifts on its own
            evidence.append(_item(tick, atoms=(DRIFT,) if step == 1 else ()))
            tick += 1
    return evidence


def test_pulses_are_commitments_on_one_channel_set():
    evidence = [
        *[_item(t, commitment="c1", signature="sig.a", atoms=(CAUSED,)) for t in range(4)],
        _item(4, commitment="c2", signature="sig.a"),  # too short
        _item(5, commitment="c3", signature="sig.a"),
        _item(6, commitment="c3", signature="sig.b"),
        _item(7, commitment="c3", signature="sig.b"),  # two channel sets: coordination
    ]
    (pulse,) = pulses_from(evidence, CHANNELS.get)
    assert pulse.source == ("channel.a",) and pulse.atoms == frozenset({CAUSED})


def test_quiet_runs_are_consecutive_passive_windows():
    evidence = [_item(t, atoms=(DRIFT,)) for t in (0, 1, 2, 5, 6, 10, 11, 12, 13)]
    assert quiet_runs(evidence) == (frozenset({DRIFT}), frozenset({DRIFT}))


def test_pulse_attribution_finds_the_onset_effect_and_ignores_drift():
    evidence = _history()
    active = [item for item in evidence if not item.is_passive]
    passive = [item for item in evidence if item.is_passive]
    estimates = atom_estimates(pulses_from(active, CHANNELS.get), quiet_runs(passive))
    caused = estimates[("channel.a",)][CAUSED]
    assert caused.agency >= 0.35 and caused.controllability > 0.0
    assert DRIFT not in estimates[("channel.a",)]
    registry = FootprintRegistry()
    registry.update(estimates)
    assert registry.footprint_of(("channel.a",)) == (footprint_id({CAUSED}), frozenset({CAUSED}))


def _estimate(agency):
    return AtomEstimate(CAUSED, controllability=0.2, agency=agency, pulses=8, quiet_runs=8)


def test_membership_has_hysteresis():
    registry = FootprintRegistry(enter=0.35, hysteresis=0.05)
    registry.update({("channel.a",): {CAUSED: _estimate(0.33)}})
    assert registry.footprint_of(("channel.a",)) is None  # below entry
    registry.update({("channel.a",): {CAUSED: _estimate(0.36)}})
    registry.update({("channel.a",): {CAUSED: _estimate(0.32)}})
    assert registry.footprint_of(("channel.a",)) is not None  # above exit
    registry.update({("channel.a",): {CAUSED: _estimate(0.29)}})
    assert registry.footprint_of(("channel.a",)) is None


def test_pinned_footprints_survive_decay_and_bounds():
    registry = FootprintRegistry(max_footprints=1)
    registry.update({("channel.a",): {CAUSED: _estimate(0.5)}})
    fid, _ = registry.footprint_of(("channel.a",))
    registry.pin(fid)
    registry.update({("channel.a",): {CAUSED: _estimate(0.0)}})
    registry.update({("channel.b",): {DRIFT: AtomEstimate(DRIFT, 0.2, 0.9, 8, 8)}})
    assert registry.footprint_of(("channel.a",))[0] == fid


def test_registry_checkpoint_round_trips():
    registry = FootprintRegistry()
    registry.update({("channel.a",): {CAUSED: _estimate(0.5)}})
    registry.pin(footprint_id({CAUSED}))
    restored = FootprintRegistry.restore(registry.checkpoint())
    assert restored.checkpoint() == registry.checkpoint()
