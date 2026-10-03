from __future__ import annotations

import pytest

from symbiont.modeling import TemporalResponsibilityTracker


def test_local_responsibility_favors_lower_loss_without_global_semantics():
    tracker = TemporalResponsibilityTracker(
        ("mechanism.a", "mechanism.b", "mechanism.c"),
        smoothing=1.0,
        temperature=0.2,
    )
    tracker.observe("mechanism.a", loss=0.1)
    tracker.observe("mechanism.b", loss=0.4)
    tracker.observe("mechanism.c", loss=0.9)

    responsibilities = tracker.responsibilities()

    assert responsibilities["mechanism.a"] > responsibilities["mechanism.b"]
    assert responsibilities["mechanism.b"] > responsibilities["mechanism.c"]
    assert sum(responsibilities.values()) == pytest.approx(1.0)


def test_unobserved_mechanism_gets_no_responsibility_after_evidence_exists():
    tracker = TemporalResponsibilityTracker(("a", "b"))
    tracker.observe("a", loss=0.2)

    responsibilities = tracker.responsibilities()

    assert responsibilities["a"] == pytest.approx(1.0)
    assert responsibilities["b"] == pytest.approx(0.0)


def test_responsibility_checkpoint_roundtrip():
    tracker = TemporalResponsibilityTracker(("a", "b"), smoothing=0.25)
    tracker.observe("a", loss=0.2)
    tracker.observe("b", loss=0.3)

    restored = TemporalResponsibilityTracker.restore(tracker.checkpoint())

    assert restored.snapshot().samples == tracker.snapshot().samples
    assert restored.snapshot().losses == pytest.approx(tracker.snapshot().losses)
    assert restored.responsibilities() == pytest.approx(tracker.responsibilities())
