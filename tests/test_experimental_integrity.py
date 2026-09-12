from __future__ import annotations

from hashlib import sha256

from symbiont.simulation import EventContext, run_simulation


def _world_digest(**kwargs) -> tuple[str, tuple[tuple[str, int], ...]]:
    digest = sha256()
    counts: dict[str, int] = {}

    def capture(event: EventContext) -> None:
        counts[event.truth_label] = counts.get(event.truth_label, 0) + 1
        vector = ",".join(f"{value:.12f}" for value in event.observation.vector())
        digest.update(
            (
                f"{event.step}|{event.host_index}|{event.truth_label}|"
                f"{event.phase}|{event.drift_state}|{vector}\n"
            ).encode("utf-8")
        )

    run_simulation(on_event=capture, **kwargs)
    return digest.hexdigest(), tuple(sorted(counts.items()))


def test_agent_side_poisoning_does_not_change_same_seed_world():
    common = dict(hosts=18, steps=110, seed=29, threat_rate=0.04)
    baseline = _world_digest(**common, poison_fraction=0.0, heterogeneity=0.12)
    poisoned = _world_digest(**common, poison_fraction=0.45, heterogeneity=0.12)

    assert poisoned == baseline


def test_agent_heterogeneity_does_not_change_same_seed_world():
    common = dict(hosts=18, steps=110, seed=31, threat_rate=0.04, poison_fraction=0.08)
    homogeneous = _world_digest(**common, heterogeneity=0.0)
    heterogeneous = _world_digest(**common, heterogeneity=0.40)

    assert heterogeneous == homogeneous


def test_evaluator_exposes_attention_and_classification_by_family_and_phase():
    result, _ = run_simulation(
        hosts=30,
        steps=160,
        seed=11,
        threat_rate=0.06,
        poison_fraction=0.08,
        heterogeneity=0.12,
    )
    breakdown = result.evaluation_breakdown
    families = breakdown["families"]
    phases = breakdown["phases"]

    for family in (
        "pathogen:ransom_sim",
        "pathogen:bot_sim",
        "pathogen:stealth_sim",
    ):
        assert family in families
        assert families[family]["threats"] > 0
        assert families[family]["attention_recall"] is not None
        assert families[family]["classification_recall"] is not None

    assert {"warmup", "pre_drift", "post_drift"} <= set(phases)
    assert breakdown["global"]["events"] == result.hosts * result.steps
    assert result.attention_recall == result.detection_rate
    assert result.attention_precision == result.precision


def test_calibration_breakdown_uses_probability_bins():
    result, _ = run_simulation(hosts=20, steps=100, seed=17, threat_rate=0.05)
    calibration = result.evaluation_breakdown["calibration"]
    bins = calibration["bins"]

    assert len(bins) == 10
    assert sum(item["count"] for item in bins) == result.hosts * result.steps
    assert 0 <= calibration["ece"] <= 1
    assert 0 <= calibration["brier_score"] <= 1
