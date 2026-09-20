"""Symbiont <-> physical 3D body runtime.

This layer intentionally keeps anatomical semantics on the apparatus side.
Symbiont receives only EmbodimentSession channel IDs.
"""
from __future__ import annotations

from dataclasses import dataclass

from symbiont.core.body import Body, BodyPhysiology, EffectorPort, ReceptorPort
from symbiont.core.embodiment import implant_body
from symbiont.core.individual import Individual
from symbiont.core.symbiont import Symbiont

from .humanoid import HumanoidPhysics


@dataclass(frozen=True, slots=True)
class Tick3D:
    tick: int
    alive: bool
    base_position: tuple[float, float, float]
    base_orientation: tuple[float, float, float, float]
    schema_confidence: float


class PyBulletEmbodimentRuntime:
    """One physically simulated anthropomorphic Symbiont individual."""

    def __init__(
        self,
        *,
        gui: bool = True,
        seed: int = 42,
        time_step: float = 1.0 / 240.0,
    ) -> None:
        try:
            import pybullet as p
        except ImportError as exc:
            raise RuntimeError(
                "PyBullet is optional. Install with: pip install 'symbiont-lab[physics3d]'"
            ) from exc

        self.p = p
        self.time_step = float(time_step)
        mode = p.GUI if gui else p.DIRECT
        self.client_id = p.connect(mode)
        if self.client_id < 0:
            raise RuntimeError("failed to connect to PyBullet")

        p.setGravity(0.0, 0.0, -9.81, physicsClientId=self.client_id)
        p.setTimeStep(self.time_step, physicsClientId=self.client_id)
        p.setPhysicsEngineParameter(
            numSolverIterations=30,
            fixedTimeStep=self.time_step,
            physicsClientId=self.client_id,
        )

        plane_shape = p.createCollisionShape(
            p.GEOM_PLANE,
            planeNormal=(0.0, 0.0, 1.0),
            physicsClientId=self.client_id,
        )
        self.plane_id = p.createMultiBody(
            baseMass=0.0,
            baseCollisionShapeIndex=plane_shape,
            physicsClientId=self.client_id,
        )
        p.changeDynamics(
            self.plane_id,
            -1,
            lateralFriction=0.95,
            restitution=0.0,
            physicsClientId=self.client_id,
        )

        self.apparatus = HumanoidPhysics(p, self.client_id)

        receptors = [
            ReceptorPort(
                port_id=receptor_id,
                kind="physical",
                ordinal=index,
                read_fn=lambda rid=receptor_id: self.apparatus.receptor_value(rid),
            )
            for index, receptor_id in enumerate(self.apparatus.receptor_ids)
        ]
        effectors = [
            EffectorPort(
                port_id=effector_id,
                kind="motor",
                ordinal=index,
                cost_per_activation=0.0,
            )
            for index, effector_id in enumerate(self.apparatus.effector_ids)
        ]
        # Mechanics-only milestone: ecological metabolism is deliberately absent
        # here. Later work can couple actual joint work to physiological cost.
        physiology = BodyPhysiology(
            energy_reserve=1.0,
            max_energy=1.0,
            basal_metabolic_rate=0.0,
            degradation_rate=0.0,
        )
        body = Body(
            "body:anthropomorphic-v0",
            morphology_name="anthropomorphic-v0",
            receptors=receptors,
            effectors=effectors,
            physiology=physiology,
        )
        symbiont = Symbiont("symbiont:3d-subject", seed=seed)
        session = implant_body(symbiont.symbiont_id, body, started_at=0)
        self.individual = Individual(symbiont=symbiont, body=body, session=session)
        self.tick_count = 0

        if gui:
            p.resetDebugVisualizerCamera(
                cameraDistance=3.1,
                cameraYaw=38.0,
                cameraPitch=-20.0,
                cameraTargetPosition=(0.0, 0.0, 0.9),
                physicsClientId=self.client_id,
            )
            p.configureDebugVisualizer(
                p.COV_ENABLE_GUI,
                0,
                physicsClientId=self.client_id,
            )

    def step(self) -> Tick3D:
        self.apparatus.sample_receptors()

        physical_readings = self.individual.body.transduce_signals()
        opaque_inputs = self.individual.session.transduce_to_symbiont(physical_readings)
        opaque_activations = self.individual.symbiont.step(opaque_inputs)
        physical_commands = self.individual.session.route_to_body(opaque_activations)
        consequences = self.individual.body.apply_activations(physical_commands)
        applied = {
            effector_id: consequence.applied_level
            for effector_id, consequence in consequences.items()
        }
        self.apparatus.apply_effectors(applied)
        self.p.stepSimulation(physicsClientId=self.client_id)
        self.individual.body.tick_physics()
        self.tick_count += 1

        position, orientation = self.p.getBasePositionAndOrientation(
            self.apparatus.body_id,
            physicsClientId=self.client_id,
        )
        return Tick3D(
            tick=self.tick_count,
            alive=self.individual.is_alive,
            base_position=tuple(float(x) for x in position),
            base_orientation=tuple(float(x) for x in orientation),
            schema_confidence=float(
                self.individual.symbiont.body_schema.overall_confidence
            ),
        )

    def close(self) -> None:
        if self.client_id >= 0:
            self.p.disconnect(physicsClientId=self.client_id)
            self.client_id = -1

    def __enter__(self) -> "PyBulletEmbodimentRuntime":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
