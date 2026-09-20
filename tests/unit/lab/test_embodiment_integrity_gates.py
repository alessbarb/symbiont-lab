from __future__ import annotations

from symbiont_lab.studies.embodiment.integrity_gates import (
    run_embodiment_integrity_gates,
)


def test_embodiment_campaign_integrity_gates_pass_on_clean_runtime():
    gates = run_embodiment_integrity_gates(
        organism_id="gate-test-subject",
        world_seed=12345,
    )

    assert gates.clean_runtime_boundary
    assert gates.clean_actuation_boundary
    assert gates.symbiont_step_surface_clean
    assert gates.germline_surface_clean
    assert gates.genome_germline_present
    assert gates.no_world_identity_in_genome
    assert gates.all_pass
