"""Mechanical contract of Competence Establishment Evidence v1 (no scientific claim)."""

from __future__ import annotations

import pytest

import symbiont_lab.studies.embodiment.reembodiment_functional_transfer as transfer
import symbiont_lab.studies.learning.competence_establishment as study
from symbiont.actuation.competence import CompetenceEvidence, CompetenceGate, CompetenceMaturity
from symbiont.core.organism_profile import CANONICAL, HISTORICAL_V0
from symbiont_lab.experiments.loader import load_experiment_file

pytestmark = pytest.mark.experiment_contract


def test_grid_is_the_preregistered_one() -> None:
    assert study.SUPPORTS == (2, 3, 4, 5, 6, 8, 10, 12, 16)
    assert study.CONSISTENCIES == (0.60, 0.70, 0.80)
    assert len(study.ARMS) == 27 and study.CURRENT_GATE in study.ARMS


def test_seed_lists_are_disjoint_from_each_other_and_from_the_transfer_experiment() -> None:
    selection, confirmation = set(study.SELECTION_SEEDS), set(study.CONFIRMATION_SEEDS)
    assert len(selection) == 8 and len(confirmation) == 12 and not selection & confirmation
    used = set(transfer.DEVELOPMENT_SEEDS) | set(transfer.CONFIRMATION_SEEDS) | {127}
    assert not (selection | confirmation) & used


def test_the_record_matches_the_frozen_constants() -> None:
    spec = load_experiment_file(
        "experiments/learning/competence-establishment-evidence-v1/experiment.toml"
    )
    frozen = spec.extra_params["establishment"]
    assert spec.protocol == study.PROTOCOL
    assert tuple(spec.seeds) == study.CONFIRMATION_SEEDS
    assert tuple(frozen["selection_seeds"]) == study.SELECTION_SEEDS
    assert tuple(frozen["supports"]) == study.SUPPORTS
    assert tuple(frozen["consistencies"]) == study.CONSISTENCIES
    assert tuple(frozen["current_gate"]) == study.CURRENT_GATE
    assert frozen["horizon"] == study.HORIZON and frozen["stable_window"] == study.STABLE_WINDOW
    assert frozen["min_seeds_improved"] == study.MIN_SEEDS_IMPROVED
    assert frozen["min_median_paired_reduction"] == study.MIN_MEDIAN_PAIRED_REDUCTION


def test_current_gate_is_the_profile_gate_of_every_existing_version() -> None:
    for profile in (HISTORICAL_V0, CANONICAL):
        assert (profile.competence_min_support, profile.competence_min_consistency) == (
            study.CURRENT_GATE
        )
    assert (CompetenceGate().min_support, CompetenceGate().min_consistency) == study.CURRENT_GATE


def test_the_gate_moves_only_the_establishment_boundary() -> None:
    evidence = dict(
        support=3, reproducibility=0.9, controllability=0.5, directional_consistency=0.65
    )
    assert CompetenceEvidence("c", **evidence).maturity is CompetenceMaturity.ESTABLISHED
    strict_support = CompetenceEvidence("c", **evidence, gate=CompetenceGate(min_support=4))
    assert strict_support.maturity is CompetenceMaturity.EMERGING
    strict_consistency = CompetenceEvidence("c", **evidence, gate=CompetenceGate(2, 0.70))
    assert strict_consistency.maturity is CompetenceMaturity.EMERGING


@pytest.mark.parametrize(
    ("valid", "expected"),
    [
        ([True] * 5, 1),
        ([False, True, True, True, False], 2),
        ([True, False, True, True, True], 3),
        ([True, True, False, True, True], 5),  # censored: never 3 in a row
        ([False] * 5, 5),
    ],
)
def test_stable_tick_and_its_censoring(valid: list[bool], expected: int) -> None:
    assert study.stable_tick(valid, window=3) == expected


def _run(seed: int, support: int, consistency: float, t_stable: int, holding: float = 0.9) -> dict:
    return {
        "seed": seed,
        "min_support": support,
        "min_consistency": consistency,
        "t_stable": t_stable,
        "holding_fraction": holding,
        "false_establishment_rate": 0.0,
    }


def test_selection_takes_the_smallest_median_and_breaks_ties_to_the_lenient_gate() -> None:
    runs = (
        [_run(seed, 2, 0.60, 900) for seed in (1, 2, 3)]
        + [_run(seed, 6, 0.70, 400) for seed in (1, 2, 3)]
        + [_run(seed, 4, 0.80, 400) for seed in (1, 2, 3)]
    )
    selection = study.select_arm(runs)
    assert selection["selected"] == {"min_support": 4, "min_consistency": 0.80}
    assert set(selection["arms"]) == {"S2-C0.60", "S6-C0.70", "S4-C0.80"}


def test_confirmation_requires_all_three_criteria() -> None:
    better = [(_run(s, 2, 0.6, 1000, 0.5), _run(s, 4, 0.7, 500, 0.6)) for s in range(12)]
    assert study.confirmation_outcome(better)["outcome"] == "SUPPORTED"
    too_few = better[:8] + [(_run(s, 2, 0.6, 500), _run(s, 4, 0.7, 600)) for s in range(4)]
    assert study.confirmation_outcome(too_few)["outcome"] == "NOT SUPPORTED"
    small = [(_run(s, 2, 0.6, 1000), _run(s, 4, 0.7, 900)) for s in range(12)]
    assert study.confirmation_outcome(small)["outcome"] == "NOT SUPPORTED"
    holds_less = [(_run(s, 2, 0.6, 1000, 0.9), _run(s, 4, 0.7, 500, 0.5)) for s in range(12)]
    assert study.confirmation_outcome(holds_less)["outcome"] == "NOT SUPPORTED"


def test_selecting_the_current_gate_means_no_change_without_running() -> None:
    result = study.run_confirmation_stage(study.CURRENT_GATE, seeds=(1,))
    assert result["outcome"] == "NO CHANGE" and result["runs"] == []


def test_mechanics_one_short_run_applies_the_arm_gate() -> None:
    run = study.run_one(7, 4, 0.70, horizon=30, window=5)
    assert run["horizon"] == 30 and 1 <= run["t_stable"] <= 30
    assert 0.0 <= run["holding_fraction"] <= 1.0
    assert 0.0 <= run["false_establishment_rate"] <= 1.0


def test_selection_parts_cover_every_pair_once_and_merge_checks_it(tmp_path) -> None:
    parts = [study.selection_part_pairs(index) for index in range(study.SELECTION_PARTS)]
    flat = [pair for part in parts for pair in part]
    assert sorted(flat) == sorted(study.SELECTION_PAIRS) and len(set(flat)) == len(flat)
    assert {len(part) for part in parts} == {36}

    def fake(index: int, *, complete: bool = True, drop: bool = False) -> dict:
        runs = [_run(seed, *arm, 100) for arm, seed in study.selection_part_pairs(index)]
        return {"part": index, "complete": complete, "runs": runs[1:] if drop else runs}

    merged = study.merge_selection([fake(i) for i in range(study.SELECTION_PARTS)])
    assert merged["selected"] == {"min_support": 2, "min_consistency": 0.60}
    with pytest.raises(ValueError):
        study.merge_selection([fake(i) for i in range(study.SELECTION_PARTS - 1)])
    with pytest.raises(ValueError):
        study.merge_selection([fake(0, complete=False)] + [fake(i) for i in range(1, 6)])
    with pytest.raises(ValueError):
        study.merge_selection([fake(0, drop=True)] + [fake(i) for i in range(1, 6)])
