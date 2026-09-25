from symbiont.cognition.generative import (
    GenerativeOperation,
    PredictionCalibration,
)


def test_calibration_requires_later_comparison_and_groups_bounded_bands():
    calibration = PredictionCalibration()
    calibration.record_prediction(
        model_id="m0", operation=GenerativeOperation.PREDICT, depth=5, uncertainty=0.2
    )
    calibration.record_comparison(
        model_id="m0",
        operation=GenerativeOperation.PREDICT,
        depth=5,
        uncertainty=0.2,
        observed_error=0.4,
    )
    bucket = calibration.bucket(
        model_id="m0", operation=GenerativeOperation.PREDICT, depth=5, uncertainty=0.2
    )
    assert bucket.prediction_count == 1
    assert bucket.later_comparable_count == 1
    assert bucket.calibration_error == 0.2
