from symbiont.simulation import run_simulation
from symbiont_lab.archive.runs import ExperimentArchive
from symbiont_lab.experiments.spec import ExperimentSpec


def test_archive_round_trip_keeps_spec_and_final_metrics(tmp_path):
    archive = ExperimentArchive(tmp_path / "experiments.jsonl")
    spec = ExperimentSpec(
        title="Drift comparison",
        hypothesis="Novelty settles after adaptation",
        success_criteria="Recent drift FP declines",
        hosts=8,
        steps=20,
        seed=4,
    )
    result, _ = run_simulation(hosts=8, steps=20, seed=4)

    saved = archive.append(spec, result, source="test")
    recent = archive.recent()

    assert len(recent) == 1
    assert recent[0].record_id == saved.record_id
    assert recent[0].spec["title"] == "Drift comparison"
    assert recent[0].spec["hypothesis"] == "Novelty settles after adaptation"
    assert recent[0].metrics["detection_rate"] == result.detection_rate
    assert recent[0].metrics["top_probe_utility"] == result.top_probe_utility


def test_archive_tolerates_corrupt_lines(tmp_path):
    path = tmp_path / "experiments.jsonl"
    path.write_text("not-json\n", encoding="utf-8")
    archive = ExperimentArchive(path)
    result, _ = run_simulation(hosts=4, steps=5, seed=2)
    archive.append(ExperimentSpec(title="Valid"), result, source="test")

    recent = archive.recent()
    assert len(recent) == 1
    assert recent[0].spec["title"] == "Valid"
