"""Integrity checks for the design pilot, not acceptance of a runtime engine."""
from pilot import evaluate, fit, series


def test_fit_known_linear_function():
    rows = [([1.0, float(x)], 2.0 + 3.0 * x) for x in range(32)]
    assert abs(fit(rows, [1.0, 5.0]) - 17.0) < 1e-5


def test_past_epochs_do_not_depend_on_future_values():
    values = list(series("lead", 17, 512))
    prefix = evaluate(values[:256])
    changed_future = evaluate(values[:256] + [(900.0, -900.0)] * 256)
    assert prefix["epochs"] == changed_future["epochs"][:4]
    assert prefix["promotions"] == [t for t in changed_future["promotions"] if t < 256]


def test_missing_target_censors_and_does_not_score_zero():
    values = list(series("lead", 17, 256))
    valid = evaluate(values)
    values[100] = (None, None)
    missing = evaluate(values)
    assert missing["censored"] > valid["censored"]
    assert missing["trials"] < valid["trials"]


def test_constant_does_not_promote():
    assert evaluate(series("constant", 17, 512))["promotions"] == []


def test_reproducible_observations_and_results():
    assert evaluate(series("lead", 29, 256)) == evaluate(series("lead", 29, 256))
