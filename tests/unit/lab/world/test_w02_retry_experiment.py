"""Locks the W02 retry protocol (experiments/world/genesis-v1) against
regression. Does not assert a scientific conclusion -- H0 was not
rejected (see audit-w02-retry.md)."""

import importlib.util
import sys
from pathlib import Path

_MODULE_PATH = (
    Path(__file__).resolve().parents[4]
    / "experiments"
    / "world"
    / "genesis-v1"
    / "run_w02_retry.py"
)
_spec = importlib.util.spec_from_file_location("run_w02_retry", _MODULE_PATH)
run_w02_retry = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("run_w02_retry", run_w02_retry)
_spec.loader.exec_module(run_w02_retry)


def test_w02_retry_is_deterministic():
    a = run_w02_retry.w02_retry(world_seed=101)
    b = run_w02_retry.w02_retry(world_seed=101)
    assert a["diverges"] == b["diverges"]
    assert a["replica_a"]["action_counts"] == b["replica_a"]["action_counts"]


def test_w02_retry_reports_a_boolean_verdict():
    result = run_w02_retry.w02_retry(world_seed=101)
    assert isinstance(result["diverges"], bool)
    assert isinstance(result["diverges_actions"], bool)
    assert isinstance(result["diverges_senses"], bool)
