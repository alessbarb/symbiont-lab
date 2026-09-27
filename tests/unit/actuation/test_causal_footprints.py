"""Causal footprints from pulses (Factorized Effect Representation v1 §4.2, §13.4, §13.7)."""

from __future__ import annotations

from symbiont.actuation.evidence import CausalEvidence
from symbiont.actuation.footprint import (
    AtomEstimate,
    FootprintRegistry,
    TransitionKind,
    atom_estimates,
    footprint_entity_id,
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


def _estimates(evidence, tick=0):
    active = [item for item in evidence if not item.is_passive]
    passive = [item for item in evidence if item.is_passive]
    return atom_estimates(pulses_from(active, CHANNELS.get), passive, tick=tick)


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
    assert drift.hits == drift.pulses
    assert drift.expected_quiet_rate > 0.8
    registry = FootprintRegistry()
    registry.update({("channel.a",): estimates}, tick=1)
    _, atoms = registry.footprint_of(("channel.a",))
    assert CAUSED in atoms and DRIFT not in atoms


def test_weak_real_effects_enter_the_footprint():
    estimates = _estimates(_history(pulse_count=30))[("channel.a",)]
    assert estimates[WEAK].agency < 0.35  # the old agentic threshold would drop it
    registry = FootprintRegistry()
    registry.update({("channel.a",): estimates}, tick=1)
    assert WEAK in registry.footprint_of(("channel.a",))[1]


def test_every_member_is_explained_by_its_evidence_and_provenance():
    registry = FootprintRegistry()
    registry.update(_estimates(_history(), tick=500), tick=500)
    traces = {trace["atom"]: trace for trace in registry.explain(("channel.a",))}
    assert set(traces) == {CAUSED, WEAK}
    trace = traces[CAUSED]
    assert trace["pulses"] == 12 and trace["hits"] == 12
    assert trace["expected_quiet_rate"] == 0.0
    assert trace["contrast"] == trace["pulse_rate_lower_bound"] > 0.05
    assert trace["controllability"] > 0.0 and trace["agency"] > 0.0
    assert trace["estimated_tick"] == 500 and trace["entered_tick"] == 500
    assert trace["last_pulse_tick"] > 0
    assert trace["entity_id"] == footprint_entity_id(("channel.a",)) and trace["version"] == 1


def _estimate(lower_bound, *, atom=CAUSED, pulses=8, tick=0):
    return AtomEstimate(atom, pulses, 4, 6.0, 40, 0, 0.0, lower_bound, 0.2, 0.3, tick, tick)


def test_every_membership_change_is_a_traced_transition_with_its_rule():
    registry = FootprintRegistry(enter_margin=0.05, exit_margin=0.0)
    source = ("channel.a",)
    registry.update({source: {CAUSED: _estimate(0.04)}}, tick=1)  # below entry
    registry.update({source: {CAUSED: _estimate(0.06)}}, tick=2)  # enters
    registry.update({source: {CAUSED: _estimate(0.02)}}, tick=3)  # retained (hysteresis)
    registry.update({source: {CAUSED: _estimate(0.0)}}, tick=4)  # exits
    kinds = [(t.kind, t.tick, t.margin, t.previous_member) for t in registry.transitions()]
    assert kinds == [
        (TransitionKind.ENTER, 2, 0.05, False),
        (TransitionKind.EXIT, 4, 0.0, True),
    ]
    enter, leave = registry.transitions()
    assert enter.footprint_before is None and enter.footprint_after == footprint_id({CAUSED})
    assert leave.footprint_before == footprint_id({CAUSED}) and leave.footprint_after is None
    assert enter.estimate.pulse_rate_lower_bound == 0.06
    assert enter.entity_id == leave.entity_id == footprint_entity_id(source)
    assert (enter.version, leave.version) == (1, 2)


def test_entity_identity_is_stable_while_content_identity_follows_membership():
    registry = FootprintRegistry()
    source = ("channel.a",)
    registry.update({source: {CAUSED: _estimate(0.5)}}, tick=1)
    first, _ = registry.footprint_of(source)
    registry.update({source: {CAUSED: _estimate(0.5), WEAK: _estimate(0.5, atom=WEAK)}}, tick=2)
    second, _ = registry.footprint_of(source)
    assert first != second
    assert {t.entity_id for t in registry.transitions()} == {footprint_entity_id(source)}
    # Content identity depends on atoms only, never on the evidence values.
    registry.update({source: {CAUSED: _estimate(0.9), WEAK: _estimate(0.7, atom=WEAK)}}, tick=3)
    assert registry.footprint_of(source)[0] == second


def test_too_few_pulses_never_enter():
    registry = FootprintRegistry(min_pulses=4)
    registry.update({("channel.a",): {CAUSED: _estimate(0.9, pulses=3)}}, tick=1)
    assert registry.footprint_of(("channel.a",)) is None


def test_pinned_content_keeps_resolving_as_a_distinct_snapshot():
    registry = FootprintRegistry()
    source = ("channel.a",)
    registry.update({source: {CAUSED: _estimate(0.5, tick=10)}}, tick=10)
    fid, atoms = registry.footprint_of(source)
    registry.pin(fid, tick=11)
    registry.update({source: {CAUSED: _estimate(0.0, tick=20)}}, tick=20)  # evidence gone
    assert registry.footprint_of(source) is None  # membership reflects current evidence
    assert registry.resolve(fid) == atoms  # the reference still resolves
    snapshot = registry.explain_pin(fid)
    assert snapshot["pinned_tick"] == 11 and snapshot["still_current"] is False
    assert snapshot["members_at_pin"][0]["estimate"]["estimated_tick"] == 10
    registry.unpin(fid, tick=21)
    assert registry.resolve(fid) is None
    assert [t.kind for t in registry.transitions()] == [
        TransitionKind.ENTER,
        TransitionKind.PIN,
        TransitionKind.EXIT,
        TransitionKind.UNPIN,
    ]


def test_bound_evicts_unpinned_footprints_with_a_trace():
    registry = FootprintRegistry(max_footprints=1)
    registry.update({("channel.a",): {CAUSED: _estimate(0.5)}}, tick=1)
    fid, _ = registry.footprint_of(("channel.a",))
    registry.pin(fid, tick=1)
    registry.update({("channel.b",): {DRIFT: _estimate(0.9, atom=DRIFT)}}, tick=2)
    assert registry.footprint_of(("channel.a",))[0] == fid
    assert registry.footprint_of(("channel.b",)) is None
    assert registry.transitions()[-1].kind is TransitionKind.EVICT


def test_restored_registry_continues_the_same_causal_history():
    def run(registry, ticks):
        for tick in ticks:
            lb = 0.2 if tick % 7 < 4 else 0.0
            registry.update(
                {
                    ("channel.a",): {CAUSED: _estimate(lb, tick=tick)},
                    ("channel.b",): {WEAK: _estimate(0.06 if tick % 3 else 0.0, atom=WEAK)},
                },
                tick=tick,
            )
            if tick == 10:
                fid, _ = registry.footprint_of(("channel.a",))
                registry.pin(fid, tick=tick)

    continuous = FootprintRegistry()
    run(continuous, range(20))
    restored = FootprintRegistry.restore(continuous.checkpoint())
    assert restored.checkpoint() == continuous.checkpoint()
    run(continuous, range(20, 40))
    run(restored, range(20, 40))
    assert restored.transitions() == continuous.transitions()
    assert restored.footprints == continuous.footprints
    assert restored.checkpoint() == continuous.checkpoint()


def test_checkpoint_keeps_each_estimate_bound_to_its_atom():
    registry = FootprintRegistry()
    registry.update(_estimates(_history()), tick=3)
    payload = registry.checkpoint()
    for member in payload["members"]:
        for record in member["records"]:
            assert record["atom"] == record["estimate"]["atom"]
    payload["members"][0]["records"][0]["estimate"]["atom"] = "effect.atom.other"
    import pytest

    with pytest.raises(ValueError):
        FootprintRegistry.restore(payload)


def test_wilson_bound():
    assert wilson_lower_bound(0, 10) == 0.0
    assert 0.0 < wilson_lower_bound(5, 10) < 0.5 < wilson_lower_bound(10, 10)


def test_estimates_carry_their_ancestry():
    evidence = _history()
    estimate = _estimates(evidence, tick=99)[("channel.a",)][CAUSED]
    passive_ticks = [item.observation_tick for item in evidence if item.is_passive]
    assert estimate.pulse_commitments == tuple(f"c{index:02d}" for index in range(12))
    assert estimate.passive_tick_range == (min(passive_ticks), max(passive_ticks))
    assert estimate.estimated_tick == 99


def test_versions_name_entity_version_and_content_separately():
    registry = FootprintRegistry()
    source = ("channel.a",)
    assert registry.version_of(source) is None
    registry.update({source: {CAUSED: _estimate(0.5)}}, tick=5)
    first = registry.version_of(source)
    registry.update({source: {CAUSED: _estimate(0.0)}}, tick=9)
    second = registry.version_of(source)
    assert first.entity_id == second.entity_id == footprint_entity_id(source)
    assert (first.version, first.since_tick, first.content_id) == (1, 5, footprint_id({CAUSED}))
    assert (second.version, second.since_tick, second.content_id, second.atoms) == (
        2,
        9,
        None,
        frozenset(),
    )


def test_pinned_snapshot_survives_restore_and_later_versions_exactly():
    import json

    source = ("channel.a",)
    registry = FootprintRegistry()
    registry.update({source: {CAUSED: _estimate(0.5, tick=10)}}, tick=10)
    pinned, atoms = registry.footprint_of(source)
    registry.pin(pinned, tick=11)
    snapshot_before = registry.explain_pin(pinned)

    restored = FootprintRegistry.restore(json.loads(json.dumps(registry.checkpoint())))
    for other in (registry, restored):
        other.update(
            {source: {CAUSED: _estimate(0.5, tick=20), WEAK: _estimate(0.5, atom=WEAK, tick=20)}},
            tick=20,
        )
        other.update({source: {WEAK: _estimate(0.5, atom=WEAK, tick=30)}}, tick=30)
        other.update({source: {DRIFT: _estimate(0.5, atom=DRIFT, tick=40)}}, tick=40)

    for other in (registry, restored):
        assert other.version_of(source).version == 4
        assert other.resolve(pinned) == atoms  # the old content still resolves exactly
        assert other.footprint_of(source)[1] == frozenset({DRIFT})  # current is independent
        snapshot = other.explain_pin(pinned)
        assert snapshot["still_current"] is False
        assert snapshot["members_at_pin"] == snapshot_before["members_at_pin"]
    assert restored.transitions() == registry.transitions()
    assert restored.checkpoint() == registry.checkpoint()
