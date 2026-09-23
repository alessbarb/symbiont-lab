from symbiont_lab.archive.studies import StudyArchive
from symbiont_lab.workbench.runs import StudyRunState, _parse_seeds
from symbiont_lab.experiments.spec import ExperimentSpec
from symbiont_lab.studies.campaigns.comparative import run_comparative_study
from symbiont_lab.studies.campaigns.interpretation import interpret_study


def test_study_progress_callback_reports_every_paired_run():
    events = []
    study = run_comparative_study(
        ExperimentSpec(hosts=6, steps=20),
        parameter="poison_fraction",
        baseline_value=0.0,
        variant_value=0.1,
        seeds=(1, 2, 3),
        on_progress=lambda *args: events.append(args),
    )
    assert len(events) == 6
    assert events[-1][0:2] == (6, 6)
    assert events[0][2] == "baseline"
    assert events[-1][2] == "variant"
    assert study.baseline.runs == 3


def test_study_server_state_tracks_progress_and_result():
    state = StudyRunState()
    assert state.start({"title": "test"}, 4)
    assert not state.start({"title": "other"}, 2)
    state.progress(2, 4, "baseline", 7)
    payload = state.payload()
    assert payload["running"]
    assert payload["completed"] == 2
    assert payload["phase"] == "baseline"
    state.fail(RuntimeError("boom"))
    assert state.payload()["error"] == "RuntimeError: boom"


def test_study_server_finish_adds_observer_interpretation():
    study = run_comparative_study(
        ExperimentSpec(hosts=6, steps=20),
        parameter="poison_fraction",
        baseline_value=0.0,
        variant_value=0.1,
        seeds=(1, 2, 3),
    )
    state = StudyRunState()
    assert state.start({"title": "test"}, 6)
    state.finish(study)
    payload = state.payload()

    assert payload["result"]["paired_deltas"]
    assert payload["interpretation"]["summary"]
    assert payload["interpretation"]["follow_up"]["parameter"] == "poison_fraction"


def test_study_server_payload_includes_record_and_campaign(tmp_path):
    archive = StudyArchive(tmp_path / "studies.jsonl")
    spec = ExperimentSpec(title="root", hosts=6, steps=20)
    study = run_comparative_study(
        spec,
        parameter="poison_fraction",
        baseline_value=0.0,
        variant_value=0.1,
        seeds=(1, 2),
        title="root",
    )
    interpretation = interpret_study(study)
    record = archive.append(spec, study, interpretation, source="test")

    state = StudyRunState(archive=archive)
    initial = state.payload()
    assert initial["records"][0]["record_id"] == record.record_id
    assert initial["campaigns"][record.record_id]["status"] == "continue"
    assert initial["campaigns"][record.record_id]["studies"] == 1

    assert state.start({"title": "child", "parent_record_id": record.record_id}, 4)
    state.finish(study, interpretation, record)
    payload = state.payload()
    assert payload["record_id"] == record.record_id
    assert payload["records"][0]["record_id"] == record.record_id
    assert payload["campaigns"][record.record_id]["proposal"] is not None


def test_dashboard_seed_parser_bounds_batch_size():
    assert _parse_seeds("1, 2,3") == (1, 2, 3)
    try:
        _parse_seeds(",".join(str(i) for i in range(51)))
    except ValueError as exc:
        assert "50 seeds" in str(exc)
    else:
        raise AssertionError("expected seed limit validation")
