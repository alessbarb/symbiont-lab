"""Competence Establishment Evidence v1: apparatus, stages and decision rule.

Implements the preregistration
``docs/design/experimentation/competence-establishment-evidence-v1.md``.

The intervention is the organism's competence establishment gate (minimum
support ``S`` and minimum directional consistency ``C``). Evaluator truth (the
arm, every score) stays in this module; the organism only receives its gate as
configuration. Pure helpers (measures, selection, decision) are what the
contract tests exercise; running seeds is a governed scientific run.
"""

from __future__ import annotations

import argparse
import itertools
import json
import statistics
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Sequence

from symbiont.actuation.binding import BindingStatus
from symbiont.core.organism_profile import CANONICAL
from symbiont.modeling.private_runtime import PrivateModelOrganismRuntime
from symbiont_lab.studies.learning.agency_acquisition_body import CausalBody, build_subject

PROTOCOL = "learning.competence-establishment-evidence"
ACTUATORS = 4
SUPPORTS = (2, 3, 4, 5, 6, 8, 10, 12, 16)
CONSISTENCIES = (0.60, 0.70, 0.80)
CURRENT_GATE = (2, 0.60)
ARMS = tuple(itertools.product(SUPPORTS, CONSISTENCIES))
SELECTION_SEEDS = (1009, 1013, 1019, 1021, 1031, 1033, 1039, 1049)
CONFIRMATION_SEEDS = (2003, 2011, 2017, 2027, 2029, 2039, 2053, 2063, 2069, 2081, 2083, 2087)

# Frozen parameters (preregistration §4-§7).
HORIZON = 2000
STABLE_WINDOW = 200
MIN_SEEDS_IMPROVED = 9
MIN_MEDIAN_PAIRED_REDUCTION = 0.20

# Execution only, not protocol: the selection stage runs as SELECTION_PARTS
# governed runs, each a fixed interleaved slice of every (arm, seed) pair, so no
# single run approaches the wall-time limit. The merged result is identical to
# running every pair in one process: runs are independent and deterministic.
SELECTION_PARTS = 6
SELECTION_PAIRS = tuple((arm, seed) for arm in ARMS for seed in SELECTION_SEEDS)


def stable_tick(valid: Sequence[bool], *, window: int = STABLE_WINDOW) -> int:
    """First tick (1-based) from which a valid binding is held for ``window``
    consecutive ticks; the horizon ``len(valid)`` if there is none (censored)."""
    horizon = len(valid)
    run = 0
    for index, holding in enumerate(valid):
        run = run + 1 if holding else 0
        if run == window:
            return index - window + 2
    return horizon


def run_one(
    seed: int,
    min_support: int,
    min_consistency: float,
    *,
    horizon: int = HORIZON,
    window: int = STABLE_WINDOW,
) -> dict[str, Any]:
    """One newborn canonical organism with gate ``(S, C)`` in the causal Body."""
    body = CausalBody(actuator_count=ACTUATORS, seed=seed)
    runtime = build_subject(
        body,
        organism_id=f"competence-establishment-{seed}",
        runtime_class=PrivateModelOrganismRuntime,
        profile=CANONICAL,
        competence_min_support=min_support,
        competence_min_consistency=min_consistency,
    )
    action = runtime._action_domain
    development = action._competence_development
    valid: list[bool] = []
    ever_established: set[str] = set()
    for _tick in range(horizon):
        runtime.tick(include_observability=False)
        body.advance(runtime.last_actuations)
        valid.append(
            any(
                binding.status is BindingStatus.VALID for binding in action.execution_bindings.items
            )
        )
        if development is not None:
            ever_established.update(
                primitive.primitive_id for primitive in development.cognitive_primitives
            )
    established_now = (
        {primitive.primitive_id for primitive in development.cognitive_primitives}
        if development is not None
        else set()
    )
    first = next((index + 1 for index, holding in enumerate(valid) if holding), None)
    after_first = valid[first - 1 :] if first is not None else []
    return {
        "seed": seed,
        "min_support": min_support,
        "min_consistency": min_consistency,
        "horizon": horizon,
        "t_stable": stable_tick(valid, window=window),
        "t_first": first,
        "holding_fraction": (sum(after_first) / len(after_first)) if after_first else 0.0,
        "false_establishment_rate": (
            len(ever_established - established_now) / len(ever_established)
            if ever_established
            else 0.0
        ),
        "competences_ever_established": len(ever_established),
    }


def _arm_key(min_support: int, min_consistency: float) -> str:
    return f"S{min_support}-C{min_consistency:.2f}"


def select_arm(runs: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Selection rule (§6): smallest median T_stable; ties to smaller S, then C."""
    by_arm: dict[tuple[int, float], list[dict[str, Any]]] = {}
    for run in runs:
        by_arm.setdefault((run["min_support"], run["min_consistency"]), []).append(run)
    summary = {
        arm: {
            "median_t_stable": statistics.median(r["t_stable"] for r in items),
            "median_holding_fraction": statistics.median(r["holding_fraction"] for r in items),
            "median_false_establishment_rate": statistics.median(
                r["false_establishment_rate"] for r in items
            ),
            "seeds": len(items),
        }
        for arm, items in by_arm.items()
    }
    selected = min(summary, key=lambda arm: (summary[arm]["median_t_stable"], arm[0], arm[1]))
    return {
        "selected": {"min_support": selected[0], "min_consistency": selected[1]},
        "arms": {_arm_key(*arm): values for arm, values in sorted(summary.items())},
    }


def confirmation_outcome(pairs: Sequence[tuple[dict[str, Any], dict[str, Any]]]) -> dict[str, Any]:
    """Decision rule (§7) over (current, selected) runs paired by seed."""
    improved = sum(selected["t_stable"] < current["t_stable"] for current, selected in pairs)
    reductions = [
        (current["t_stable"] - selected["t_stable"]) / current["t_stable"]
        for current, selected in pairs
    ]
    median_reduction = statistics.median(reductions)
    holding_current = statistics.median(current["holding_fraction"] for current, _ in pairs)
    holding_selected = statistics.median(selected["holding_fraction"] for _, selected in pairs)
    supported = (
        improved >= MIN_SEEDS_IMPROVED
        and median_reduction >= MIN_MEDIAN_PAIRED_REDUCTION
        and holding_selected >= holding_current
    )
    return {
        "seeds_improved": improved,
        "median_paired_reduction": median_reduction,
        "median_holding_fraction": {"current": holding_current, "selected": holding_selected},
        "outcome": "SUPPORTED" if supported else "NOT SUPPORTED",
    }


def selection_part_pairs(part: int, parts: int = SELECTION_PARTS) -> tuple:
    """The (arm, seed) pairs of one selection part: every ``parts``-th pair."""
    if not 0 <= part < parts:
        raise ValueError("selection part out of range")
    return SELECTION_PAIRS[part::parts]


def _run_pair(pair: tuple) -> dict[str, Any]:
    (support, consistency), seed = pair
    return run_one(seed, support, consistency)


def run_selection_part(
    part: int, output: Path, parts: int = SELECTION_PARTS, *, workers: int = 1
) -> dict[str, Any]:
    """Run one part, rewriting ``output`` after every run so a stop keeps what ran.

    ``workers`` > 1 runs pairs in separate processes; every run is independent
    and deterministic, so the result does not depend on it.
    """
    pairs = selection_part_pairs(part, parts)
    result: dict[str, Any] = {
        "protocol": PROTOCOL,
        "stage": "selection-part",
        "part": part,
        "parts": parts,
        "pairs": len(pairs),
        "complete": False,
        "runs": [],
    }
    output.parent.mkdir(parents=True, exist_ok=True)

    def record(run: dict[str, Any]) -> None:
        result["runs"].append(run)
        result["runs"].sort(
            key=lambda run: SELECTION_PAIRS.index(
                ((run["min_support"], run["min_consistency"]), run["seed"])
            )
        )
        result["complete"] = len(result["runs"]) == len(pairs)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if workers <= 1:
        for item in pairs:
            record(_run_pair(item))
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for run in pool.map(_run_pair, pairs):
                record(run)
    return result


def merge_selection(parts: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Join complete parts, check they cover every pair exactly once, then select."""
    if len(parts) != SELECTION_PARTS or sorted(p["part"] for p in parts) != list(
        range(SELECTION_PARTS)
    ):
        raise ValueError("selection needs every part exactly once")
    if not all(p.get("complete") for p in parts):
        raise ValueError("a selection part is incomplete")
    runs = [run for p in parts for run in p["runs"]]
    covered = sorted(((r["min_support"], r["min_consistency"]), r["seed"]) for r in runs)
    if covered != sorted(SELECTION_PAIRS):
        raise ValueError("selection parts do not cover every (arm, seed) pair exactly once")
    return {
        "protocol": PROTOCOL,
        "stage": "selection",
        "seeds": list(SELECTION_SEEDS),
        **select_arm(runs),
        "runs": runs,
    }


def run_confirmation_stage(
    selected: tuple[int, float], seeds: Sequence[int] = CONFIRMATION_SEEDS
) -> dict[str, Any]:
    if tuple(selected) == CURRENT_GATE:
        return {
            "protocol": PROTOCOL,
            "stage": "confirmation",
            "selected": list(selected),
            "outcome": "NO CHANGE",
            "runs": [],
        }
    pairs = [(run_one(seed, *CURRENT_GATE), run_one(seed, *selected)) for seed in seeds]
    return {
        "protocol": PROTOCOL,
        "stage": "confirmation",
        "seeds": list(seeds),
        "selected": list(selected),
        **confirmation_outcome(pairs),
        "runs": [run for pair in pairs for run in pair],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("selection-part", "select", "confirmation"))
    parser.add_argument("--part", type=int, help="selection part, 0 to SELECTION_PARTS - 1")
    parser.add_argument("--parts", type=Path, nargs="+", help="every selection part file")
    parser.add_argument("--selection", type=Path, help="selection.json from the select stage")
    parser.add_argument("--workers", type=int, default=1, help="processes for selection parts")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.stage == "selection-part":
        if args.part is None:
            parser.error("selection-part needs --part")
        result = run_selection_part(args.part, args.output, workers=args.workers)
        print(json.dumps({key: result[key] for key in result if key != "runs"}, indent=2))
        return 0
    if args.stage == "select":
        if not args.parts:
            parser.error("select needs --parts")
        result = merge_selection(
            [json.loads(path.read_text(encoding="utf-8")) for path in args.parts]
        )
    else:
        if args.selection is None:
            parser.error("the confirmation stage needs --selection")
        chosen = json.loads(args.selection.read_text(encoding="utf-8"))["selected"]
        result = run_confirmation_stage(
            (int(chosen["min_support"]), float(chosen["min_consistency"]))
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in result if key != "runs"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
