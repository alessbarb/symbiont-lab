from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from symbiont.core.advisory import load_advisory_log
from symbiont.host.checkpoint import load_checkpoint_file, save_checkpoint_atomic

__all__ = [
    "OperatorJudgment",
    "AdvisoryEvaluationSummary",
    "record_operator_judgment",
    "evaluate_advisories",
    "evaluate_advisories_over_time",
]


class OperatorJudgment(StrEnum):
    """A real host operator's own judgment of one fired advisory — never
    synthesized, never inferred by the organism, never read back into
    :mod:`symbiont.core.advisory`'s trigger logic (roadmap v0.49). This is
    laboratory apparatus measuring the organism from the outside, the same
    separation `symbiont_lab`'s synthetic evaluator has always held toward
    `symbiont`'s cognition — applied here to a real host's advisories
    instead of a simulated pathogen's ground truth.
    """

    USEFUL = "useful"
    FALSE_ALARM = "false_alarm"
    UNKNOWN = "unknown"


@dataclass(slots=True, frozen=True)
class AdvisoryEvaluationSummary:
    """Purely descriptive measurement of fired advisories against real
    operator judgment — count and rate only, never a verdict about the
    organism's design and never a signal consumed by it."""

    total_fired: int
    total_labeled: int
    useful_count: int
    false_alarm_count: int
    unknown_count: int

    @property
    def usefulness_rate(self) -> float | None:
        """Fraction of *labeled* advisories the operator judged useful, or
        ``None`` when nothing has been labeled yet — never a manufactured
        rate from zero data."""
        if self.total_labeled == 0:
            return None
        return self.useful_count / self.total_labeled

    @property
    def false_alarm_rate(self) -> float | None:
        if self.total_labeled == 0:
            return None
        return self.false_alarm_count / self.total_labeled

    @property
    def label_coverage(self) -> float | None:
        """Fraction of *all fired* advisories that have been reviewed at
        all, labeled or not."""
        if self.total_fired == 0:
            return None
        return self.total_labeled / self.total_fired


def _advisory_key(advisory: dict[str, Any]) -> str:
    return f"{advisory['tick']}:{advisory['capability_id']}"


def record_operator_judgment(
    advisory_log_path: str | Path,
    labels_path: str | Path,
    *,
    tick: int,
    capability_id: str,
    judgment: OperatorJudgment,
    note: str | None = None,
) -> None:
    """Record a real operator's judgment of one specific fired advisory.

    Refuses to label an advisory that was never actually fired (identified
    by ``tick``/``capability_id`` matching an entry in ``advisory_log_path``)
    — a label can only ever attach to something the organism actually
    produced, never a hypothetical one. Storage is a separate file from the
    advisory log itself, written atomically (v0.46's primitive), so
    labeling can never corrupt or rewrite the organism's own record of what
    it advised.
    """
    fired = load_advisory_log(advisory_log_path)
    key = f"{tick}:{capability_id}"
    matched = next((entry for entry in fired if _advisory_key(entry) == key), None)
    if matched is None:
        raise ValueError(
            f"no fired advisory found for tick={tick!r}, capability_id={capability_id!r} in {advisory_log_path}"
        )

    labels = load_checkpoint_file(labels_path) or {"labels": {}}
    labels.setdefault("labels", {})
    labels["labels"][key] = {
        "tick": tick,
        "capability_id": capability_id,
        "summary": matched["summary"],
        "judgment": judgment.value,
        "note": note,
    }
    save_checkpoint_atomic(labels, labels_path)


def _load_labels(labels_path: str | Path) -> dict[str, dict[str, Any]]:
    payload = load_checkpoint_file(labels_path)
    if payload is None:
        return {}
    return payload.get("labels", {})


def evaluate_advisories(
    advisory_log_path: str | Path,
    labels_path: str | Path,
) -> AdvisoryEvaluationSummary:
    """Measure every advisory the organism has fired against whatever real
    operator judgments have been recorded for it (roadmap v0.49).

    This never feeds back into the organism: it only reads the advisory
    log and the separate labels file, and produces a summary a human (or a
    future study) can read. Nothing here is wired into
    :class:`~symbiont.core.advisory.DefensiveAdvisor`.
    """
    fired = load_advisory_log(advisory_log_path)
    labels = _load_labels(labels_path)

    useful = false_alarm = unknown = 0
    for advisory in fired:
        label = labels.get(_advisory_key(advisory))
        if label is None:
            continue
        judgment = label.get("judgment")
        if judgment == OperatorJudgment.USEFUL.value:
            useful += 1
        elif judgment == OperatorJudgment.FALSE_ALARM.value:
            false_alarm += 1
        elif judgment == OperatorJudgment.UNKNOWN.value:
            unknown += 1

    return AdvisoryEvaluationSummary(
        total_fired=len(fired),
        total_labeled=useful + false_alarm + unknown,
        useful_count=useful,
        false_alarm_count=false_alarm,
        unknown_count=unknown,
    )


def evaluate_advisories_over_time(
    advisory_log_path: str | Path,
    labels_path: str | Path,
    *,
    window_ticks: int,
) -> tuple[tuple[int, int, AdvisoryEvaluationSummary], ...]:
    """Bucket fired advisories into consecutive tick windows and summarize
    each independently, so a trend in usefulness/false-alarm rate over time
    is visible rather than collapsed into one lifetime number (roadmap
    v0.49's "how it adapts over time").

    Returns a tuple of ``(window_start_tick, window_end_tick, summary)`` in
    ascending order. A window with no fired advisories is omitted rather
    than reported as a manufactured zero.
    """
    if window_ticks < 1:
        raise ValueError("window_ticks must be at least 1")

    fired = load_advisory_log(advisory_log_path)
    labels = _load_labels(labels_path)
    if not fired:
        return ()

    buckets: dict[int, list[dict[str, Any]]] = {}
    for advisory in fired:
        bucket_index = (advisory["tick"] - 1) // window_ticks
        buckets.setdefault(bucket_index, []).append(advisory)

    results = []
    for bucket_index in sorted(buckets):
        bucket = buckets[bucket_index]
        useful = false_alarm = unknown = 0
        for advisory in bucket:
            label = labels.get(_advisory_key(advisory))
            if label is None:
                continue
            judgment = label.get("judgment")
            if judgment == OperatorJudgment.USEFUL.value:
                useful += 1
            elif judgment == OperatorJudgment.FALSE_ALARM.value:
                false_alarm += 1
            elif judgment == OperatorJudgment.UNKNOWN.value:
                unknown += 1
        summary = AdvisoryEvaluationSummary(
            total_fired=len(bucket),
            total_labeled=useful + false_alarm + unknown,
            useful_count=useful,
            false_alarm_count=false_alarm,
            unknown_count=unknown,
        )
        window_start = bucket_index * window_ticks + 1
        window_end = window_start + window_ticks - 1
        results.append((window_start, window_end, summary))

    return tuple(results)
