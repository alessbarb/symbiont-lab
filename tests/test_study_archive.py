from symbiont.experiment import ExperimentSpec
from symbiont.interpretation import interpret_study
from symbiont.study import run_comparative_study
from symbiont.study_archive import StudyArchive


def _completed_study(title: str = "poison study"):
    spec = ExperimentSpec(title=title, hosts=6, steps=20)
    study = run_comparative_study(
        spec,
        parameter="poison_fraction",
        baseline_value=0.0,
        variant_value=0.1,
        seeds=(1, 2),
        title=title,
    )
    return spec, study, interpret_study(study)


def test_study_archive_round_trip_preserves_interpretation_and_parent(tmp_path):
    archive = StudyArchive(tmp_path / "studies.jsonl")
    spec, study, interpretation = _completed_study()

    root = archive.append(spec, study, interpretation, source="test")
    child = archive.append(
        spec,
        study,
        interpretation,
        source="test",
        parent_record_id=root.record_id,
    )
    recent = archive.recent()

    assert len(recent) == 2
    assert recent[0].record_id == child.record_id
    assert recent[0].parent_record_id == root.record_id
    assert recent[0].study["parameter"] == "poison_fraction"
    assert recent[0].interpretation["summary"] == interpretation.summary


def test_study_archive_tolerates_corrupt_lines(tmp_path):
    path = tmp_path / "studies.jsonl"
    path.write_text("not-json\n", encoding="utf-8")
    archive = StudyArchive(path)
    spec, study, interpretation = _completed_study("valid")
    archive.append(spec, study, interpretation, source="test")

    recent = archive.recent()
    assert len(recent) == 1
    assert recent[0].study["title"] == "valid"


def test_study_archive_reconstructs_parent_lineage(tmp_path):
    archive = StudyArchive(tmp_path / "studies.jsonl")
    spec, study, interpretation = _completed_study()

    root = archive.append(spec, study, interpretation, source="test")
    child = archive.append(
        spec,
        study,
        interpretation,
        source="test",
        parent_record_id=root.record_id,
    )
    grandchild = archive.append(
        spec,
        study,
        interpretation,
        source="test",
        parent_record_id=child.record_id,
    )

    lineage = archive.lineage(grandchild.record_id)
    assert [record.record_id for record in lineage] == [
        grandchild.record_id,
        child.record_id,
        root.record_id,
    ]
