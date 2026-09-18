from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
import math
from typing import Any, Iterable, Mapping

from ..host.percepts import Percept
from ..host.readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit
from .fitness import sensory_fitness
from .limits import SensoryLimits
from .modalities import DEFAULT_MODALITIES, SensoryModality
from .plasticity import SensoryMutation, SensoryMutationKind
from .sensor import MaturityState, SensorState
from .transduction import TransductionKind, apply_transduction


_QUALITY_SCORE = {
    ReadingQuality.NOMINAL: 1.0,
    ReadingQuality.DEGRADED: 0.6,
    ReadingQuality.STALE: 0.25,
    ReadingQuality.UNAVAILABLE: 0.0,
}


class SensorySystem:
    """Organism-owned transduction between raw host samples and cognition."""

    SCHEMA_VERSION = 1

    def __init__(
        self,
        *,
        limits: SensoryLimits | None = None,
        modalities: Iterable[SensoryModality] = DEFAULT_MODALITIES,
        plasticity_enabled: bool = False,
        next_sensor_id: int = 1,
    ) -> None:
        self.limits = limits or SensoryLimits()
        resolved = tuple(modalities)
        if not resolved or len(resolved) > self.limits.max_modalities:
            raise ValueError("invalid sensory modality count")
        if len({item.modality_id for item in resolved}) != len(resolved):
            raise ValueError("sensory modality ids must be unique")
        self._modalities = {item.modality_id: item for item in resolved}
        if "modality.identity" not in self._modalities:
            raise ValueError("identity modality is required for compatibility")
        self.plasticity_enabled = bool(plasticity_enabled)
        if isinstance(next_sensor_id, bool) or not isinstance(next_sensor_id, int) or next_sensor_id < 1:
            raise ValueError("next_sensor_id must be positive")
        self._next_sensor_id = next_sensor_id
        self._sensors: dict[str, SensorState] = {}
        self._mutations: list[SensoryMutation] = []
        self._last_tick = 0

    @property
    def sensors(self) -> tuple[SensorState, ...]:
        return tuple(self._sensors[key] for key in sorted(self._sensors))

    @property
    def modalities(self) -> tuple[SensoryModality, ...]:
        return tuple(self._modalities[key] for key in sorted(self._modalities))

    @property
    def mutations(self) -> tuple[SensoryMutation, ...]:
        return tuple(self._mutations)

    def constitution(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "plasticity_enabled": self.plasticity_enabled,
            "limits": asdict(self.limits),
            "modalities": [
                {
                    "modality_id": item.modality_id,
                    "allowed_transductions": [kind.value for kind in item.allowed_transductions],
                    "max_inputs": item.max_inputs,
                    "temporal_capacity": item.temporal_capacity,
                    "base_cost": item.base_cost,
                }
                for item in self.modalities
            ],
        }

    @staticmethod
    def _identity_id(source_id: str) -> str:
        digest = sha256(f"symbiont-sensor-identity:{source_id}".encode("utf-8")).hexdigest()[:24]
        return f"sensor.identity.{digest}"

    def ensure_identity_sensor(self, source_id: str, cognitive_name: str, *, tick: int) -> SensorState:
        sensor_id = self._identity_id(source_id)
        existing = self._sensors.get(sensor_id)
        if existing is not None:
            # Cognitive aliases may legitimately evolve while the physical
            # sensor identity remains tied to the source.
            existing.cognitive_name = cognitive_name
            return existing
        if len(self._sensors) >= self.limits.max_active_sensors:
            raise ValueError("sensory system active sensor limit reached")
        modality = self._modalities["modality.identity"]
        sensor = SensorState(
            sensor_id=sensor_id,
            modality_id=modality.modality_id,
            source_ids=(source_id,),
            cognitive_name=cognitive_name,
            transduction=TransductionKind.IDENTITY,
            born_tick=tick,
            transduction_cost=modality.base_cost,
        )
        self._sensors[sensor_id] = sensor
        return sensor

    def _allocate_id(self) -> str:
        while True:
            sensor_id = f"sensor.{self._next_sensor_id:08d}"
            self._next_sensor_id += 1
            if sensor_id not in self._sensors:
                return sensor_id

    def duplicate(
        self,
        parent_sensor_id: str,
        *,
        modality_id: str,
        transduction: TransductionKind | None = None,
        tick: int,
    ) -> SensorState:
        if len(self._sensors) >= self.limits.max_active_sensors:
            raise ValueError("sensory system active sensor limit reached")
        parent = self._sensors[parent_sensor_id]
        modality = self._modalities[modality_id]
        if len(parent.source_ids) > modality.max_inputs:
            raise ValueError("modality cannot accept the parent source count")
        candidates = tuple(kind for kind in modality.allowed_transductions if kind is not TransductionKind.IDENTITY)
        kind = transduction or (candidates[0] if candidates else TransductionKind.IDENTITY)
        if kind not in modality.allowed_transductions:
            raise ValueError("transduction is not available in modality")
        sensor_id = self._allocate_id()
        child = SensorState(
            sensor_id=sensor_id,
            modality_id=modality_id,
            source_ids=parent.source_ids,
            cognitive_name=sensor_id,
            transduction=kind,
            gain=parent.gain,
            decay=parent.decay,
            threshold=parent.threshold,
            born_tick=tick,
            transduction_cost=modality.base_cost * (1.0 + 0.25 * len(parent.source_ids)),
            parent_sensor_ids=(parent.sensor_id,),
            structural_revision=parent.structural_revision + 1,
        )
        self._sensors[sensor_id] = child
        self._record_mutation(SensoryMutationKind.DUPLICATE, child, tick=tick, parent_ids=(parent.sensor_id,))
        return child

    def create_multisource_sensor(
        self,
        source_ids: Iterable[str],
        *,
        modality_id: str = "modality.gamma",
        tick: int,
    ) -> SensorState:
        sources = tuple(sorted(set(source_ids)))
        modality = self._modalities[modality_id]
        if len(sources) < 2 or len(sources) > min(modality.max_inputs, self.limits.max_sources_per_sensor):
            raise ValueError("invalid multisource sensor source count")
        if TransductionKind.MIX not in modality.allowed_transductions:
            raise ValueError("modality does not support multisource mixing")
        if len(self._sensors) >= self.limits.max_active_sensors:
            raise ValueError("sensory system active sensor limit reached")
        sensor_id = self._allocate_id()
        sensor = SensorState(
            sensor_id=sensor_id,
            modality_id=modality_id,
            source_ids=sources,
            cognitive_name=sensor_id,
            transduction=TransductionKind.MIX,
            born_tick=tick,
            transduction_cost=modality.base_cost * (1.0 + 0.25 * len(sources)),
        )
        self._sensors[sensor_id] = sensor
        self._record_mutation(SensoryMutationKind.DUPLICATE, sensor, tick=tick, parent_ids=())
        return sensor

    @staticmethod
    def _digest(sensor: SensorState) -> str:
        encoded = json.dumps(sensor.checkpoint(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(encoded).hexdigest()

    def _record_mutation(
        self,
        kind: SensoryMutationKind,
        sensor: SensorState,
        *,
        tick: int,
        parent_ids: tuple[str, ...],
        pre_digest: str = "",
    ) -> None:
        post = self._digest(sensor)
        raw_id = f"{tick}:{sensor.sensor_id}:{kind.value}:{pre_digest}:{post}"
        mutation = SensoryMutation(
            mutation_id=sha256(raw_id.encode("utf-8")).hexdigest()[:24],
            tick=tick,
            sensor_id=sensor.sensor_id,
            parent_ids=parent_ids,
            kind=kind,
            pre_digest=pre_digest or post,
            post_digest=post,
            cost=min(1.0, sensor.transduction_cost),
        )
        self._mutations.append(mutation)
        del self._mutations[:-256]

    def transduce(
        self,
        readings: Iterable[SensorReading],
        *,
        percept_names: Mapping[str, str],
        tick: int,
    ) -> tuple[Percept, ...]:
        self._last_tick = tick
        by_source = {reading.capability_id: reading for reading in readings}
        for source_id, cognitive_name in sorted(percept_names.items()):
            self.ensure_identity_sensor(source_id, cognitive_name, tick=tick)

        outputs: list[Percept] = []
        for sensor in self.sensors:
            source_readings = [by_source.get(source_id) for source_id in sensor.source_ids]
            if any(reading is None for reading in source_readings):
                continue
            concrete = [reading for reading in source_readings if reading is not None]
            sensor.age_ticks += 1
            quality_score = min(_QUALITY_SCORE[reading.quality] for reading in concrete)
            sensor.observe_quality(quality_score)
            sensor.advance_maturity()
            if any(reading.value is None for reading in concrete):
                outputs.append(Percept(
                    name=sensor.cognitive_name,
                    value=None,
                    unit=concrete[0].unit,
                    quality=ReadingQuality.UNAVAILABLE,
                    privacy_class=concrete[0].privacy_class,
                    sensor_id=sensor.sensor_id,
                    modality_id=sensor.modality_id,
                    source_ids=sensor.source_ids,
                    confidence=sensor.confidence,
                ))
                continue

            values = [float(reading.value) for reading in concrete if reading.value is not None]
            output, previous, integrator = apply_transduction(
                sensor.transduction,
                values,
                gain=sensor.gain,
                decay=sensor.decay,
                threshold=sensor.threshold,
                previous=sensor.previous_input,
                integrator=sensor.integrator,
            )
            sensor.previous_input = previous
            sensor.integrator = integrator
            sensor.last_output = output
            unit = concrete[0].unit if len(concrete) == 1 and sensor.transduction is TransductionKind.IDENTITY else Unit.RATIO
            quality = min(concrete, key=lambda reading: _QUALITY_SCORE[reading.quality]).quality
            privacy = (
                ReadingPrivacyClass.AGGREGATE
                if any(reading.privacy_class is ReadingPrivacyClass.AGGREGATE for reading in concrete)
                else ReadingPrivacyClass.NON_IDENTIFYING
            )
            outputs.append(Percept(
                name=sensor.cognitive_name,
                value=output,
                unit=unit,
                quality=quality,
                privacy_class=privacy,
                sensor_id=sensor.sensor_id,
                modality_id=sensor.modality_id,
                source_ids=sensor.source_ids,
                confidence=sensor.confidence,
            ))
        return tuple(outputs)

    def update_downstream_utility(self, predictive_gain_by_name: Mapping[str, float]) -> None:
        for sensor in self._sensors.values():
            gain = max(0.0, min(1.0, float(predictive_gain_by_name.get(sensor.cognitive_name, 0.0))))
            cost = min(1.0, sensor.transduction_cost)
            score = sensory_fitness(
                predictive_contribution=gain,
                downstream_contribution=gain,
                novelty=max(0.0, 1.0 - sensor.redundancy),
                reliability=sensor.confidence,
                redundancy=sensor.redundancy,
                cost=cost,
            )
            sensor.observe_utility(score)

    def _refresh_structural_redundancy(self) -> None:
        sensors = self.sensors
        for sensor in sensors:
            peers = [
                other for other in sensors
                if other.sensor_id != sensor.sensor_id and other.source_ids == sensor.source_ids
            ]
            if not peers:
                sensor.redundancy = 0.0
            elif any(
                other.transduction is sensor.transduction
                and abs(other.gain - sensor.gain) < 1e-9
                and abs(other.decay - sensor.decay) < 1e-9
                for other in peers
            ):
                sensor.redundancy = 1.0
            else:
                sensor.redundancy = 0.25

    def plastic_step(self, *, tick: int) -> tuple[SensoryMutation, ...]:
        if not self.plasticity_enabled:
            return ()
        if tick <= 0 or tick % self.limits.mutation_window_ticks:
            return ()
        before = len(self._mutations)
        self._refresh_structural_redundancy()

        specialised = [sensor for sensor in self.sensors if not sensor.sensor_id.startswith("sensor.identity.")]
        # Prune mature, redundant and low-utility variants first.
        prunable = [
            sensor for sensor in specialised
            if sensor.age_ticks >= 32 and sensor.utility < 0.08 and sensor.redundancy >= 0.75
        ][: self.limits.max_sensor_mutations_per_window]
        for sensor in prunable:
            pre = self._digest(sensor)
            removed = self._sensors.pop(sensor.sensor_id)
            self._record_mutation(
                SensoryMutationKind.PRUNE,
                removed,
                tick=tick,
                parent_ids=removed.parent_sensor_ids,
                pre_digest=pre,
            )

        remaining_budget = self.limits.max_sensor_mutations_per_window - len(prunable)
        nascent = sum(sensor.maturity is MaturityState.NASCENT for sensor in self._sensors.values())
        identities = [
            sensor for sensor in self.sensors
            if sensor.sensor_id.startswith("sensor.identity.") and sensor.age_ticks >= 16
        ]
        if remaining_budget > 0 and identities and nascent < self.limits.max_nascent_sensors:
            # Developmental exploration is local and deterministic.  It does
            # not know which transform is correct; different substrate
            # families are tried under the same bounded resource pressure.
            parent = max(identities, key=lambda sensor: (sensor.utility, sensor.confidence, sensor.sensor_id))
            used_modalities = {
                sensor.modality_id for sensor in specialised if sensor.source_ids == parent.source_ids
            }
            modality_order = ("modality.alpha", "modality.beta")
            modality_id = next((item for item in modality_order if item not in used_modalities), None)
            if modality_id is not None:
                self.duplicate(parent.sensor_id, modality_id=modality_id, tick=tick)

        return tuple(self._mutations[before:])

    def phenotype_view(self) -> dict[str, Any]:
        sensors = self.sensors
        counts = {state.value: 0 for state in MaturityState}
        for sensor in sensors:
            counts[sensor.maturity.value] += 1
        return {
            "schema_version": self.SCHEMA_VERSION,
            "modalities": [
                {
                    "modality_id": modality.modality_id,
                    "sensor_count": sum(sensor.modality_id == modality.modality_id for sensor in sensors),
                    "max_inputs": modality.max_inputs,
                    "temporal_capacity": modality.temporal_capacity,
                }
                for modality in self.modalities
            ],
            "sensors": [
                {
                    "sensor_id": sensor.sensor_id,
                    "modality_id": sensor.modality_id,
                    "source_count": len(sensor.source_ids),
                    "maturity": sensor.maturity.value,
                    "health": round(sensor.health, 6),
                    "confidence": round(sensor.confidence, 6),
                    "utility": round(sensor.utility, 6),
                    "redundancy": round(sensor.redundancy, 6),
                    "cost": round(sensor.acquisition_cost + sensor.transduction_cost, 6),
                    "parent_sensor_ids": list(sensor.parent_sensor_ids),
                    "downstream_name": sensor.cognitive_name,
                }
                for sensor in sensors
            ],
            "summary": {
                "active": len(sensors),
                "nascent": counts[MaturityState.NASCENT.value],
                "immature": counts[MaturityState.IMMATURE.value],
                "established": counts[MaturityState.ESTABLISHED.value],
                "specialised": counts[MaturityState.SPECIALISED.value],
                "degraded": counts[MaturityState.DEGRADED.value],
            },
        }

    def checkpoint(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "constitution": self.constitution(),
            "next_sensor_id": self._next_sensor_id,
            "last_tick": self._last_tick,
            "sensors": [sensor.checkpoint() for sensor in self.sensors],
            "mutations": [asdict(item) | {"kind": item.kind.value} for item in self._mutations],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        if len(encoded) > self.limits.max_sensor_checkpoint_bytes:
            raise ValueError("sensory checkpoint exceeds max_sensor_checkpoint_bytes")
        return payload

    @classmethod
    def restore(cls, payload: dict[str, Any] | None, *, plasticity_enabled: bool | None = None) -> "SensorySystem":
        if payload is None:
            return cls(plasticity_enabled=bool(plasticity_enabled))
        if not isinstance(payload, dict) or payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("unsupported sensory system checkpoint")
        constitution = payload.get("constitution", {})
        raw_limits = constitution.get("limits", {})
        limits = SensoryLimits(**raw_limits) if isinstance(raw_limits, dict) else SensoryLimits()
        system = cls(
            limits=limits,
            plasticity_enabled=(
                bool(plasticity_enabled)
                if plasticity_enabled is not None
                else bool(constitution.get("plasticity_enabled", False))
            ),
            next_sensor_id=int(payload.get("next_sensor_id", 1)),
        )
        raw_sensors = payload.get("sensors", [])
        if not isinstance(raw_sensors, list) or len(raw_sensors) > limits.max_active_sensors:
            raise ValueError("invalid sensory sensor list")
        for raw in raw_sensors:
            if not isinstance(raw, dict):
                raise ValueError("invalid sensory sensor entry")
            sensor = SensorState.restore(raw)
            modality = system._modalities.get(sensor.modality_id)
            if modality is None:
                raise ValueError("checkpoint references unknown modality")
            if len(sensor.source_ids) > min(modality.max_inputs, limits.max_sources_per_sensor):
                raise ValueError("checkpoint sensor exceeds modality input bound")
            if sensor.transduction not in modality.allowed_transductions:
                raise ValueError("checkpoint transduction is not allowed by modality")
            if sensor.sensor_id in system._sensors:
                raise ValueError("duplicate sensor id")
            system._sensors[sensor.sensor_id] = sensor
        system._last_tick = int(payload.get("last_tick", 0))
        # Mutation history is intentionally descriptive; malformed history
        # must not compromise the restored functional phenotype.
        return system
