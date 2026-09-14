from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import math
from itertools import combinations
from typing import Any, Iterable

from .readings import ReadingQuality, SensorReading


@dataclass(slots=True)
class SenseState:
    """Learned, non-semantic description of one discovered host signal."""

    capability_id: str
    percept_name: str
    samples: int = 0
    available_samples: int = 0
    mean: float = 0.0
    m2: float = 0.0
    last_value: float | None = None
    delta_ewma: float = 0.0

    @property
    def variance(self) -> float:
        return self.m2 / (self.available_samples - 1) if self.available_samples > 1 else 0.0

    @property
    def availability(self) -> float:
        return self.available_samples / self.samples if self.samples else 0.0

    @property
    def utility(self) -> float:
        if self.available_samples < 2:
            return 0.0
        scale = abs(self.mean) + math.sqrt(max(0.0, self.variance)) + 1e-12
        variability = min(1.0, math.sqrt(max(0.0, self.variance)) / scale)
        motion = min(1.0, self.delta_ewma / scale)
        return self.availability * (0.65 * variability + 0.35 * motion)

    def observe(self, reading: SensorReading) -> None:
        self.samples += 1
        if reading.quality is ReadingQuality.UNAVAILABLE or reading.value is None:
            return
        value = float(reading.value)
        if not math.isfinite(value):
            return
        if self.last_value is not None:
            delta = abs(value - self.last_value)
            self.delta_ewma = delta if self.available_samples == 1 else (0.2 * delta + 0.8 * self.delta_ewma)
        self.last_value = value
        self.available_samples += 1
        delta = value - self.mean
        self.mean += delta / self.available_samples
        self.m2 += delta * (value - self.mean)

    def to_payload(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "percept_name": self.percept_name,
            "samples": self.samples,
            "available_samples": self.available_samples,
            "mean": self.mean,
            "m2": self.m2,
            # last_value intentionally omitted: a checkpoint stores learned
            # abstract state, never the latest raw host reading.
            "delta_ewma": self.delta_ewma,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "SenseState":
        state = cls(
            capability_id=str(payload["capability_id"]),
            percept_name=str(payload["percept_name"]),
            samples=max(0, int(payload.get("samples", 0))),
            available_samples=max(0, int(payload.get("available_samples", 0))),
            mean=float(payload.get("mean", 0.0)),
            m2=max(0.0, float(payload.get("m2", 0.0))),
            last_value=None,
            delta_ewma=max(0.0, float(payload.get("delta_ewma", 0.0))),
        )
        if state.available_samples > state.samples:
            raise ValueError("available_samples cannot exceed samples")
        return state


@dataclass(slots=True)
class PairAccumulator:
    """Bounded online bivariate statistics; no sample history is retained."""

    count: int = 0
    sum_x: float = 0.0
    sum_y: float = 0.0
    sum_xx: float = 0.0
    sum_yy: float = 0.0
    sum_xy: float = 0.0

    def observe(self, x: float, y: float) -> None:
        if not math.isfinite(x) or not math.isfinite(y):
            return
        self.count += 1
        self.sum_x += x
        self.sum_y += y
        self.sum_xx += x * x
        self.sum_yy += y * y
        self.sum_xy += x * y

    @property
    def correlation(self) -> float | None:
        if self.count < 3:
            return None
        n = float(self.count)
        covariance = n * self.sum_xy - self.sum_x * self.sum_y
        spread_x = n * self.sum_xx - self.sum_x * self.sum_x
        spread_y = n * self.sum_yy - self.sum_y * self.sum_y
        if spread_x <= 1e-18 or spread_y <= 1e-18:
            return None
        value = covariance / math.sqrt(spread_x * spread_y)
        return max(-1.0, min(1.0, value))

    def to_payload(self) -> dict[str, float | int]:
        return {
            "count": self.count,
            "sum_x": self.sum_x,
            "sum_y": self.sum_y,
            "sum_xx": self.sum_xx,
            "sum_yy": self.sum_yy,
            "sum_xy": self.sum_xy,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "PairAccumulator":
        return cls(
            count=max(0, int(payload.get("count", 0))),
            sum_x=float(payload.get("sum_x", 0.0)),
            sum_y=float(payload.get("sum_y", 0.0)),
            sum_xx=float(payload.get("sum_xx", 0.0)),
            sum_yy=float(payload.get("sum_yy", 0.0)),
            sum_xy=float(payload.get("sum_xy", 0.0)),
        )


@dataclass(slots=True)
class SensoryRelation:
    """Learned relation between two opaque senses.

    ``synchronous`` measures same-tick association. ``a_to_b`` measures how
    the previous value of A relates to the current value of B; ``b_to_a`` is
    the reverse. These are descriptive predictive associations, not claims of
    causation.
    """

    capability_a: str
    capability_b: str
    synchronous: PairAccumulator = field(default_factory=PairAccumulator)
    a_to_b: PairAccumulator = field(default_factory=PairAccumulator)
    b_to_a: PairAccumulator = field(default_factory=PairAccumulator)

    def to_payload(self) -> dict[str, Any]:
        return {
            "capability_a": self.capability_a,
            "capability_b": self.capability_b,
            "synchronous": self.synchronous.to_payload(),
            "a_to_b": self.a_to_b.to_payload(),
            "b_to_a": self.b_to_a.to_payload(),
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "SensoryRelation":
        return cls(
            capability_a=str(payload["capability_a"]),
            capability_b=str(payload["capability_b"]),
            synchronous=PairAccumulator.from_payload(dict(payload.get("synchronous", {}))),
            a_to_b=PairAccumulator.from_payload(dict(payload.get("a_to_b", {}))),
            b_to_a=PairAccumulator.from_payload(dict(payload.get("b_to_a", {}))),
        )


@dataclass(slots=True, frozen=True)
class RelationView:
    sense_a: str
    sense_b: str
    synchronous: float | None
    a_to_b: float | None
    b_to_a: float | None
    samples: int


class AdaptiveSenseModel:
    """Develop a bounded sensory repertoire from semantically unknown signals.

    The organism learns each signal's usefulness and also how senses relate to
    one another. Highly redundant senses are de-prioritized so the active
    repertoire tends toward complementary information instead of several
    copies of the same underlying variation.
    """

    def __init__(
        self,
        *,
        min_samples: int = 4,
        active_limit: int = 24,
        max_candidates: int = 256,
        relation_window: int = 32,
        max_relations: int = 1024,
        min_relation_samples: int = 6,
        redundancy_threshold: float = 0.97,
    ) -> None:
        if min_samples < 1:
            raise ValueError("min_samples must be at least 1")
        if active_limit < 1:
            raise ValueError("active_limit must be at least 1")
        if max_candidates < active_limit:
            raise ValueError("max_candidates must be at least active_limit")
        if not 2 <= relation_window <= max_candidates:
            raise ValueError("relation_window must be between 2 and max_candidates")
        if max_relations < 1:
            raise ValueError("max_relations must be positive")
        if min_relation_samples < 3:
            raise ValueError("min_relation_samples must be at least 3")
        if not 0.0 < redundancy_threshold <= 1.0:
            raise ValueError("redundancy_threshold must be in (0, 1]")
        self._min_samples = min_samples
        self._active_limit = active_limit
        self._max_candidates = max_candidates
        self._relation_window = relation_window
        self._max_relations = max_relations
        self._min_relation_samples = min_relation_samples
        self._redundancy_threshold = redundancy_threshold
        self._states: dict[str, SenseState] = {}
        self._relations: dict[tuple[str, str], SensoryRelation] = {}
        self._previous_values: dict[str, float] = {}

    @staticmethod
    def _percept_name(capability_id: str) -> str:
        digest = sha256(f"symbiont-sense:{capability_id}".encode("utf-8")).hexdigest()[:12]
        return f"sense_{digest}"

    @property
    def states(self) -> tuple[SenseState, ...]:
        return tuple(sorted(self._states.values(), key=lambda item: item.percept_name))

    @property
    def relations(self) -> tuple[RelationView, ...]:
        views: list[RelationView] = []
        for relation in self._relations.values():
            state_a = self._states.get(relation.capability_a)
            state_b = self._states.get(relation.capability_b)
            if state_a is None or state_b is None:
                continue
            views.append(
                RelationView(
                    sense_a=state_a.percept_name,
                    sense_b=state_b.percept_name,
                    synchronous=relation.synchronous.correlation,
                    a_to_b=relation.a_to_b.correlation,
                    b_to_a=relation.b_to_a.correlation,
                    samples=relation.synchronous.count,
                )
            )
        return tuple(sorted(views, key=lambda item: (-item.samples, item.sense_a, item.sense_b)))

    def _relation(self, capability_a: str, capability_b: str) -> SensoryRelation | None:
        first, second = sorted((capability_a, capability_b))
        key = (first, second)
        relation = self._relations.get(key)
        if relation is None:
            if len(self._relations) >= self._max_relations:
                return None
            relation = SensoryRelation(first, second)
            self._relations[key] = relation
        return relation

    def observe(self, readings: Iterable[SensorReading]) -> None:
        current_values: dict[str, float] = {}
        for reading in readings:
            state = self._states.get(reading.capability_id)
            if state is None:
                if len(self._states) >= self._max_candidates:
                    continue
                state = SenseState(
                    capability_id=reading.capability_id,
                    percept_name=self._percept_name(reading.capability_id),
                )
                self._states[reading.capability_id] = state
            state.observe(reading)
            if reading.value is not None and reading.quality is not ReadingQuality.UNAVAILABLE:
                value = float(reading.value)
                if math.isfinite(value):
                    current_values[reading.capability_id] = value

        # Bound pair learning to the most informative currently observed
        # candidates. At most C(32, 2)=496 pair records are touched per tick.
        relation_candidates = [
            self._states[capability_id]
            for capability_id in current_values
            if capability_id in self._states
        ]
        relation_candidates.sort(key=lambda state: (-state.utility, state.percept_name))
        chosen_ids = [state.capability_id for state in relation_candidates[: self._relation_window]]

        for capability_a, capability_b in combinations(chosen_ids, 2):
            relation = self._relation(capability_a, capability_b)
            if relation is None:
                continue
            first, second = relation.capability_a, relation.capability_b
            relation.synchronous.observe(current_values[first], current_values[second])
            if first in self._previous_values:
                relation.a_to_b.observe(self._previous_values[first], current_values[second])
            if second in self._previous_values:
                relation.b_to_a.observe(self._previous_values[second], current_values[first])

        # Previous values are in-memory transient state only; they are never
        # exported to the checkpoint.
        self._previous_values = {capability_id: current_values[capability_id] for capability_id in chosen_ids}

    def _is_redundant(self, candidate: SenseState, selected: list[SenseState]) -> bool:
        for other in selected:
            key = tuple(sorted((candidate.capability_id, other.capability_id)))
            relation = self._relations.get(key)
            if relation is None or relation.synchronous.count < self._min_relation_samples:
                continue
            correlation = relation.synchronous.correlation
            if correlation is not None and abs(correlation) >= self._redundancy_threshold:
                return True
        return False

    def active_states(self) -> tuple[SenseState, ...]:
        established = [state for state in self._states.values() if state.available_samples >= self._min_samples]
        ranked = sorted(established, key=lambda state: (-state.utility, state.percept_name))
        selected: list[SenseState] = []
        redundant: list[SenseState] = []
        for state in ranked:
            if self._is_redundant(state, selected):
                redundant.append(state)
            else:
                selected.append(state)
            if len(selected) >= self._active_limit:
                break
        # If the environment is intrinsically redundant, fill spare capacity
        # rather than starving cognition of senses altogether.
        if len(selected) < self._active_limit:
            for state in redundant:
                if state not in selected:
                    selected.append(state)
                if len(selected) >= self._active_limit:
                    break
        return tuple(selected)

    def percept_names(self) -> dict[str, str]:
        return {state.capability_id: state.percept_name for state in self.active_states()}

    def strongest_relations(self, *, limit: int = 16) -> tuple[RelationView, ...]:
        if limit < 1:
            return ()
        eligible = [relation for relation in self.relations if relation.samples >= self._min_relation_samples]

        def strength(relation: RelationView) -> float:
            values = [
                abs(value)
                for value in (relation.synchronous, relation.a_to_b, relation.b_to_a)
                if value is not None
            ]
            return max(values, default=0.0)

        return tuple(sorted(eligible, key=lambda item: (-strength(item), -item.samples, item.sense_a, item.sense_b))[:limit])

    def export(self) -> dict[str, Any]:
        return {
            "min_samples": self._min_samples,
            "active_limit": self._active_limit,
            "max_candidates": self._max_candidates,
            "relation_window": self._relation_window,
            "max_relations": self._max_relations,
            "min_relation_samples": self._min_relation_samples,
            "redundancy_threshold": self._redundancy_threshold,
            "states": [state.to_payload() for state in self.states],
            "relations": [
                relation.to_payload()
                for _, relation in sorted(self._relations.items())
            ],
        }

    @classmethod
    def restore(cls, payload: dict[str, Any] | None) -> "AdaptiveSenseModel":
        if not payload:
            return cls()
        model = cls(
            min_samples=int(payload.get("min_samples", 4)),
            active_limit=int(payload.get("active_limit", 24)),
            max_candidates=int(payload.get("max_candidates", 256)),
            relation_window=int(payload.get("relation_window", 32)),
            max_relations=int(payload.get("max_relations", 1024)),
            min_relation_samples=int(payload.get("min_relation_samples", 6)),
            redundancy_threshold=float(payload.get("redundancy_threshold", 0.97)),
        )
        for item in payload.get("states", [])[: model._max_candidates]:
            state = SenseState.from_payload(item)
            model._states[state.capability_id] = state
        for item in payload.get("relations", [])[: model._max_relations]:
            relation = SensoryRelation.from_payload(item)
            if relation.capability_a not in model._states or relation.capability_b not in model._states:
                continue
            key = tuple(sorted((relation.capability_a, relation.capability_b)))
            model._relations[key] = relation
        return model
