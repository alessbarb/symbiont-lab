"""Physics3D journals every causal provenance event exactly once (Causal Provenance v1 §6)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pybullet = pytest.importorskip("pybullet")

from lab.physics3d.cli import main
from lab.physics3d.persistence import read_symbiont_bundle_runtime


@pytest.mark.slow
def test_cli_journal_holds_each_emitted_event_once(tmp_path: Path) -> None:
    journal = tmp_path / "provenance.jsonl"
    symbiont = tmp_path / "organism.symbiont"
    args = [
        "--headless", "--no-monitor", "--no-slm", "--new-symbiont", "--fresh-body",
        "--ticks", "150", "--factorized-effects", "--provenance-journal", str(journal),
        "--symbiont-file", str(symbiont), "--body-state-file", str(tmp_path / "body.json"),
        "--telemetry-file", str(tmp_path / "telemetry"),
    ]  # fmt: skip
    assert main(args) == 0

    events = [json.loads(line) for line in journal.read_text().splitlines()]
    runtime = read_symbiont_bundle_runtime(symbiont)
    log = runtime["actuation"]["action_domain"]["sensorimotor_v2"]["agency_acquisition"]
    assert events and len({e["event_id"] for e in events}) == len(events)
    assert len(events) == log["provenance"]["emitted"]
