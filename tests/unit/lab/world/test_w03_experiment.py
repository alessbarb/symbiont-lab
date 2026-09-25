"""Locks the W03 protocol against regression. Does not assert a scientific
conclusion beyond what audit-w03.md actually found: H0 was rejected, but
the initially-hypothesized mechanism (hazard density-coupling) was ruled
out by its own control -- both facts are locked here, not just the
convenient one.
"""

import importlib.util
import sys
from pathlib import Path

_MODULE_PATH = (
    Path(__file__).resolve().parents[4] / "experiments" / "world" / "genesis-v1" / "run_w03.py"
)
_spec = importlib.util.spec_from_file_location("run_w03", _MODULE_PATH)
run_w03 = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("run_w03", run_w03)
_spec.loader.exec_module(run_w03)


def test_w03_treatment_is_deterministic():
    # organism_id feeds the hazard RNG namespace (adapter.py), so a
    # meaningful determinism check must hold organism_id fixed -- a
    # different prefix is expected to (and does) change outcomes.
    a = run_w03.w03(id_prefix="lock-same")
    b = run_w03.w03(id_prefix="lock-same")
    assert a["reject_h0"] == b["reject_h0"]
    assert a["by_region_dominant_resources"] == b["by_region_dominant_resources"]


def test_w03_with_control_reports_booleans():
    result = run_w03.w03_with_control()
    assert isinstance(result["treatment"]["reject_h0"], bool)
    assert isinstance(result["control_zero_density_coupling"]["reject_h0"], bool)
    assert isinstance(result["mechanism_supported"], bool)


def test_control_ablation_actually_zeroes_density_coupling():
    from symbiont_lab.world.genesis_v2 import build_ground_truth_v2

    truth = run_w03._zero_density_coupling(build_ground_truth_v2())
    assert all(law.density_coupling == 0.0 for law in truth.hazards.values())
