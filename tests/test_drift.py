import random

from symbiont.agent import Agent
from symbiont.collective import CollectiveMemory
from symbiont.model import Observation
from symbiont.simulation import run_simulation
from symbiont.world import apply_regime_shift, make_profiles


def test_regime_shift_changes_only_selected_synthetic_profiles():
    rng = random.Random(4)
    profiles = make_profiles(10, rng)
    before = [(p.cpu, p.network, p.file_changes, p.new_processes) for p in profiles]
    selected = apply_regime_shift(profiles, rng, fraction=0.3, magnitude=0.25)

    assert len(selected) == 3
    for index, profile in enumerate(profiles):
        after = (profile.cpu, profile.network, profile.file_changes, profile.new_processes)
        assert (after != before[index]) == (index in selected)


def test_agent_adapts_to_sustained_low_risk_novel_regime_without_labels():
    collective = CollectiveMemory()
    agent = Agent("adaptive")
    normal = Observation(0.15, 0.12, 0.08, 0.05, 0.01)
    shifted = Observation(0.22, 0.80, 0.45, 0.25, 0.04)

    for step in range(40):
        agent.observe(step, normal, collective)
    for step in range(40, 55):
        agent.observe(step, shifted, collective)

    assert agent.drift_adaptations > 0


def test_simulation_exposes_changing_world_metrics():
    snapshots = []
    result, _ = run_simulation(
        hosts=20,
        steps=130,
        seed=21,
        drift_step=60,
        drift_fraction=0.5,
        drift_magnitude=0.30,
        on_snapshot=snapshots.append,
    )

    assert result.drifted_hosts == 10
    assert result.drift_adaptations >= 0
    assert 0 <= result.drift_false_positive_rate <= 1
    assert 0 <= result.recent_drift_false_positive_rate <= 1
    assert not snapshots[40].drift_active
    assert snapshots[-1].drift_active
    assert snapshots[-1].drifted_hosts == 10
