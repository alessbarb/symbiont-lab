from symbiont.collective import CollectiveMemory
from symbiont.reasoning import ReasoningEngine
from symbiont.simulation import run_simulation


def test_reasoner_returns_only_aggregate_hypotheses():
    collective = CollectiveMemory()
    for i in range(6):
        collective.report("M-M-H-M-M", i < 3, 0.8, f"agent-{i}")
    hypotheses = ReasoningEngine().analyze(collective)
    assert hypotheses
    hypothesis = hypotheses[0]
    assert hypothesis.fingerprint == "M-M-H-M-M"
    assert hypothesis.questions
    assert 0 <= hypothesis.confidence <= 1
    assert 0 <= hypothesis.priority <= 1


def test_reasoning_is_deterministic_for_same_collective_state():
    collective = CollectiveMemory()
    for i in range(7):
        collective.report("L-H-M-M-M", i < 4, 0.7, f"agent-{i}")
    engine = ReasoningEngine()
    assert engine.analyze(collective) == engine.analyze(collective)


def test_live_snapshots_expose_bounded_hypotheses():
    snapshots = []
    run_simulation(hosts=30, steps=140, seed=11, on_snapshot=snapshots.append)
    assert snapshots
    assert isinstance(snapshots[-1].reasoning_hypotheses, tuple)
    assert 0 <= snapshots[-1].reasoning_priority <= 1
