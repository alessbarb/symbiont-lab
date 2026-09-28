"""Persistent run/organism/body catalog for the Physics3D workbench."""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from symbiont import __version__ as symbiont_version
from symbiont_lab.experience import (
    RunGuard,
    RunKind,
    consequence_policy,
    run_definition,
)
from symbiont_lab.observation.cadence import ExecutionRates
from symbiont_lab.physics3d.bodies import DEFAULT_BODY_REGISTRY, BodyRegistry
from symbiont_lab.physics3d.engine import (
    DEFAULT_STATE_DIR,
    DEFAULT_SYMBIONT_FILE,
    LEGACY_BODY_FILE,
)
from symbiont_lab.physics3d.environments import environment_recipe
from symbiont_lab.physics3d.persistence import (
    read_symbiont_bundle_manifest,
    read_symbiont_bundle_runtime,
)
from symbiont_lab.physics3d.reembodiment import lifecycle_summary

DEFAULT_LAB_STATE_ROOT = DEFAULT_STATE_DIR.parent
DEFAULT_SEED = 42


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _retain(source: Path, destination: Path) -> None:
    """Content-addressed retention: an existing destination is never rewritten."""
    if destination.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_name(f".{destination.name}.tmp")
    shutil.copy2(source, temp)
    temp.replace(destination)


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
    environment: str | None = None
    run_kind: RunKind = RunKind.WORLD_OPEN
    definition_id: str = "open-world-v1"
    seed: int = DEFAULT_SEED

    def run_guard(self) -> RunGuard:
        return RunGuard(self.run_kind)

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
        return "resume" if self.body_mode == "resume" else "reembodiment"

    def runner_kwargs(self) -> dict[str, object]:
        return {
            "body_kind": self.body_kind,
            "environment": self.environment,
            "seed": self.seed,
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
            "environment": self.environment,
            "run_kind": self.run_kind.value,
            "definition_id": self.definition_id,
            "seed": self.seed,
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
        self._include_legacy_default = self.root.resolve() == DEFAULT_LAB_STATE_ROOT.resolve()
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
        try:
            manifest = read_symbiont_bundle_manifest(bundle)
        except Exception:
            manifest = {}

        if manifest:
            return {
                "organism_id": manifest.get("organism_id"),
                "tick": int(manifest.get("saved_at_tick") or 0),
                "saved_at_tick": int(manifest.get("saved_at_tick") or 0),
                "experiences": int(
                    manifest.get("experience_count") or manifest.get("experiences") or 0
                ),
                "models": int(manifest.get("model_record_count") or manifest.get("models") or 0),
                "genome_id": manifest.get("genome_id"),
                "vital_state": manifest.get("vital_state"),
                "body_age_ticks": (
                    int(manifest["body_age_ticks"])
                    if manifest.get("body_age_ticks") is not None
                    else 0
                ),
                "body_senescence": float(manifest.get("body_senescence") or 0.0),
                "embodiment_summary_count": int(manifest.get("embodiment_summary_count") or 0),
                "known_contract_count": int(manifest.get("known_contract_count") or 0),
                "last_epoch_summary": manifest.get("last_epoch_summary"),
                "symbiont_state": manifest.get("symbiont_state", "dormant"),
                "embodiment_epoch": int(manifest.get("embodiment_epoch") or 1),
                "embodiment_history_count": int(manifest.get("embodiment_history_count") or 0),
                "body_id": manifest.get("body_id"),
                "embodiment_id": manifest.get("embodiment_id"),
                "body_kind": manifest.get("body_kind"),
                "receptor_count": manifest.get("receptor_count"),
                "effector_count": manifest.get("effector_count"),
                "checkpoint_id": manifest.get("checkpoint_id"),
                "checkpoint_hash": manifest.get("checkpoint_hash"),
                "manifest_generated_from_checkpoint_hash": manifest.get(
                    "manifest_generated_from_checkpoint_hash"
                ),
                "runnable": True,
            }

        try:
            payload = read_symbiont_bundle_runtime(bundle)
        except Exception:
            return {}
        ledger = payload.get("experience_ledger", {})
        registry = payload.get("private_model_registry", {})
        genome = payload.get("genome", {})
        living_body = payload.get("living_body", {})
        vital_state = living_body.get("vital_state") if isinstance(living_body, dict) else None
        lifecycle = lifecycle_summary(payload)
        current = lifecycle.get("current", {})
        summaries = payload.get("embodiment_epoch_summaries")
        summaries = summaries if isinstance(summaries, list) else []
        archive = payload.get("embodiment_archive")
        memories = archive.get("body_memories") if isinstance(archive, dict) else []
        memories = memories if isinstance(memories, list) else []
        known_contracts = {
            str(item.get("contract_fingerprint"))
            for item in memories
            if isinstance(item, dict)
            and isinstance(item.get("contract_fingerprint"), str)
            and item.get("contract_fingerprint")
        }
        last_summary = summaries[-1] if summaries and isinstance(summaries[-1], dict) else None
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
            "vital_state": vital_state,
            "body_age_ticks": (
                int(living_body.get("age_ticks") or 0) if isinstance(living_body, dict) else 0
            ),
            "body_senescence": (
                float(living_body.get("senescence") or 0.0)
                if isinstance(living_body, dict)
                else 0.0
            ),
            "embodiment_summary_count": len(summaries),
            "known_contract_count": len(known_contracts),
            "last_epoch_summary": last_summary,
            "symbiont_state": lifecycle.get("state", "dormant"),
            "embodiment_epoch": lifecycle.get("epoch", 1),
            "embodiment_history_count": lifecycle.get("history_count", 0),
            "body_id": current.get("body_id") if isinstance(current, dict) else None,
            "embodiment_id": (current.get("embodiment_id") if isinstance(current, dict) else None),
            "body_kind": current.get("body_kind") if isinstance(current, dict) else None,
            "receptor_count": current.get("receptor_count") if isinstance(current, dict) else None,
            "effector_count": current.get("effector_count") if isinstance(current, dict) else None,
            "runnable": True,
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

        if self._include_legacy_default and DEFAULT_SYMBIONT_FILE.is_file():
            summary = self._bundle_summary(DEFAULT_SYMBIONT_FILE)
            items.append(
                {
                    **summary,
                    "ref": "legacy-default",
                    "legacy": True,
                    "bundle_available": True,
                    "body_kind": "anthropomorphic-v4",
                    "last_body_ref": "legacy-default" if LEGACY_BODY_FILE.is_file() else None,
                }
            )
        items.sort(
            key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""),
            reverse=True,
        )
        return items

    def set_alias(self, organism_ref: str, alias: str | None) -> dict[str, Any]:
        """Observer-only human name for an organism.

        Lives in the Lab's organism metadata, never in the portable bundle or
        runtime state, so Symbiont cannot know it. Survives every run because
        finalize() merges over existing metadata. Empty clears it.
        """
        ref = str(organism_ref or "").strip()
        directory = self.organisms_dir / ref
        if not ref or "/" in ref or ref.startswith(".") or not directory.is_dir():
            raise ValueError("unknown organism")
        text = " ".join(str(alias or "").split())
        if len(text) > 64:
            raise ValueError("alias must be at most 64 characters")
        path = directory / "metadata.json"
        metadata = _read_json(path)
        if text:
            metadata["alias"] = text
        else:
            metadata.pop("alias", None)
        metadata["ref"] = ref
        _write_json(path, metadata)
        return {"ref": ref, "alias": metadata.get("alias")}

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
        if LEGACY_BODY_FILE.is_file():
            last_body_ref = f"body-legacy-{safe}"
            body_dir = self.bodies_dir / last_body_ref
            body_dir.mkdir(parents=True, exist_ok=True)
            body_destination = body_dir / "body.json"
            if not body_destination.exists():
                shutil.copy2(LEGACY_BODY_FILE, body_destination)
            _write_json(
                body_dir / "metadata.json",
                {
                    "ref": last_body_ref,
                    "body_kind": "anthropomorphic-v4",
                    "created_at": _now(),
                    "updated_at": _now(),
                    "migrated_from": str(LEGACY_BODY_FILE),
                    "organism_ref": ref,
                    "checkpoint_available": True,
                },
            )
        descriptor = self.body_registry.get("anthropomorphic-v6")
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
        body_kind = str(payload.get("body_kind") or "anthropomorphic-v6")
        descriptor = self.body_registry.get(body_kind)
        definition = run_definition(payload.get("definition_id"))
        if not definition.launchable:
            raise ValueError(
                f"{definition.definition_id} is not launchable: {definition.unavailable_reason}"
            )
        if definition.body_kind is not None and body_kind != definition.body_kind:
            raise ValueError(f"{definition.definition_id} requires body {definition.body_kind}")
        policy = consequence_policy(definition.kind)
        environment = payload.get("environment")
        if definition.environment is not None:
            if environment not in (None, definition.environment):
                raise ValueError(
                    f"{definition.definition_id} fixes environment {definition.environment}"
                )
            environment = definition.environment
        if environment is not None:
            environment_recipe(environment)
        seed = payload.get("seed", DEFAULT_SEED)
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("seed must be an integer")
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
            summary = self._bundle_summary(bundle)
            previous_kind = str(summary.get("body_kind") or metadata.get("body_kind") or body_kind)
            if body_mode == "resume":
                if summary.get("vital_state") == "dead":
                    raise ValueError("previous body is dead; select a fresh body for re-embodiment")
                if policy.refuses_start(summary.get("vital_state")):
                    raise ValueError(
                        "previous body is at the protected viability boundary; "
                        "acquisition requires a fresh body"
                    )
                if previous_kind != body_kind:
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
            if definition.environment is not None:
                # A resumed pose keeps its world; historical poses used flat-v1.
                saved_world = _read_json(body_file).get("lab_world")
                saved_name = saved_world.get("name") if isinstance(saved_world, dict) else "flat-v1"
                if saved_name != definition.environment:
                    raise ValueError(
                        f"resumed body lives in {saved_name}; {definition.definition_id} "
                        f"requires {definition.environment} and therefore a fresh body"
                    )
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
            same_contract = meta.get("receptor_count") in (
                None,
                descriptor.receptor_count,
            ) and meta.get("effector_count") in (None, descriptor.effector_count)
            compatibility = "same-contract" if same_contract else "reembodiment"

        launch = Physics3DLaunchSpec(
            run_id=run_id,
            organism_ref=organism_ref,
            body_ref=body_ref,
            body_kind=body_kind,
            environment=environment,
            organism_mode=organism_mode,
            body_mode=body_mode,
            symbiont_file=symbiont_file,
            body_file=body_file,
            telemetry_file=telemetry_file,
            run_kind=definition.kind,
            definition_id=definition.definition_id,
            seed=seed,
        )
        rates = ExecutionRates.resolve(physics_hz=240, cognition_hz=24)
        manifest = {
            **launch.as_dict(),
            "definition": definition.as_dict(),
            "rates": {
                "physics_hz": rates.physics_hz,
                "cognition_hz": rates.cognition_hz,
                "observation_hz": rates.observation_hz,
                "render_hz": rates.render_hz,
            },
            "software": {"symbiont_version": str(symbiont_version)},
            "starting_state": self._retain_state(launch),
            "termination_reason": None,
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

    def _retain_state(self, launch: Physics3DLaunchSpec) -> dict[str, Any]:
        """Identify and keep State X (ADR-0009); a new organism starts at genesis."""
        if launch.new_symbiont or not launch.symbiont_file.is_file():
            return {"genesis": True}
        state = self._retain_organism(launch.organism_ref, launch.symbiont_file)
        if launch.body_mode == "resume" and launch.body_file.is_file():
            body_hash = _sha256(launch.body_file)
            retained = (
                self.bodies_dir
                / launch.body_ref
                / "checkpoints"
                / f"{body_hash.removeprefix('sha256:')[:16]}.json"
            )
            _retain(launch.body_file, retained)
            state["body_checkpoint_hash"] = body_hash
            state["body_retained_path"] = str(retained.relative_to(self.root))
        else:
            state["body_checkpoint_hash"] = None
        return state

    def _retain_organism(self, organism_ref: str, bundle: Path) -> dict[str, Any]:
        summary = self._bundle_summary(bundle)
        bundle_hash = _sha256(bundle)
        checkpoint_id = str(
            summary.get("checkpoint_id") or f"chk-{bundle_hash.removeprefix('sha256:')[:16]}"
        )
        # checkpoint_id is organism+tick only; two bundles can share it (e.g. a
        # re-embodiment stopped before its first tick), so the name carries
        # the content hash too.
        digest = bundle_hash.removeprefix("sha256:")[:16]
        retained = (
            self.organisms_dir / organism_ref / "checkpoints" / f"{checkpoint_id}-{digest}.symbiont"
        )
        _retain(bundle, retained)
        return {
            "genesis": False,
            "checkpoint_id": checkpoint_id,
            "checkpoint_hash": summary.get("checkpoint_hash"),
            "bundle_hash": bundle_hash,
            "retained_path": str(retained.relative_to(self.root)),
            "tick": summary.get("tick"),
            "embodiment_epoch": summary.get("embodiment_epoch"),
            "embodiment_id": summary.get("embodiment_id"),
            "body_id": summary.get("body_id"),
            "symbiont_state": summary.get("symbiont_state"),
            "vital_state": summary.get("vital_state"),
        }

    def mark_running(self, launch: Physics3DLaunchSpec) -> None:
        path = self.runs_dir / launch.run_id / "manifest.json"
        manifest = _read_json(path)
        manifest["status"] = "running"
        _write_json(path, manifest)

    def finalize(
        self,
        launch: Physics3DLaunchSpec,
        *,
        status: str,
        error: str | None = None,
        termination_reason: str | None = None,
        protection_breach: bool = False,
    ) -> None:
        descriptor = self.body_registry.get(launch.body_kind)
        run_manifest_path = self.runs_dir / launch.run_id / "manifest.json"
        manifest = _read_json(run_manifest_path)
        summary = self._bundle_summary(launch.symbiont_file)
        ending_state = (
            self._retain_organism(launch.organism_ref, launch.symbiont_file)
            if launch.symbiont_file.is_file()
            else None
        )
        if ending_state is not None and launch.body_file.is_file():
            ending_state["body_checkpoint_hash"] = _sha256(launch.body_file)
        body_lost = summary.get("vital_state") == "dead"
        manifest.update(
            {
                "status": status,
                "ended_at": _now(),
                "error": error,
                "end_tick": summary.get("tick"),
                "organism_id": summary.get("organism_id"),
                "termination_reason": termination_reason,
                "protection_breach": bool(protection_breach),
                "ending_state": ending_state,
                "lifecycle": {
                    "embodiment_epoch": summary.get("embodiment_epoch"),
                    "embodiment_closed": body_lost,
                    "symbiont_state": summary.get("symbiont_state"),
                    "vital_state": summary.get("vital_state"),
                    "reembodiment_required": body_lost,
                },
            }
        )
        _write_json(run_manifest_path, manifest)

        organism_meta_path = self.organisms_dir / launch.organism_ref / "metadata.json"
        existing = _read_json(organism_meta_path)
        body_checkpoint_available = launch.body_file.is_file()
        persisted_body_kind = (
            summary.get("body_kind") or existing.get("body_kind") or launch.body_kind
        )
        persisted_receptors = (
            summary.get("receptor_count")
            if summary.get("receptor_count") is not None
            else existing.get("receptor_count", descriptor.receptor_count)
        )
        persisted_effectors = (
            summary.get("effector_count")
            if summary.get("effector_count") is not None
            else existing.get("effector_count", descriptor.effector_count)
        )
        organism_meta = {
            **existing,
            **summary,
            "ref": launch.organism_ref,
            "created_at": existing.get("created_at") or manifest.get("started_at") or _now(),
            "updated_at": _now(),
            "body_kind": persisted_body_kind,
            "last_body_ref": (
                launch.body_ref if body_checkpoint_available else existing.get("last_body_ref")
            ),
            "last_run_id": launch.run_id,
            "receptor_count": persisted_receptors,
            "effector_count": persisted_effectors,
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
            "checkpoint_available": body_checkpoint_available,
            "vital_state": summary.get("vital_state"),
            "resumable": bool(body_checkpoint_available and summary.get("vital_state") != "dead"),
        }
        body_meta.setdefault("created_at", manifest.get("started_at") or _now())
        _write_json(body_meta_path, body_meta)


__all__ = [
    "DEFAULT_LAB_STATE_ROOT",
    "Physics3DLaunchSpec",
    "Physics3DRunStore",
]
