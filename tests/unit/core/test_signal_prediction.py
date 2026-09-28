import math
import random

import pytest
from symbiont.core.signal_knowledge_checkpoint import validate_checkpoint
from symbiont.core.signal_prediction import (
    BoundedPredictor,
    RidgePredictor,
    absolute_loss,
    baseline_predictions,
    improvement_class,
    scaled_squared_loss,
)


def test_bounded_predictor_is_in_memory_and_deterministic():
    predictor = BoundedPredictor(history_limit=2)
    assert predictor.predict() is None
    predictor.observe(1.0)
    predictor.observe(2.0)
    predictor.observe(3.0)
    assert predictor.predict() == 3.0
    assert predictor.count == 2
    assert absolute_loss(2.0, 3.5) == 1.5
    assert absolute_loss(None, 1.0) is None
    with pytest.raises(ValueError):
        predictor.observe(float("nan"))
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



def _legacy_ridge_predict(rows, regularization, features):
    if not rows or len(features) != len(rows[0][0]):
        return None
    x = [1.0, *(float(v) for v in features)]
    if any(not math.isfinite(v) for v in x):
        return None
    width = len(x)
    matrix = [[0.0] * (width + 1) for _ in range(width)]
    for row, target in rows:
        z = [1.0, *row]
        for i in range(width):
            for j in range(width):
                matrix[i][j] += z[i] * z[j]
            matrix[i][-1] += z[i] * target
    for i in range(1, width):
        matrix[i][i] += regularization
    for col in range(width):
        pivot = max(range(col, width), key=lambda r: abs(matrix[r][col]))
        if abs(matrix[pivot][col]) < 1e-12:
            return None
        matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
        divisor = matrix[col][col]
        matrix[col] = [v / divisor for v in matrix[col]]
        for r in range(width):
            if r == col:
                continue
            factor = matrix[r][col]
            matrix[r] = [a - factor * b for a, b in zip(matrix[r], matrix[col])]
    value = sum(matrix[i][-1] * x[i] for i in range(width))
    return value if math.isfinite(value) else None


def test_ridge_precomputed_rows_are_bit_exact_with_legacy_predict():
    rng = random.Random(127)
    predictor = RidgePredictor(history_limit=64)
    rows = []

    for _ in range(80):
        features = tuple(rng.uniform(-3.0, 3.0) for _ in range(3))
        target = rng.uniform(-2.0, 2.0)
        predictor.observe(features, target)
        rows.append((tuple(float(v) for v in features), float(target)))
        rows = rows[-64:]

        query = tuple(rng.uniform(-4.0, 4.0) for _ in range(3))
        assert predictor.predict(query) == _legacy_ridge_predict(
            rows,
            predictor.regularization,
            query,
        )


def test_ridge_precomputation_survives_checkpoint_roundtrip_exactly():
    predictor = RidgePredictor(history_limit=8)
    for value in range(1, 9):
        predictor.observe(
            (float(value), float(value % 3), float(value) * 0.25),
            float(value) * 1.5 - 2.0,
        )

    query = (9.0, 0.0, 2.25)
    before = predictor.predict(query)
    restored = RidgePredictor.from_checkpoint(predictor.checkpoint())

    assert restored.predict(query) == before
    assert restored.checkpoint() == predictor.checkpoint()



def test_ridge_width4_preserves_first_pivot_on_exact_tie():
    predictor = RidgePredictor(history_limit=8)
    rows = []
    for index in range(1, 9):
        features = (1.0, float(index % 2), float(index % 3))
        target = float(index) * 0.75 - 1.0
        predictor.observe(features, target)
        rows.append((features, target))

    query = (1.0, 1.0, 2.0)
    assert predictor.predict(query) == _legacy_ridge_predict(
        rows,
        predictor.regularization,
        query,
    )


def test_ridge_non_width4_keeps_generic_solver_exact():
    predictor = RidgePredictor(history_limit=8)
    rows = []
    for index in range(1, 9):
        features = (float(index), float(index % 2))
        target = float(index) * 0.5 + 3.0
        predictor.observe(features, target)
        rows.append((features, target))

    query = (9.0, 1.0)
    assert predictor.predict(query) == _legacy_ridge_predict(
        rows,
        predictor.regularization,
        query,
    )
