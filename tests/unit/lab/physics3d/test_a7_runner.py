import json
from dataclasses import dataclass

import pytest

from symbiont_lab.studies.physics3d.a7_artifacts import verify_execution_artifacts
from symbiont_lab.studies.physics3d.a7_campaign import A7Run
from symbiont_lab.studies.physics3d.a7_runner import run_campaign, run_execution


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
        self.apparatus = type("Apparatus", (), {"effector_ids": ("e0",)})()

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
    with pytest.raises(PermissionError, match="freeze, scientific review, and owner approval"):
        run_campaign(
            tmp_path,
            protocol_frozen=False,
            scientific_review_approved=True,
            owner_launch_approved=True,
        )
