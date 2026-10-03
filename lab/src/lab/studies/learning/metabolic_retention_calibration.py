"""Metabolic Retention Price Calibration v1: apparatus, stages and decision rule.

Implements the preregistration
``docs/design/experimentation/metabolic-retention-price-calibration-v1.md`` (r2).

The intervention is the price an organism pays per tick for retained structure
(per drift baseline, per cognitive node) and the share of it paid while dormant.
Evaluator truth (the arm, the energy support, every score) stays in this module;
the organism only receives its prices as configuration and energy through the
body's ordinary intake path. Pure helpers are what the contract tests exercise;
running seeds is a governed scientific run.
"""

from __future__ import annotations

import argparse
import itertools
import json
import statistics
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Sequence

from lab.studies.learning.agency_acquisition_body import CausalBody, build_subject
from lab.studies.learning.competence_establishment import stable_tick
from symbiont.core.embodiment.physiology import LivingBodyState
from symbiont.core.orchestration.runtime import OrganismDeadError
from symbiont.core.organism_profile import CANONICAL
from symbiont.modeling.private_runtime import PrivateModelOrganismRuntime
from symbiont.sensory.limits import SensoryLimits

PROTOCOL = "learning.metabolic-retention-price-calibration"
ACTUATORS = 4
BASELINE_PRICES = (0.001, 0.0005, 0.00025, 0.000125)
NODE_PRICES = (0.0005, 0.00025, 0.000125)
DORMANCY_FACTORS = (1.0, 0.5, 0.25)
CURRENT_PRICES = (0.001, 0.0005, 1.0)
ARMS = tuple(itertools.product(BASELINE_PRICES, NODE_PRICES, DORMANCY_FACTORS))
PILOT_SEEDS = (3083, 3089, 3109)
SELECTION_SEEDS = (3001, 3011, 3019, 3023, 3037, 3041, 3049, 3061)
CONFIRMATION_SEEDS = (4001, 4003, 4007, 4013, 4019, 4021, 4027, 4049, 4051, 4057, 4073, 4079)

# Frozen parameters (preregistration §4-§8, r2).
HORIZON = 2000
BODY_ENERGY = 4.0
SUPPORT_WINDOW = 200
SUPPORT_CEILING_FRACTION = 0.9
MIN_ALIVE_SEEDS = 6
MIN_SEEDS_NOT_WORSE = 9
MIN_T_STABLE_REDUCTION = 0.10
MAX_RETAINED_GROWTH = 2.0

# Execution only, not protocol: the support rule runs first as its own governed
# run, then the selection stage as SELECTION_PARTS governed runs, each a fixed
# interleaved slice of every (arm, seed) pair under that support rate. The merged
# result is identical to one process: runs are independent and deterministic.
SELECTION_PARTS = 8
SELECTION_PAIRS = tuple((arm, seed) for arm in ARMS for seed in SELECTION_SEEDS)


def eligible(prices: Sequence[float], support_rate: float) -> bool:
    """Coherence constraint (§6, r2): retention at full sensory capacity, active,
    costs no more than the energy support."""
    return SensoryLimits().max_active_sensors * prices[0] <= support_rate


def _subject(seed: int, prices: Sequence[float]) -> tuple[Any, CausalBody]:
    body = CausalBody(actuator_count=ACTUATORS, seed=seed)
    runtime = build_subject(
        body,
        organism_id=f"retention-calibration-{seed}",
        runtime_class=PrivateModelOrganismRuntime,
        profile=CANONICAL,
        living_body_state=LivingBodyState(energy_reserve=BODY_ENERGY, max_energy=BODY_ENERGY),
        retention_price_baseline=prices[0],
        retention_price_node=prices[1],
        dormancy_retention_factor=prices[2],
    )
    return runtime, body


def measure_support(seeds: Sequence[int] = PILOT_SEEDS) -> dict[str, Any]:
    """Support rule (§4, r2): the median over pilot seeds of a newborn's mean
    energy spend per tick over ticks 1-200 under the current prices, measured
    by refilling the body to full after every tick."""
    means = []
    for seed in seeds:
        runtime, body = _subject(seed, CURRENT_PRICES)
        state = runtime._living_body_state
        spent = []
        for _tick in range(SUPPORT_WINDOW):
            runtime.tick(include_observability=False)
            body.advance(runtime.last_actuations)
            spent.append(state.max_energy - state.energy_reserve)
            runtime.metabolism.intake_untyped(state.max_energy - state.energy_reserve)
        means.append(statistics.fmean(spent))
    return {
        "pilot_seeds": list(seeds),
        "mean_spend_per_tick": dict(zip(map(str, seeds), means)),
        "support_rate": statistics.median(means),
    }


def run_one(
    seed: int,
    prices: Sequence[float],
    support_rate: float,
    *,
    horizon: int = HORIZON,
) -> dict[str, Any]:
    """One newborn canonical organism with ``prices`` under bounded support."""
    runtime, body = _subject(seed, prices)
    state = runtime._living_body_state
    valid: list[bool] = []
    retention_spend = 0.0
    total_spend = 0.0
    death = None
    for tick in range(1, horizon + 1):
        room = SUPPORT_CEILING_FRACTION * state.max_energy - state.energy_reserve
        if room > 0.0:
            runtime.metabolism.intake_untyped(min(support_rate, room))
        before = state.energy_reserve
        try:
            runtime.tick(include_observability=False)
        except OrganismDeadError:
            death = tick
            break
        body.advance(runtime.last_actuations)
        total_spend += max(0.0, before - state.energy_reserve)
        retention_spend += runtime._memory_domain.retained_units(
            drift_baseline_count=len(runtime._drift_baselines),
            cognitive_node_count=(
                len(runtime.cognitive_bridge.graph.nodes) if runtime.cognitive_bridge else 0
            ),
            baseline_price=prices[0],
            node_price=prices[1],
        )
        valid.append(
            any(
                binding.status.value == "valid"
                for binding in runtime._action_domain.execution_bindings.items
            )
        )
        if not state.alive:
            death = tick
            break
    survival = death if death is not None else horizon
    padded = valid + [False] * (horizon - len(valid))
    return {
        "seed": seed,
        "prices": list(prices),
        "survival": survival,
        "t_stable": stable_tick(padded),
        "retained_structure": len(runtime._drift_baselines)
        + (len(runtime.cognitive_bridge.graph.nodes) if runtime.cognitive_bridge else 0),
        "retention_share": (retention_spend / total_spend) if total_spend > 0.0 else 0.0,
    }


def select_prices(runs: Sequence[dict[str, Any]], support_rate: float) -> dict[str, Any]:
    """Selection rule (§7): among eligible arms alive at the horizon on at least
    MIN_ALIVE_SEEDS seeds, the smallest median T_stable; ties to the higher
    baseline price, then node price, then dormancy factor."""
    by_arm: dict[tuple[float, float, float], list[dict[str, Any]]] = {}
    for run in runs:
        by_arm.setdefault(tuple(run["prices"]), []).append(run)
    summary = {}
    for arm, items in by_arm.items():
        summary[arm] = {
            "eligible": eligible(arm, support_rate),
            "alive_at_horizon": sum(r["survival"] >= HORIZON for r in items),
            "median_survival": statistics.median(r["survival"] for r in items),
            "median_t_stable": statistics.median(r["t_stable"] for r in items),
            "median_retained_structure": statistics.median(r["retained_structure"] for r in items),
        }
    qualifying = [
        arm
        for arm, values in summary.items()
        if values["eligible"] and values["alive_at_horizon"] >= MIN_ALIVE_SEEDS
    ]
    selected = (
        min(
            qualifying,
            key=lambda arm: (summary[arm]["median_t_stable"], -arm[0], -arm[1], -arm[2]),
        )
        if qualifying
        else None
    )
    return {
        "selected": list(selected) if selected is not None else None,
        "arms": {"/".join(map(str, arm)): values for arm, values in sorted(summary.items())},
    }


def confirmation_outcome(pairs: Sequence[tuple[dict[str, Any], dict[str, Any]]]) -> dict[str, Any]:
    """Decision rule (§8) over (current, selected) runs paired by seed."""
    not_worse = sum(selected["survival"] >= current["survival"] for current, selected in pairs)
    survival_current = statistics.median(c["survival"] for c, _ in pairs)
    survival_selected = statistics.median(s["survival"] for _, s in pairs)
    t_current = statistics.median(c["t_stable"] for c, _ in pairs)
    t_selected = statistics.median(s["t_stable"] for _, s in pairs)
    retained_current = statistics.median(c["retained_structure"] for c, _ in pairs)
    retained_selected = statistics.median(s["retained_structure"] for _, s in pairs)
    longer = survival_selected > survival_current
    equal_but_faster = (
        survival_selected == survival_current == HORIZON
        and t_current > 0
        and (t_current - t_selected) / t_current >= MIN_T_STABLE_REDUCTION
    )
    supported = (
        not_worse >= MIN_SEEDS_NOT_WORSE
        and (longer or equal_but_faster)
        and retained_selected <= MAX_RETAINED_GROWTH * retained_current
    )
    return {
        "seeds_not_worse": not_worse,
        "median_survival": {"current": survival_current, "selected": survival_selected},
        "median_t_stable": {"current": t_current, "selected": t_selected},
        "median_retained_structure": {"current": retained_current, "selected": retained_selected},
        "outcome": "SUPPORTED" if supported else "NOT SUPPORTED",
    }


def selection_part_pairs(part: int, parts: int = SELECTION_PARTS) -> tuple:
    """The (arm, seed) pairs of one selection part: every ``parts``-th pair."""
    if not 0 <= part < parts:
        raise ValueError("selection part out of range")
    return SELECTION_PAIRS[part::parts]


def _run_pair(task: tuple) -> dict[str, Any]:
    (arm, seed), rate = task
    return run_one(seed, arm, rate)


def run_selection_part(
    part: int,
    support: dict[str, Any],
    output: Path,
    parts: int = SELECTION_PARTS,
    *,
    workers: int = 1,
) -> dict[str, Any]:
    """Run one part, rewriting ``output`` after every run so a stop keeps what ran.

    ``workers`` > 1 runs pairs in separate processes; every run is independent
    and deterministic, so the result does not depend on it.
    """
    pairs = selection_part_pairs(part, parts)
    rate = float(support["support_rate"])
    result: dict[str, Any] = {
        "protocol": PROTOCOL,
        "stage": "selection-part",
        "part": part,
        "parts": parts,
        "support_rate": rate,
        "pairs": len(pairs),
        "complete": False,
        "runs": [],
    }
    output.parent.mkdir(parents=True, exist_ok=True)

    def record(run: dict[str, Any]) -> None:
        result["runs"].append(run)
        result["runs"].sort(
            key=lambda run: SELECTION_PAIRS.index((tuple(run["prices"]), run["seed"]))
        )
        result["complete"] = len(result["runs"]) == len(pairs)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if workers <= 1:
        for item in [(pair, rate) for pair in pairs]:
            record(_run_pair(item))
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for run in pool.map(_run_pair, [(pair, rate) for pair in pairs]):
                record(run)
    return result


def merge_selection(support: dict[str, Any], parts: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Join complete parts run under one support rate, check coverage, then select."""
    if len(parts) != SELECTION_PARTS or sorted(p["part"] for p in parts) != list(
        range(SELECTION_PARTS)
    ):
        raise ValueError("selection needs every part exactly once")
    if not all(p.get("complete") for p in parts):
        raise ValueError("a selection part is incomplete")
    rate = float(support["support_rate"])
    if any(float(p["support_rate"]) != rate for p in parts):
        raise ValueError("selection parts ran under different support rates")
    runs = [run for p in parts for run in p["runs"]]
    covered = sorted((tuple(r["prices"]), r["seed"]) for r in runs)
    if covered != sorted(SELECTION_PAIRS):
        raise ValueError("selection parts do not cover every (arm, seed) pair exactly once")
    return {
        "protocol": PROTOCOL,
        "stage": "selection",
        "seeds": list(SELECTION_SEEDS),
        "support": support,
        **select_prices(runs, rate),
        "runs": runs,
    }


def run_confirmation_stage(
    selected: Sequence[float] | None,
    support_rate: float,
    seeds: Sequence[int] = CONFIRMATION_SEEDS,
) -> dict[str, Any]:
    if selected is None or tuple(selected) == CURRENT_PRICES:
        return {
            "protocol": PROTOCOL,
            "stage": "confirmation",
            "selected": list(selected) if selected is not None else None,
            "outcome": "NO CHANGE",
            "runs": [],
        }
    pairs = [
        (run_one(seed, CURRENT_PRICES, support_rate), run_one(seed, selected, support_rate))
        for seed in seeds
    ]
    return {
        "protocol": PROTOCOL,
        "stage": "confirmation",
        "seeds": list(seeds),
        "selected": list(selected),
        "support_rate": support_rate,
        **confirmation_outcome(pairs),
        "runs": [run for pair in pairs for run in pair],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("support", "selection-part", "select", "confirmation"))
    parser.add_argument("--support", type=Path, help="support.json from the support stage")
    parser.add_argument("--part", type=int, help="selection part, 0 to SELECTION_PARTS - 1")
    parser.add_argument("--parts", type=Path, nargs="+", help="every selection part file")
    parser.add_argument("--selection", type=Path, help="selection.json from the select stage")
    parser.add_argument("--workers", type=int, default=1, help="processes for selection parts")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.stage == "support":
        result = {"protocol": PROTOCOL, "stage": "support", **measure_support(), "runs": []}
    elif args.stage in ("selection-part", "select"):
        if args.support is None:
            parser.error(f"{args.stage} needs --support")
        support = json.loads(args.support.read_text(encoding="utf-8"))
        if args.stage == "selection-part":
            if args.part is None:
                parser.error("selection-part needs --part")
            result = run_selection_part(args.part, support, args.output, workers=args.workers)
            print(json.dumps({key: result[key] for key in result if key != "runs"}, indent=2))
            return 0
        if not args.parts:
            parser.error("select needs --parts")
        result = merge_selection(
            support, [json.loads(path.read_text(encoding="utf-8")) for path in args.parts]
        )
    else:
        if args.selection is None:
            parser.error("the confirmation stage needs --selection")
        selection = json.loads(args.selection.read_text(encoding="utf-8"))
        result = run_confirmation_stage(
            selection["selected"], float(selection["support"]["support_rate"])
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in result if key != "runs"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
