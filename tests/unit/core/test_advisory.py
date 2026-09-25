from __future__ import annotations

import pytest
from symbiont.core.advisory import (
    _BANNED_WORDS,
    AdvisoryConsentRequiredError,
    DefensiveAdvisor,
    _evaluate_signals,
    append_advisories_to_log,
    load_advisory_log,
)
from symbiont.core.evidence import DissentRecord
from symbiont.core.narrative import NarrativeEntry
from symbiont.core.runtime import RuntimeTickResult

from symbiont.host.drift import DriftKind, DriftObservation


def _narrative(capability_id: str, uncertainty: float) -> NarrativeEntry:
    return NarrativeEntry(
        capability_id=capability_id,
        familiarity="familiar",
        uncertainty=uncertainty,
        attended=True,
        attention_cost=1.0,
        evidence_gathered=0,
        dissent=None,
        summary="...",
    )


def _result(
    *,
    tick: int = 1,
    drift_kind: DriftKind = DriftKind.REGIME_SHIFT,
    uncertainty: float = 5.0,
    investigated: str | None = "cpu",
    dissent: DissentRecord | None = None,
) -> RuntimeTickResult:
    return RuntimeTickResult(
        tick=tick,
        snapshot=None,
        percepts=(),
        drift_observations={"cpu": DriftObservation(kind=drift_kind, z_score=9.0)},
        allocations=(),
        investigated_capability=investigated,
        evidence_gathered=2,
        dissent=dissent,
        narrative=(_narrative("cpu", uncertainty),),
    )


_DISSENT = DissentRecord(
    capability_id="cpu", prior_mean=1.0, prior_stdev=0.1, evidence_mean=9.0, z_score=80.0
)


# --- rule composition ---


def test_regime_shift_alone_does_not_fire():
    result = _result(uncertainty=0.1, investigated=None, dissent=None)
    assert _evaluate_signals(result, uncertainty_threshold=1.0) == ()


def test_regime_shift_plus_high_uncertainty_fires():
    result = _result(uncertainty=5.0, investigated=None, dissent=None)
    advisories = _evaluate_signals(result, uncertainty_threshold=1.0)

    assert len(advisories) == 1
    kinds = {signal.kind for signal in advisories[0].signals}
    assert kinds == {"persistent_deviation", "unusual_activity"}


def test_regime_shift_plus_dissent_fires():
    result = _result(uncertainty=0.1, investigated="cpu", dissent=_DISSENT)
    advisories = _evaluate_signals(result, uncertainty_threshold=1.0)

    assert len(advisories) == 1
    kinds = {signal.kind for signal in advisories[0].signals}
    assert kinds == {"persistent_deviation", "contradictory_evidence"}


def test_all_three_signals_fire_together():
    result = _result(uncertainty=5.0, investigated="cpu", dissent=_DISSENT)
    advisories = _evaluate_signals(result, uncertainty_threshold=1.0)

    assert len(advisories) == 1
    kinds = {signal.kind for signal in advisories[0].signals}
    assert kinds == {"persistent_deviation", "unusual_activity", "contradictory_evidence"}


def test_non_regime_shift_drift_never_fires():
    for kind in (DriftKind.NONE, DriftKind.ISOLATED, DriftKind.GRADUAL):
        result = _result(drift_kind=kind, uncertainty=5.0, investigated="cpu", dissent=_DISSENT)
        assert _evaluate_signals(result, uncertainty_threshold=1.0) == ()


def test_dissent_on_a_different_capability_does_not_corroborate():
    other_dissent = DissentRecord(
        capability_id="disk", prior_mean=1.0, prior_stdev=0.1, evidence_mean=9.0, z_score=80.0
    )
    result = _result(uncertainty=0.1, investigated="disk", dissent=other_dissent)
    assert _evaluate_signals(result, uncertainty_threshold=1.0) == ()


def test_infinite_uncertainty_never_counts_as_unusual_activity():
    """An unacclimated capability has infinite uncertainty by construction
    (v0.38) — that is "unknown", not "unusual", and must not corroborate."""
    result = _result(uncertainty=float("inf"), investigated=None, dissent=None)
    assert _evaluate_signals(result, uncertainty_threshold=1.0) == ()


# --- vocabulary discipline ---


def test_summary_never_contains_banned_vocabulary():
    result = _result(uncertainty=5.0, investigated="cpu", dissent=_DISSENT)
    advisories = _evaluate_signals(result, uncertainty_threshold=1.0)

    for advisory in advisories:
        text = advisory.summary.lower()
        for word in _BANNED_WORDS:
            assert word not in text
        for signal in advisory.signals:
            assert word not in signal.detail.lower()


def test_advisory_exposes_no_classification_field():
    result = _result(uncertainty=5.0, investigated="cpu", dissent=_DISSENT)
    advisory = _evaluate_signals(result, uncertainty_threshold=1.0)[0]

    public_attrs = {name for name in dir(advisory) if not name.startswith("_")}
    assert public_attrs <= {"tick", "capability_id", "signals", "summary"}


# --- DefensiveAdvisor: independent consent + rate limiting ---


def test_rejects_non_positive_uncertainty_threshold():
    with pytest.raises(ValueError):
        DefensiveAdvisor(uncertainty_threshold=0.0)


def test_rejects_negative_min_seconds_between_advisories():
    with pytest.raises(ValueError):
        DefensiveAdvisor(min_seconds_between_advisories=-1.0)


def test_not_consented_by_default():
    advisor = DefensiveAdvisor()
    assert not advisor.is_consented


def test_evaluate_requires_consent():
    advisor = DefensiveAdvisor(consented=False)
    with pytest.raises(AdvisoryConsentRequiredError):
        advisor.evaluate(_result())


def test_evaluate_works_once_granted():
    advisor = DefensiveAdvisor(consented=True, uncertainty_threshold=1.0)
    advisories = advisor.evaluate(_result(uncertainty=5.0, investigated=None, dissent=None))
    assert len(advisories) == 1


def test_revoke_blocks_further_evaluation():
    advisor = DefensiveAdvisor(consented=True)
    advisor.revoke()
    with pytest.raises(AdvisoryConsentRequiredError):
        advisor.evaluate(_result())


class _FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


def test_rate_limit_suppresses_a_repeat_advisory_too_soon():
    clock = _FakeClock()
    advisor = DefensiveAdvisor(
        consented=True, uncertainty_threshold=1.0, min_seconds_between_advisories=10.0, clock=clock
    )
    first = advisor.evaluate(_result(uncertainty=5.0, investigated=None, dissent=None))
    assert len(first) == 1

    clock.now = 2.0
    second = advisor.evaluate(_result(uncertainty=5.0, investigated=None, dissent=None))
    assert second == ()  # rate-limited, not raised


def test_rate_limit_allows_a_repeat_advisory_after_interval():
    clock = _FakeClock()
    advisor = DefensiveAdvisor(
        consented=True, uncertainty_threshold=1.0, min_seconds_between_advisories=10.0, clock=clock
    )
    advisor.evaluate(_result(uncertainty=5.0, investigated=None, dissent=None))

    clock.now = 10.0
    second = advisor.evaluate(_result(uncertainty=5.0, investigated=None, dissent=None))
    assert len(second) == 1


def test_no_advisory_does_not_reset_rate_limit_clock():
    clock = _FakeClock()
    advisor = DefensiveAdvisor(
        consented=True, uncertainty_threshold=1.0, min_seconds_between_advisories=10.0, clock=clock
    )
    advisor.evaluate(_result(uncertainty=5.0, investigated=None, dissent=None))

    clock.now = 1.0
    quiet_result = _result(
        drift_kind=DriftKind.NONE, uncertainty=0.1, investigated=None, dissent=None
    )
    advisor.evaluate(
        quiet_result
    )  # no advisory conditions met; must not touch the rate-limit clock

    clock.now = 5.0
    still_limited = advisor.evaluate(_result(uncertainty=5.0, investigated=None, dissent=None))
    assert still_limited == ()  # only 5s since the *first* advisory, still under the 10s limit


# --- durable advisory log ---


def test_append_advisories_is_a_noop_for_empty_tuple(tmp_path):
    path = tmp_path / "advisories.json"
    append_advisories_to_log((), path)
    assert not path.exists()


def test_append_and_load_advisory_log_round_trips(tmp_path):
    path = tmp_path / "advisories.json"
    result = _result(uncertainty=5.0, investigated="cpu", dissent=_DISSENT)
    advisories = _evaluate_signals(result, uncertainty_threshold=1.0)

    append_advisories_to_log(advisories, path)
    logged = load_advisory_log(path)

    assert len(logged) == 1
    assert logged[0]["capability_id"] == "cpu"
    assert logged[0]["summary"] == advisories[0].summary


def test_appending_twice_accumulates_entries(tmp_path):
    path = tmp_path / "advisories.json"
    result = _result(uncertainty=5.0, investigated="cpu", dissent=_DISSENT)
    advisories = _evaluate_signals(result, uncertainty_threshold=1.0)

    append_advisories_to_log(advisories, path)
    append_advisories_to_log(advisories, path)

    assert len(load_advisory_log(path)) == 2


def test_load_advisory_log_empty_when_no_file(tmp_path):
    assert load_advisory_log(tmp_path / "missing.json") == ()
