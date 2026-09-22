from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING

from .metrics import brier_score, expected_calibration_error, rate

if TYPE_CHECKING:
    from symbiont.core.foundation.model import Assessment


@dataclass(slots=True)
class EvaluationCounts:
    events: int = 0
    threats: int = 0
    benign: int = 0
    investigated: int = 0
    predicted_threat: int = 0
    attention_tp: int = 0
    attention_fp: int = 0
    attention_fn: int = 0
    classification_tp: int = 0
    classification_fp: int = 0
    classification_tn: int = 0
    classification_fn: int = 0

    def record(self, *, is_threat: bool, investigated: bool, predicted_threat: bool) -> None:
        self.events += 1
        self.investigated += int(investigated)
        self.predicted_threat += int(predicted_threat)
        if is_threat:
            self.threats += 1
            self.attention_tp += int(investigated)
            self.attention_fn += int(not investigated)
            self.classification_tp += int(predicted_threat)
            self.classification_fn += int(not predicted_threat)
        else:
            self.benign += 1
            self.attention_fp += int(investigated)
            self.classification_fp += int(predicted_threat)
            self.classification_tn += int(not predicted_threat)

    @staticmethod
    def _rate(numerator: int, denominator: int) -> float | None:
        return rate(numerator, denominator)

    @property
    def attention_recall(self) -> float | None:
        return rate(self.attention_tp, self.threats)

    @property
    def attention_precision(self) -> float | None:
        return rate(self.attention_tp, self.attention_tp + self.attention_fp)

    @property
    def attention_false_positive_rate(self) -> float | None:
        return rate(self.attention_fp, self.benign)

    @property
    def classification_recall(self) -> float | None:
        return rate(self.classification_tp, self.threats)

    @property
    def classification_precision(self) -> float | None:
        return rate(
            self.classification_tp,
            self.classification_tp + self.classification_fp,
        )

    @property
    def classification_false_positive_rate(self) -> float | None:
        return rate(self.classification_fp, self.benign)

    @property
    def classification_accuracy(self) -> float | None:
        return rate(
            self.classification_tp + self.classification_tn,
            self.events,
        )

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload.update(
            {
                "attention_recall": self.attention_recall,
                "attention_precision": self.attention_precision,
                "attention_false_positive_rate": self.attention_false_positive_rate,
                "classification_recall": self.classification_recall,
                "classification_precision": self.classification_precision,
                "classification_false_positive_rate": self.classification_false_positive_rate,
                "classification_accuracy": self.classification_accuracy,
            }
        )
        return payload


@dataclass(slots=True)
class CalibrationBin:
    count: int = 0
    probability_sum: float = 0.0
    target_sum: float = 0.0


@dataclass(slots=True)
class Evaluator:
    counts: EvaluationCounts = field(default_factory=EvaluationCounts)
    family_counts: dict[str, EvaluationCounts] = field(default_factory=dict)
    phase_counts: dict[str, EvaluationCounts] = field(default_factory=dict)
    drift_counts: dict[str, EvaluationCounts] = field(default_factory=dict)
    decisions: int = 0
    brier_sum: float = 0.0
    calibration_bins: list[CalibrationBin] = field(
        default_factory=lambda: [CalibrationBin() for _ in range(10)]
    )
    high_confidence_predictions: int = 0
    high_confidence_errors: int = 0
    high_confidence_threat_misses: int = 0
    drift_recent: list[int] = field(default_factory=list)

    def record(
        self,
        *,
        is_threat: bool,
        investigated: bool,
        assessment: Assessment,
        truth_label: str = "unknown",
        phase: str = "unknown",
        drift_state: str = "unknown",
    ) -> None:
        predicted = assessment.believes_threat
        self.counts.record(
            is_threat=is_threat,
            investigated=investigated,
            predicted_threat=predicted,
        )
        self.family_counts.setdefault(truth_label, EvaluationCounts()).record(
            is_threat=is_threat,
            investigated=investigated,
            predicted_threat=predicted,
        )
        self.phase_counts.setdefault(phase, EvaluationCounts()).record(
            is_threat=is_threat,
            investigated=investigated,
            predicted_threat=predicted,
        )
        self.drift_counts.setdefault(drift_state, EvaluationCounts()).record(
            is_threat=is_threat,
            investigated=investigated,
            predicted_threat=predicted,
        )

        probability = min(1.0, max(0.0, assessment.threat_probability if assessment.threat_probability is not None else (1.0 if predicted else 0.0)))
        target = 1.0 if is_threat else 0.0
        self.decisions += 1
        self.brier_sum += (probability - target) ** 2
        bin_index = min(int(probability * len(self.calibration_bins)), len(self.calibration_bins) - 1)
        calibration_bin = self.calibration_bins[bin_index]
        calibration_bin.count += 1
        calibration_bin.probability_sum += probability
        calibration_bin.target_sum += target

        predicted_confidence = probability if predicted else 1.0 - probability
        if predicted_confidence >= 0.75:
            self.high_confidence_predictions += 1
            self.high_confidence_errors += int(predicted != is_threat)
            if is_threat and not predicted:
                self.high_confidence_threat_misses += 1

        if drift_state == "affected" and not is_threat:
            self.drift_recent.append(int(investigated))
            if len(self.drift_recent) > 200:
                self.drift_recent.pop(0)

    @property
    def pathogen_events(self) -> int:
        return self.counts.threats

    @property
    def benign_events(self) -> int:
        return self.counts.benign

    @property
    def true_positives(self) -> int:
        return self.counts.attention_tp

    @property
    def false_positives(self) -> int:
        return self.counts.attention_fp

    @property
    def false_negatives(self) -> int:
        return self.counts.attention_fn

    @property
    def classification_true_positives(self) -> int:
        return self.counts.classification_tp

    @property
    def classification_false_positives(self) -> int:
        return self.counts.classification_fp

    @property
    def classification_true_negatives(self) -> int:
        return self.counts.classification_tn

    @property
    def classification_false_negatives(self) -> int:
        return self.counts.classification_fn

    @property
    def calibration_error(self) -> float:
        return expected_calibration_error(self.calibration_bins, self.decisions)

    @property
    def brier_score(self) -> float:
        return brier_score(self.decisions, self.brier_sum)

    @property
    def overconfidence_rate(self) -> float:
        if not self.high_confidence_predictions:
            return 0.0
        return self.high_confidence_errors / self.high_confidence_predictions

    @property
    def high_confidence_miss_rate(self) -> float:
        if not self.pathogen_events:
            return 0.0
        return self.high_confidence_threat_misses / self.pathogen_events

    @property
    def blind_spot_rate(self) -> float:
        """Legacy alias for high-confidence classification misses."""
        return self.high_confidence_miss_rate

    @property
    def classification_miss_rate(self) -> float:
        if not self.pathogen_events:
            return 0.0
        return self.classification_false_negatives / self.pathogen_events

    @property
    def drift_false_positive_rate(self) -> float:
        affected = self.drift_counts.get("affected")
        if affected is None or not affected.benign:
            return 0.0
        return affected.attention_fp / affected.benign

    @property
    def recent_drift_false_positive_rate(self) -> float:
        return sum(self.drift_recent) / len(self.drift_recent) if self.drift_recent else 0.0

    def breakdown(self) -> dict[str, object]:
        return {
            "global": self.counts.as_dict(),
            "families": {
                name: counts.as_dict()
                for name, counts in sorted(self.family_counts.items())
            },
            "phases": {
                name: counts.as_dict()
                for name, counts in sorted(self.phase_counts.items())
            },
            "drift": {
                name: counts.as_dict()
                for name, counts in sorted(self.drift_counts.items())
            },
            "calibration": {
                "ece": self.calibration_error,
                "brier_score": self.brier_score,
                "overconfidence_rate": self.overconfidence_rate,
                "high_confidence_miss_rate": self.high_confidence_miss_rate,
                "bins": [
                    {
                        "count": item.count,
                        "mean_probability": (
                            item.probability_sum / item.count if item.count else None
                        ),
                        "event_rate": (
                            item.target_sum / item.count if item.count else None
                        ),
                    }
                    for item in self.calibration_bins
                ],
            },
        }
