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

from .reembodiment import lifecycle_summary
from .runtime import Tick3D
from .telemetry_reader import detect_telemetry_run, open_telemetry


def _atomic_write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (
        json.dumps(
            payload,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    )
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return path


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
    raw_current = (
        raw_lifecycle.get("current")
        if isinstance(raw_lifecycle, dict) and isinstance(raw_lifecycle.get("current"), dict)
        else {}
    )
    raw_episode = runtime_payload.get("embodiment_episode")
    raw_episode = raw_episode if isinstance(raw_episode, dict) else {}

    lifecycle_data = lifecycle_summary(runtime_payload)
    current = (
        dict(lifecycle_data.get("current", {}))
        if isinstance(lifecycle_data.get("current"), dict)
        else {}
    )
    for k, v in raw_current.items():
        if v is not None:
            current[k] = v
    if raw_episode.get("embodiment_id"):
        current["embodiment_id"] = raw_episode.get("embodiment_id")
    if raw_episode.get("body_id"):
        current["body_id"] = raw_episode.get("body_id")

    embodiment_epoch = (
        (raw_lifecycle.get("epoch") if isinstance(raw_lifecycle, dict) else None)
        or raw_episode.get("epoch")
        or lifecycle_data.get("epoch")
        or 1
    )
    embodiment_epoch = int(embodiment_epoch or 1)
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
        "embodiment_history_count": int(lifecycle_data.get("history_count", 0)),
        "runtime_schema_version": runtime_payload.get("schema_version"),
        "software_version": "0.1.0",
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
    registry = runtime_payload.get("private_model_registry", {})
    records = registry.get("records", []) if isinstance(registry, dict) else []
    model_ids = [
        str(record.get("model_id"))
        for record in records
        if (
            isinstance(record, dict)
            and isinstance(record.get("model_id"), str)
            and record.get("state") != "retired"
        )
    ]

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
    manifest_bytes = (
        json.dumps(
            manifest_payload,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")

    fd, temp_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
    )
    os.close(fd)
    try:
        with zipfile.ZipFile(
            temp_name,
            "w",
            compression=zipfile.ZIP_STORED,
        ) as archive:
            archive.writestr("manifest.json", manifest_bytes)
            archive.writestr("runtime.json", runtime_bytes)
            for model_id in sorted(set(model_ids)):
                for suffix in (".json", ".pt", ".tokenizer.json"):
                    source = models_root / f"{model_id}{suffix}"
                    if source.is_file():
                        archive.write(
                            source,
                            arcname=f"models/{model_id}{suffix}",
                        )
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)

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
                    raise ValueError(
                        "portable Symbiont bundle has manifest.json but no runtime.json"
                    )
                runtime_bytes = archive.read("runtime.json")
                runtime_sha256 = hashlib.sha256(runtime_bytes).hexdigest()
                expected = f"sha256:{runtime_sha256}"
                if raw.get("checkpoint_hash") != expected:
                    raise ValueError(
                        f"manifest checkpoint_hash mismatch: {raw.get('checkpoint_hash')} != {expected}"
                    )
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


def load_symbiont_bundle(
    path: str | Path,
    models_dir: str | Path,
) -> dict:
    """Restore runtime state and materialize bundled private SLM artifacts."""
    source = Path(path).expanduser()
    models_root = Path(models_dir).expanduser()
    models_root.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(source, "r") as archive:
        names = set(archive.namelist())
        if "runtime.json" not in names:
            raise ValueError("portable Symbiont bundle has no runtime.json")
        raw = json.loads(archive.read("runtime.json").decode("utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("portable Symbiont runtime root must be an object")

        for name in sorted(names):
            if not name.startswith("models/"):
                continue
            leaf = name.removeprefix("models/")
            if "/" in leaf or not leaf or not (leaf.endswith(".json") or leaf.endswith(".pt")):
                raise ValueError("portable Symbiont bundle contains unsafe model path")
            destination = models_root / leaf
            temporary = destination.with_name(f".{destination.name}.tmp")
            temporary.write_bytes(archive.read(name))
            os.replace(temporary, destination)
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
