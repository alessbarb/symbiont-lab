import json
from dataclasses import dataclass

import pytest

from symbiont_lab.studies.physics3d.a7_artifacts import (
    verify_execution_artifacts,
    write_execution_artifacts,
)
from symbiont_lab.studies.physics3d.a7_campaign import A7Run
from symbiont_lab.studies.physics3d.a7_runner import _validate_records, run_campaign, run_execution


@dataclass(frozen=True)
class FakeTick:
    tick: int
    embodiment_id: str
    mechanical_work_joules: float = 0.0
    positive_actuator_work_joules: float = 0.0
    negative_actuator_work_joules: float = 0.0
    absolute_actuator_work_joules: float = 0.0
    net_actuator_work_joules: float = 0.0


class FakeRuntime:
    def __init__(self, **_kwargs):
        self.tick_count = 0
        self.p = self
        self.client_id = 0
        self.apparatus = type(
            "Apparatus",
            (),
            {"effector_ids": ("e0",), "body_id": 1, "motor_joint_indices": (0,)},
        )()
        self.body_descriptor = type(
            "Descriptor",
            (),
            {
                "observer_joint_specs": (
                    type("JointSpec", (), {"lower": -1.0, "upper": 1.0, "max_velocity": 2.0})(),
                )
            },
        )()

    def getPhysicsEngineParameters(self, **_kwargs):
        return {"numSolverIterations": 120, "fixedTimeStep": 1 / 240}

    def physical_checkpoint(self):
        return {"tick": self.tick_count}, self.tick_count

    def checkpoint(self, **_kwargs):
        return {"saved_at_tick": self.tick_count}

    def step(self, **_kwargs):
        self.tick_count += 1
        return FakeTick(self.tick_count, "body-1")

    def passive_telemetry_state(self):
        return {
            "physics": {
                "raw_substeps": [
                    {
                        "base_position": [0.0, 0.0, 1.0],
                        "base_orientation": [0.0, 0.0, 0.0, 1.0],
                        "linear_velocity": [0.0, 0.0, 0.0],
                        "angular_velocity": [0.0, 0.0, 0.0],
                        "joints": [{"position": 0.0, "velocity": 0.0, "commanded_torque": 0.0}],
                        "contacts": [],
                    }
                ],
                "mechanical_work_joules": 0.0,
                "positive_actuator_work_joules": 0.0,
                "negative_actuator_work_joules": 0.0,
                "absolute_actuator_work_joules": 0.0,
                "net_actuator_work_joules": 0.0,
                "contact_count": 0,
                "ground_contact_count": 0,
                "self_contact_count": 0,
                "resource_contact_count": 0,
                "max_contact_normal_force": 0.0,
            }
        }

    def close(self):
        pass


def _run():
    return A7Run(
        body="anthropomorphic-v6",
        condition="idle",
        arm="nominal",
        seed=42,
        repeat=1,
    )


def test_a7_single_execution_refuses_to_run_without_all_authorizations(tmp_path):
    called = False

    def factory(**_kwargs):
        nonlocal called
        called = True
        return FakeRuntime()

    with pytest.raises(PermissionError, match="freeze, scientific review, and owner approval"):
        run_execution(_run(), tmp_path, runtime_factory=factory, horizon=2)
    assert not called


def test_a7_single_execution_writes_hashed_per_run_artifacts(tmp_path):
    directory = run_execution(
        _run(),
        tmp_path,
        horizon=2,
        protocol_frozen=True,
        scientific_review_approved=True,
        owner_launch_approved=True,
        runtime_factory=FakeRuntime,
    )

    assert verify_execution_artifacts(directory)["integrity"] is True
    assert len((directory / "ticks.jsonl").read_text(encoding="utf-8").splitlines()) == 2
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["record_count"] == 2
    assert manifest["solver_configuration"]["numSolverIterations"] == 120
    summary = json.loads((directory / "validation.json").read_text(encoding="utf-8"))
    assert summary["outcome"] == "pass"


def test_a7_campaign_refuses_launch_when_a_gate_is_missing(tmp_path):
    with pytest.raises(
        PermissionError,
        match="runner validation, artifact/replay gates, protocol freeze, scientific review",
    ):
        run_campaign(
            tmp_path,
            runner_validated=True,
            artifact_replay_gates_passed=True,
            protocol_frozen=False,
            scientific_review_approved=True,
            owner_launch_approved=True,
        )


def test_collision_self_contact_does_not_count_as_prescribed_fixture_contact():
    run = A7Run(
        body="anthropomorphic-v6",
        condition="collision",
        arm="nominal",
        seed=42,
        repeat=1,
    )
    self_contact = {
        "body_a": 7,
        "body_b": 7,
        "link_a": 0,
        "link_b": 1,
        "position_a": [0.0, 0.0, 0.0],
        "position_b": [0.0, 0.0, 0.0],
        "normal_on_b": [0.0, 0.0, 1.0],
        "distance": 0.0,
        "normal_force": 1.0,
        "lateral_friction_1": 0.0,
        "lateral_friction_2": 0.0,
    }
    records = [
        {
            "body_id": 7,
            "actuation_input": {"eff.0": 0.0},
            "tick": {
                "mechanical_work_joules": 0.0,
                "positive_actuator_work_joules": 0.0,
                "negative_actuator_work_joules": 0.0,
                "absolute_actuator_work_joules": 0.0,
                "net_actuator_work_joules": 0.0,
            },
            "physics": {
                "raw_substeps": [
                    {
                        "base_position": [0.0, 0.0, 1.0],
                        "base_orientation": [0.0, 0.0, 0.0, 1.0],
                        "linear_velocity": [0.0, 0.0, 0.0],
                        "angular_velocity": [0.0, 0.0, 0.0],
                        "joints": [],
                        "contacts": [self_contact],
                    }
                ]
            },
        }
    ]

    result = _validate_records(run, records)

    assert result["outcome"] == "not_testable"
    assert result["observed"]["contact_events"] == 0


def test_validation_enforces_descriptor_joint_position_and_velocity_limits():
    run = _run()
    records = [
        {
            "actuation_input": {"eff.0": 0.0},
            "tick": {
                name: 0.0
                for name in (
                    "mechanical_work_joules",
                    "positive_actuator_work_joules",
                    "negative_actuator_work_joules",
                    "absolute_actuator_work_joules",
                    "net_actuator_work_joules",
                )
            },
            "physics": {
                "raw_substeps": [
                    {
                        "base_position": [0.0, 0.0, 1.0],
                        "base_orientation": [0.0, 0.0, 0.0, 1.0],
                        "linear_velocity": [0.0, 0.0, 0.0],
                        "angular_velocity": [0.0, 0.0, 0.0],
                        "joints": [
                            {
                                "joint_index": 0,
                                "position": 1.1,
                                "velocity": 0.1,
                                "commanded_torque": 0.0,
                            }
                        ],
                        "contacts": [],
                    }
                ]
            },
        }
    ]

    result = _validate_records(run, records, joint_limits={0: (-1.0, 1.0, 2.0)})

    assert result["outcome"] == "fail"
    assert result["joint_limit_violations"]


@pytest.mark.parametrize(
    "missing_gate",
    ("runner_validated", "artifact_replay_gates_passed"),
)
def test_a7_campaign_requires_runner_and_artifact_replay_gates(tmp_path, missing_gate):
    gates = {
        "runner_validated": True,
        "artifact_replay_gates_passed": True,
        "protocol_frozen": True,
        "scientific_review_approved": True,
        "owner_launch_approved": True,
    }
    gates[missing_gate] = False
    with pytest.raises(PermissionError, match="runner validation, artifact/replay gates"):
        run_campaign(tmp_path, **gates)


def test_a7_campaign_indexes_exact_264_runs_and_replay_gates(tmp_path, monkeypatch):
    launches = []
    raw_substep = {
        "base_position": [0.0, 0.0, 1.0],
        "base_orientation": [0.0, 0.0, 0.0, 1.0],
        "linear_velocity": [0.0, 0.0, 0.0],
        "angular_velocity": [0.0, 0.0, 0.0],
        "joints": [],
        "contacts": [],
    }

    def fake_run_execution(run, artifact_root, **_kwargs):
        launches.append(run.key)
        destination = artifact_root.joinpath(*run.key.split("/"))
        tick = {
            "tick": 1,
            "embodiment_id": run.body,
            "mechanical_work_joules": 0.0,
            "positive_actuator_work_joules": 0.0,
            "negative_actuator_work_joules": 0.0,
            "absolute_actuator_work_joules": 0.0,
            "net_actuator_work_joules": 0.0,
        }
        physics = {
            "raw_substeps": [raw_substep],
            "mechanical_work_joules": 0.0,
            "positive_actuator_work_joules": 0.0,
            "negative_actuator_work_joules": 0.0,
            "absolute_actuator_work_joules": 0.0,
            "net_actuator_work_joules": 0.0,
            "contact_count": 0,
            "ground_contact_count": 0,
            "self_contact_count": 0,
            "resource_contact_count": 0,
            "max_contact_normal_force": 0.0,
        }
        write_execution_artifacts(
            destination,
            manifest={"run_key": run.key},
            ticks=[{"tick": tick, "physics": physics, "actuation_input": {"eff.0": 0.0}}],
            checkpoints=[],
            validation={"outcome": "pass"},
        )
        return destination

    monkeypatch.setattr(
        "symbiont_lab.studies.physics3d.a7_runner.run_execution", fake_run_execution
    )
    index = run_campaign(
        tmp_path,
        runner_validated=True,
        artifact_replay_gates_passed=True,
        protocol_frozen=True,
        scientific_review_approved=True,
        owner_launch_approved=True,
    )

    assert len(launches) == 264
    assert len(set(launches)) == 264
    assert index["execution_count"] == 264
    assert len(index["completed_runs"]) == 264
    assert index["all_replays_pass"] is True
    assert len(index["replay_comparisons"]) == 132


def test_a7_interrupted_campaign_writes_full_index_with_inconclusive_missing_runs(
    tmp_path, monkeypatch
):
    calls = 0

    def interrupted_run(run, artifact_root, **_kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("simulated stop")
        destination = artifact_root.joinpath(*run.key.split("/"))
        write_execution_artifacts(
            destination,
            manifest={"run_key": run.key},
            ticks=[],
            checkpoints=[],
            validation={"outcome": "pass"},
        )
        return destination

    monkeypatch.setattr("symbiont_lab.studies.physics3d.a7_runner.run_execution", interrupted_run)
    index = run_campaign(
        tmp_path,
        runner_validated=True,
        artifact_replay_gates_passed=True,
        protocol_frozen=True,
        scientific_review_approved=True,
        owner_launch_approved=True,
    )

    assert index["campaign_status"] == "partial"
    assert len(index["completed_runs"]) == 264
    assert sum(run["outcome"] == "inconclusive" for run in index["completed_runs"]) == 263
    assert index["execution_errors"][0]["error"] == "RuntimeError: simulated stop"
    assert len(index["replay_comparisons"]) == 132
    assert index["all_replays_pass"] is False
