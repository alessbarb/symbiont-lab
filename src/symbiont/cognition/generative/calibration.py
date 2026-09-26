"""Bounded calibration statistics for later-comparable predictions."""

from __future__ import annotations

from dataclasses import dataclass

from .types import GenerativeOperation, bounded_identifier, unit_interval


@dataclass(frozen=True, slots=True)
class CalibrationBucket:
    prediction_count: int
    later_comparable_count: int
    mean_declared_uncertainty: float
    mean_observed_error: float
    calibration_error: float


class PredictionCalibration:
    """Stores aggregate calibration only after an external comparison."""

    def __init__(self) -> None:
        self._buckets: dict[tuple[str, GenerativeOperation, int, int], list[float]] = {}

    def record_prediction(
        self,
        *,
        model_id: str,
        operation: GenerativeOperation,
        depth: int,
        uncertainty: float,
    ) -> None:
        self._validate(model_id, operation, depth, uncertainty)
        key = self._key(model_id, operation, depth, uncertainty)
        bucket = self._buckets.setdefault(key, [0.0, 0.0, 0.0])
        bucket[0] += 1
        bucket[2] += uncertainty

    def record_comparison(
        self,
        *,
        model_id: str,
        operation: GenerativeOperation,
        depth: int,
        uncertainty: float,
        observed_error: float,
    ) -> None:
        self._validate(model_id, operation, depth, uncertainty)
        unit_interval(observed_error, name="observed_error")
        key = self._key(model_id, operation, depth, uncertainty)
        bucket = self._buckets.setdefault(key, [0.0, 0.0, 0.0])
        if bucket[1] >= bucket[0]:
            raise ValueError("comparison requires an unpaired prediction in the same bucket")
        bucket[1] += 1
        bucket.append(observed_error)

    def checkpoint(self) -> dict[str, object]:
        """Persist bounded aggregate calibration, never generated trajectories."""
        return {
            "buckets": [
                {
                    "model_id": model_id,
                    "operation": operation.value,
                    "depth_bucket": depth_bucket,
                    "uncertainty_bucket": uncertainty_bucket,
                    "prediction_count": int(values[0]),
                    "comparable_count": int(values[1]),
                    "uncertainty_sum": float(values[2]),
                    "errors": [float(value) for value in values[3:]],
                }
                for (model_id, operation, depth_bucket, uncertainty_bucket), values
                in sorted(
                    self._buckets.items(),
                    key=lambda item: (
                        item[0][0],
                        item[0][1].value,
                        item[0][2],
                        item[0][3],
                    ),
                )
            ]
        }

    @classmethod
    def from_checkpoint(cls, payload: object) -> "PredictionCalibration":
        if not isinstance(payload, dict):
            raise ValueError("calibration checkpoint must be an object")
        raw_buckets = payload.get("buckets", [])
        if not isinstance(raw_buckets, list) or len(raw_buckets) > 4096:
            raise ValueError("invalid calibration bucket collection")
        obj = cls()
        for item in raw_buckets:
            if not isinstance(item, dict):
                raise ValueError("invalid calibration bucket")
            try:
                model_id = bounded_identifier(item["model_id"], name="model_id")
                operation = GenerativeOperation(item["operation"])
                depth_bucket = int(item["depth_bucket"])
                uncertainty_bucket = int(item["uncertainty_bucket"])
                prediction_count = int(item["prediction_count"])
                comparable_count = int(item["comparable_count"])
                uncertainty_sum = float(item["uncertainty_sum"])
                errors = [float(value) for value in item.get("errors", [])]
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("invalid calibration bucket") from exc
            if (
                depth_bucket < 0
                or not 0 <= uncertainty_bucket <= 9
                or prediction_count < 0
                or comparable_count < 0
                or comparable_count > prediction_count
                or len(errors) != comparable_count
                or not 0.0 <= uncertainty_sum <= float(prediction_count)
                or any(not 0.0 <= error <= 1.0 for error in errors)
            ):
                raise ValueError("invalid calibration bucket values")
            obj._buckets[(model_id, operation, depth_bucket, uncertainty_bucket)] = [
                float(prediction_count),
                float(comparable_count),
                uncertainty_sum,
                *errors,
            ]
        return obj

    def bucket(
        self, *, model_id: str, operation: GenerativeOperation, depth: int, uncertainty: float
    ) -> CalibrationBucket:
        self._validate(model_id, operation, depth, uncertainty)
        values = self._buckets.get(
            self._key(model_id, operation, depth, uncertainty), [0.0, 0.0, 0.0]
        )
        prediction_count, comparable_count, uncertainty_sum = values[:3]
        errors = values[3:]
        mean_uncertainty = uncertainty_sum / prediction_count if prediction_count else 0.0
        mean_error = sum(errors) / len(errors) if errors else 0.0
        return CalibrationBucket(
            int(prediction_count),
            int(comparable_count),
            mean_uncertainty,
            mean_error,
            abs(mean_uncertainty - mean_error) if errors else 0.0,
        )

    @staticmethod
    def _key(model_id, operation, depth, uncertainty):
        return (model_id, operation, depth // 4, min(9, int(uncertainty * 10)))

    @staticmethod
    def _validate(model_id, operation, depth, uncertainty):
        bounded_identifier(model_id, name="model_id")
        if not isinstance(operation, GenerativeOperation):
            raise ValueError("operation must be a GenerativeOperation")
        if isinstance(depth, bool) or not isinstance(depth, int) or depth < 0:
            raise ValueError("depth must be a non-negative integer")
        unit_interval(uncertainty, name="uncertainty")


__all__ = ["CalibrationBucket", "PredictionCalibration"]
