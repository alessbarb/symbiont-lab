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
        for modality in resolved:
            if modality.max_inputs > self.limits.max_sources_per_sensor:
                raise ValueError("modality max_inputs exceeds sensory source bound")
            if modality.temporal_capacity > self.limits.max_temporal_depth:
                raise ValueError("modality temporal_capacity exceeds sensory temporal bound")
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

    def germinal_copy(self) -> "SensorySystem":
        """Copy sensory capacity across birth without acquired phenotype."""
        return SensorySystem(
            limits=self.limits,
            modalities=self.modalities,
            plasticity_enabled=self.plasticity_enabled,
        )

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
        # Compatibility mode preserves the historical cognitive alias exactly.
        # Adaptive mode uses the receptor's own stable identity: source-level
        # names may mature or change, but the organism-owned sensor must not.
        resolved_name = sensor_id if self.plasticity_enabled else cognitive_name
        existing = self._sensors.get(sensor_id)
        if existing is not None:
            existing.cognitive_name = resolved_name
            return existing
        if len(self._sensors) >= self.limits.max_active_sensors:
            raise ValueError("sensory system active sensor limit reached")
        modality = self._modalities["modality.identity"]
        sensor = SensorState(
            sensor_id=sensor_id,
            modality_id=modality.modality_id,
            source_ids=(source_id,),
            cognitive_name=resolved_name,
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
            gain=max(0.125, min(8.0, parent.gain * (1.05 if self._next_sensor_id % 2 else 0.95))),
            decay=max(0.0, min(1.0, parent.decay + (0.05 if self._next_sensor_id % 2 else -0.05))),
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
        parent_sensor_ids: tuple[str, ...] = (),
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
            parent_sensor_ids=parent_sensor_ids,
        )
        self._sensors[sensor_id] = sensor
        self._record_mutation(
            SensoryMutationKind.SOURCE_REWIRE,
            sensor,
            tick=tick,
            parent_ids=parent_sensor_ids,
        )
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
                    confidence=sensor.confidence,
                ))
                continue

            values = [float(reading.value) for reading in concrete if reading.value is not None]
            sensor.cold_start_observed = sensor.cold_start_pending
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
            sensor.cold_start_pending = False
            sensor.last_output = output
            sensor.observe_output(output)
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
                confidence=sensor.confidence,
            ))
        return tuple(outputs)

    def update_acquisition_costs(self, costs_by_source: Mapping[str, float]) -> None:
        """Attribute one physical acquisition cost across receptors sharing it."""
        cleaned: dict[str, float] = {}
        for source_id, raw_cost in costs_by_source.items():
            if (
                not isinstance(source_id, str)
                or not source_id
                or isinstance(raw_cost, bool)
                or not isinstance(raw_cost, (int, float))
                or not math.isfinite(float(raw_cost))
                or float(raw_cost) < 0.0
            ):
                raise ValueError("source acquisition costs must be finite and non-negative")
            cleaned[source_id] = float(raw_cost)

        consumers: dict[str, int] = {}
        for sensor in self._sensors.values():
            for source_id in sensor.source_ids:
                consumers[source_id] = consumers.get(source_id, 0) + 1

        for sensor in self._sensors.values():
            sensor.acquisition_cost = sum(
                cleaned.get(source_id, 0.0) / max(1, consumers.get(source_id, 1))
                for source_id in sensor.source_ids
            )

    def update_downstream_utility(self, predictive_gain_by_name: Mapping[str, float]) -> None:
        for sensor in self._sensors.values():
            gain = max(0.0, min(1.0, float(predictive_gain_by_name.get(sensor.cognitive_name, 0.0))))
            cost = min(1.0, sensor.acquisition_cost + sensor.transduction_cost)
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

        # Homeostatic parameter adaptation is organism-side and target-free.
        # It only tries to keep receptor response away from saturation/silence;
        # it does not know what transformation the evaluator expects.
        adjustments = 0
        for sensor in specialised:
            if adjustments >= self.limits.max_sensor_mutations_per_window:
                break
            if sensor.output_observations < 4:
                continue
            pre = self._digest(sensor)
            old_gain = sensor.gain
            if sensor.output_abs_ewma < 0.10:
                sensor.gain = min(8.0, sensor.gain * 1.05)
            elif sensor.output_abs_ewma > 2.0:
                sensor.gain = max(0.125, sensor.gain * 0.95)
            if sensor.transduction is TransductionKind.INTEGRATE:
                if sensor.output_delta_ewma > 1.0:
                    sensor.decay = min(0.98, sensor.decay + 0.02)
                elif sensor.output_delta_ewma < 0.01:
                    sensor.decay = max(0.10, sensor.decay - 0.02)
            if abs(sensor.gain - old_gain) > 1e-12 or pre != self._digest(sensor):
                sensor.structural_revision += 1
                self._record_mutation(
                    SensoryMutationKind.PARAMETER_ADJUST,
                    sensor,
                    tick=tick,
                    parent_ids=sensor.parent_sensor_ids,
                    pre_digest=pre,
                )
                adjustments += 1

        # Prune mature, redundant and low-utility variants first.
        prune_budget = max(0, self.limits.max_sensor_mutations_per_window - adjustments)
        prunable = [
            sensor for sensor in specialised
            if (
                (
                    sensor.age_ticks >= 32
                    and sensor.utility_observations >= 8
                    and sensor.utility < 0.08
                    and sensor.redundancy >= 0.75
                )
                or (
                    sensor.age_ticks >= 64
                    and sensor.utility_observations >= 16
                    and sensor.utility < 0.02
                )
            )
        ][:prune_budget]
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

        remaining_budget = self.limits.max_sensor_mutations_per_window - len(prunable) - adjustments
        nascent = sum(sensor.maturity is MaturityState.NASCENT for sensor in self._sensors.values())
        identities = [
            sensor for sensor in self.sensors
            if sensor.sensor_id.startswith("sensor.identity.") and sensor.age_ticks >= 16
        ]
        if remaining_budget > 0 and identities and nascent < self.limits.max_nascent_sensors:
            # Developmental exploration is local and deterministic. It does
            # not know which transform is correct; different substrate
            # families are tried under the same bounded resource pressure.
            parent = max(identities, key=lambda sensor: (sensor.utility, sensor.confidence, sensor.sensor_id))
            live_specialised = [
                sensor for sensor in self.sensors
                if not sensor.sensor_id.startswith("sensor.identity.")
            ]
            used_modalities = {
                sensor.modality_id for sensor in live_specialised if sensor.source_ids == parent.source_ids
            }
            modality_order = ("modality.alpha", "modality.beta")
            modality_id = next((item for item in modality_order if item not in used_modalities), None)
            if modality_id is not None:
                self.duplicate(parent.sensor_id, modality_id=modality_id, tick=tick)
                remaining_budget -= 1

        # Once single-source substrates have had an opportunity to mature,
        # the organism may explore one bounded pair of already-known sources.
        # Pair choice uses only organism-side confidence/utility and stable
        # opaque ids; no evaluator-supplied "correct pair" can enter here.
        current_nascent = sum(
            sensor.maturity is MaturityState.NASCENT for sensor in self._sensors.values()
        )
        if (
            remaining_budget > 0
            and len(identities) >= 2
            and current_nascent < self.limits.max_nascent_sensors
        ):
            ranked_identities = sorted(
                identities,
                key=lambda sensor: (-sensor.utility, -sensor.confidence, sensor.sensor_id),
            )
            chosen: tuple[SensorState, SensorState] | None = None
            existing_pairs = {
                sensor.source_ids
                for sensor in self.sensors
                if sensor.modality_id == "modality.gamma" and len(sensor.source_ids) > 1
            }
            for left_index, left in enumerate(ranked_identities):
                for right in ranked_identities[left_index + 1:]:
                    pair = tuple(sorted((left.source_ids[0], right.source_ids[0])))
                    if pair not in existing_pairs:
                        chosen = (left, right)
                        break
                if chosen is not None:
                    break
            if chosen is not None:
                left, right = chosen
                self.create_multisource_sensor(
                    (left.source_ids[0], right.source_ids[0]),
                    tick=tick,
                    parent_sensor_ids=(left.sensor_id, right.sensor_id),
                )

        if len(self._mutations) - before > self.limits.max_sensor_mutations_per_window:
            raise RuntimeError("sensory mutation budget invariant violated")
        return tuple(self._mutations[before:])

    def phenotype_view(
        self,
        *,
        signal_ids_by_source: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        sensors = self.sensors
        resolved_signals = dict(signal_ids_by_source or {})
        if any(
            not isinstance(source_id, str) or not source_id
            or not isinstance(signal_id, str) or not signal_id.startswith("signal.")
            for source_id, signal_id in resolved_signals.items()
        ):
            raise ValueError("signal_ids_by_source must map source ids to opaque signal ids")
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
                    "signal_ids": [
                        resolved_signals[source_id]
                        for source_id in sensor.source_ids
                        if source_id in resolved_signals
                    ],
                    "maturity": sensor.maturity.value,
                    "health": round(sensor.health, 6),
                    "confidence": round(sensor.confidence, 6),
                    "utility": round(sensor.utility, 6),
                    "redundancy": round(sensor.redundancy, 6),
                    "cost": round(sensor.acquisition_cost + sensor.transduction_cost, 6),
                    "parent_sensor_ids": list(sensor.parent_sensor_ids),
                    "downstream_name": sensor.cognitive_name,
                    "cold_start": sensor.cold_start_observed,
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
        if not isinstance(constitution, dict):
            raise ValueError("sensory constitution must be an object")
        raw_limits = constitution.get("limits", {})
        if not isinstance(raw_limits, dict):
            raise ValueError("sensory limits must be an object")
        limits = SensoryLimits(**raw_limits)

        raw_modalities = constitution.get("modalities")
        if not isinstance(raw_modalities, list) or not raw_modalities:
            raise ValueError("sensory modalities must be a non-empty array")
        modalities: list[SensoryModality] = []
        for raw_modality in raw_modalities:
            if not isinstance(raw_modality, dict):
                raise ValueError("sensory modality entries must be objects")
            allowed = raw_modality.get("allowed_transductions")
            if not isinstance(allowed, list) or not allowed:
                raise ValueError("sensory modality transductions must be a non-empty array")
            try:
                modalities.append(SensoryModality(
                    modality_id=raw_modality["modality_id"],
                    allowed_transductions=tuple(TransductionKind(item) for item in allowed),
                    max_inputs=raw_modality["max_inputs"],
                    temporal_capacity=raw_modality["temporal_capacity"],
                    base_cost=raw_modality["base_cost"],
                ))
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"invalid sensory modality checkpoint: {exc}") from exc

        next_sensor_id = payload.get("next_sensor_id", 1)
        if isinstance(next_sensor_id, bool) or not isinstance(next_sensor_id, int) or next_sensor_id < 1:
            raise ValueError("next_sensor_id must be a positive integer")
        stored_plasticity = constitution.get("plasticity_enabled", False)
        if not isinstance(stored_plasticity, bool):
            raise ValueError("sensory plasticity_enabled must be boolean")
        system = cls(
            limits=limits,
            modalities=tuple(modalities),
            plasticity_enabled=(
                plasticity_enabled
                if plasticity_enabled is not None
                else stored_plasticity
            ),
            next_sensor_id=next_sensor_id,
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
        raw_mutations = payload.get("mutations", [])
        if not isinstance(raw_mutations, list) or len(raw_mutations) > 256:
            raise ValueError("invalid sensory mutation history")
        restored_mutations = [SensoryMutation.restore(raw) for raw in raw_mutations]
        pruned_sensor_ids = {
            mutation.sensor_id
            for mutation in restored_mutations
            if mutation.kind is SensoryMutationKind.PRUNE
        }
        known_history_ids = set(system._sensors) | pruned_sensor_ids
        for mutation in restored_mutations:
            if mutation.sensor_id not in known_history_ids:
                raise ValueError("mutation history references an unknown sensor lineage")
        system._mutations = restored_mutations
        last_tick = payload.get("last_tick", 0)
        if isinstance(last_tick, bool) or not isinstance(last_tick, int) or last_tick < 0:
            raise ValueError("last_tick must be a non-negative integer")
        system._last_tick = last_tick
        return system
