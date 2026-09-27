"""Causal Provenance v1: contract, bounded frontier and durable journal."""

from __future__ import annotations

import json

import pytest

from symbiont.actuation.footprint import (
    AtomEstimate,
    FootprintRegistry,
    footprint_entity_id,
    snapshot_ref,
    version_ref,
)
from symbiont.provenance import CausalEvent, CausalRef, ProvenanceLog
from symbiont_lab.observation.provenance_journal import ProvenanceJournal

CAUSED = "effect.atom.caused"
OTHER = "effect.atom.other"
SOURCE = ("channel.a",)


def _estimate(atom, lower_bound, tick, commitments=("c1", "c2", "c3", "c4")):
    return AtomEstimate(
        atom,
        len(commitments),
        3,
        6.0,
        40,
        0,
        0.0,
        lower_bound,
        0.2,
        0.3,
        tick,
        tick,
        pulse_commitments=commitments,
        passive_tick_range=(0, tick),
    )


def test_event_ids_are_pure_and_round_trip():
    event = CausalEvent(
        tick=3,
        domain="d",
        operation="op",
        subject=CausalRef("k", "a"),
        caused_by=(CausalRef("k", "b"),),
        produced=(CausalRef("k", "a"),),
        rule="r",
        parameters={"x": 0.5},
    )
    again = CausalEvent.from_payload(json.loads(json.dumps(event.payload())))
    assert again == event and again.event_id == event.event_id
    tampered = {**event.payload(), "tick": 4}
    with pytest.raises(ValueError):
        CausalEvent.from_payload(tampered)
    with pytest.raises(ValueError):
        CausalEvent(
            tick=1,
            domain="d",
            operation="o",
            subject=CausalRef("k", "a"),
            caused_by=(),
            parameters={"raw": [1, 2]},
        )


def _registry(log):
    return FootprintRegistry(provenance=log)


def test_every_version_change_names_its_causes_down_to_pulses():
    log = ProvenanceLog()
    registry = _registry(log)
    registry.update({SOURCE: {CAUSED: _estimate(CAUSED, 0.5, 10)}}, tick=10)
    entity = footprint_entity_id(SOURCE)
    v1 = version_ref(entity, 1)
    (estimate,) = log.causes_of(v1)
    assert estimate.kind == "atom_estimate"
    causes = log.causes_of(estimate)
    assert CausalRef("commitment", "c1") in causes
    assert CausalRef("passive_windows", "t0-t10") in causes
    version_event = log.events()[-1]
    assert version_event.rule and version_event.parameters["entered"] == 1


def test_frontier_keeps_only_live_references():
    log = ProvenanceLog()
    registry = _registry(log)
    entity = footprint_entity_id(SOURCE)
    for tick in range(1, 30):
        lower = 0.5 if tick % 2 else 0.0
        registry.update({SOURCE: {CAUSED: _estimate(CAUSED, lower, tick)}}, tick=tick)
    live = log.live_refs()
    versions = [ref for ref in live if ref.kind == "footprint_version"]
    assert versions == [version_ref(entity, registry.version_of(SOURCE).version)]
    assert len(live) <= 2  # current version (+ its estimate when it has members)


def test_live_snapshot_is_explainable_from_journal_after_the_ring_wraps(tmp_path):
    log = ProvenanceLog(capacity=4)
    journal = ProvenanceJournal(tmp_path / "provenance.jsonl")
    log.subscribe(journal.append)
    registry = _registry(log)
    registry.update({SOURCE: {CAUSED: _estimate(CAUSED, 0.5, 10)}}, tick=10)
    content, _ = registry.footprint_of(SOURCE)
    registry.pin(content, tick=11)
    for tick in range(12, 40):
        atom = CAUSED if tick % 3 else OTHER
        registry.update({SOURCE: {atom: _estimate(atom, 0.5, tick)}}, tick=tick)
    snapshot = snapshot_ref(content)
    assert snapshot in log.live_refs()
    assert all(event.subject != snapshot for event in log.events())  # ring wrapped
    ancestors = journal.ancestors(snapshot)
    assert version_ref(footprint_entity_id(SOURCE), 1) in ancestors
    assert CausalRef("commitment", "c1") in ancestors


def test_restored_organism_emits_the_same_events_and_frontier():
    def run(registry, ticks):
        for tick in ticks:
            atom = CAUSED if tick % 3 else OTHER
            lower = 0.5 if tick % 4 else 0.0
            registry.update({SOURCE: {atom: _estimate(atom, lower, tick)}}, tick=tick)
            if tick == 5:
                registry.pin(registry.footprint_of(SOURCE)[0], tick=tick)

    log = ProvenanceLog()
    continuous = _registry(log)
    run(continuous, range(1, 20))
    restored_log = ProvenanceLog.restore(json.loads(json.dumps(log.checkpoint())))
    restored = FootprintRegistry.restore(
        json.loads(json.dumps(continuous.checkpoint())), provenance=restored_log
    )
    mark = len(log.events())
    run(continuous, range(20, 40))
    run(restored, range(20, 40))
    assert restored_log.events() == log.events()[mark:]
    assert restored_log.checkpoint()["frontier"] == log.checkpoint()["frontier"]
    assert restored.checkpoint() == continuous.checkpoint()


def test_emission_never_changes_registry_behaviour():
    silent, traced = FootprintRegistry(), FootprintRegistry(provenance=ProvenanceLog())
    for tick in range(1, 30):
        atom = CAUSED if tick % 3 else OTHER
        estimates = {SOURCE: {atom: _estimate(atom, 0.5 if tick % 4 else 0.0, tick)}}
        silent.update(estimates, tick=tick)
        traced.update(estimates, tick=tick)
    payload_silent, payload_traced = silent.checkpoint(), traced.checkpoint()
    payload_traced.pop("live_estimates")
    payload_silent.pop("live_estimates")
    assert payload_silent == payload_traced
