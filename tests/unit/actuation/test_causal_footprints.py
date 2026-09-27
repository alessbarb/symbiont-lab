"""Causal footprints from pulses (Factorized Effect Representation v1 §4.2, §13.4, §13.7)."""

from __future__ import annotations

from dataclasses import replace

from symbiont.actuation.evidence import CausalEvidence
from symbiont.actuation.footprint import (
    AtomEstimate,
    FootprintRegistry,
    atom_estimates,
    footprint_id,
    pulses_from,
    wilson_lower_bound,
)

CAUSED = "effect.atom.caused"
WEAK = "effect.atom.weak"
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


def _history(pulse_count=12):
    """Pulses of 6 windows; quiet runs of 4.  Drift happens once per 4 ticks anyway."""
    evidence, tick = [], 0
    for index in range(pulse_count):
        for step in range(6):
            atoms = set()
            if step == 0:
                atoms.add(CAUSED)  # onset effect, every pulse
                if index % 4 == 0:
                    atoms.add(WEAK)  # a real but weak effect: a quarter of the pulses
            if step == 3:
                atoms.add(DRIFT)
            evidence.append(_item(tick, commitment=f"c{index:02d}", signature="sig.a", atoms=atoms))
            tick += 1
        for step in range(4):
            evidence.append(_item(tick, atoms=(DRIFT,) if step == 1 else ()))
            tick += 1
    return evidence


def _estimates(evidence):
    active = [item for item in evidence if not item.is_passive]
    passive = [item for item in evidence if item.is_passive]
    return atom_estimates(pulses_from(active, CHANNELS.get), passive)


def test_pulses_are_commitments_on_one_channel_set():
    evidence = [
        *[_item(t, commitment="c1", signature="sig.a", atoms=(CAUSED,)) for t in range(4)],
        _item(4, commitment="c2", signature="sig.a"),  # too short
        _item(5, commitment="c3", signature="sig.a"),
        _item(6, commitment="c3", signature="sig.b"),
        _item(7, commitment="c3", signature="sig.b"),  # two channel sets: coordination
    ]
    (pulse,) = pulses_from(evidence, CHANNELS.get)
    assert pulse.source == ("channel.a",) and pulse.windows == 4
    assert pulse.commitment_id == "c1"


def test_length_matched_baseline_rejects_drift_that_pulses_merely_last_longer_for():
    estimates = _estimates(_history())[("channel.a",)]
    drift = estimates[DRIFT]
    # Drift occurs in every 6-window pulse and once per 4 quiet windows: a
    # naive pulse-vs-run comparison would call it caused.
    assert drift.hits == drift.pulses
    assert drift.expected_quiet_rate > 0.8
    registry = FootprintRegistry()
    registry.update({("channel.a",): estimates})
    _, atoms = registry.footprint_of(("channel.a",))
    assert CAUSED in atoms and DRIFT not in atoms


def test_weak_real_effects_enter_the_footprint():
    estimates = _estimates(_history(pulse_count=30))[("channel.a",)]
    assert estimates[WEAK].agency < 0.35  # the old agentic threshold would drop it
    registry = FootprintRegistry()
    registry.update({("channel.a",): estimates})
    assert WEAK in registry.footprint_of(("channel.a",))[1]


def test_every_member_is_explained_by_its_evidence():
    registry = FootprintRegistry()
    registry.update(_estimates(_history()))
    traces = {trace["atom"]: trace for trace in registry.explain(("channel.a",))}
    assert set(traces) == {CAUSED, WEAK}
    trace = traces[CAUSED]
    assert trace["pulses"] == 12 and trace["hits"] == 12
    assert trace["expected_quiet_rate"] == 0.0
    assert trace["contrast"] == trace["pulse_rate_lower_bound"] > 0.05
    assert trace["controllability"] > 0.0 and trace["agency"] > 0.0


def _estimate(lower_bound, *, pulses=8):
    return AtomEstimate(CAUSED, pulses, 4, 6.0, 40, 0, 0.0, lower_bound, 0.2, 0.3)


def test_membership_has_hysteresis_on_the_margin():
    registry = FootprintRegistry(enter_margin=0.05, exit_margin=0.0)
    registry.update({("channel.a",): {CAUSED: _estimate(0.04)}})
    assert registry.footprint_of(("channel.a",)) is None  # below entry
    registry.update({("channel.a",): {CAUSED: _estimate(0.06)}})
    registry.update({("channel.a",): {CAUSED: _estimate(0.02)}})
    assert registry.footprint_of(("channel.a",)) is not None  # above exit
    registry.update({("channel.a",): {CAUSED: _estimate(0.0)}})
    assert registry.footprint_of(("channel.a",)) is None


def test_too_few_pulses_never_enter():
    registry = FootprintRegistry(min_pulses=4)
    registry.update({("channel.a",): {CAUSED: _estimate(0.9, pulses=3)}})
    assert registry.footprint_of(("channel.a",)) is None


def test_pinned_footprints_keep_resolving_and_survive_bounds():
    registry = FootprintRegistry(max_footprints=1)
    registry.update({("channel.a",): {CAUSED: _estimate(0.5)}})
    fid, atoms = registry.footprint_of(("channel.a",))
    registry.pin(fid)
    registry.update({("channel.a",): {CAUSED: _estimate(0.0)}})
    other = replace(_estimate(0.9), atom=DRIFT)
    registry.update({("channel.b",): {DRIFT: other}})
    assert registry.footprint_of(("channel.a",)) == (fid, atoms)


def test_wilson_bound_and_checkpoint_round_trip():
    assert wilson_lower_bound(0, 10) == 0.0
    assert 0.0 < wilson_lower_bound(5, 10) < 0.5 < wilson_lower_bound(10, 10)
    registry = FootprintRegistry()
    registry.update(_estimates(_history()))
    registry.pin(footprint_id({CAUSED}))
    restored = FootprintRegistry.restore(registry.checkpoint())
    assert restored.checkpoint() == registry.checkpoint()
    assert restored.explain(("channel.a",)) == registry.explain(("channel.a",))
