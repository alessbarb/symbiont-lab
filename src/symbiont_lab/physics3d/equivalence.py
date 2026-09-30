"""Causal equivalence primitive for Physics3D snapshots.

A PASS is strong evidence only for the scenario/configuration actually exercised.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from symbiont_lab.modeling.determinism import (
    TrainingDeterminism,
    configure_training_determinism,
)

from .engine import run


class DeterminismContractError(RuntimeError):
    """The configured equivalence run cannot establish deterministic training."""


@dataclass(frozen=True, slots=True)
class EquivalenceRunConfig:
    ticks: int
    body_kind: str
    seed: int = 42
    training: bool = False
    synchronous_training: bool = True
    train_interval: int = 32
    observation_hz: int = 1
    torch_threads: int = 1
    torch_interop_threads: int = 1
    deterministic_algorithms: bool = True


def _digest(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _file_digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return digest.hexdigest()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix().encode()
        digest.update(len(rel).to_bytes(4, "big"))
        digest.update(rel)
        digest.update(bytes.fromhex(hashlib.sha256(path.read_bytes()).hexdigest()))
    return digest.hexdigest()


def _private_model_state(payload: object) -> object | None:
    if isinstance(payload, dict):
        for key in ("private_model_registry", "private_models", "model_registry", "models"):
            if key in payload:
                return payload[key]
        for value in payload.values():
            found = _private_model_state(value)
            if found is not None:
                return found
    return None


def _registry_state(payload: object) -> dict[str, object] | None:
    """Extract only model-lifecycle state from an organism checkpoint."""
    if not isinstance(payload, Mapping):
        return None
    registry = payload.get("private_model_registry")
    if isinstance(registry, Mapping):
        records = registry.get("records")
        if isinstance(records, list):
            normalized: list[dict[str, object]] = []
            for raw in records:
                if not isinstance(raw, Mapping):
                    continue
                normalized.append(
                    {
                        "model_id": raw.get("model_id"),
                        "state": raw.get("state"),
                        "parent_model_id": raw.get("parent_model_id"),
                        "generation": raw.get("generation"),
                    }
                )
            normalized.sort(key=lambda row: str(row.get("model_id") or ""))
            active = next(
                (
                    str(row["model_id"])
                    for row in normalized
                    if row.get("state") == "active" and row.get("model_id") is not None
                ),
                None,
            )
            return {
                "records": normalized,
                "active_model_id": active,
            }
    for value in payload.values():
        found = _registry_state(value)
        if found is not None:
            return found
    return None


def _configure_equivalence_determinism(config: EquivalenceRunConfig) -> dict[str, object] | None:
    if not config.training:
        return None
    if not config.synchronous_training:
        raise DeterminismContractError("training equivalence requires synchronous training")
    if config.torch_threads != 1 or config.torch_interop_threads != 1:
        raise DeterminismContractError(
            "training equivalence requires one CPU thread and one interop thread"
        )
    try:
        effective = configure_training_determinism(
            TrainingDeterminism(
                seed=config.seed,
                cpu_threads=config.torch_threads,
                interop_threads=config.torch_interop_threads,
                deterministic_algorithms=config.deterministic_algorithms,
                warn_only=False,
            )
        )
    except (ImportError, RuntimeError) as exc:
        raise DeterminismContractError(str(exc)) from exc
    if effective.get("cpu_threads") != config.torch_threads:
        raise DeterminismContractError(
            f"torch CPU thread contract not established: {effective.get('cpu_threads')}"
        )
    if effective.get("interop_threads") != config.torch_interop_threads:
        raise DeterminismContractError(
            f"torch interop-thread contract not established: {effective.get('interop_threads')}"
        )
    if config.deterministic_algorithms and not effective.get("deterministic_algorithms"):
        raise DeterminismContractError("torch deterministic algorithms are not enabled")
    if effective.get("warn_only"):
        raise DeterminismContractError("torch deterministic mode is warn-only")
    return effective


def run_digests(
    snapshot_dir: Path,
    ticks: int | None = None,
    *,
    body_kind: str | None = None,
    config: EquivalenceRunConfig | None = None,
) -> dict[str, Any]:
    if config is None:
        if ticks is None:
            raise ValueError("ticks or config is required")
        config = EquivalenceRunConfig(
            ticks=int(ticks),
            body_kind=body_kind or "anthropomorphic-v6-vision",
        )

    determinism = _configure_equivalence_determinism(config)
    per_tick: list[tuple[int, str]] = []
    private_model_per_tick: list[tuple[int, str | None]] = []
    registry_per_tick: list[tuple[int, str | None]] = []
    promotion_events: list[dict[str, object]] = []
    training_completions = 0
    previous_ids: set[str] | None = None
    previous_active: str | None = None
    last_payload: object = {}

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shutil.copy2(snapshot_dir / "organism.symbiont", work / "organism.symbiont")
        shutil.copy2(snapshot_dir / "body.json", work / "body.json")
        if (snapshot_dir / "models").is_dir():
            shutil.copytree(snapshot_dir / "models", work / "models")
        else:
            (work / "models").mkdir()

        initial_models = _tree_digest(work / "models")

        def observe(tick: int, payload: object) -> None:
            nonlocal last_payload, previous_ids, previous_active, training_completions
            last_payload = payload
            per_tick.append((tick, _digest(payload)))
            private = _private_model_state(payload)
            private_model_per_tick.append((tick, _digest(private) if private is not None else None))
            registry = _registry_state(payload)
            registry_per_tick.append((tick, _digest(registry) if registry is not None else None))
            if registry is None:
                return
            records = registry.get("records", [])
            ids = {
                str(row["model_id"])
                for row in records
                if isinstance(row, Mapping) and row.get("model_id") is not None
            }
            active = registry.get("active_model_id")
            active_id = str(active) if active is not None else None
            if previous_ids is None:
                previous_ids = ids
                previous_active = active_id
                return
            training_completions += len(ids - previous_ids)
            if active_id is not None and active_id != previous_active:
                promotion_events.append(
                    {
                        "tick": int(tick),
                        "from_model_id": previous_active,
                        "to_model_id": active_id,
                    }
                )
            previous_ids = ids
            previous_active = active_id

        previous_strict = os.environ.get("SYMBIONT_STRICT_DETERMINISM")
        if config.training:
            os.environ["SYMBIONT_STRICT_DETERMINISM"] = "1"
        try:
            exit_code = run(
                headless=True,
                ticks=config.ticks,
                seed=config.seed,
                symbiont_file=work / "organism.symbiont",
                body_file=work / "body.json",
                telemetry_file=work / "telemetry",
                body_kind=config.body_kind,
                show_monitor=False,
                enable_slm=config.training,
                slm_train_interval=config.train_interval,
                slm_device="cpu",
                slm_synchronous=config.training and config.synchronous_training,
                checkpoint_interval=10**9,
                factorized_effects=True,
                observation_hz=config.observation_hz,
                provenance_journal=work / "provenance.jsonl",
                checkpoint_observer=observe,
            )
        finally:
            if previous_strict is None:
                os.environ.pop("SYMBIONT_STRICT_DETERMINISM", None)
            else:
                os.environ["SYMBIONT_STRICT_DETERMINISM"] = previous_strict

        final_models = _tree_digest(work / "models")
        private_model_transitions = sum(
            1
            for (_, previous), (_, current) in zip(
                private_model_per_tick, private_model_per_tick[1:]
            )
            if previous != current
        )
        registry_final = _registry_state(last_payload)
        return {
            "schema_version": 3,
            "config": asdict(config),
            "determinism": determinism,
            "exit_code": exit_code,
            "ticks": config.ticks,
            "per_tick": per_tick,
            "private_model_per_tick": private_model_per_tick,
            "registry_per_tick": registry_per_tick,
            "private_model_final": _digest(_private_model_state(last_payload)),
            "registry_final": registry_final,
            "private_model_transitions": private_model_transitions,
            "training_completions": training_completions,
            "promotion_events": promotion_events,
            "model_tree_initial": initial_models,
            "model_tree_final": final_models,
            "model_tree_changed": initial_models != final_models,
            "provenance": _file_digest(work / "provenance.jsonl"),
            "body": _digest(json.loads((work / "body.json").read_text(encoding="utf-8"))),
        }


def first_divergence(a: dict, b: dict) -> int | None:
    for (tick_a, digest_a), (tick_b, digest_b) in zip(a["per_tick"], b["per_tick"]):
        if tick_a != tick_b or digest_a != digest_b:
            return tick_a
    if len(a["per_tick"]) != len(b["per_tick"]):
        return min(len(a["per_tick"]), len(b["per_tick"]))
    return None


def equivalent(a: dict, b: dict) -> bool:
    return (
        first_divergence(a, b) is None
        and a.get("provenance") == b.get("provenance")
        and a.get("body") == b.get("body")
        and a.get("private_model_per_tick") == b.get("private_model_per_tick")
        and a.get("registry_per_tick") == b.get("registry_per_tick")
        and a.get("training_completions") == b.get("training_completions")
        and a.get("promotion_events") == b.get("promotion_events")
        and a.get("model_tree_final") == b.get("model_tree_final")
    )


if __name__ == "__main__":
    snapshot, ticks, out = Path(sys.argv[1]), int(sys.argv[2]), Path(sys.argv[3])
    kind = sys.argv[4] if len(sys.argv) > 4 else "anthropomorphic-v6-vision"
    out.write_text(
        json.dumps(run_digests(snapshot, ticks, body_kind=kind), sort_keys=True),
        encoding="utf-8",
    )
