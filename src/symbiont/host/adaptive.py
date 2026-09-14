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
    last_seen_tick: int = 0

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
            # last_value is transient raw host state and never enters a checkpoint.
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
    """Bounded online bivariate statistics; no sample history is retained.

    Uses Welford-style centered accumulation (running means and co-moments),
    not raw sums of squares, so correlation stays numerically stable
    regardless of the absolute scale or offset of the values observed
    (roadmap safety finding A06) — a large, monotonically-increasing Linux
    counter pair with a perfect linear relationship no longer silently
    loses that relationship to floating-point cancellation.
    """

    count: int = 0
    mean_x: float = 0.0
    mean_y: float = 0.0
    m2_x: float = 0.0
    m2_y: float = 0.0
    c_xy: float = 0.0

    def observe(self, x: float, y: float) -> None:
        if not math.isfinite(x) or not math.isfinite(y):
            return
        self.count += 1
        dx = x - self.mean_x
        self.mean_x += dx / self.count
        dy = y - self.mean_y
        self.mean_y += dy / self.count
        self.c_xy += dx * (y - self.mean_y)
        self.m2_x += dx * (x - self.mean_x)
        self.m2_y += dy * (y - self.mean_y)

    @property
    def correlation(self) -> float | None:
        if self.count < 3:
            return None
        if self.m2_x <= 1e-18 or self.m2_y <= 1e-18:
            return None
        value = self.c_xy / math.sqrt(self.m2_x * self.m2_y)
        if not math.isfinite(value):
            return None
        return max(-1.0, min(1.0, value))

    def to_payload(self) -> dict[str, float | int]:
        return {
            "count": self.count,
            "mean_x": self.mean_x,
            "mean_y": self.mean_y,
            "m2_x": self.m2_x,
            "m2_y": self.m2_y,
            "c_xy": self.c_xy,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "PairAccumulator":
        return cls(
            count=max(0, int(payload.get("count", 0))),
            mean_x=float(payload.get("mean_x", 0.0)),
            mean_y=float(payload.get("mean_y", 0.0)),
            m2_x=max(0.0, float(payload.get("m2_x", 0.0))),
            m2_y=max(0.0, float(payload.get("m2_y", 0.0))),
            c_xy=float(payload.get("c_xy", 0.0)),
        )


@dataclass(slots=True)
class SensoryRelation:
    """Descriptive relation between two opaque senses, never a causal claim."""

    capability_a: str
    capability_b: str
    synchronous: PairAccumulator = field(default_factory=PairAccumulator)
    a_to_b: PairAccumulator = field(default_factory=PairAccumulator)
    b_to_a: PairAccumulator = field(default_factory=PairAccumulator)
    last_seen_tick: int = 0

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


@dataclass(slots=True, frozen=True)
class SamplingPlan:
    """One developmental decision about where to spend observation effort."""

    active: tuple[str, ...]
    probing: tuple[str, ...]
    dormant_count: int
    unknown_count: int

    @property
    def requested_ids(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((*self.active, *self.probing)))


class AdaptiveSenseModel:
    """Develop and selectively exercise a bounded repertoire of unknown senses.

    Senses move implicitly through three developmental tiers:

    * active — useful, complementary senses sampled routinely;
    * probing — unknown/dormant senses sampled on a rotating exploration budget;
    * dormant — known but currently unselected senses that remain discoverable and
      periodically return to probing, preventing irreversible early blindness.
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
        exploration_limit: int = 32,
        probe_limit: int = 4,
        probe_cursor: int = 0,
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
        if not 1 <= exploration_limit <= max_candidates:
            raise ValueError("exploration_limit must be between 1 and max_candidates")
        if not 1 <= probe_limit <= exploration_limit:
            raise ValueError("probe_limit must be between 1 and exploration_limit")
        if probe_cursor < 0:
            raise ValueError("probe_cursor must be non-negative")

        self._min_samples = min_samples
        self._active_limit = active_limit
        self._max_candidates = max_candidates
        self._relation_window = relation_window
        self._max_relations = max_relations
        self._min_relation_samples = min_relation_samples
        self._redundancy_threshold = redundancy_threshold
        self._exploration_limit = exploration_limit
        self._probe_limit = probe_limit
        self._probe_cursor = probe_cursor
        self._states: dict[str, SenseState] = {}
        self._relations: dict[tuple[str, str], SensoryRelation] = {}
        self._previous_values: dict[str, float] = {}
        self._last_plan = SamplingPlan((), (), 0, 0)
        self._tick = 0

    @staticmethod
    def _percept_name(capability_id: str) -> str:
        digest = sha256(f"symbiont-sense:{capability_id}".encode("utf-8")).hexdigest()[:12]
        return f"sense_{digest}"

    @staticmethod
    def _sampling_order(capability_id: str) -> str:
        return sha256(f"symbiont-sampling:{capability_id}".encode("utf-8")).hexdigest()

    @property
    def states(self) -> tuple[SenseState, ...]:
        return tuple(sorted(self._states.values(), key=lambda item: item.percept_name))

    @property
    def last_sampling_plan(self) -> SamplingPlan:
        return self._last_plan

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

    def _evict_state_for(self, incoming_capability_id: str) -> bool:
        """Retire the least-recently-observed state to make room for a
        capability this codebase has never seen before (roadmap safety
        finding A04) — without this, a fixed historical-occupancy cap turns
        into a permanent block on ever learning anything new once it fills
        up, even if every one of those old candidates has since vanished.
        Never evicts anything just observed in the current call.
        """
        candidates = [
            state for state in self._states.values() if state.last_seen_tick < self._tick
        ]
        if not candidates:
            return False
        oldest = min(candidates, key=lambda state: (state.last_seen_tick, state.capability_id))
        del self._states[oldest.capability_id]
        stale_keys = [key for key in self._relations if oldest.capability_id in key]
        for key in stale_keys:
            del self._relations[key]
        return True

    def _relation(self, capability_a: str, capability_b: str) -> SensoryRelation | None:
        first, second = sorted((capability_a, capability_b))
        key = (first, second)
        relation = self._relations.get(key)
        if relation is None:
            if len(self._relations) >= self._max_relations and not self._evict_relation():
                return None
            relation = SensoryRelation(first, second)
            self._relations[key] = relation
        relation.last_seen_tick = self._tick
        return relation

    def _evict_relation(self) -> bool:
        """Retire the least-recently-observed relation to make room for a
        genuinely new pair once the relation table is full (roadmap safety
        finding A04)."""
        candidates = [
            relation for relation in self._relations.values() if relation.last_seen_tick < self._tick
        ]
        if not candidates:
            return False
        oldest = min(candidates, key=lambda relation: (relation.last_seen_tick, relation.capability_a, relation.capability_b))
        del self._relations[(oldest.capability_a, oldest.capability_b)]
        return True

    def observe(self, readings: Iterable[SensorReading]) -> None:
        self._tick += 1
        current_values: dict[str, float] = {}
        for reading in readings:
            state = self._states.get(reading.capability_id)
            if state is None:
                if len(self._states) >= self._max_candidates and not self._evict_state_for(reading.capability_id):
                    continue
                state = SenseState(
                    capability_id=reading.capability_id,
                    percept_name=self._percept_name(reading.capability_id),
                )
                self._states[reading.capability_id] = state
            state.last_seen_tick = self._tick
            state.observe(reading)
            if reading.value is not None and reading.quality is not ReadingQuality.UNAVAILABLE:
                value = float(reading.value)
                if math.isfinite(value):
                    current_values[reading.capability_id] = value

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
        if len(selected) < self._active_limit:
            for state in redundant:
                if state not in selected:
                    selected.append(state)
                if len(selected) >= self._active_limit:
                    break
        return tuple(selected)

    def percept_names(self) -> dict[str, str]:
        return {state.capability_id: state.percept_name for state in self.active_states()}

    def sampling_plan(self, available_ids: Iterable[str]) -> SamplingPlan:
        """Choose routine senses plus a bounded rotating exploration slice.

        During early development there may be no active sense yet, so up to
        ``exploration_limit`` unknown candidates are sampled per tick. Once at least
        one sense matures, all active senses remain routine while at most
        ``probe_limit`` unknown/dormant candidates are revisited. The cursor rotates
        deterministically through the whole pool, guaranteeing eventual re-probing
        without randomness or unbounded work.
        """
        available = tuple(sorted(set(available_ids), key=self._sampling_order))[: self._max_candidates]
        available_set = set(available)
        active = tuple(
            state.capability_id
            for state in self.active_states()
            if state.capability_id in available_set
        )
        active_set = set(active)
        unknown = [capability_id for capability_id in available if capability_id not in self._states]
        dormant = [
            capability_id
            for capability_id in available
            if capability_id in self._states and capability_id not in active_set
        ]
        pool = tuple((*unknown, *dormant))
        budget = self._probe_limit if active else self._exploration_limit
        probing: list[str] = []
        if pool:
            start = self._probe_cursor % len(pool)
            count = min(budget, len(pool))
            for offset in range(count):
                probing.append(pool[(start + offset) % len(pool)])
            self._probe_cursor += count

        plan = SamplingPlan(
            active=active,
            probing=tuple(probing),
            dormant_count=len(dormant),
            unknown_count=len(unknown),
        )
        self._last_plan = plan
        return plan

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
        """Serialize only established descriptive state (roadmap safety
        finding A02).

        A sense's aggregate mean/variance or a pair's aggregate sums are not
        yet a meaningfully-descriptive baseline before ``min_samples``/
        ``min_relation_samples`` — they are, arithmetically, close to or
        exactly the raw reading(s) themselves (with a single sample, mean
        *is* the reading; with two, the pair sums solve directly back to the
        two readings). Withholding an aggregate until it is actually
        established is the same discipline
        :class:`~symbiont.host.acclimation.HostAcclimation` already holds to
        for `baseline()`, applied here to what gets exported at all.

        This narrows, but does not eliminate, exposure: repeatedly exporting
        an *established* aggregate and differencing two exports separated by
        one new sample can still algebraically solve for that one sample.
        No mechanism here defends against that yet — treat this as reducing
        the earliest, worst exposure (a brand-new signal's first reading),
        not as an unconditional non-reconstruction guarantee.
        """
        return {
            "min_samples": self._min_samples,
            "active_limit": self._active_limit,
            "max_candidates": self._max_candidates,
            "relation_window": self._relation_window,
            "max_relations": self._max_relations,
            "min_relation_samples": self._min_relation_samples,
            "redundancy_threshold": self._redundancy_threshold,
            "exploration_limit": self._exploration_limit,
            "probe_limit": self._probe_limit,
            "probe_cursor": self._probe_cursor,
            "states": [
                state.to_payload() for state in self.states if state.available_samples >= self._min_samples
            ],
            "relations": [
                relation.to_payload()
                for _, relation in sorted(self._relations.items())
                if relation.synchronous.count >= self._min_relation_samples
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
            exploration_limit=int(payload.get("exploration_limit", 32)),
            probe_limit=int(payload.get("probe_limit", 4)),
            probe_cursor=int(payload.get("probe_cursor", 0)),
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
