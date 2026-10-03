"""Headless single-run and campaign orchestration for Physics3D A7.

The campaign entry point requires explicit freeze, scientific-review, and owner
launch confirmations. Creating a matrix or validating the mechanics never
implicitly authorizes execution.
"""

from __future__ import annotations

import importlib.metadata
import json
import math
import platform
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from lab.studies.physics3d.a7_artifacts import (
    compare_replays,
    verify_execution_artifacts,
    write_execution_artifacts,
)
from lab.studies.physics3d.a7_campaign import A7Run, campaign_index_payload, planned_runs

HORIZON_TICKS = 360
CHECKPOINT_TICK = 180
REPLAY_TOLERANCE = 1e-9
CONTACT_POINT_LIMIT = 100
PENETRATION_LIMIT_M = 0.02
NORMAL_FORCE_LIMIT_N = 10_000.0
JOINT_LIMIT_TOLERANCE = 1e-6


def actuation_for_tick(effector_ids: tuple[str, ...], tick: int) -> dict[str, float]:
    """Return the fixed A7 pulse schedule, or all-zero when idle is requested."""
    return {
        effector_id: 0.65 if (tick + 7 * ordinal) % 80 < 20 else 0.0
        for ordinal, effector_id in enumerate(effector_ids)
    }


def _runtime_factory(**kwargs: Any):
    from lab.physics3d.runtime import PyBulletEmbodimentRuntime

    return PyBulletEmbodimentRuntime(**kwargs)


def _git_revision() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _version(package: str) -> str:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def _new_runtime(
    run: A7Run, *, body: str, factory: Callable[..., Any], checkpoint=None, physical_state=None
):
    return factory(
        gui=False,
        seed=run.seed,
        body_kind=body,
        environment="contact-garden-v1" if run.condition == "collision" else "flat-v1",
        capture_physics_trace=True,
        runtime_checkpoint=checkpoint,
        physical_state=physical_state,
    )


def _set_collision_initial_state(runtime: Any) -> None:
    p, client, body = runtime.p, runtime.client_id, runtime.apparatus.body_id
    _, position = p.getBasePositionAndOrientation(body, physicsClientId=client)
    p.resetBasePositionAndOrientation(
        body, (1.8, 0.0, float(position[2])), (0.0, 0.0, 0.0, 1.0), physicsClientId=client
    )
    p.resetBaseVelocity(body, (0.0, 2.0, 0.0), (0.0, 0.0, 0.0), physicsClientId=client)
    for joint_index in runtime.apparatus.motor_joint_indices:
        p.resetJointState(body, joint_index, 0.0, 0.0, physicsClientId=client)


def _apply_arm(runtime: Any, run: A7Run) -> dict[str, Any]:
    if run.condition not in {"collision", "friction", "mass"}:
        return {}
    p, client, body = runtime.p, runtime.client_id, runtime.apparatus.body_id
    evidence: dict[str, Any] = {}
    if run.condition == "collision":
        _set_collision_initial_state(runtime)
    elif run.condition == "friction":
        factor = {"minus-10-percent": 0.9, "nominal": 1.0, "plus-10-percent": 1.1}[run.arm]
        requested = 0.95 * factor
        p.changeDynamics(runtime.plane_id, -1, lateralFriction=requested, physicsClientId=client)
        observed = float(p.getDynamicsInfo(runtime.plane_id, -1, physicsClientId=client)[1])
        evidence = {"requested_lateral_friction": requested, "observed_lateral_friction": observed}
        if not math.isclose(requested, observed, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(
                f"PyBullet clamped A7 friction: requested {requested}, observed {observed}"
            )
    elif run.condition == "mass":
        factor = {"minus-10-percent": 0.9, "nominal": 1.0, "plus-10-percent": 1.1}[run.arm]
        rows = []
        for link_index in range(-1, p.getNumJoints(body, physicsClientId=client)):
            info = p.getDynamicsInfo(body, link_index, physicsClientId=client)
            mass = float(info[0])
            inertia = tuple(float(value) for value in info[2])
            if mass <= 0.0:
                continue
            requested_mass = mass * factor
            requested_inertia = tuple(value * factor for value in inertia)
            p.changeDynamics(
                body,
                link_index,
                mass=requested_mass,
                localInertiaDiagonal=requested_inertia,
                physicsClientId=client,
            )
            observed = p.getDynamicsInfo(body, link_index, physicsClientId=client)
            observed_mass = float(observed[0])
            observed_inertia = tuple(float(value) for value in observed[2])
            if not math.isclose(observed_mass, requested_mass, rel_tol=0.0, abs_tol=1e-9):
                raise ValueError(f"mass change not applied at link {link_index}")
            if any(
                not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-9)
                for actual, expected in zip(observed_inertia, requested_inertia, strict=True)
            ):
                raise ValueError(f"inertia change not applied at link {link_index}")
            rows.append({"link": link_index, "mass": observed_mass, "inertia": observed_inertia})
        evidence = {"scale": factor, "segments": rows}
    return evidence


def _step_segment(
    runtime: Any, run: A7Run, *, start: int, stop: int, records: list, zero_actuation: bool
) -> None:
    ids = tuple(runtime.apparatus.effector_ids)
    for tick_no in range(start, stop + 1):
        override = (
            {effector_id: 0.0 for effector_id in ids}
            if zero_actuation
            else actuation_for_tick(ids, tick_no)
        )
        tick = runtime.step(physical_actuation_override=override)
        telemetry = runtime.passive_telemetry_state()
        physics = telemetry.get("physics")
        if not isinstance(physics, dict) or not isinstance(physics.get("raw_substeps"), list):
            raise RuntimeError(f"missing raw physics trace at tick {tick_no}")
        records.append(
            {
                "tick": asdict(tick),
                "physics": physics,
                "actuation_input": override,
                "body_id": getattr(runtime.apparatus, "body_id", None),
            }
        )


def _validate_records(
    run: A7Run,
    records: list[dict[str, Any]],
    *,
    joint_limits: dict[int, tuple[float, float, float]] | None = None,
) -> dict[str, Any]:
    max_contacts = 0
    max_penetration = 0.0
    max_normal_force = 0.0
    non_finite: list[str] = []
    contact_events = 0
    energy_values: list[float] = []
    unevaluated: list[str] = []
    joint_violations: list[str] = []
    for record_index, record in enumerate(records):
        tick = record["tick"]
        actuation = record.get("actuation_input")
        if not isinstance(actuation, dict):
            unevaluated.append(f"records[{record_index}].actuation_input")
        else:
            for effector_id, value in actuation.items():
                if (
                    not isinstance(value, (int, float))
                    or isinstance(value, bool)
                    or not math.isfinite(value)
                    or not 0.0 <= value <= 1.0
                ):
                    non_finite.append(f"records[{record_index}].actuation_input.{effector_id}")
        for name in (
            "mechanical_work_joules",
            "positive_actuator_work_joules",
            "negative_actuator_work_joules",
            "absolute_actuator_work_joules",
            "net_actuator_work_joules",
        ):
            value = tick.get(name)
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
            ):
                non_finite.append(f"records[{record_index}].tick.{name}")
            else:
                energy_values.append(float(value))
        for substep_index, substep in enumerate(record["physics"]["raw_substeps"]):
            position = substep["base_position"]
            orientation = substep["base_orientation"]
            quaternion_norm = math.sqrt(sum(float(value) ** 2 for value in orientation))
            vectors = {
                "base_position": position,
                "base_orientation": orientation,
                "linear_velocity": substep.get("linear_velocity", ()),
                "angular_velocity": substep.get("angular_velocity", ()),
            }
            for field, values in vectors.items():
                if not values or any(not math.isfinite(float(value)) for value in values):
                    non_finite.append(f"records[{record_index}].substeps[{substep_index}].{field}")
            for joint_index, joint in enumerate(substep.get("joints", [])):
                for field in ("position", "velocity", "commanded_torque"):
                    value = joint.get(field)
                    if value is None or not math.isfinite(float(value)):
                        non_finite.append(
                            f"records[{record_index}].substeps[{substep_index}]"
                            f".joints[{joint_index}].{field}"
                        )
                declared = (joint_limits or {}).get(int(joint.get("joint_index", joint_index)))
                if declared is None:
                    unevaluated.append(
                        f"records[{record_index}].substeps[{substep_index}]"
                        f".joints[{joint_index}].declared_limits"
                    )
                elif all(
                    isinstance(joint.get(field), (int, float))
                    and not isinstance(joint.get(field), bool)
                    and math.isfinite(float(joint[field]))
                    for field in ("position", "velocity")
                ):
                    lower, upper, maximum_velocity = declared
                    position_value = float(joint["position"])
                    velocity_value = float(joint["velocity"])
                    if (
                        position_value < lower - JOINT_LIMIT_TOLERANCE
                        or position_value > upper + JOINT_LIMIT_TOLERANCE
                    ):
                        joint_violations.append(
                            f"records[{record_index}].substeps[{substep_index}]"
                            f".joints[{joint_index}].position_outside_declared_range"
                        )
                    elif abs(velocity_value) > maximum_velocity + JOINT_LIMIT_TOLERANCE:
                        joint_violations.append(
                            f"records[{record_index}].substeps[{substep_index}]"
                            f".joints[{joint_index}].velocity_exceeds_declared_limit"
                        )
            if any(not math.isfinite(float(value)) for value in (*position, *orientation)):
                non_finite.append(f"records[{record_index}].substeps[{substep_index}].transform")
            elif abs(quaternion_norm - 1.0) > 1e-6:
                non_finite.append(
                    f"records[{record_index}].substeps[{substep_index}].quaternion_norm"
                )
            contacts = substep.get("contacts", [])
            body_id = record.get("body_id")
            external_contacts = [
                contact
                for contact in contacts
                if body_id is None
                or not (contact.get("body_a") == body_id and contact.get("body_b") == body_id)
            ]
            max_contacts = max(max_contacts, len(external_contacts))
            contact_events += len(external_contacts)
            for contact in external_contacts:
                for field in (
                    "position_a",
                    "position_b",
                    "normal_on_b",
                    "distance",
                    "normal_force",
                    "lateral_friction_1",
                    "lateral_friction_2",
                ):
                    values = (
                        contact.get(field, ())
                        if field in {"position_a", "position_b", "normal_on_b"}
                        else (contact.get(field),)
                    )
                    if any(value is None or not math.isfinite(float(value)) for value in values):
                        non_finite.append(
                            f"records[{record_index}].substeps[{substep_index}].contacts.{field}"
                        )
                max_penetration = max(max_penetration, max(0.0, -float(contact["distance"])))
                max_normal_force = max(max_normal_force, float(contact["normal_force"]))
    collision_not_testable = run.condition == "collision" and not contact_events
    failures = []
    if non_finite:
        failures.append("non-finite or invalid physical state/work")
    if joint_violations:
        failures.append("joint state exceeds declared anatomical or velocity limits")
    if max_contacts > CONTACT_POINT_LIMIT:
        failures.append("contact point count exceeds criterion")
    if max_penetration > PENETRATION_LIMIT_M:
        failures.append("penetration exceeds criterion")
    if max_normal_force > NORMAL_FORCE_LIMIT_N:
        failures.append("normal force exceeds criterion")
    outcome = (
        "fail"
        if failures
        else "inconclusive"
        if unevaluated
        else "not_testable"
        if collision_not_testable
        else "pass"
    )
    return {
        "outcome": outcome,
        **(
            {"reason": "prescribed collision produced no external contact"}
            if collision_not_testable and not failures and not unevaluated
            else {}
        ),
        "failures": failures,
        "observed": {
            "record_count": len(records),
            "contact_events": contact_events,
            "max_contact_points": max_contacts,
            "max_penetration_m": max_penetration,
            "max_normal_force_n": max_normal_force,
            "energy_work_min": min(energy_values, default=None),
            "energy_work_max": max(energy_values, default=None),
        },
        "criteria": {
            "max_contact_points": CONTACT_POINT_LIMIT,
            "max_penetration_m": PENETRATION_LIMIT_M,
            "max_normal_force_n": NORMAL_FORCE_LIMIT_N,
            "quaternion_norm_error": 1e-6,
            "joint_limit_tolerance": JOINT_LIMIT_TOLERANCE,
            "joint_position_and_velocity_limits": "body descriptor declarations",
        },
        "non_finite_fields": non_finite,
        "unevaluated_fields": sorted(set(unevaluated)),
        "joint_limit_violations": joint_violations,
    }


def run_execution(
    run: A7Run,
    artifact_root: Path,
    *,
    horizon: int = HORIZON_TICKS,
    protocol_frozen: bool = False,
    scientific_review_approved: bool = False,
    owner_launch_approved: bool = False,
    runtime_factory: Callable[..., Any] = _runtime_factory,
) -> Path:
    """Execute one A7 run and persist an immutable directory of raw evidence.

    This low-level function is for controlled runner validation only. Production
    campaign launch is mediated by ``run_campaign`` and its authorization gate.
    """
    if not (protocol_frozen and scientific_review_approved and owner_launch_approved):
        raise PermissionError("A7 execution requires freeze, scientific review, and owner approval")
    if horizon < 2:
        raise ValueError("horizon must be at least two ticks for checkpoint/replay split")
    destination = artifact_root.joinpath(*run.key.split("/"))
    if destination.exists():
        raise FileExistsError(destination)
    runtime = None
    records: list[dict[str, Any]] = []
    checkpoints: list[dict[str, Any]] = []
    perturbation_evidence: dict[str, Any] = {}
    initial_states: list[dict[str, Any]] = []
    try:
        source_body = run.source_body or run.body
        runtime = _new_runtime(run, body=source_body, factory=runtime_factory)
        perturbation_evidence.update(_apply_arm(runtime, run))
        initial_states.append(runtime.physical_checkpoint()[0])
        split = min(CHECKPOINT_TICK, horizon // 2)
        if run.condition == "re-embodiment":
            _step_segment(runtime, run, start=1, stop=split, records=records, zero_actuation=True)
            checkpoint = runtime.checkpoint(advance_lineage=False)
            checkpoints.append(
                {
                    "tick": runtime.tick_count,
                    "organism": checkpoint,
                    "physical": runtime.physical_checkpoint()[0],
                }
            )
            runtime.close()
            runtime = _new_runtime(
                run,
                body=run.destination_body or run.body,
                factory=runtime_factory,
                checkpoint=checkpoint,
            )
            initial_states.append(runtime.physical_checkpoint()[0])
            _step_segment(
                runtime, run, start=split + 1, stop=horizon, records=records, zero_actuation=True
            )
        elif run.condition == "checkpoint-restore":
            _step_segment(runtime, run, start=1, stop=split, records=records, zero_actuation=True)
            checkpoint = runtime.checkpoint(advance_lineage=False)
            physical, physical_tick = runtime.physical_checkpoint()
            checkpoints.append(
                {"tick": physical_tick, "organism": checkpoint, "physical": physical}
            )
            runtime.close()
            runtime = _new_runtime(
                run,
                body=run.body,
                factory=runtime_factory,
                checkpoint=checkpoint,
                physical_state=physical,
            )
            _apply_arm(runtime, run)
            initial_states.append(runtime.physical_checkpoint()[0])
            _step_segment(
                runtime, run, start=split + 1, stop=horizon, records=records, zero_actuation=True
            )
        else:
            for segment_start in range(1, horizon + 1, split):
                segment_stop = min(horizon, segment_start + split - 1)
                _step_segment(
                    runtime,
                    run,
                    start=segment_start,
                    stop=segment_stop,
                    records=records,
                    zero_actuation=run.condition != "actuation",
                )
                if segment_stop < horizon:
                    checkpoint = runtime.checkpoint(advance_lineage=False)
                    physical, physical_tick = runtime.physical_checkpoint()
                    checkpoints.append(
                        {"tick": physical_tick, "organism": checkpoint, "physical": physical}
                    )
        descriptor = getattr(runtime, "body_descriptor", None)
        joint_specs = getattr(descriptor, "observer_joint_specs", ())
        joint_limits = {
            joint_index: (float(spec.lower), float(spec.upper), float(spec.max_velocity))
            for joint_index, spec in zip(
                runtime.apparatus.motor_joint_indices, joint_specs, strict=True
            )
        }
        validation = _validate_records(run, records, joint_limits=joint_limits)
        validation["perturbation_readback"] = perturbation_evidence
        validation["observed_embodiment_ids"] = sorted(
            {record["tick"]["embodiment_id"] for record in records}
        )
        manifest = {
            "protocol": "design.embodiment.physics3d-a7-stability-gate-v1",
            "run": asdict(run),
            "run_key": run.key,
            "repository_revision": _git_revision(),
            "python_version": platform.python_version(),
            "package_version": _version("symbiont-lab"),
            "pybullet_version": _version("pybullet"),
            "host": platform.platform(),
            "horizon_ticks": horizon,
            "checkpoint_tick": split,
            "time_step_s": 1.0 / 240.0,
            "physics_substeps_per_tick": 10,
            "record_count": len(records),
            "initial_physical_states": initial_states,
            "gravity_m_s2": [0.0, 0.0, -9.81],
            "solver_configuration": runtime.p.getPhysicsEngineParameters(
                physicsClientId=runtime.client_id
            ),
        }
    finally:
        if runtime is not None:
            runtime.close()
    write_execution_artifacts(
        destination,
        manifest=manifest,
        ticks=records,
        checkpoints=checkpoints,
        validation=validation,
    )
    return destination


def run_campaign(
    artifact_root: Path,
    *,
    runner_validated: bool = False,
    artifact_replay_gates_passed: bool = False,
    protocol_frozen: bool,
    scientific_review_approved: bool,
    owner_launch_approved: bool,
    runs: tuple[A7Run, ...] | None = None,
    runtime_factory: Callable[..., Any] = _runtime_factory,
) -> dict[str, Any]:
    """Run the matrix only when all independent launch gates are explicitly true."""
    if not (
        runner_validated
        and artifact_replay_gates_passed
        and protocol_frozen
        and scientific_review_approved
        and owner_launch_approved
    ):
        raise PermissionError(
            "A7 launch requires runner validation, artifact/replay gates, protocol freeze, "
            "scientific review, and owner approval"
        )
    selected_runs = runs if runs is not None else planned_runs()
    if not selected_runs:
        raise ValueError("campaign matrix is empty")
    required_keys = {run.key for run in planned_runs()}
    if (
        len(selected_runs) != len(required_keys)
        or {run.key for run in selected_runs} != required_keys
    ):
        raise ValueError("A7 campaign must contain the exact complete preregistered run matrix")
    completed: dict[str, Path] = {}
    execution_errors: list[dict[str, str]] = []
    for run in selected_runs:
        try:
            completed[run.key] = run_execution(
                run,
                artifact_root,
                protocol_frozen=protocol_frozen,
                scientific_review_approved=scientific_review_approved,
                owner_launch_approved=owner_launch_approved,
                runtime_factory=runtime_factory,
            )
        except Exception as exc:
            execution_errors.append({"run_key": run.key, "error": f"{type(exc).__name__}: {exc}"})
            break
    outcomes: list[dict[str, Any]] = []
    replay_groups: dict[tuple[str, str, str, int], dict[int, Path]] = {}
    for run in selected_runs:
        path = completed.get(run.key)
        if path is None:
            outcomes.append(
                {
                    "run_key": run.key,
                    "outcome": "inconclusive",
                    "reason": "execution did not produce artifacts",
                }
            )
            continue
        integrity = verify_execution_artifacts(path)
        if not integrity["integrity"]:
            outcomes.append({"run_key": run.key, "outcome": "inconclusive", "integrity": integrity})
        else:
            replay_groups.setdefault((run.body, run.condition, run.arm, run.seed), {})[
                run.repeat
            ] = path
            validation = json.loads((path / "validation.json").read_text(encoding="utf-8"))
            outcomes.append(
                {
                    "run_key": run.key,
                    "manifest": f"{run.key}/manifest.json",
                    "outcome": validation["outcome"],
                    "integrity": integrity,
                }
            )
    replay_comparisons = []
    for group in sorted({(run.body, run.condition, run.arm, run.seed) for run in selected_runs}):
        repeat_paths = replay_groups.get(group, {})
        if set(repeat_paths) != {1, 2}:
            replay_comparisons.append(
                {"group": group, "pass": False, "reason": "missing or invalid repeat artifacts"}
            )
            continue
        left = _load_replay_projection(repeat_paths[1] / "ticks.jsonl")
        right = _load_replay_projection(repeat_paths[2] / "ticks.jsonl")
        result = compare_replays(left, right, tolerance=REPLAY_TOLERANCE)
        replay_comparisons.append({"group": group, **result})
    index = campaign_index_payload()
    index.update(
        {
            "execution_authorized": True,
            "campaign_status": "partial" if execution_errors else "completed",
            "execution_errors": execution_errors,
            "completed_runs": outcomes,
            "replay_comparisons": replay_comparisons,
            "all_replays_pass": all(item.get("pass") is True for item in replay_comparisons),
        }
    )
    index_path = artifact_root / "campaign-index.json"
    if index_path.exists():
        raise FileExistsError(f"A7 campaign index is immutable: {index_path}")
    index_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = index_path.with_name(f".{index_path.name}.tmp")
    temporary.write_text(
        json.dumps(index, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    temporary.rename(index_path)
    return index


def _load_replay_projection(path: Path) -> list[dict[str, Any]]:
    projection = []
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        physics = record["physics"]
        tick = record["tick"]
        projection.append(
            {
                "tick": tick["tick"],
                "embodiment_id": tick["embodiment_id"],
                "actuation_input": record["actuation_input"],
                "raw_substeps": physics["raw_substeps"],
                "mechanical_work_joules": physics["mechanical_work_joules"],
                "positive_actuator_work_joules": physics["positive_actuator_work_joules"],
                "negative_actuator_work_joules": physics["negative_actuator_work_joules"],
                "absolute_actuator_work_joules": physics["absolute_actuator_work_joules"],
                "net_actuator_work_joules": physics["net_actuator_work_joules"],
                "contact_count": physics["contact_count"],
                "ground_contact_count": physics["ground_contact_count"],
                "self_contact_count": physics["self_contact_count"],
                "resource_contact_count": physics["resource_contact_count"],
                "max_contact_normal_force": physics["max_contact_normal_force"],
            }
        )
    return projection
