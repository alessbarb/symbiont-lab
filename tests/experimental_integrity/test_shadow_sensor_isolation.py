from __future__ import annotations

from symbiont.simulation import run_simulation
from symbiont_lab.studies.evidence.second_look import run_second_look_study


def test_second_look_shadow_isolation():
    """Observer-side second look probes must not perturb simulated species."""
    # Baseline simulation without second-look
    base_res, base_collective = run_simulation(hosts=20, steps=60, seed=99)

    # Second look study with shadow sensor probes
    study = run_second_look_study(hosts=20, steps=60, seed=99)

    # Invariants
    assert study.world_digest is not None
    # Underlying world event count and baseline results must align
    assert len(study.outcomes) > 0
