from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_e8_campaign_aggregator_requires_exact_validated_seed_set(tmp_path: Path) -> None:
    aggregator = _load_script("aggregate_e8_label_invariance")
    pairs = []
    for seed in aggregator.PREREGISTERED_SEEDS:
        receipt = tmp_path / f"{seed}.receipt.json"
        result = tmp_path / f"{seed}.result.json"
        receipt.write_text(
            json.dumps(
                {
                    "commit": "a" * 40,
                    "execution_fingerprint": {"git_commit": "a" * 40},
                    "seed": seed,
                    "state": "complete",
                    "returncode": 0,
                    "scientific_input": {
                        "mode": "protocol-generated",
                        "external_state": False,
                    },
                }
            ),
            encoding="utf-8",
        )
        result.write_text(
            json.dumps(
                {
                    "seeds": [seed],
                    "steps": 300,
                    "invariant_rate": 1.0,
                    "integrity_pass": True,
                    "replay_deterministic": True,
                }
            ),
            encoding="utf-8",
        )
        pairs.append((receipt, result))

    summary = aggregator.aggregate(pairs)
    assert summary["a8_pass"] is True
    assert [row["seed"] for row in summary["seeds"]] == list(aggregator.PREREGISTERED_SEEDS)
    with pytest.raises(ValueError, match="exactly ten"):
        aggregator.aggregate(pairs[:-1])


def test_e8_runner_invokes_one_preregistered_seed_at_fixed_horizon(monkeypatch, capsys) -> None:
    runner = _load_script("run_e8_label_invariance")
    calls = []

    def run_study(*, seeds, steps):
        calls.append((seeds, steps))
        return SimpleNamespace(as_dict=lambda: {"seeds": list(seeds), "steps": steps})

    monkeypatch.setattr(runner, "run_label_invariance_study", run_study)
    monkeypatch.setattr("sys.argv", ["run_e8_label_invariance.py", "--seed", "101"])
    monkeypatch.setenv("SYMBIONT_SEED", "101")
    assert runner.main() == 0
    assert calls == [((101,), 300)]
    assert json.loads(capsys.readouterr().out) == {"seeds": [101], "steps": 300}


def test_e8_aggregator_rejects_seed_mismatch_and_unstable_commit(tmp_path: Path) -> None:
    aggregator = _load_script("aggregate_e8_label_invariance")
    pairs = []
    for index, seed in enumerate(aggregator.PREREGISTERED_SEEDS):
        receipt = tmp_path / f"r{seed}.json"
        result = tmp_path / f"o{seed}.json"
        receipt.write_text(
            json.dumps(
                {
                    "commit": ("b" if index else "a") * 40,
                    "execution_fingerprint": {"git_commit": ("b" if index else "a") * 40},
                    "seed": seed + (1 if index == 0 else 0),
                    "state": "complete",
                    "returncode": 0,
                    "scientific_input": {
                        "mode": "protocol-generated",
                        "external_state": False,
                    },
                }
            ),
            encoding="utf-8",
        )
        result.write_text(
            json.dumps(
                {
                    "seeds": [seed],
                    "steps": 300,
                    "invariant_rate": 1.0,
                    "integrity_pass": True,
                    "replay_deterministic": True,
                }
            ),
            encoding="utf-8",
        )
        pairs.append((receipt, result))
    with pytest.raises(ValueError, match="seed mismatch"):
        aggregator.aggregate(pairs)
