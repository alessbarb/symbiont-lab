"""Regression (ADR-0010 Gate I): telemetry snapshots used to call checkpoint(),
which recorded them as save events, so observation density changed the parent
hash of later real saves."""

from __future__ import annotations

from symbiont.core.orchestration.runtime import OrganismRuntime


def test_observer_read_does_not_change_later_save_lineage() -> None:
    quiet = OrganismRuntime(organism_id="lineage")
    observed = OrganismRuntime(organism_id="lineage")
    quiet.checkpoint()
    observed.checkpoint()

    peek = observed.checkpoint(advance_lineage=False)
    observed.checkpoint(advance_lineage=False)

    assert peek["checkpoint_lineage"]["checkpoint_id"] == quiet.state_hash()
    assert observed.checkpoint()["checkpoint_lineage"] == quiet.checkpoint()["checkpoint_lineage"]
