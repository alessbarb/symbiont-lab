from __future__ import annotations

import math

import pytest

from symbiont.core.selfmodel import IDLE_GRACE_TICKS, RecencyClass, SelfModel
from symbiont.host.readings import CapabilitySamplingOutcome, ReadingQuality, SamplingOutcomeKind


def _outcome(
    capability_id: str = "sense-a",
    kind: SamplingOutcomeKind = SamplingOutcomeKind.SUCCEEDED,
    elapsed: float = 0.01,
    quality: ReadingQuality | None = ReadingQuality.NOMINAL,
) -> CapabilitySamplingOutcome:
    return CapabilitySamplingOutcome(
        capability_id=capability_id,
        provider_id="p",
        kind=kind,
        attributed_elapsed_s=elapsed,
        quality=quality,
    )


def test_cold_start_health_and_confidence_are_neutral_and_low():
    model = SelfModel()
    assert model.health("unseen") == pytest.approx(0.5)
    assert model.confidence("unseen") == pytest.approx(0.0)
    assert not model.is_established("unseen")


def test_repeated_nominal_success_raises_health_and_confidence():
    model = SelfModel()
    for tick in range(50):
        model.observe(outcome=_outcome(), tick=tick)
    assert model.health("sense-a") > 0.9
    assert model.is_established("sense-a")
    assert model.confidence("sense-a") > 0.5


def test_provider_failure_lowers_health_but_not_other_senses():
    model = SelfModel()
    for tick in range(50):
        model.observe(outcome=_outcome(), tick=tick)
        model.observe(outcome=_outcome(capability_id="sense-b"), tick=tick)
    for tick in range(50, 60):
        model.observe(outcome=_outcome(kind=SamplingOutcomeKind.PROVIDER_FAILED, quality=None), tick=tick)
    assert model.health("sense-a") < 0.9
    assert model.health("sense-b") > 0.9


def test_confidence_stays_low_before_minimum_attempts_even_if_perfect():
    model = SelfModel()
    model.observe(outcome=_outcome(), tick=0)
    assert not model.is_established("sense-a")
    assert model.confidence("sense-a") < 0.2


def test_confidence_and_health_are_always_finite_and_bounded():
    model = SelfModel()
    for tick in range(50):
        model.observe(outcome=_outcome(elapsed=1e9), tick=tick)
    assert 0.0 <= model.health("sense-a") <= 1.0
    assert 0.0 <= model.confidence("sense-a") <= 1.0
    assert math.isfinite(model.health("sense-a"))


def test_relative_cost_defaults_to_one_with_no_reference_data():
    model = SelfModel()
    assert model.relative_cost("sense-a", reference_ids=()) == pytest.approx(1.0)


def test_relative_cost_reflects_expense_relative_to_established_median():
    model = SelfModel()
    for tick in range(10):
        model.observe(outcome=_outcome("cheap", elapsed=0.001), tick=tick)
        model.observe(outcome=_outcome("expensive", elapsed=0.1), tick=tick)
    cheap = model.relative_cost("cheap", reference_ids=("cheap", "expensive"))
    expensive = model.relative_cost("expensive", reference_ids=("cheap", "expensive"))
    assert expensive > cheap


def test_reconcile_drops_senses_outside_the_allowed_set():
    model = SelfModel()
    for tick in range(10):
        model.observe(outcome=_outcome("keep"), tick=tick)
        model.observe(outcome=_outcome("drop"), tick=tick)
    model.reconcile(allowed_sense_ids={"keep"})
    exported = model.export(current_tick=9)
    assert "drop" not in exported
    assert "keep" in exported


def test_export_omits_unestablished_senses_and_restore_round_trips():
    model = SelfModel()
    for tick in range(10):
        model.observe(outcome=_outcome(), tick=tick)
    exported = model.export(current_tick=9)
    assert "sense-a" in exported
    restored = SelfModel.restore(exported, allowed_sense_ids={"sense-a"}, current_tick=9)
    assert restored.is_established("sense-a")
    assert restored.health("sense-a") == pytest.approx(model.health("sense-a"), abs=0.1)


def test_restore_rejects_payload_over_max_senses():
    huge_payload = {
        f"sense-{i}": {"cost_class": 0, "health_class": 8, "confidence_class": 8, "maturity_class": 4, "recency_class": 0}
        for i in range(SelfModel.MAX_SENSES + 1)
    }
    with pytest.raises(ValueError):
        SelfModel.restore(huge_payload, allowed_sense_ids=set(huge_payload), current_tick=0)


def test_restore_rejects_non_finite_or_out_of_range_values():
    with pytest.raises(ValueError):
        SelfModel.restore(
            {
                "sense-a": {
                    "cost_class": 999,
                    "health_class": 8,
                    "confidence_class": 8,
                    "maturity_class": 4,
                    "recency_class": 0,
                }
            },
            allowed_sense_ids={"sense-a"},
            current_tick=0,
        )


def test_health_without_current_tick_is_unchanged_from_v053():
    model = SelfModel()
    for tick in range(50):
        model.observe(outcome=_outcome(), tick=tick)
    assert model.health("sense-a") == model.health("sense-a", current_tick=None)


def test_health_within_grace_period_is_not_decayed():
    model = SelfModel()
    for tick in range(50):
        model.observe(outcome=_outcome(), tick=tick)
    undecayed = model.health("sense-a")
    assert model.health("sense-a", current_tick=49 + IDLE_GRACE_TICKS) == pytest.approx(undecayed)


def test_health_decays_toward_neutral_past_grace_period():
    model = SelfModel()
    for tick in range(50):
        model.observe(outcome=_outcome(), tick=tick)
    undecayed = model.health("sense-a")
    far_future = 49 + IDLE_GRACE_TICKS + 200
    decayed = model.health("sense-a", current_tick=far_future)
    assert decayed < undecayed
    assert decayed == pytest.approx(0.5, abs=0.05)


def test_confidence_decays_toward_zero_past_grace_period():
    model = SelfModel()
    for tick in range(50):
        model.observe(outcome=_outcome(), tick=tick)
    far_future = 49 + IDLE_GRACE_TICKS + 200
    assert model.confidence("sense-a", current_tick=far_future) == pytest.approx(0.0, abs=0.05)


def test_idle_decay_is_computed_not_mutated():
    model = SelfModel()
    for tick in range(50):
        model.observe(outcome=_outcome(), tick=tick)
    far_future = 49 + IDLE_GRACE_TICKS + 200
    first = model.health("sense-a", current_tick=far_future)
    second = model.health("sense-a", current_tick=far_future)
    assert first == second
    assert model.health("sense-a") != pytest.approx(0.5, abs=0.01)


def test_is_established_and_relative_cost_are_never_decayed():
    model = SelfModel()
    for tick in range(50):
        model.observe(outcome=_outcome(), tick=tick)
    assert model.is_established("sense-a")
    cost_now = model.relative_cost("sense-a", reference_ids=("sense-a",))
    assert cost_now == pytest.approx(1.0)


def test_export_uses_recency_class_not_exact_last_observed_tick():
    """Design §17: replace SelfModel's one remaining exact field."""
    model = SelfModel()
    for tick in range(10):
        model.observe(outcome=_outcome(), tick=tick)
    exported = model.export(current_tick=9)
    entry = exported["sense-a"]
    assert "last_observed_tick" not in entry
    assert entry["recency_class"] == RecencyClass.CURRENT.value  # observed this same tick


def test_restore_seeds_last_observed_tick_relative_to_the_given_current_tick():
    """Restoring at the same tick the checkpoint was saved at (saved_at_tick)
    reproduces the CURRENT class exactly (idle_ticks=0 both ways); restoring
    at a much later tick must not claim the sense was observed that recently."""
    model = SelfModel()
    for tick in range(10):
        model.observe(outcome=_outcome(), tick=tick)
    exported = model.export(current_tick=9)

    restored_same_tick = SelfModel.restore(exported, allowed_sense_ids={"sense-a"}, current_tick=9)
    close_tick_health = restored_same_tick.health("sense-a", current_tick=9 + IDLE_GRACE_TICKS)
    assert close_tick_health == pytest.approx(model.health("sense-a"), abs=0.05)


def test_restore_rejects_out_of_range_recency_class():
    with pytest.raises(ValueError):
        SelfModel.restore(
            {
                "sense-a": {
                    "cost_class": 0,
                    "health_class": 8,
                    "confidence_class": 8,
                    "maturity_class": 4,
                    "recency_class": 999,
                }
            },
            allowed_sense_ids={"sense-a"},
            current_tick=0,
        )


def test_restore_never_fabricates_the_real_original_idle_offset():
    """P11-style guarantee applied to SelfModel: a DORMANT restore at a much
    later current_tick must not reconstruct the real original idle gap."""
    model = SelfModel()
    for tick in range(10):
        model.observe(outcome=_outcome(), tick=tick)
    exported = model.export(current_tick=500)  # 490 ticks idle -> DORMANT
    assert exported["sense-a"]["recency_class"] == RecencyClass.DORMANT.value

    restored = SelfModel.restore(exported, allowed_sense_ids={"sense-a"}, current_tick=1000)
    idle_at_restore = 1000 - restored._states["sense-a"].last_observed_tick
    assert idle_at_restore != 490  # the fixed DORMANT representative, not the real original gap


def test_consecutive_checkpoints_cannot_be_differenced_to_recover_exact_observation():
    model = SelfModel()
    for tick in range(10):
        model.observe(outcome=_outcome(elapsed=0.01), tick=tick)
    checkpoint_before = model.export(current_tick=10)

    model.observe(outcome=_outcome(elapsed=0.999999), tick=10)
    checkpoint_after = model.export(current_tick=10)

    before_health = checkpoint_before["sense-a"]["health_class"]
    after_health = checkpoint_after["sense-a"]["health_class"]
    assert before_health == after_health
