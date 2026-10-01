"""Verify the pinned Python runtime before executing a scientific entry point."""

from __future__ import annotations

import json
import os
import runpy
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from .manifest import ExecutionFingerprint


def run_verified(argv: Sequence[str]) -> None:
    """Verify this child against launcher declarations, then run a Python target."""
    expected_data = os.environ.get("SYMBIONT_EXPECTED_EXECUTION_FINGERPRINT")
    config_data = os.environ.get("SYMBIONT_EFFECTIVE_CONFIG")
    experiment_id = os.environ.get("SYMBIONT_EXPERIMENT_ID")
    seed = os.environ.get("SYMBIONT_SEED")
    if not expected_data or config_data is None or experiment_id is None or seed is None:
        raise RuntimeError("scientific launcher did not provide an execution declaration")
    declared = ExecutionFingerprint(**json.loads(expected_data))
    actual = ExecutionFingerprint.capture(
        declared.repo_root,
        effective_config=json.loads(config_data),
        experiment_id=experiment_id,
        seed=int(seed),
    )
    actual.assert_matches_declared(declared)

    if len(argv) < 2:
        raise RuntimeError("verified child requires a Python target")
    mode, target, *target_args = argv
    if mode == "script":
        sys.argv = [target, *target_args]
        sys.path[0] = str(Path(target).absolute().parent)
        runpy.run_path(target, run_name="__main__")
    elif mode == "module":
        sys.argv = [target, *target_args]
        runpy.run_module(target, run_name="__main__", alter_sys=True)
    elif mode == "code":
        sys.argv = ["-c", *target_args]
        sys.path[0] = ""
        exec(compile(target, "<string>", "exec"), {"__name__": "__main__", "__file__": "<string>"})
    else:
        raise RuntimeError(f"unsupported Python target mode: {mode}")


def capture_fingerprint(
    *,
    repo_root: str,
    effective_config: str,
    experiment_id: str,
    seed: int,
) -> dict[str, object]:
    """Capture the pinned source runtime declaration for the parent launcher."""
    fingerprint = ExecutionFingerprint.capture(
        repo_root,
        effective_config=json.loads(effective_config),
        experiment_id=experiment_id,
        seed=seed,
    )
    if not fingerprint.is_hermetic_to(repo_root):
        raise RuntimeError("scientific process resolves packages outside its pinned checkout")
    return asdict(fingerprint)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--capture":
        print(
            json.dumps(
                capture_fingerprint(
                    repo_root=sys.argv[2],
                    effective_config=sys.argv[3],
                    experiment_id=sys.argv[4],
                    seed=int(sys.argv[5]),
                ),
                sort_keys=True,
            )
        )
    else:
        run_verified(sys.argv[1:])
