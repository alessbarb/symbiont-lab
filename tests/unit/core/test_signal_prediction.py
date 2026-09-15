import pytest

from symbiont.core.signal_prediction import BoundedPredictor, RidgePredictor, absolute_loss, baseline_predictions, scaled_squared_loss, improvement_class
from symbiont.core.signal_knowledge_checkpoint import validate_checkpoint


def test_bounded_predictor_is_in_memory_and_deterministic():
    predictor = BoundedPredictor(history_limit=2)
    assert predictor.predict() is None
    predictor.observe(1.0); predictor.observe(2.0); predictor.observe(3.0)
    assert predictor.predict() == 3.0
    assert predictor.count == 2
    assert absolute_loss(2.0, 3.5) == 1.5
    assert absolute_loss(None, 1.0) is None
    with pytest.raises(ValueError): predictor.observe(float("nan"))
    refs = baseline_predictions([1.0, 2.0, 3.0])
    assert refs["zero"] == 0.0 and refs["persistence"] == 3.0


def test_checkpoint_validation_is_atomic_and_rejects_raw_sample_fields():
    with pytest.raises(ValueError):
        validate_checkpoint({"schema_version": 1, "profiles": [], "samples": [1.0]})


def test_protocol_loss_and_improvement_require_comparable_scale():
    assert scaled_squared_loss(1.0, 0.0, 1.0) == 1.0
    assert scaled_squared_loss(10.0, 0.0, 1.0) == 16.0
    assert scaled_squared_loss(1.0, 0.0, 0.0) is None
    assert improvement_class(0.8, 1.0) == "material"
    assert improvement_class(0.99, 1.0) == "none"
    assert improvement_class(0.0, 0.0) == "none"


def test_ridge_predictor_is_bounded_and_trains_only_on_observed_targets():
    predictor = RidgePredictor()
    assert predictor.predict((2.0,)) is None
    for x in range(1, 8):
        predictor.observe((float(x),), 3.0 * x + 1.0)
    estimate = predictor.predict((8.0,))
    assert estimate is not None and abs(estimate - 25.0) < 0.01
    assert predictor.count == 7
