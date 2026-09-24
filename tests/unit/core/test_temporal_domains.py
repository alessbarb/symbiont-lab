from __future__ import annotations

from symbiont.core.physiology import LivingBodyState
from symbiont.core.runtime import OrganismRuntime


def _old_symbiont_with_fresh_body(*, symbiont_tick: int = 10_000) -> OrganismRuntime:
    body = LivingBodyState(
        energy_reserve=10_000.0,
        max_energy=10_000.0,
        growth_progress=1.0,
        age_ticks=0,
    )
    return OrganismRuntime(
        tick_count=symbiont_tick,
        living_body_state=body,
        discover_senses=False,
        bootstrap_semantic_senses=False,
        interoception_enabled=False,
        investigate_ticks=0,
        min_samples=1,
    )


def test_old_symbiont_can_occupy_a_biologically_new_body() -> None:
    runtime = _old_symbiont_with_fresh_body()

    assert runtime.tick_count == 10_000
    assert runtime.living_body_state.age_ticks == 0
    assert runtime.living_body_state.senescence == 0.0

    runtime.tick()

    assert runtime.tick_count == 10_001
    assert runtime.living_body_state.age_ticks == 1
    assert runtime.living_body_state.senescence == 0.0


def test_same_body_resume_preserves_local_age_independently_of_symbiont_tick() -> None:
    runtime = _old_symbiont_with_fresh_body(symbiont_tick=50_000)
    runtime.run(3)
    checkpoint = runtime.checkpoint()

    assert checkpoint["saved_at_tick"] == 50_003
    assert checkpoint["living_body"]["age_ticks"] == 3

    restored = OrganismRuntime.from_checkpoint(
        checkpoint,
        discover_senses=False,
        bootstrap_semantic_senses=False,
        interoception_enabled=False,
        investigate_ticks=0,
        min_samples=1,
    )

    assert restored.tick_count == 50_003
    assert restored.living_body_state.age_ticks == 3

    restored.tick()

    assert restored.tick_count == 50_004
    assert restored.living_body_state.age_ticks == 4


def test_symbiont_historical_time_does_not_trigger_body_senescence() -> None:
    runtime = _old_symbiont_with_fresh_body(symbiont_tick=1_000_000)

    runtime.run(8)

    assert runtime.tick_count == 1_000_008
    assert runtime.living_body_state.age_ticks == 8
    assert runtime.living_body_state.senescence == 0.0
