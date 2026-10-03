from __future__ import annotations

from symbiont.cognition.structure import StructuralPlasticity


def test_explained_relation_consumes_stale_growth_evidence():
    plasticity = StructuralPlasticity(
        min_candidate_support=2,
        tentative_lifetime_ticks=8,
        cooldown_ticks=8,
    )
    for tick in range(4):
        plasticity.observe_coactivation(
            source_id="a",
            target_id="b",
            source_active=True,
            target_active=True,
            tick=tick,
        )

    before = plasticity.export_checkpoint()
    assert before["coactivation_counts"]

    plasticity.mark_relation_explained("a", "b")

    after = plasticity.export_checkpoint()
    assert after["coactivation_counts"] == []

    # If the relation later disappears, fresh evidence is required.
    plasticity.observe_coactivation(
        source_id="a",
        target_id="b",
        source_active=True,
        target_active=True,
        tick=10,
    )
    refreshed = plasticity.export_checkpoint()
    assert refreshed["coactivation_counts"][0]["count"] == 1
