from symbiont.collective import CollectiveMemory
from symbiont.curiosity import CuriosityPlanner
from symbiont.reasoning import ReasoningEngine
from symbiont.simulation import run_simulation


def _unresolved_collective() -> CollectiveMemory:
    collective = CollectiveMemory()
    fp = "M-H-H-M-M"
    for index in range(8):
        collective.report(fp, index < 4, 0.85, f"source-{index}")
    # Add a neighboring pattern so the planner can compare known evidence.
    for index in range(6):
        collective.report("M-M-H-M-M", True, 0.80, f"neighbor-{index}")
    return collective


def test_curiosity_planner_ranks_shadow_only_counterfactuals():
    collective = _unresolved_collective()
    hypotheses = ReasoningEngine().analyze(collective)
    probes = CuriosityPlanner().plan(hypotheses, collective)

    assert probes
    assert all(0 <= probe.expected_information_gain <= 1 for probe in probes)
    assert all(0 <= probe.utility <= 1 for probe in probes)
    assert list(probes) == sorted(probes, key=lambda probe: (-probe.utility, probe.feature, probe.counterfactual_fingerprint))
    assert all("shadow-only" in probe.question for probe in probes)


def test_live_snapshots_publish_curiosity_agenda():
    snapshots = []
    result, _ = run_simulation(hosts=20, steps=120, seed=9, on_snapshot=snapshots.append)
    final = snapshots[-1]

    assert isinstance(final.curiosity_probes, tuple)
    assert 0 <= final.curiosity_focus <= 1
    assert result.curiosity_probes == len(final.curiosity_probes)
    assert result.top_probe_utility == final.curiosity_focus
