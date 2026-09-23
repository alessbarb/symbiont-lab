import pytest

from symbiont.core.agent import Agent
from symbiont.core.collective import CollectiveMemory
from symbiont.core.memory import AgentMemory, Episode
from symbiont.core.model import Observation
from symbiont.simulation import run_simulation
from symbiont_lab.server.state import DashboardState


def test_observation_contains_no_ground_truth_label():
    obs = Observation(0.15, 0.12, 0.08, 0.05, 0.01)
    assert not hasattr(obs, "label")


def test_agent_learns_baseline_then_flags_disruptive_event():
    collective = CollectiveMemory()
    agent = Agent("a")
    normal = Observation(0.15, 0.12, 0.08, 0.05, 0.01)
    for step in range(40):
        agent.observe(step, normal, collective)

    abnormal = Observation(0.75, 0.88, 0.92, 0.70, 0.80)
    assessment = agent.observe(41, abnormal, collective)

    assert assessment.novelty > 0.5
    assert assessment.should_investigate
    assert agent.investigated == 1


def test_collective_separates_threat_belief_from_certainty():
    c = CollectiveMemory()
    for i in range(8):
        c.report("H-H-H-H-H", i < 4, 0.9, f"agent-{i}")

    threat, certainty = c.belief("H-H-H-H-H")

    assert threat == pytest.approx(0.5)
    assert certainty < 0.75
    assert c.open_questions(min_reports=4)


def test_collective_downranks_consistent_minority_inverter():
    c = CollectiveMemory()
    for pattern in range(14):
        fp = f"pattern-{pattern}"
        for i in range(7):
            c.report(fp, True, 0.9, f"honest-{i}")
        c.report(fp, False, 0.9, "inverter")
        c.recalibrate_sources()

    honest_mean = sum(c.trust(f"honest-{i}") for i in range(7)) / 7
    assert c.trust("inverter") < honest_mean
    assert c.trust("inverter") < 0.55


def test_memory_forgets_low_salience_and_consolidates_useful_episode():
    memory = AgentMemory(retention_steps=10)
    memory.remember(Episode(0, "L-L-L-L-L", 0.01, 0.02, False))
    memory.remember(Episode(0, "M-M-M-M-M", 0.30, 0.35, True))
    memory.forget(20)

    assert memory.forgotten == 1
    assert memory.consolidated == 1
    assert "M-M-M-M-M" in memory.concepts


def test_simulation_is_deterministic_and_nontrivial():
    first, _ = run_simulation(hosts=30, steps=140, seed=11)
    second, _ = run_simulation(hosts=30, steps=140, seed=11)

    assert first == second
    assert first.pathogen_events > 0
    assert first.false_positive_investigations > 0
    assert first.false_negatives > 0
    assert first.poisoned_agents > 0


def test_simulation_publishes_live_snapshots():
    snapshots = []
    result, _ = run_simulation(
        hosts=8,
        steps=20,
        seed=3,
        on_snapshot=snapshots.append,
    )

    assert len(snapshots) == 20
    assert snapshots[-1].step == result.steps
    assert snapshots[-1].investigated == result.investigated
    assert 0 <= snapshots[-1].mean_source_trust <= 1


def test_server_state_exposes_latest_history():
    state = DashboardState(max_points=2)
    state.start({"seed": 7})
    snapshots = []
    run_simulation(hosts=5, steps=3, seed=7, on_snapshot=snapshots.append)
    for snapshot in snapshots:
        state.add(snapshot)

    payload = state.payload()
    assert len(payload["history"]) == 2
    assert payload["current"]["step"] == 3
