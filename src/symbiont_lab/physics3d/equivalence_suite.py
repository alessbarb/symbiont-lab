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

from .equivalence import EquivalenceRunConfig, equivalent, first_divergence, run_digests


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
    min_training_windows: int
    coverage: tuple[str, ...]


def load_suite(path: Path) -> tuple[str, tuple[Scenario, ...]]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    root = path.parent
    scenarios = []
    for raw in data.get("scenario", []):
        scenarios.append(
            Scenario(
                scenario_id=str(raw["id"]),
                snapshot=(root / str(raw["snapshot"])).resolve(),
                body_kind=str(raw["body_kind"]),
                ticks=int(raw["ticks"]),
                seed=int(raw.get("seed", 42)),
                training=bool(raw.get("training", False)),
                train_interval=int(raw.get("train_interval", 32)),
                min_training_windows=int(raw.get("min_training_windows", 0)),
                coverage=tuple(str(x) for x in raw.get("coverage", [])),
            )
        )
    return str(data["suite_id"]), tuple(scenarios)


def _finite_result(result: dict) -> bool:
    def walk(value) -> bool:
        if isinstance(value, float):
            return math.isfinite(value)
        if isinstance(value, dict):
            return all(walk(v) for v in value.values())
        if isinstance(value, (list, tuple)):
            return all(walk(v) for v in value)
        return True
    return walk(result)


def run_once(scenario: Scenario) -> dict:
    try:
        verify_snapshot(scenario.snapshot)
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
    )
    try:
        first = run_digests(scenario.snapshot, config=config)
        second = run_digests(scenario.snapshot, config=config)
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

    if scenario.training and scenario.min_training_windows:
        minimum_ticks = scenario.train_interval * scenario.min_training_windows
        if scenario.ticks < minimum_ticks:
            return {
                "status": EquivalenceStatus.NOT_ASSESSABLE_MISSING_EVENT,
                "reason": f"horizon {scenario.ticks} < {minimum_ticks} ticks of requested coverage",
            }
        observed = int(first.get("private_model_transitions", 0))
        if observed < scenario.min_training_windows:
            return {
                "status": EquivalenceStatus.NOT_ASSESSABLE_MISSING_EVENT,
                "reason": (
                    f"observed {observed} private-model lifecycle transitions; "
                    f"{scenario.min_training_windows} required"
                ),
            }
    return {"status": EquivalenceStatus.PASS, "result": first}


def compare(scenario: Scenario, baseline: dict, candidate: dict) -> dict:
    if baseline.get("status") != EquivalenceStatus.PASS:
        return {"status": baseline.get("status"), "reason": baseline.get("reason")}
    if candidate.get("status") != EquivalenceStatus.PASS:
        return {"status": candidate.get("status"), "reason": candidate.get("reason")}
    a, b = baseline["result"], candidate["result"]
    if equivalent(a, b):
        return {"status": EquivalenceStatus.PASS, "first_divergence": None}
    return {
        "status": EquivalenceStatus.FAIL_CAUSAL_DIVERGENCE,
        "first_divergence": first_divergence(a, b),
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
