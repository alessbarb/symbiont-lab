#!/usr/bin/env python3
"""Validate a complete governed E8 campaign from receipt/result JSON pairs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PREREGISTERED_SEEDS = (101, 127, 149, 173, 211, 257, 307, 353, 401, 457)


def aggregate(pairs: list[tuple[Path, Path]]) -> dict[str, Any]:
    if len(pairs) != len(PREREGISTERED_SEEDS):
        raise ValueError("campaign must contain exactly ten receipt/result pairs")
    validated: dict[int, dict[str, Any]] = {}
    candidate_commits: set[str] = set()
    for receipt_path, result_path in pairs:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        result = json.loads(result_path.read_text(encoding="utf-8"))
        seed = int(result["seeds"][0])
        if result["seeds"] != [seed] or seed not in PREREGISTERED_SEEDS:
            raise ValueError(f"result must contain exactly one preregistered seed: {result_path}")
        if seed in validated:
            raise ValueError(f"duplicate seed result: {seed}")
        if receipt.get("seed") != seed:
            raise ValueError(f"receipt/result seed mismatch for seed {seed}")
        if receipt.get("state") != "complete" or receipt.get("returncode") != 0:
            raise ValueError(f"receipt is not a successful completed run for seed {seed}")
        if receipt.get("scientific_input") != {
            "mode": "protocol-generated",
            "external_state": False,
        }:
            raise ValueError(f"receipt input provenance is not protocol-generated for seed {seed}")
        candidate_commits.add(str(receipt.get("commit", "")))
        fingerprint = receipt.get("execution_fingerprint", {})
        if fingerprint.get("git_commit") != receipt.get("commit"):
            raise ValueError(f"receipt fingerprint commit mismatch for seed {seed}")
        if (
            result.get("integrity_pass") is not True
            or result.get("replay_deterministic") is not True
        ):
            raise ValueError(f"integrity/replay gate failed for seed {seed}")
        if result.get("steps") != 300 or result.get("invariant_rate") not in (0.0, 1.0):
            raise ValueError(f"invalid one-seed E8 result for seed {seed}")
        validated[seed] = {
            "seed": seed,
            "invariant_rate": result["invariant_rate"],
            "replay_deterministic": result["replay_deterministic"],
            "integrity_pass": result["integrity_pass"],
            "receipt": str(receipt_path),
            "result": str(result_path),
        }
    if set(validated) != set(PREREGISTERED_SEEDS):
        missing = sorted(set(PREREGISTERED_SEEDS) - set(validated))
        raise ValueError(f"campaign is missing preregistered seeds: {missing}")
    if len(candidate_commits) != 1 or "" in candidate_commits:
        raise ValueError("all receipts must name one common non-empty candidate commit")
    ordered = [validated[seed] for seed in PREREGISTERED_SEEDS]
    return {
        "candidate_commit": next(iter(candidate_commits)),
        "seeds": ordered,
        "a8_pass": all(item["invariant_rate"] == 1.0 for item in ordered),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pair", action="append", nargs=2, metavar=("RECEIPT", "RESULT"), required=True
    )
    args = parser.parse_args()
    try:
        summary = aggregate([(Path(receipt), Path(result)) for receipt, result in args.pair])
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
