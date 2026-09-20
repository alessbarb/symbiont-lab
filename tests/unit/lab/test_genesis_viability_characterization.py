from __future__ import annotations

from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.studies.world.genesis_viability import (
    run_genesis_viability_characterization,
)


def test_genesis_viability_characterization_is_deterministic():
    result = run_genesis_viability_characterization(
        seeds=(101,),
        steps=20,
        founders=2,
        width=4,
        height=4,
    )
    replay = run_genesis_viability_characterization(
        seeds=(101,),
        steps=20,
        founders=2,
        width=4,
        height=4,
    )
    assert result == replay
    assert result.replay_deterministic
    assert len(result.per_seed) == 1
    assert len(result.per_seed[0].founders) == 2


def test_genesis_viability_characterization_reports_physical_budgets():
    result = run_genesis_viability_characterization(
        seeds=(101,),
        steps=10,
        founders=1,
        width=3,
        height=3,
    )
    founder = result.per_seed[0].founders[0]

    assert founder.lifespan_ticks > 0
    assert founder.absorbed >= 0.0
    assert founder.motor_cost >= 0.0
    assert founder.basal_cost >= 0.0
    assert founder.basal_wear >= 0.0
    assert founder.deferred_damage >= 0.0
    assert founder.hazard_damage >= 0.0
    assert founder.move_count >= 0
    assert founder.hazard_exposure_count >= 0


def test_genesis_viability_protocol_is_registered():
    protocol = get_protocol("world.genesis-viability-characterization")
    result = protocol(
        seeds=(101,),
        steps=5,
        founders=1,
        width=2,
        height=2,
    )
    assert result.founders_per_seed == 1
    assert result.steps == 5
