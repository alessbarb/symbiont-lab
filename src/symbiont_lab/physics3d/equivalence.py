"""Equivalence harness (Simulation Throughput v1 §2).

Runs a copy of a Physics3D snapshot for a fixed number of ticks and records a
per-tick digest of the organism's causal state (its checkpoint), plus the
final provenance journal and body. Two code versions are equivalent on a
snapshot when every digest matches; the first differing tick localises a
divergence. Training is off: the harness checks the per-tick organism.

Usage (once per code tree, then compare the two JSON files):
    python -m symbiont_lab.physics3d.equivalence <snapshot_dir> <ticks> <out.json>
where <snapshot_dir> holds organism.symbiont, body.json and models/.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

from .engine import run


def _digest(payload) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _file_digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def run_digests(snapshot_dir: Path, ticks: int, *, body_kind: str) -> dict:
    per_tick: list[tuple[int, str]] = []
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shutil.copy2(snapshot_dir / "organism.symbiont", work / "organism.symbiont")
        shutil.copy2(snapshot_dir / "body.json", work / "body.json")
        shutil.copytree(snapshot_dir / "models", work / "models")
        run(
            headless=True,
            ticks=ticks,
            symbiont_file=work / "organism.symbiont",
            body_file=work / "body.json",
            telemetry_file=work / "telemetry.jsonl",
            body_kind=body_kind,
            show_monitor=False,
            enable_slm=False,
            checkpoint_interval=10**9,
            factorized_effects=True,
            observation_hz=1,
            provenance_journal=work / "provenance.jsonl",
            checkpoint_observer=lambda tick, payload: per_tick.append((tick, _digest(payload))),
        )
        return {
            "ticks": ticks,
            "per_tick": per_tick,
            "provenance": _file_digest(work / "provenance.jsonl"),
            "body": _digest(json.loads((work / "body.json").read_text(encoding="utf-8"))),
        }


def first_divergence(a: dict, b: dict) -> int | None:
    """First tick whose organism digest differs (None when equivalent)."""
    for (tick_a, digest_a), (tick_b, digest_b) in zip(a["per_tick"], b["per_tick"]):
        if tick_a != tick_b or digest_a != digest_b:
            return tick_a
    if len(a["per_tick"]) != len(b["per_tick"]):
        return min(len(a["per_tick"]), len(b["per_tick"]))
    return None


def equivalent(a: dict, b: dict) -> bool:
    return (
        first_divergence(a, b) is None
        and a["provenance"] == b["provenance"]
        and a["body"] == b["body"]
    )


if __name__ == "__main__":
    snapshot, ticks, out = Path(sys.argv[1]), int(sys.argv[2]), Path(sys.argv[3])
    kind = sys.argv[4] if len(sys.argv) > 4 else "anthropomorphic-v6-vision"
    out.write_text(json.dumps(run_digests(snapshot, ticks, body_kind=kind)), encoding="utf-8")
