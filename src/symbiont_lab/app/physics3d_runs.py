"""Persistent run/organism/body catalog for the Physics3D workbench."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import uuid
from typing import Any

from symbiont_lab.physics3d.bodies import BodyRegistry, DEFAULT_BODY_REGISTRY
from symbiont_lab.physics3d.engine import (
    DEFAULT_BODY_FILE,
    DEFAULT_STATE_DIR,
    DEFAULT_SYMBIONT_FILE,
)
from symbiont_lab.physics3d.persistence import load_symbiont_bundle


DEFAULT_LAB_STATE_ROOT = DEFAULT_STATE_DIR.parent


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp")
    temp.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)


@dataclass(frozen=True, slots=True)
class Physics3DLaunchSpec:
    run_id: str
    organism_ref: str
    body_ref: str
    body_kind: str
    organism_mode: str
    body_mode: str
    symbiont_file: Path
    body_file: Path
    telemetry_file: Path

    @property
    def new_symbiont(self) -> bool:
        return self.organism_mode == "new"

    @property
    def fresh_body(self) -> bool:
        return self.body_mode == "fresh"

    @property
    def embodiment_mode(self) -> str:
        if self.new_symbiont:
            return "new"
        return "resume" if self.body_mode == "resume" else "transplant"

    def runner_kwargs(self) -> dict[str, object]:
        return {
            "body_kind": self.body_kind,
            "symbiont_file": self.symbiont_file,
            "body_file": self.body_file,
            "telemetry_file": self.telemetry_file,
            "new_symbiont": self.new_symbiont,
            "fresh_body": self.fresh_body,
        }

    def as_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "organism_ref": self.organism_ref,
            "body_ref": self.body_ref,
            "body_kind": self.body_kind,
            "organism_mode": self.organism_mode,
            "body_mode": self.body_mode,
            "embodiment_mode": self.embodiment_mode,
        }


class Physics3DRunStore:
    """Own workbench persistence without changing organism cognition."""

    def __init__(
        self,
        root: str | Path = DEFAULT_LAB_STATE_ROOT,
        *,
        body_registry: BodyRegistry = DEFAULT_BODY_REGISTRY,
    ) -> None:
        self.root = Path(root).expanduser()
        self.organisms_dir = self.root / "organisms"
        self.bodies_dir = self.root / "bodies"
        self.runs_dir = self.root / "runs"
        self.body_registry = body_registry
        for path in (self.organisms_dir, self.bodies_dir, self.runs_dir):
            path.mkdir(parents=True, exist_ok=True)

    def bodies(self) -> list[dict[str, object]]:
        return [item.as_dict() for item in self.body_registry.list()]

    def _organism_metadata(self, ref: str) -> dict[str, Any]:
        return _read_json(self.organisms_dir / ref / "metadata.json")

    def _body_metadata(self, ref: str) -> dict[str, Any]:
        return _read_json(self.bodies_dir / ref / "metadata.json")

    def _bundle_summary(self, bundle: Path) -> dict[str, Any]:
        if not bundle.is_file():
            return {}
        scratch = bundle.parent / ".catalog-models"
        try:
            payload = load_symbiont_bundle(bundle, scratch)
        except Exception:
            return {}
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
        ledger = payload.get("experience_ledger", {})
        registry = payload.get("private_model_registry", {})
        genome = payload.get("genome", {})
        return {
            "organism_id": payload.get("organism_id"),
            "tick": int(payload.get("saved_at_tick") or 0),
            "experiences": (
                len(ledger.get("records", []))
                if isinstance(ledger, dict) and isinstance(ledger.get("records"), list)
                else 0
            ),
            "models": (
                len(registry.get("records", []))
                if isinstance(registry, dict) and isinstance(registry.get("records"), list)
                else 0
            ),
            "genome_id": genome.get("genome_id") if isinstance(genome, dict) else None,
        }

    def organisms(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for directory in sorted(self.organisms_dir.iterdir()):
            if not directory.is_dir():
                continue
            metadata = _read_json(directory / "metadata.json")
            bundle = directory / "organism.symbiont"
            if not metadata and not bundle.is_file():
                continue
            summary = self._bundle_summary(bundle) if bundle.is_file() else {}
            item = {
                **metadata,
                **{key: value for key, value in summary.items() if value is not None},
                "ref": directory.name,
                "bundle_available": bundle.is_file(),
            }
            items.append(item)

        if DEFAULT_SYMBIONT_FILE.is_file():
            summary = self._bundle_summary(DEFAULT_SYMBIONT_FILE)
            items.append({
                **summary,
                "ref": "legacy-default",
                "legacy": True,
                "bundle_available": True,
                "body_kind": "anthropomorphic-v4",
                "last_body_ref": "legacy-default" if DEFAULT_BODY_FILE.is_file() else None,
            })
        items.sort(key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""), reverse=True)
        return items

    def runs(self, limit: int = 20) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for directory in self.runs_dir.iterdir():
            if directory.is_dir():
                manifest = _read_json(directory / "manifest.json")
                if manifest:
                    records.append(manifest)
        records.sort(key=lambda item: str(item.get("started_at") or ""), reverse=True)
        return records[: max(1, int(limit))]

    def _materialize_legacy_organism(self) -> str:
        summary = self._bundle_summary(DEFAULT_SYMBIONT_FILE)
        identity = str(summary.get("organism_id") or uuid.uuid4().hex[:12])
        safe = "".join(ch for ch in identity.lower() if ch.isalnum())[-12:] or uuid.uuid4().hex[:12]
        ref = f"org-{safe}"
        directory = self.organisms_dir / ref
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / "organism.symbiont"
        if not destination.exists():
            shutil.copy2(DEFAULT_SYMBIONT_FILE, destination)
        last_body_ref = None
        if DEFAULT_BODY_FILE.is_file():
            last_body_ref = f"body-legacy-{safe}"
            body_dir = self.bodies_dir / last_body_ref
            body_dir.mkdir(parents=True, exist_ok=True)
            body_destination = body_dir / "body.json"
            if not body_destination.exists():
                shutil.copy2(DEFAULT_BODY_FILE, body_destination)
            _write_json(body_dir / "metadata.json", {
                "ref": last_body_ref,
                "body_kind": "anthropomorphic-v4",
                "created_at": _now(),
                "updated_at": _now(),
                "migrated_from": str(DEFAULT_BODY_FILE),
                "organism_ref": ref,
                "checkpoint_available": True,
            })
        descriptor = self.body_registry.get("anthropomorphic-v4")
        metadata = {
            **summary,
            "ref": ref,
            "created_at": _now(),
            "updated_at": _now(),
            "migrated_from": str(DEFAULT_SYMBIONT_FILE),
            "body_kind": "anthropomorphic-v4",
            "last_body_ref": last_body_ref,
            "receptor_count": descriptor.receptor_count,
            "effector_count": descriptor.effector_count,
        }
        _write_json(directory / "metadata.json", metadata)
        return ref

    def prepare(self, payload: dict[str, Any]) -> Physics3DLaunchSpec:
        body_kind = str(payload.get("body_kind") or "anthropomorphic-v4")
        descriptor = self.body_registry.get(body_kind)
        organism = payload.get("organism", {})
        body = payload.get("body", {})
        if not isinstance(organism, dict) or not isinstance(body, dict):
            raise ValueError("organism and body must be objects")

        organism_mode = str(organism.get("mode") or "new")
        body_mode = str(body.get("mode") or "fresh")
        if organism_mode not in {"new", "existing"}:
            raise ValueError("organism mode must be new or existing")
        if body_mode not in {"fresh", "resume"}:
            raise ValueError("body mode must be fresh or resume")
        if organism_mode == "new" and body_mode == "resume":
            raise ValueError("a new organism cannot resume a previous body")

        if organism_mode == "new":
            organism_ref = f"org-{uuid.uuid4().hex[:12]}"
        else:
            organism_ref = str(organism.get("ref") or "").strip()
            if not organism_ref:
                raise ValueError("existing organism requires ref")
            if organism_ref == "legacy-default":
                organism_ref = self._materialize_legacy_organism()
            metadata = self._organism_metadata(organism_ref)
            bundle = self.organisms_dir / organism_ref / "organism.symbiont"
            if not bundle.is_file():
                raise ValueError("selected organism checkpoint is unavailable")
            previous_kind = str(metadata.get("body_kind") or body_kind)
            previous_receptors = metadata.get("receptor_count")
            previous_effectors = metadata.get("effector_count")
            if previous_receptors is not None and previous_effectors is not None:
                if (
                    int(previous_receptors) != descriptor.receptor_count
                    or int(previous_effectors) != descriptor.effector_count
                ):
                    raise ValueError(
                        "selected body has an incompatible opaque sensorimotor contract"
                    )
            if body_mode == "resume" and previous_kind != body_kind:
                raise ValueError("resume requires the same body kind")

        organism_dir = self.organisms_dir / organism_ref
        organism_dir.mkdir(parents=True, exist_ok=True)
        symbiont_file = organism_dir / "organism.symbiont"

        if body_mode == "resume":
            organism_meta = self._organism_metadata(organism_ref)
            body_ref = str(organism_meta.get("last_body_ref") or "")
            if not body_ref:
                raise ValueError("selected organism has no resumable body")
            body_file = self.bodies_dir / body_ref / "body.json"
            if not body_file.is_file():
                raise ValueError("selected physical body checkpoint is unavailable")
        else:
            body_ref = f"body-{uuid.uuid4().hex[:12]}"
            body_dir = self.bodies_dir / body_ref
            body_dir.mkdir(parents=True, exist_ok=True)
            body_file = body_dir / "body.json"

        run_id = datetime.now(timezone.utc).strftime("run-%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
        run_dir = self.runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        telemetry_file = run_dir / "telemetry"

        compatibility = "new"
        previous_kind = None
        if organism_mode == "existing":
            meta = self._organism_metadata(organism_ref)
            previous_kind = meta.get("body_kind")
            same_contract = (
                meta.get("receptor_count") in (None, descriptor.receptor_count)
                and meta.get("effector_count") in (None, descriptor.effector_count)
            )
            compatibility = "same-contract" if same_contract else "incompatible"

        launch = Physics3DLaunchSpec(
            run_id=run_id,
            organism_ref=organism_ref,
            body_ref=body_ref,
            body_kind=body_kind,
            organism_mode=organism_mode,
            body_mode=body_mode,
            symbiont_file=symbiont_file,
            body_file=body_file,
            telemetry_file=telemetry_file,
        )
        manifest = {
            **launch.as_dict(),
            "status": "starting",
            "started_at": _now(),
            "ended_at": None,
            "compatibility": compatibility,
            "previous_body_kind": previous_kind,
            "contract": {
                "receptors": descriptor.receptor_count,
                "effectors": descriptor.effector_count,
                "motor_dof": descriptor.motor_dof,
            },
        }
        _write_json(run_dir / "manifest.json", manifest)
        return launch

    def mark_running(self, launch: Physics3DLaunchSpec) -> None:
        path = self.runs_dir / launch.run_id / "manifest.json"
        manifest = _read_json(path)
        manifest["status"] = "running"
        _write_json(path, manifest)

    def finalize(self, launch: Physics3DLaunchSpec, *, status: str, error: str | None = None) -> None:
        descriptor = self.body_registry.get(launch.body_kind)
        run_manifest_path = self.runs_dir / launch.run_id / "manifest.json"
        manifest = _read_json(run_manifest_path)
        summary = self._bundle_summary(launch.symbiont_file)
        manifest.update({
            "status": status,
            "ended_at": _now(),
            "error": error,
            "end_tick": summary.get("tick"),
            "organism_id": summary.get("organism_id"),
        })
        _write_json(run_manifest_path, manifest)

        organism_meta_path = self.organisms_dir / launch.organism_ref / "metadata.json"
        existing = _read_json(organism_meta_path)
        organism_meta = {
            **existing,
            **summary,
            "ref": launch.organism_ref,
            "created_at": existing.get("created_at") or manifest.get("started_at") or _now(),
            "updated_at": _now(),
            "body_kind": launch.body_kind,
            "last_body_ref": launch.body_ref,
            "last_run_id": launch.run_id,
            "receptor_count": descriptor.receptor_count,
            "effector_count": descriptor.effector_count,
        }
        _write_json(organism_meta_path, organism_meta)

        body_meta_path = self.bodies_dir / launch.body_ref / "metadata.json"
        body_meta = {
            **self._body_metadata(launch.body_ref),
            "ref": launch.body_ref,
            "body_kind": launch.body_kind,
            "updated_at": _now(),
            "last_run_id": launch.run_id,
            "organism_ref": launch.organism_ref,
            "checkpoint_available": launch.body_file.is_file(),
        }
        body_meta.setdefault("created_at", manifest.get("started_at") or _now())
        _write_json(body_meta_path, body_meta)


__all__ = [
    "DEFAULT_LAB_STATE_ROOT",
    "Physics3DLaunchSpec",
    "Physics3DRunStore",
]
