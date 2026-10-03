"""Execution provenance: commitments name their intent and end once (Causal Provenance v1)."""

from __future__ import annotations

import copy

from lab.integration.organism import restore_canonical_organism
from lab.studies.learning.agency_acquisition_body import (
    CausalBody,
    build_subject,
    subject_lifecycle,
)
from symbiont.cognition.limits import KernelLimits
from symbiont.provenance import CausalRef


def _developed(ticks=400):
    body = CausalBody(actuator_count=4, seed=127)
    runtime = build_subject(body, organism_id="exec-prov", factorized_effects=True)
    for _ in range(ticks):
        runtime.tick()
        body.advance(runtime.last_actuations)
    return runtime, body


def test_commitments_are_traced_from_start_to_single_end():
    runtime, _ = _developed()
    events = runtime._action_domain.acquisition.provenance.events()
    starts = {e.subject for e in events if (e.domain, e.operation) == ("execution", "commit")}
    ends = [e.subject for e in events if (e.domain, e.operation) == ("execution", "end")]
    assert ends and len(ends) == len(set(ends))  # each commitment ends once
    assert set(ends) <= starts
    intent_commits = [
        e
        for e in events
        if e.operation == "commit" and any(ref.kind == "intent" for ref in e.caused_by)
    ]
    assert intent_commits  # admitted intents reach motor authority through a commitment
    satisfied = [e for e in events if e.operation == "satisfied"]
    for event in satisfied:
        commitment = next(ref for ref in event.caused_by if ref.kind == "commitment")
        assert commitment in starts


def _restored(runtime, body):
    twin_body = copy.deepcopy(body)
    twin = restore_canonical_organism(
        runtime.checkpoint(),
        host_lifecycle=subject_lifecycle(twin_body),
        host_reading_providers=(twin_body,),
        kernel_limits=KernelLimits(),
        bootstrap_semantic_senses=False,
        discover_senses=True,
        min_samples=1,
    )
    return twin, twin_body


def test_restored_continuations_emit_identical_provenance():
    runtime, body = _developed(300)
    first, first_body = _restored(runtime, body)
    second, second_body = _restored(runtime, body)
    for _ in range(150):
        for twin, twin_body in ((first, first_body), (second, second_body)):
            twin.tick()
            twin_body.advance(twin.last_actuations)
    a = first._action_domain.acquisition.provenance
    b = second._action_domain.acquisition.provenance
    assert a.events() == b.events() and a.events()
    assert a.checkpoint() == b.checkpoint()
    assert all(isinstance(ref, CausalRef) for ref in a.live_refs())
