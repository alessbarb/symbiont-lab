"""Locks the preregistered W01/W02 protocol (experiments/world/genesis-v1)
against regression: the runner must keep executing and keep returning the
same *shape* of result deterministically. It does not assert a scientific
conclusion -- H0 was not rejected for either gate (see audit.md) and this
test must not silently start asserting the opposite as behavior drifts.
"""

import importlib.util
import sys
from pathlib import Path

_MODULE_PATH = (
    Path(__file__).resolve().parents[4] / "experiments" / "world" / "genesis-v1" / "run_w01_w02.py"
)
_spec = importlib.util.spec_from_file_location("run_w01_w02", _MODULE_PATH)
run_w01_w02 = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("run_w01_w02", run_w01_w02)
_spec.loader.exec_module(run_w01_w02)


def test_w01_is_deterministic_for_the_same_seed_and_policy():
    a = run_w01_w02.run_one(101, "cognitive")
    b = run_w01_w02.run_one(101, "cognitive")
    assert a["action_counts"] == b["action_counts"]
    assert a["composite_score"] == b["composite_score"]


def test_w01_reports_a_result_for_every_preregistered_seed():
    result = run_w01_w02.w01()
    seeds_covered = {r["seed"] for r in result["results"]}
    assert seeds_covered == set(run_w01_w02.SEEDS)
    assert isinstance(result["reject_h0"], bool)


def test_w02_identical_clone_is_a_pure_determinism_check():
    result = run_w01_w02.w02(seed=101)
    assert result["identical_clone"]["diverges"] is False


def test_w02_distinct_history_result_is_reproducible():
    a = run_w01_w02.w02(seed=101)
    b = run_w01_w02.w02(seed=101)
    assert a["distinct_history"]["diverges"] == b["distinct_history"]["diverges"]
