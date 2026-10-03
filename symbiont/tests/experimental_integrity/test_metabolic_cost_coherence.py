"""Retention cost at full sensory capacity must stay within the basal budget.

Today it does not: one drift baseline costs 0.001 per tick and a canonical
organism may hold one per receptor, up to the sensory capacity, which is several
times the whole basal spend of a living organism. No result backs the current
prices; their recalibration is a pending experiment (canonical organism profile
register, §3). The test is a strict expected failure so the incoherence stays
declared, and fixing the prices forces this marker to be removed.
"""

from __future__ import annotations

import pytest

from symbiont.core.domains.memory import MemoryDomain
from symbiont.core.orchestration.runtime import OrganismRuntime
from symbiont.sensory.limits import SensoryLimits

from ..bodies import test_body_kwargs

TICKS = 20


def _basal_spend_per_tick() -> float:
    runtime = OrganismRuntime(**test_body_kwargs(), min_samples=1, investigate_ticks=0)
    before = runtime.living_body_state.energy_reserve
    runtime.run(TICKS)
    return (before - runtime.living_body_state.energy_reserve) / TICKS


@pytest.mark.xfail(
    strict=True,
    reason="retention prices not yet calibrated by experiment (ADR-0062 register §3)",
)
def test_retention_at_full_sensory_capacity_fits_the_basal_budget() -> None:
    capacity = SensoryLimits().max_active_sensors
    retention = MemoryDomain.retained_units(drift_baseline_count=capacity, cognitive_node_count=0)
    assert retention <= _basal_spend_per_tick()
