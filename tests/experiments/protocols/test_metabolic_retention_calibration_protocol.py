"""Mechanical contract of Metabolic Retention Price Calibration v1 (no scientific claim)."""

from __future__ import annotations

import pytest

import symbiont_lab.studies.embodiment.reembodiment_functional_transfer as transfer
import symbiont_lab.studies.learning.competence_establishment as establishment
import symbiont_lab.studies.learning.metabolic_retention_calibration as study
from symbiont.core.domains.memory import MemoryDomain
from symbiont.core.organism_profile import CANONICAL, HISTORICAL_V0
from symbiont_lab.experiments.loader import load_experiment_file

pytestmark = pytest.mark.experiment_contract


def test_grid_is_the_preregistered_one() -> None:
    assert len(study.ARMS) == 36 and study.CURRENT_PRICES in study.ARMS


def test_current_prices_are_every_existing_profile() -> None:
    for profile in (HISTORICAL_V0, CANONICAL):
        assert (
            profile.retention_price_baseline,
            profile.retention_price_node,
            profile.dormancy_retention_factor,
        ) == study.CURRENT_PRICES


def test_seed_lists_are_disjoint_from_every_other_study() -> None:
    lists = (study.PILOT_SEEDS, study.SELECTION_SEEDS, study.CONFIRMATION_SEEDS)
    union = set().union(*lists)
    assert len(union) == sum(map(len, lists))
    others = (
        set(transfer.DEVELOPMENT_SEEDS)
        | set(transfer.CONFIRMATION_SEEDS)
        | set(establishment.SELECTION_SEEDS)
        | set(establishment.CONFIRMATION_SEEDS)
        | {127}
    )
    assert not union & others


def test_the_record_matches_the_frozen_constants() -> None:
    spec = load_experiment_file(
        "experiments/learning/metabolic-retention-price-calibration-v1/experiment.toml"
    )
    frozen = spec.extra_params["retention"]
    assert spec.protocol == study.PROTOCOL
    assert tuple(spec.seeds) == study.CONFIRMATION_SEEDS
    assert tuple(frozen["pilot_seeds"]) == study.PILOT_SEEDS
    assert tuple(frozen["selection_seeds"]) == study.SELECTION_SEEDS
    assert tuple(frozen["baseline_prices"]) == study.BASELINE_PRICES
    assert tuple(frozen["node_prices"]) == study.NODE_PRICES
    assert tuple(frozen["dormancy_factors"]) == study.DORMANCY_FACTORS
    assert tuple(frozen["current_prices"]) == study.CURRENT_PRICES
    assert frozen["horizon"] == study.HORIZON and frozen["body_energy"] == study.BODY_ENERGY
    assert frozen["min_alive_seeds"] == study.MIN_ALIVE_SEEDS
    assert frozen["min_seeds_not_worse"] == study.MIN_SEEDS_NOT_WORSE
    assert frozen["min_t_stable_reduction"] == study.MIN_T_STABLE_REDUCTION
    assert frozen["max_retained_growth"] == study.MAX_RETAINED_GROWTH


def test_default_prices_reproduce_the_historical_formula() -> None:
    assert MemoryDomain.retained_units(drift_baseline_count=7, cognitive_node_count=28) == (
        7 * 0.001 + 28 * 0.0005
    )
    dormant = MemoryDomain.retained_units(
        drift_baseline_count=10, cognitive_node_count=0, dormant=True, dormancy_factor=0.25
    )
    assert dormant == pytest.approx(0.0025)


def test_coherence_rule_compares_full_capacity_retention_with_the_support() -> None:
    assert study.eligible((0.000125, 0.0005, 1.0), support_rate=0.04)
    assert not study.eligible((0.001, 0.0005, 1.0), support_rate=0.04)


def _run(seed: int, prices, survival: int, t_stable: int, retained: int = 100) -> dict:
    return {
        "seed": seed,
        "prices": list(prices),
        "survival": survival,
        "t_stable": t_stable,
        "retained_structure": retained,
    }


def test_selection_requires_eligibility_and_survival_then_breaks_ties_to_pressure() -> None:
    cheap, cheaper, current = (
        (0.00025, 0.00025, 1.0),
        (0.000125, 0.000125, 0.25),
        study.CURRENT_PRICES,
    )
    runs = (
        [_run(s, current, 2000, 100) for s in range(8)]  # fastest but ineligible
        + [_run(s, cheap, 2000, 400) for s in range(8)]
        + [_run(s, cheaper, 2000, 400) for s in range(8)]
    )
    selection = study.select_prices(runs, support_rate=0.08)
    assert selection["selected"] == list(cheap)
    dying = [_run(s, cheap, 1500 if s < 3 else 2000, 300) for s in range(8)]
    assert study.select_prices(dying, support_rate=0.08)["selected"] is None


def test_confirmation_requires_all_criteria() -> None:
    sel = (0.00025, 0.00025, 1.0)
    longer = [
        (_run(s, study.CURRENT_PRICES, 900, 2000), _run(s, sel, 2000, 800)) for s in range(12)
    ]
    assert study.confirmation_outcome(longer)["outcome"] == "SUPPORTED"
    hoarding = [
        (_run(s, study.CURRENT_PRICES, 900, 2000, 100), _run(s, sel, 2000, 800, 300))
        for s in range(12)
    ]
    assert study.confirmation_outcome(hoarding)["outcome"] == "NOT SUPPORTED"
    worse = [(_run(s, study.CURRENT_PRICES, 2000, 900), _run(s, sel, 1200, 900)) for s in range(12)]
    assert study.confirmation_outcome(worse)["outcome"] == "NOT SUPPORTED"


def test_no_qualifying_arm_or_current_prices_mean_no_change() -> None:
    assert study.run_confirmation_stage(None, 0.08, seeds=(1,))["outcome"] == "NO CHANGE"
    assert study.run_confirmation_stage(study.CURRENT_PRICES, 0.08, seeds=(1,))["outcome"] == (
        "NO CHANGE"
    )


def test_mechanics_one_short_run_under_bounded_support() -> None:
    run = study.run_one(7, (0.000125, 0.000125, 0.25), support_rate=0.08, horizon=40)
    assert 1 <= run["survival"] <= 40 and 1 <= run["t_stable"] <= 40
    assert 0.0 <= run["retention_share"] <= 1.0


def test_selection_parts_cover_every_pair_once_and_merge_checks_support() -> None:
    parts = [study.selection_part_pairs(index) for index in range(study.SELECTION_PARTS)]
    flat = [pair for part in parts for pair in part]
    assert sorted(flat) == sorted(study.SELECTION_PAIRS) and len(set(flat)) == len(flat)
    support = {"support_rate": 0.08}

    def fake(index: int, rate: float = 0.08) -> dict:
        runs = [_run(seed, arm, 2000, 500) for arm, seed in study.selection_part_pairs(index)]
        return {"part": index, "complete": True, "support_rate": rate, "runs": runs}

    merged = study.merge_selection(support, [fake(i) for i in range(study.SELECTION_PARTS)])
    assert merged["support"] == support
    with pytest.raises(ValueError):
        study.merge_selection(support, [fake(0, rate=0.09)] + [fake(i) for i in range(1, 8)])
