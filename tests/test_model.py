from symbiont.collective import CollectiveMemory
from symbiont.agent import Agent
from symbiont.model import Observation


def test_agent_learns_baseline_then_flags_disruptive_event():
    collective = CollectiveMemory()
    agent = Agent("a")
    normal = Observation(0.15, 0.12, 0.08, 0.05, 0.01)
    for step in range(40):
        agent.observe(step, normal, collective)

    abnormal = Observation(0.75, 0.88, 0.92, 0.70, 0.80, "pathogen:test")
    assessment = agent.observe(41, abnormal, collective)

    assert assessment.novelty > 0.5
    assert assessment.should_investigate
    assert agent.true_positive_investigations == 1


def test_collective_confidence_grows_with_diverse_sources():
    c = CollectiveMemory()
    for i in range(8):
        c.report("H-H-H-H-H", True, 0.9, f"agent-{i}")
    assert c.confidence("H-H-H-H-H") > 0.75
