"""Versioned multi-scenario causal equivalence suite."""

from __future__ import annotations

import argparse
import json
import math
import tomllib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from symbiont_lab.experiments.snapshot_archive import verify_snapshot

from .equivalence import (
    DeterminismContractError,
    EquivalenceRunConfig,
    equivalent,
    first_divergence,
    run_digests,
)


class EquivalenceStatus(StrEnum):
    PASS = "PASS"
    FAIL_CAUSAL_DIVERGENCE = "FAIL_CAUSAL_DIVERGENCE"
    NOT_ASSESSABLE_NONDETERMINISM = "NOT_ASSESSABLE_NONDETERMINISM"
    NOT_ASSESSABLE_MISSING_EVENT = "NOT_ASSESSABLE_MISSING_EVENT"
    NOT_ASSESSABLE_INVALID_SNAPSHOT = "NOT_ASSESSABLE_INVALID_SNAPSHOT"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class Scenario:
    scenario_id: str
    snapshot: Path
    body_kind: str
    ticks: int
    seed: int
    training: bool
    train_interval: int
    min_training_completions: int
    require_promotion_event: bool
    coverage: tuple[str, ...]


def load_suite(path: Path) -> tuple[str, tuple[Scenario, ...]]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    root = path.parent
    scenarios: list[Scenario] = []
    for raw in data.get("scenario", []):
        minimum = int(raw.get("min_training_completions", raw.get("min_training_windows", 0)))
        scenarios.append(
            Scenario(
                scenario_id=str(raw["id"]),
                snapshot=(root / str(raw["snapshot"])).resolve(),
                body_kind=str(raw["body_kind"]),
                ticks=int(raw["ticks"]),
                seed=int(raw.get("seed", 42)),
                training=bool(raw.get("training", False)),
                train_interval=int(raw.get("train_interval", 32)),
                min_training_completions=minimum,
                require_promotion_event=bool(raw.get("require_promotion_event", False)),
                coverage=tuple(str(x) for x in raw.get("coverage", [])),
            )
        )
    return str(data["suite_id"]), tuple(scenarios)


def _finite_result(result: dict) -> bool:
    def walk(value: object) -> bool:
        if isinstance(value, float):
            return math.isfinite(value)
        if isinstance(value, dict):
            return all(walk(v) for v in value.values())
        if isinstance(value, (list, tuple)):
            return all(walk(v) for v in value)
        return True

    return walk(result)


def _coverage_failure(scenario: Scenario, result: dict) -> str | None:
    if scenario.training:
        observed = int(result.get("training_completions", 0))
        if observed < scenario.min_training_completions:
            return (
                f"observed {observed} completed private-model trainings; "
                f"{scenario.min_training_completions} required"
            )
    if scenario.require_promotion_event and not result.get("promotion_events"):
        return "no private-model promotion event was observed"
    return None


def run_once(scenario: Scenario) -> dict:
    try:
        snapshot_manifest = verify_snapshot(scenario.snapshot)
    except Exception as exc:
        return {
            "status": EquivalenceStatus.NOT_ASSESSABLE_INVALID_SNAPSHOT,
            "reason": str(exc),
        }

    config = EquivalenceRunConfig(
        ticks=scenario.ticks,
        body_kind=scenario.body_kind,
        seed=scenario.seed,
        training=scenario.training,
        synchronous_training=True,
        train_interval=scenario.train_interval,
        torch_threads=1,
        torch_interop_threads=1,
        deterministic_algorithms=True,
    )
    try:
        first = run_digests(scenario.snapshot, config=config)
        second = run_digests(scenario.snapshot, config=config)
    except DeterminismContractError as exc:
        return {
            "status": EquivalenceStatus.NOT_ASSESSABLE_NONDETERMINISM,
            "reason": str(exc),
        }
    except Exception as exc:
        return {"status": EquivalenceStatus.ERROR, "reason": f"{type(exc).__name__}: {exc}"}

    if not _finite_result(first) or not _finite_result(second):
        return {
            "status": EquivalenceStatus.NOT_ASSESSABLE_NONDETERMINISM,
            "reason": "non-finite output",
        }
    if not equivalent(first, second):
        return {
            "status": EquivalenceStatus.NOT_ASSESSABLE_NONDETERMINISM,
            "reason": "reference snapshot is not deterministic under this scenario",
            "first_divergence": first_divergence(first, second),
        }

    failure = _coverage_failure(scenario, first)
    if failure is not None:
        return {
            "status": EquivalenceStatus.NOT_ASSESSABLE_MISSING_EVENT,
            "reason": failure,
            "training_completions": int(first.get("training_completions", 0)),
            "promotion_events": len(first.get("promotion_events", [])),
        }

    return {
        "status": EquivalenceStatus.PASS,
        "snapshot": {
            "snapshot_id": snapshot_manifest.get("snapshot_id"),
            "organism_id": snapshot_manifest.get("organism_id"),
            "captured_tick": snapshot_manifest.get("captured_tick"),
            "body_kind": snapshot_manifest.get("body_kind")
            or snapshot_manifest.get("body_kind_from_state"),
            "organism_sha256": snapshot_manifest.get("organism_sha256"),
            "body_sha256": snapshot_manifest.get("body_sha256"),
            "models_tree_sha256": snapshot_manifest.get("models_tree_sha256"),
        },
        "coverage": {
            "declared": list(scenario.coverage),
            "training_completions": int(first.get("training_completions", 0)),
            "promotion_events": len(first.get("promotion_events", [])),
        },
        "result": first,
    }


def compare(scenario: Scenario, baseline: dict, candidate: dict) -> dict:
    if baseline.get("status") != EquivalenceStatus.PASS:
        return {
            "status": baseline.get("status"),
            "reason": baseline.get("reason"),
        }
    if candidate.get("status") != EquivalenceStatus.PASS:
        return {
            "status": candidate.get("status"),
            "reason": candidate.get("reason"),
        }
    a, b = baseline["result"], candidate["result"]
    if equivalent(a, b):
        return {
            "status": EquivalenceStatus.PASS,
            "first_divergence": None,
            "coverage": baseline.get("coverage"),
            "snapshot": baseline.get("snapshot"),
        }
    return {
        "status": EquivalenceStatus.FAIL_CAUSAL_DIVERGENCE,
        "first_divergence": first_divergence(a, b),
        "baseline_active_model": (a.get("registry_final") or {}).get("active_model_id"),
        "candidate_active_model": (b.get("registry_final") or {}).get("active_model_id"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("suite", type=Path)
    parser.add_argument("scenario")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    _, scenarios = load_suite(args.suite)
    scenario = next((s for s in scenarios if s.scenario_id == args.scenario), None)
    if scenario is None:
        raise SystemExit(f"unknown scenario: {args.scenario}")
    payload = run_once(scenario)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    return 0 if payload["status"] == EquivalenceStatus.PASS else 2


if __name__ == "__main__":
    raise SystemExit(main())
