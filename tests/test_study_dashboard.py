from symbiont.dashboard import StudyDashboardState, _parse_seeds
from symbiont.experiment import ExperimentSpec
from symbiont.study import run_comparative_study


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


def test_study_dashboard_state_tracks_progress_and_result():
    state = StudyDashboardState()
    assert state.start({"title": "test"}, 4)
    assert not state.start({"title": "other"}, 2)
    state.progress(2, 4, "baseline", 7)
    payload = state.payload()
    assert payload["running"]
    assert payload["completed"] == 2
    assert payload["phase"] == "baseline"
    state.fail(RuntimeError("boom"))
    assert state.payload()["error"] == "RuntimeError: boom"


def test_study_dashboard_finish_adds_observer_interpretation():
    study = run_comparative_study(
        ExperimentSpec(hosts=6, steps=20),
        parameter="poison_fraction",
        baseline_value=0.0,
        variant_value=0.1,
        seeds=(1, 2, 3),
    )
    state = StudyDashboardState()
    assert state.start({"title": "test"}, 6)
    state.finish(study)
    payload = state.payload()

    assert payload["result"]["paired_deltas"]
    assert payload["interpretation"]["summary"]
    assert payload["interpretation"]["follow_up"]["parameter"] == "poison_fraction"


def test_dashboard_seed_parser_bounds_batch_size():
    assert _parse_seeds("1, 2,3") == (1, 2, 3)
    try:
        _parse_seeds(",".join(str(i) for i in range(51)))
    except ValueError as exc:
        assert "50 seeds" in str(exc)
    else:
        raise AssertionError("expected seed limit validation")
