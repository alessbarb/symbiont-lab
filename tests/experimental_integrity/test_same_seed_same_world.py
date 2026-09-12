from __future__ import annotations

from symbiont.simulation import EventContext, run_simulation
from symbiont_lab.studies.common.digests import compute_world_digest


def test_identical_seed_produces_identical_world_digest():
    """Runs with the same seed must produce identical world event digests."""
    events_a: list[EventContext] = []
    events_b: list[EventContext] = []

    res_a, _ = run_simulation(hosts=20, steps=60, seed=42, on_event=events_a.append)
    res_b, _ = run_simulation(hosts=20, steps=60, seed=42, on_event=events_b.append)

    digest_a = compute_world_digest(events_a)
    digest_b = compute_world_digest(events_b)

    assert digest_a == digest_b
    assert res_a.pathogen_events == res_b.pathogen_events
    assert res_a.benign_events == res_b.benign_events
