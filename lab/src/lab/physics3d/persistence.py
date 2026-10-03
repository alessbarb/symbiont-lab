"""Durable files for Physics3D apparatus state and passive telemetry."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import zipfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from embodiment.physics3d.reembodiment import lifecycle_summary
from lab.physics3d.runtime import Tick3D
from lab.physics3d.telemetry.reader import detect_telemetry_run, open_telemetry
from symbiont import __version__ as symbiont_version
from symbiont.host.durable import durable_atomic_replacement, durable_atomic_write_json


def _atomic_write_json(path: Path, payload: dict) -> Path:
    return durable_atomic_write_json(
        path,
        payload,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        sync_dir=True,
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def validate_bundle_export_invariants(
    manifest: dict[str, Any],
    runtime_payload: dict[str, Any],
    runtime_sha256: str,
) -> None:
    """Enforce strict export invariants before packaging a Symbiont bundle."""
    runtime_tick = int(runtime_payload.get("saved_at_tick") or 0)
    if manifest.get("saved_at_tick") != runtime_tick:
        raise ValueError(
            f"Export invariant violated: manifest.saved_at_tick ({manifest.get('saved_at_tick')}) "
            f"!= runtime.saved_at_tick ({runtime_tick})"
        )
    if manifest.get("symbiont_tick") != runtime_tick:
        raise ValueError(
            f"Export invariant violated: manifest.symbiont_tick ({manifest.get('symbiont_tick')}) "
            f"!= runtime.saved_at_tick ({runtime_tick})"
        )

    expected_hash = f"sha256:{runtime_sha256}"
    if manifest.get("checkpoint_hash") != expected_hash:
        raise ValueError(
            f"Export invariant violated: manifest.checkpoint_hash ({manifest.get('checkpoint_hash')}) "
            f"!= runtime sha256 ({expected_hash})"
        )
    if manifest.get("manifest_generated_from_checkpoint_hash") != expected_hash:
        raise ValueError(
            "Export invariant violated: manifest_generated_from_checkpoint_hash "
            f"({manifest.get('manifest_generated_from_checkpoint_hash')}) != {expected_hash}"
        )

    lifecycle = runtime_payload.get("embodiment_lifecycle")
    if isinstance(lifecycle, dict):
        current = lifecycle.get("current")
        if isinstance(current, dict):
            if "embodiment_id" in current and manifest.get("embodiment_id") != current.get(
                "embodiment_id"
            ):
                raise ValueError(
                    f"Export invariant violated: manifest.embodiment_id ({manifest.get('embodiment_id')}) "
                    f"!= runtime current embodiment_id ({current.get('embodiment_id')})"
                )
            if "body_id" in current and manifest.get("body_id") != current.get("body_id"):
                raise ValueError(
                    f"Export invariant violated: manifest.body_id ({manifest.get('body_id')}) "
                    f"!= runtime current body_id ({current.get('body_id')})"
                )
            if current.get("body_kind") and manifest.get("body_kind") != current.get("body_kind"):
                raise ValueError(
                    f"Export invariant violated: manifest.body_kind ({manifest.get('body_kind')}) "
                    f"!= runtime current body_kind ({current.get('body_kind')})"
                )


def build_symbiont_bundle_manifest(
    runtime_payload: dict[str, Any],
    *,
    runtime_sha256: str,
) -> dict[str, Any]:
    """Derive an authoritative, self-describing manifest from an atomic runtime snapshot."""
    saved_at_tick = int(runtime_payload.get("saved_at_tick") or 0)
    organism_id = str(runtime_payload.get("organism_id") or "")
    raw_lifecycle = runtime_payload.get("embodiment_lifecycle")
    raw_current: dict[str, Any] = {}
    if isinstance(raw_lifecycle, dict):
        raw_current_val = raw_lifecycle.get("current")
        if isinstance(raw_current_val, dict):
            raw_current = raw_current_val
    raw_episode = runtime_payload.get("embodiment_episode")
    raw_episode = raw_episode if isinstance(raw_episode, dict) else {}

    lifecycle_data = lifecycle_summary(runtime_payload)
    lifecycle_current = lifecycle_data.get("current")
    current: dict[str, Any] = dict(lifecycle_current) if isinstance(lifecycle_current, dict) else {}
    for k, v in raw_current.items():
        if v is not None:
            current[k] = v
    if raw_episode.get("embodiment_id"):
        current["embodiment_id"] = raw_episode.get("embodiment_id")
    if raw_episode.get("body_id"):
        current["body_id"] = raw_episode.get("body_id")

    raw_epoch = (
        (raw_lifecycle.get("epoch") if isinstance(raw_lifecycle, dict) else None)
        or raw_episode.get("epoch")
        or lifecycle_data.get("epoch")
        or 1
    )
    embodiment_epoch = max(1, int(raw_epoch)) if isinstance(raw_epoch, (int, str, float)) else 1
    symbiont_state = str(
        (raw_lifecycle.get("state") if isinstance(raw_lifecycle, dict) else None)
        or raw_episode.get("state")
        or lifecycle_data.get("state")
        or "dormant"
    )

    archive = runtime_payload.get("embodiment_archive")
    archive = archive if isinstance(archive, dict) else {}

    living_body = runtime_payload.get("living_body")
    living_body = living_body if isinstance(living_body, dict) else {}

    vital_state = (
        current.get("body_vital_state")
        or living_body.get("vital_state")
        or runtime_payload.get("last_runtime_vital_state")
        or "active"
    )
    development_phase = runtime_payload.get("last_runtime_development_phase") or "juvenile"

    registry = runtime_payload.get("private_model_registry")
    registry = registry if isinstance(registry, dict) else {}
    records = registry.get("records", []) if isinstance(registry.get("records"), list) else []
    active_shadow = sum(1 for r in records if isinstance(r, dict) and r.get("state") == "shadow")

    exp_ledger = runtime_payload.get("experience_ledger")
    exp_ledger = exp_ledger if isinstance(exp_ledger, dict) else {}
    exp_records = (
        exp_ledger.get("records", []) if isinstance(exp_ledger.get("records"), list) else []
    )

    genome = runtime_payload.get("genome")
    genome = genome if isinstance(genome, dict) else {}

    summaries = runtime_payload.get("embodiment_epoch_summaries")
    summaries = summaries if isinstance(summaries, list) else []
    last_summary = summaries[-1] if summaries and isinstance(summaries[-1], dict) else None

    memories = (
        archive.get("body_memories", []) if isinstance(archive.get("body_memories"), list) else []
    )
    known_contracts = len(
        {
            str(m.get("contract_fingerprint"))
            for m in memories
            if isinstance(m, dict) and m.get("contract_fingerprint")
        }
    )

    safe_id = "".join(ch for ch in organism_id.lower() if ch.isalnum())[-12:] or "organism"
    checkpoint_id = f"chk-{safe_id}-{saved_at_tick:08d}"

    raw_history_count = lifecycle_data.get("history_count", 0)
    history_count = (
        max(0, int(raw_history_count)) if isinstance(raw_history_count, (int, str, float)) else 0
    )

    manifest: dict[str, Any] = {
        "bundle_schema_version": "1.0",
        "checkpoint_id": checkpoint_id,
        "checkpoint_hash": f"sha256:{runtime_sha256}",
        "manifest_generated_from_checkpoint_hash": f"sha256:{runtime_sha256}",
        "organism_id": organism_id,
        "saved_at_tick": saved_at_tick,
        "symbiont_tick": saved_at_tick,
        "tick": saved_at_tick,
        "generation": int(runtime_payload.get("generation") or 0),
        "embodiment_epoch": embodiment_epoch,
        "embodiment_id": current.get("embodiment_id"),
        "body_id": current.get("body_id"),
        "body_kind": current.get("body_kind"),
        "body_age_ticks": (
            int(living_body["age_ticks"])
            if "age_ticks" in living_body and living_body["age_ticks"] is not None
            else None
        ),
        "body_senescence": (
            float(living_body["senescence"])
            if "senescence" in living_body and living_body["senescence"] is not None
            else 0.0
        ),
        "receptor_count": current.get("receptor_count"),
        "effector_count": current.get("effector_count"),
        "model_record_count": len(records),
        "models": len(records),
        "active_shadow_models": active_shadow,
        "experience_count": len(exp_records),
        "experiences": len(exp_records),
        "genome_id": genome.get("genome_id"),
        "vital_state": str(vital_state),
        "symbiont_state": symbiont_state,
        "development_phase": str(development_phase),
        "embodiment_summary_count": len(summaries),
        "known_contract_count": known_contracts,
        "last_epoch_summary": last_summary,
        "embodiment_history_count": history_count,
        "runtime_schema_version": runtime_payload.get("schema_version"),
        "software_version": str(runtime_payload.get("software_version") or symbiont_version),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    validate_bundle_export_invariants(manifest, runtime_payload, runtime_sha256)
    return manifest


def sync_organism_metadata(
    bundle_path: Path,
    manifest: dict[str, Any],
) -> Path | None:
    """Atomically synchronize external metadata.json alongside a bundle from its manifest."""
    bundle_path = bundle_path.resolve()
    parent = bundle_path.parent
    meta_path = parent / "metadata.json"
    if not (
        bundle_path.name == "organism.symbiont"
        and (meta_path.is_file() or parent.name.startswith("org-"))
    ):
        return None

    existing = _read_json(meta_path)
    ref = str(existing.get("ref") or parent.name)
    updated = {
        **existing,
        **manifest,
        "ref": ref,
        "tick": manifest.get("saved_at_tick", 0),
        "models": manifest.get("model_record_count", 0),
        "experiences": manifest.get("experience_count", 0),
        "symbiont_state": manifest.get("symbiont_state", "active"),
        "updated_at": manifest.get("created_at") or datetime.now(timezone.utc).isoformat(),
        "runnable": True,
    }
    _atomic_write_json(meta_path, updated)
    return meta_path


def save_symbiont_bundle(
    runtime_payload: dict,
    models_dir: str | Path,
    path: str | Path,
    *,
    sync_metadata: bool = True,
) -> Path:
    """Atomically save one portable organism bundle, including private SLM artifacts."""
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    models_root = Path(models_dir).expanduser()
    artifacts: dict[str, bytes] = {}
    for model_id, required in _bundle_models(runtime_payload):
        for suffix in (".json", ".pt", ".tokenizer.json"):
            source = models_root / f"{model_id}{suffix}"
            if source.is_file():
                artifacts[f"models/{model_id}{suffix}"] = source.read_bytes()
            elif required:
                raise ValueError(f"missing required model artifact: {source.name}")

    runtime_bytes = json.dumps(
        runtime_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    runtime_sha256 = hashlib.sha256(runtime_bytes).hexdigest()

    manifest_payload = build_symbiont_bundle_manifest(
        runtime_payload,
        runtime_sha256=runtime_sha256,
    )
    manifest_payload["bundle_schema_version"] = "1.1"
    manifest_payload["model_artifacts"] = {
        name: f"sha256:{hashlib.sha256(data).hexdigest()}"
        for name, data in sorted(artifacts.items())
    }
    manifest_bytes = (
        json.dumps(
            manifest_payload,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")

    with durable_atomic_replacement(target, sync_dir=True) as temp_name:
        with zipfile.ZipFile(
            temp_name,
            "w",
            compression=zipfile.ZIP_STORED,
        ) as archive:
            archive.writestr("manifest.json", manifest_bytes)
            archive.writestr("runtime.json", runtime_bytes)
            for name, data in sorted(artifacts.items()):
                archive.writestr(name, data)
        with open(temp_name, "rb") as handle:
            os.fsync(handle.fileno())

    if sync_metadata:
        sync_organism_metadata(target, manifest_payload)

    return target


def read_symbiont_bundle_manifest(
    path: str | Path,
    *,
    verify: bool = False,
) -> dict[str, Any]:
    """Read manifest.json from a portable organism bundle.

    If reading a legacy bundle lacking manifest.json, falls back to deriving
    the manifest from runtime.json.
    """
    source = Path(path).expanduser()
    with zipfile.ZipFile(source, "r") as archive:
        return _read_bundle_manifest(archive, verify=verify)


def _read_bundle_manifest(archive: zipfile.ZipFile, *, verify: bool) -> dict[str, Any]:
    names = set(archive.namelist())
    if "manifest.json" in names:
        try:
            raw = json.loads(archive.read("manifest.json").decode("utf-8"))
        except Exception as exc:
            raise ValueError("portable Symbiont bundle has corrupt manifest.json") from exc
        if not isinstance(raw, dict):
            raise ValueError("portable Symbiont manifest root must be an object")
        if verify:
            if "runtime.json" not in names:
                raise ValueError("portable Symbiont bundle has manifest.json but no runtime.json")
            runtime_bytes = archive.read("runtime.json")
            runtime_sha256 = hashlib.sha256(runtime_bytes).hexdigest()
            expected = f"sha256:{runtime_sha256}"
            if raw.get("checkpoint_hash") != expected:
                raise ValueError(
                    f"manifest checkpoint_hash mismatch: {raw.get('checkpoint_hash')} != {expected}"
                )
            # Revision Coherence v1 §3.7: the manifest describes exactly
            # this runtime (Workbench metadata.json is never authority).
            runtime_payload = json.loads(runtime_bytes.decode("utf-8"))
            if not isinstance(runtime_payload, dict):
                raise ValueError("portable Symbiont runtime root must be an object")
            validate_bundle_export_invariants(raw, runtime_payload, runtime_sha256)
            derived = build_symbiont_bundle_manifest(
                json.loads(runtime_bytes.decode("utf-8")), runtime_sha256=runtime_sha256
            )
            for field in ("saved_at_tick", "organism_id", "embodiment_epoch"):
                if raw.get(field) != derived.get(field):
                    raise ValueError(f"manifest {field} does not match runtime.json")
        return raw

    if "runtime.json" not in names:
        raise ValueError("portable Symbiont bundle has neither manifest.json nor runtime.json")
    runtime_bytes = archive.read("runtime.json")
    try:
        runtime_payload = json.loads(runtime_bytes.decode("utf-8"))
    except Exception as exc:
        raise ValueError("portable Symbiont bundle has corrupt runtime.json") from exc
    if not isinstance(runtime_payload, dict):
        raise ValueError("portable Symbiont runtime root must be an object")
    runtime_sha256 = hashlib.sha256(runtime_bytes).hexdigest()
    return build_symbiont_bundle_manifest(runtime_payload, runtime_sha256=runtime_sha256)


def read_symbiont_bundle_runtime(path: str | Path) -> dict:
    """Read only runtime.json from a portable organism bundle.

    Catalogs and preflight checks must not materialize private model artifacts.
    Full artifact extraction belongs exclusively to an actual runtime restore.
    """
    source = Path(path).expanduser()
    with zipfile.ZipFile(source, "r") as archive:
        try:
            raw = json.loads(archive.read("runtime.json").decode("utf-8"))
        except KeyError as exc:
            raise ValueError("portable Symbiont bundle has no runtime.json") from exc
        if not isinstance(raw, dict):
            raise ValueError("portable Symbiont runtime root must be an object")
        return raw


def _bundle_models(payload: dict) -> list[tuple[str, bool]]:
    registry = payload.get("private_model_registry", {})
    records = registry.get("records", []) if isinstance(registry, dict) else []
    models = []
    for record in records:
        if not isinstance(record, dict) or record.get("state") == "retired":
            continue
        model_id = record.get("model_id")
        if (
            not isinstance(model_id, str)
            or not model_id
            or any(
                c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
                for c in model_id
            )
        ):
            raise ValueError("portable Symbiont bundle contains unsafe model identity")
        models.append((model_id, record.get("state") in {"active", "shadow"}))
    return models


def load_symbiont_bundle(
    path: str | Path,
    models_dir: str | Path,
) -> dict:
    """Verify a complete bundle before publishing artifacts without overwriting.

    Legacy manifest-free and 1.0 bundles lack artifact hashes but still undergo
    path, duplicate-member and required-artifact checks. Conflicting local
    artifacts are rejected; identical files are reused. Publication failures
    roll back newly installed files (not a crash-atomic multi-file transaction).
    """
    source = Path(path).expanduser()
    models_root = Path(models_dir).expanduser()
    with zipfile.ZipFile(source, "r") as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("portable Symbiont bundle contains duplicate members")
        manifest = _read_bundle_manifest(archive, verify=True)
        raw = json.loads(archive.read("runtime.json").decode("utf-8"))
        artifacts = {}
        for name in names:
            if name in {"manifest.json", "runtime.json"}:
                continue
            leaf = name.removeprefix("models/")
            if (
                not name.startswith("models/")
                or "/" in leaf
                or "\\" in leaf
                or not leaf
                or leaf.startswith(".")
                or not (leaf.endswith(".json") or leaf.endswith(".pt"))
            ):
                raise ValueError("portable Symbiont bundle contains unsafe model path")
            artifacts[name] = archive.read(name)
        for model_id, required in _bundle_models(raw):
            if required:
                for suffix in (".json", ".pt", ".tokenizer.json"):
                    if f"models/{model_id}{suffix}" not in artifacts:
                        raise ValueError(f"missing required model artifact: {model_id}{suffix}")
        version = manifest.get("bundle_schema_version")
        if version not in {"1.0", "1.1"}:
            raise ValueError("unsupported portable Symbiont bundle schema")
        if version == "1.1" or "model_artifacts" in manifest:
            inventory = {
                name: f"sha256:{hashlib.sha256(data).hexdigest()}"
                for name, data in artifacts.items()
            }
            if manifest.get("model_artifacts") != inventory:
                raise ValueError("portable Symbiont bundle artifact inventory mismatch")

    pending = {}
    for name, data in artifacts.items():
        destination = models_root / name.removeprefix("models/")
        if destination.is_symlink():
            raise ValueError(f"model artifact destination is a symlink: {destination.name}")
        if destination.exists():
            if not destination.is_file() or destination.read_bytes() != data:
                raise ValueError(f"conflicting local model artifact: {destination.name}")
        else:
            pending[destination] = data
    if not pending:
        return raw
    models_root.mkdir(parents=True, exist_ok=True)
    installed = []
    with tempfile.TemporaryDirectory(prefix=".bundle-", dir=models_root) as staging:
        staged = []
        for destination, data in pending.items():
            temporary = Path(staging) / destination.name
            temporary.write_bytes(data)
            staged.append((temporary, destination))
        try:
            for temporary, destination in staged:
                # Atomic no-clobber publication, including concurrent writers.
                os.link(temporary, destination)
                installed.append(destination)
        except BaseException:
            for destination in reversed(installed):
                destination.unlink()
            raise
    return raw


def save_runtime_state_file(payload: dict, path: str | Path) -> Path:
    """Save the canonical body-independent organism runtime checkpoint."""
    return _atomic_write_json(Path(path).expanduser(), payload)


def load_runtime_state_file(path: str | Path) -> dict:
    target = Path(path).expanduser()
    payload = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("organism runtime state root must be an object")
    return payload


def save_body_state_file(payload: dict, path: str | Path) -> Path:
    """Save apparatus-owned physical pose separately from the Symbiont file."""
    return _atomic_write_json(Path(path).expanduser(), payload)


def load_body_state_file(path: str | Path) -> dict:
    target = Path(path).expanduser()
    payload = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("physical body state root must be an object")
    return payload


class TelemetryWriter:
    """Append-only apparatus telemetry. It never feeds cognition."""

    def __init__(self, path: str | Path, *, flush_every: int = 64) -> None:
        if flush_every < 1:
            raise ValueError("flush_every must be >= 1")
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a", encoding="utf-8", buffering=8192)
        self._flush_every = int(flush_every)
        self._pending = 0

    def append(self, record: Tick3D) -> None:
        self._handle.write(
            json.dumps(
                asdict(record),
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )
        self._handle.write("\n")
        self._pending += 1
        if self._pending >= self._flush_every:
            self._handle.flush()
            self._pending = 0

    def flush(self) -> None:
        if not self._handle.closed:
            self._handle.flush()
            self._pending = 0

    def close(self) -> None:
        if not self._handle.closed:
            self._handle.flush()
            self._handle.close()
            self._pending = 0


def load_telemetry_records(
    path: str | Path,
    *,
    ignore_errors: bool = False,
) -> list[dict]:
    """Read Tick3D summaries through the version-neutral telemetry API."""
    version, target = detect_telemetry_run(path)
    if version != "legacy":
        return list(open_telemetry(target).iter_summaries())

    records = []
    with target.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                if isinstance(item, dict):
                    records.append(item)
            except json.JSONDecodeError as exc:
                if ignore_errors:
                    continue
                raise ValueError(f"corrupt telemetry record at line {line_no}: {exc}") from exc
    return records


def load_telemetry_transitions(path: str | Path) -> list[dict]:
    """Read fully reconstructed rich states independent of storage version."""
    version, target = detect_telemetry_run(path)
    if version == "legacy":
        raise ValueError("historical single-file telemetry has no reconstructible rich transitions")
    return list(open_telemetry(target).iter_states())


__all__ = [
    "TelemetryWriter",
    "build_symbiont_bundle_manifest",
    "load_body_state_file",
    "load_runtime_state_file",
    "read_symbiont_bundle_manifest",
    "read_symbiont_bundle_runtime",
    "load_symbiont_bundle",
    "load_telemetry_records",
    "load_telemetry_transitions",
    "open_telemetry",
    "save_body_state_file",
    "save_runtime_state_file",
    "save_symbiont_bundle",
    "sync_organism_metadata",
    "validate_bundle_export_invariants",
]
