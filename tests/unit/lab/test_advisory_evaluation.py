from __future__ import annotations

import pytest
from symbiont.core.advisory import AdvisorySignal, DefensiveAdvisory, append_advisories_to_log

from symbiont_lab.evaluation.advisory_evaluation import (
    OperatorJudgment,
    evaluate_advisories,
    evaluate_advisories_over_time,
    record_operator_judgment,
)


def _advisory(tick: int, capability_id: str) -> DefensiveAdvisory:
    return DefensiveAdvisory(
        tick=tick,
        capability_id=capability_id,
        signals=(AdvisorySignal(kind="persistent_deviation", detail="x"),),
        summary=f"{capability_id} review at tick {tick}",
    )


def test_evaluate_with_no_advisories_and_no_labels(tmp_path):
    log_path = tmp_path / "advisories.json"
    labels_path = tmp_path / "labels.json"

    summary = evaluate_advisories(log_path, labels_path)

    assert summary.total_fired == 0
    assert summary.total_labeled == 0
    assert summary.usefulness_rate is None
    assert summary.false_alarm_rate is None
    assert summary.label_coverage is None


def test_record_judgment_rejects_advisory_that_never_fired(tmp_path):
    log_path = tmp_path / "advisories.json"
    labels_path = tmp_path / "labels.json"
    append_advisories_to_log((_advisory(1, "cpu"),), log_path)

    with pytest.raises(ValueError):
        record_operator_judgment(
            log_path, labels_path, tick=99, capability_id="nope", judgment=OperatorJudgment.USEFUL
        )


def test_record_and_evaluate_a_single_useful_judgment(tmp_path):
    log_path = tmp_path / "advisories.json"
    labels_path = tmp_path / "labels.json"
    append_advisories_to_log((_advisory(1, "cpu"),), log_path)

    record_operator_judgment(
        log_path, labels_path, tick=1, capability_id="cpu", judgment=OperatorJudgment.USEFUL
    )
    summary = evaluate_advisories(log_path, labels_path)

    assert summary.total_fired == 1
    assert summary.total_labeled == 1
    assert summary.useful_count == 1
    assert summary.usefulness_rate == pytest.approx(1.0)
    assert summary.false_alarm_rate == pytest.approx(0.0)
    assert summary.label_coverage == pytest.approx(1.0)


def test_unlabeled_advisories_are_not_counted_as_labeled(tmp_path):
    log_path = tmp_path / "advisories.json"
    labels_path = tmp_path / "labels.json"
    append_advisories_to_log((_advisory(1, "cpu"), _advisory(2, "disk")), log_path)

    record_operator_judgment(
        log_path, labels_path, tick=1, capability_id="cpu", judgment=OperatorJudgment.USEFUL
    )
    summary = evaluate_advisories(log_path, labels_path)

    assert summary.total_fired == 2
    assert summary.total_labeled == 1
    assert summary.label_coverage == pytest.approx(0.5)


def test_unknown_judgment_counts_as_labeled_but_not_useful_or_false_alarm(tmp_path):
    log_path = tmp_path / "advisories.json"
    labels_path = tmp_path / "labels.json"
    append_advisories_to_log((_advisory(1, "cpu"),), log_path)

    record_operator_judgment(
        log_path, labels_path, tick=1, capability_id="cpu", judgment=OperatorJudgment.UNKNOWN
    )
    summary = evaluate_advisories(log_path, labels_path)

    assert summary.total_labeled == 1
    assert summary.unknown_count == 1
    assert summary.useful_count == 0
    assert summary.false_alarm_count == 0


def test_relabeling_the_same_advisory_overwrites_the_judgment(tmp_path):
    log_path = tmp_path / "advisories.json"
    labels_path = tmp_path / "labels.json"
    append_advisories_to_log((_advisory(1, "cpu"),), log_path)

    record_operator_judgment(
        log_path, labels_path, tick=1, capability_id="cpu", judgment=OperatorJudgment.USEFUL
    )
    record_operator_judgment(
        log_path, labels_path, tick=1, capability_id="cpu", judgment=OperatorJudgment.FALSE_ALARM
    )

    summary = evaluate_advisories(log_path, labels_path)
    assert summary.total_labeled == 1
    assert summary.useful_count == 0
    assert summary.false_alarm_count == 1


def test_note_is_stored_alongside_judgment(tmp_path):
    log_path = tmp_path / "advisories.json"
    labels_path = tmp_path / "labels.json"
    append_advisories_to_log((_advisory(1, "cpu"),), log_path)

    record_operator_judgment(
        log_path,
        labels_path,
        tick=1,
        capability_id="cpu",
        judgment=OperatorJudgment.USEFUL,
        note="caught a real leak",
    )

    from symbiont.host.checkpoint import load_checkpoint_file

    labels = load_checkpoint_file(labels_path)
    assert labels["labels"]["1:cpu"]["note"] == "caught a real leak"


def test_evaluate_over_time_rejects_non_positive_window():
    with pytest.raises(ValueError):
        evaluate_advisories_over_time("x", "y", window_ticks=0)


def test_evaluate_over_time_omits_empty_windows(tmp_path):
    log_path = tmp_path / "advisories.json"
    labels_path = tmp_path / "labels.json"
    append_advisories_to_log(
        (_advisory(1, "cpu"), _advisory(3, "disk"), _advisory(12, "cpu")), log_path
    )

    windows = evaluate_advisories_over_time(log_path, labels_path, window_ticks=5)

    starts = [start for start, _end, _summary in windows]
    assert starts == [1, 11]  # ticks 6-10 fired nothing, correctly omitted


def test_evaluate_over_time_buckets_correctly(tmp_path):
    log_path = tmp_path / "advisories.json"
    labels_path = tmp_path / "labels.json"
    append_advisories_to_log((_advisory(1, "cpu"), _advisory(5, "disk")), log_path)
    record_operator_judgment(
        log_path, labels_path, tick=1, capability_id="cpu", judgment=OperatorJudgment.USEFUL
    )

    windows = evaluate_advisories_over_time(log_path, labels_path, window_ticks=5)

    assert len(windows) == 1
    start, end, summary = windows[0]
    assert (start, end) == (1, 5)
    assert summary.total_fired == 2
    assert summary.useful_count == 1


def test_evaluate_over_time_empty_log_returns_empty_tuple(tmp_path):
    assert (
        evaluate_advisories_over_time(
            tmp_path / "missing.json", tmp_path / "labels.json", window_ticks=5
        )
        == ()
    )


def test_summary_exposes_no_classification_field():
    """Same discipline as everywhere else: count/rate only, never a verdict
    about the organism (ADR-0003)."""
    from symbiont_lab.evaluation.advisory_evaluation import AdvisoryEvaluationSummary

    summary = AdvisoryEvaluationSummary(
        total_fired=0, total_labeled=0, useful_count=0, false_alarm_count=0, unknown_count=0
    )
    public_attrs = {name for name in dir(summary) if not name.startswith("_")}
    assert public_attrs <= {
        "total_fired",
        "total_labeled",
        "useful_count",
        "false_alarm_count",
        "unknown_count",
        "usefulness_rate",
        "false_alarm_rate",
        "label_coverage",
    }
