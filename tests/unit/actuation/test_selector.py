from __future__ import annotations

from symbiont.actuation.selector import MotorIntentSelector


def test_selector_returns_none_below_threshold():
    selector = MotorIntentSelector(selection_threshold=0.5)
    assert selector.select({"actuator.a": 0.49}) is None


def test_selector_chooses_highest_activation_for_compatibility_view():
    selector = MotorIntentSelector(selection_threshold=0.1)
    intent = selector.select({"actuator.b": 0.4, "actuator.a": 0.8})
    assert intent is not None
    assert intent.actuator_id == "actuator.a"
    assert intent.activation == 0.8


def test_selector_returns_bounded_concurrent_intents():
    selector = MotorIntentSelector(selection_threshold=0.1)
    intents = selector.select_many(
        {
            "actuator.d": 0.3,
            "actuator.c": 0.7,
            "actuator.b": 0.9,
            "actuator.a": 0.8,
            "actuator.e": 0.6,
        },
        max_concurrent=4,
    )
    assert [item.actuator_id for item in intents] == [
        "actuator.b",
        "actuator.a",
        "actuator.c",
        "actuator.e",
    ]


def test_selector_uses_lexical_id_for_exact_tie():
    selector = MotorIntentSelector(selection_threshold=0.1)
    intent = selector.select({"actuator.z": 0.7, "actuator.a": 0.7})
    assert intent is not None
    assert intent.actuator_id == "actuator.a"


def test_selector_ignores_non_numeric_and_non_finite_values():
    selector = MotorIntentSelector(selection_threshold=0.1)
    assert selector.select({"a": True, "b": float("nan")}) is None
