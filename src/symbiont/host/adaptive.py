from __future__ import annotations
from .hypotheses import HypothesisTracker

from dataclasses import dataclass, field
from hashlib import sha256
import math
from itertools import combinations
from typing import Any, Iterable

from .readings import ReadingQuality, SensorReading


def _require_finite(value: Any, field: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def _require_nonneg_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an int")
    if value < 0:
        raise ValueError(f"{field} must be non-negative")
    return value


def _canonical_pair(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


_UTILITY_VARIABILITY_WEIGHT = 0.65
_UTILITY_MOTION_WEIGHT = 0.35


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
        return self.availability * (_UTILITY_VARIABILITY_WEIGHT * variability + _UTILITY_MOTION_WEIGHT * motion)

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
        samples = _require_nonneg_int(payload.get("samples", 0), "samples")
        available_samples = _require_nonneg_int(payload.get("available_samples", 0), "available_samples")
        mean = _require_finite(payload.get("mean", 0.0), "mean")
        m2 = _require_finite(payload.get("m2", 0.0), "m2")
        if m2 < 0.0:
            raise ValueError("m2 must be non-negative")
        delta_ewma = _require_finite(payload.get("delta_ewma", 0.0), "delta_ewma")
        if delta_ewma < 0.0:
            raise ValueError("delta_ewma must be non-negative")
        state = cls(
            capability_id=str(payload["capability_id"]),
            percept_name=str(payload["percept_name"]),
            samples=samples,
            available_samples=available_samples,
            mean=mean,
            m2=m2,
            last_value=None,
            delta_ewma=delta_ewma,
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
        count = _require_nonneg_int(payload.get("count", 0), "count")
        legacy_keys = {"sum_x", "sum_y", "sum_xx", "sum_yy", "sum_xy"}
        if legacy_keys.issubset(payload) and not {"mean_x", "mean_y", "m2_x", "m2_y", "c_xy"}.issubset(payload):
            sum_x = _require_finite(payload["sum_x"], "sum_x")
            sum_y = _require_finite(payload["sum_y"], "sum_y")
            sum_xx = _require_finite(payload["sum_xx"], "sum_xx")
            sum_yy = _require_finite(payload["sum_yy"], "sum_yy")
            sum_xy = _require_finite(payload["sum_xy"], "sum_xy")
            if count == 0:
                return cls()
            mean_x = sum_x / count
            mean_y = sum_y / count
            m2_x = max(0.0, sum_xx - (sum_x * sum_x) / count)
            m2_y = max(0.0, sum_yy - (sum_y * sum_y) / count)
            c_xy = sum_xy - (sum_x * sum_y) / count
            return cls(count=count, mean_x=mean_x, mean_y=mean_y, m2_x=m2_x, m2_y=m2_y, c_xy=c_xy)

        mean_x = _require_finite(payload.get("mean_x", 0.0), "mean_x")
        mean_y = _require_finite(payload.get("mean_y", 0.0), "mean_y")
        m2_x = _require_finite(payload.get("m2_x", 0.0), "m2_x")
        m2_y = _require_finite(payload.get("m2_y", 0.0), "m2_y")
        if m2_x < 0.0 or m2_y < 0.0:
            raise ValueError("m2_x and m2_y must be non-negative")
        c_xy = _require_finite(payload.get("c_xy", 0.0), "c_xy")
        return cls(count=count, mean_x=mean_x, mean_y=mean_y, m2_x=m2_x, m2_y=m2_y, c_xy=c_xy)


@dataclass(slots=True)
class SensoryRelation:
    """Descriptive relation between two opaque senses, never a causal claim."""

    capability_a: str
    capability_b: str
    synchronous: PairAccumulator = field(default_factory=PairAccumulator)
    a_to_b: PairAccumulator = field(default_factory=PairAccumulator)
    b_to_a: PairAccumulator = field(default_factory=PairAccumulator)
    last_seen_tick: int = 0

    def to_payload(self, *, min_samples: int) -> dict[str, Any]:
        """Serialize, withholding each of the three pair accumulators
        independently until it individually clears ``min_samples``
        (roadmap safety finding B01)."""

        def gate(accumulator: PairAccumulator) -> dict[str, float | int] | None:
            return accumulator.to_payload() if accumulator.count >= min_samples else None

        return {
            "capability_a": self.capability_a,
            "capability_b": self.capability_b,
            "synchronous": gate(self.synchronous),
            "a_to_b": gate(self.a_to_b),
            "b_to_a": gate(self.b_to_a),
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "SensoryRelation":
        def restore(key: str) -> PairAccumulator:
            raw = payload.get(key)
            return PairAccumulator.from_payload(dict(raw)) if raw else PairAccumulator()

        return cls(
            capability_a=str(payload["capability_a"]),
            capability_b=str(payload["capability_b"]),
            synchronous=restore("synchronous"),
            a_to_b=restore("a_to_b"),
            b_to_a=restore("b_to_a"),
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



# Historical AdaptiveSenseModel threshold.
# Retained deliberately to preserve checkpoint and behavioral compatibility.
# Do not align with EpistemicConventions.established_signal_min_samples (5)
# without an explicit checkpoint migration and biological regression study.
_ADAPTIVE_HISTORICAL_MIN_SAMPLES: int = 4

from ..core.limits import OrganismLimits

_DEFAULT_LIMITS = OrganismLimits()


class AdaptiveSenseModel:
    """Develop and selectively exercise a bounded repertoire of unknown senses.

    Senses move implicitly through three developmental tiers:

    * active — useful, complementary senses sampled routinely;
    * probing — unknown/dormant senses sampled on a rotating exploration budget;
    * dormant — known but currently unselected senses that remain discoverable and
      periodically return to probing, preventing irreversible early blindness.

    Checkpoints keep a bounded set of one-way capability fingerprints in
    addition to established aggregate states. This lets a restarted organism
    remember that an under-sampled surface was already encountered without
    persisting the one or two observations that would be raw-telemetry-
    equivalent. Recognition survives; immature measurements do not.
    """

    def __init__(
        self,
        *,
        min_samples: int = _ADAPTIVE_HISTORICAL_MIN_SAMPLES,
        active_limit: int = 24,
        max_candidates: int = _DEFAULT_LIMITS.max_candidate_senses,
        relation_window: int = 32,
        max_relations: int = _DEFAULT_LIMITS.max_relations,
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
        self._hypotheses = HypothesisTracker()
        self._previous_values: dict[str, float] = {}
        self._last_plan = SamplingPlan((), (), 0, 0)
        self._tick = 0
        self._evicted_percept_names: list[str] = []
        self._relation_changes = 0
        self._known_capability_fingerprints: dict[str, None] = {}

    @staticmethod
    def _percept_name(capability_id: str) -> str:
        digest = sha256(f"symbiont-sense:{capability_id}".encode("utf-8")).hexdigest()[:12]
        return f"sense_{digest}"

    @staticmethod
    def _sampling_order(capability_id: str) -> str:
        return sha256(f"symbiont-sampling:{capability_id}".encode("utf-8")).hexdigest()

    @staticmethod
    def _capability_fingerprint(capability_id: str) -> str:
        return sha256(f"symbiont-seen:{capability_id}".encode("utf-8")).hexdigest()

    def _remember_capability(self, capability_id: str) -> None:
        fingerprint = self._capability_fingerprint(capability_id)
        self._known_capability_fingerprints.pop(fingerprint, None)
        self._known_capability_fingerprints[fingerprint] = None
        while len(self._known_capability_fingerprints) > self._max_candidates:
            oldest = next(iter(self._known_capability_fingerprints))
            del self._known_capability_fingerprints[oldest]

    def _was_seen(self, capability_id: str) -> bool:
        return self._capability_fingerprint(capability_id) in self._known_capability_fingerprints

    @property
    def states(self) -> tuple[SenseState, ...]:
        return tuple(sorted(self._states.values(), key=lambda item: item.percept_name))

    @property
    def known_capability_fingerprints(self) -> tuple[str, ...]:
        return tuple(self._known_capability_fingerprints)

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

    @property
    def hypotheses(self):
        """Evidence-gated relationship hypotheses; never semantic labels."""
        return self._hypotheses.items

    def _evict_state_for(self, incoming_capability_id: str) -> bool:
        """Retire the least-recently-observed aggregate state to make room.

        The one-way recognition fingerprint intentionally survives state
        eviction while it remains inside the bounded recognition set: losing
        detailed aggregates is different from forgetting that a surface has
        been encountered before.
        """
        candidates = [state for state in self._states.values() if state.last_seen_tick < self._tick]
        if not candidates:
            return False
        oldest = min(candidates, key=lambda state: (state.last_seen_tick, state.capability_id))
        del self._states[oldest.capability_id]
        self._evicted_percept_names.append(oldest.percept_name)
        stale_keys = [key for key in self._relations if oldest.capability_id in key]
        for key in stale_keys:
            del self._relations[key]
        self._relation_changes += len(stale_keys)
        return True

    def drain_evicted_percept_names(self) -> tuple[str, ...]:
        """Return, and forget, every percept name evicted since the last call."""
        drained = tuple(self._evicted_percept_names)
        self._evicted_percept_names.clear()
        return drained

    def drain_relation_churn(self) -> float:
        """Return bounded structural relation churn since the last read.

        Only relation creation/eviction is counted; evidence updates do not
        inflate churn.  The value is a passive, normalized observation for
        external instrumentation and is intentionally not used by cognition.
        """
        changes = self._relation_changes
        self._relation_changes = 0
        return max(0.0, min(1.0, changes / max(1, self._relation_window)))

    def _relation(self, capability_a: str, capability_b: str) -> SensoryRelation | None:
        key = _canonical_pair(capability_a, capability_b)
        relation = self._relations.get(key)
        if relation is None:
            if len(self._relations) >= self._max_relations and not self._evict_relation():
                return None
            relation = SensoryRelation(key[0], key[1])
            self._relations[key] = relation
            self._relation_changes += 1
        relation.last_seen_tick = self._tick
        return relation

    def _evict_relation(self) -> bool:
        candidates = [relation for relation in self._relations.values() if relation.last_seen_tick < self._tick]
        if not candidates:
            return False
        oldest = min(
            candidates,
            key=lambda relation: (relation.last_seen_tick, relation.capability_a, relation.capability_b),
        )
        del self._relations[(oldest.capability_a, oldest.capability_b)]
        self._relation_changes += 1
        return True

    def observe(self, readings: Iterable[SensorReading]) -> None:
        self._tick += 1
        current_values: dict[str, float] = {}
        for reading in readings:
            self._remember_capability(reading.capability_id)
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
        for relation in self._relations.values():
            self._hypotheses.observe(
                (relation.capability_a, relation.capability_b),
                correlation=relation.synchronous.correlation,
                samples=relation.synchronous.count,
                min_samples=self._min_relation_samples,
                tick=self._tick,
            )
            # Trim in batches; sorting the bounded table for every newly
            # observed pair would make discovery quadratic in a long-lived
            # resident.
            if len(self._hypotheses.items) > self._max_relations * 2:
                self._hypotheses.trim(self._max_relations)

    def _is_redundant(self, candidate: SenseState, selected: list[SenseState]) -> bool:
        for other in selected:
            key = _canonical_pair(candidate.capability_id, other.capability_id)
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
        """Return only the currently active learned identities."""
        return {state.capability_id: state.percept_name for state in self.active_states()}

    def developed_percept_names(self) -> dict[str, str]:
        """Return every mature identity, whether active or temporarily dormant.

        Active selection controls sampling effort; it must not redefine a
        sense's identity. Runtime routing uses this mapping to ensure a
        bootstrap capability never reverts from its learned ``sense_*`` name
        merely because another sense currently outranks it for attention.
        """
        return {
            state.capability_id: state.percept_name
            for state in self._states.values()
            if state.available_samples >= self._min_samples
        }

    def sampling_plan(self, available_ids: Iterable[str]) -> SamplingPlan:
        """Choose routine senses plus a bounded rotating exploration slice.

        A capability with no restored aggregate state can still be dormant if
        its privacy-safe fingerprint says it was encountered before. This is
        the restart-stable distinction between "known but statistics omitted"
        and genuinely unknown.
        """
        available = tuple(sorted(set(available_ids), key=self._sampling_order))[: self._max_candidates]
        available_set = set(available)
        active = tuple(
            state.capability_id
            for state in self.active_states()
            if state.capability_id in available_set
        )
        active_set = set(active)
        unknown = [
            capability_id
            for capability_id in available
            if capability_id not in active_set
            and capability_id not in self._states
            and not self._was_seen(capability_id)
        ]
        dormant = [
            capability_id
            for capability_id in available
            if capability_id not in active_set
            and (capability_id in self._states or self._was_seen(capability_id))
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

        return tuple(
            sorted(
                eligible,
                key=lambda item: (-strength(item), -item.samples, item.sense_a, item.sense_b),
            )[:limit]
        )

    def export(self) -> dict[str, Any]:
        """Serialize established descriptive state plus opaque recognition.

        Under-sampled aggregates remain withheld because with one sample the
        mean is the reading itself. ``known_capability_fingerprints`` stores
        only bounded one-way recognition tokens, never sample counts, means,
        deltas or latest values, so restart continuity does not weaken that
        privacy gate.
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
            "known_capability_fingerprints": list(self._known_capability_fingerprints),
            "states": [
                state.to_payload() for state in self.states if state.available_samples >= self._min_samples
            ],
            "relations": [
                relation.to_payload(min_samples=self._min_relation_samples)
                for _, relation in sorted(self._relations.items())
                if max(relation.synchronous.count, relation.a_to_b.count, relation.b_to_a.count)
                >= self._min_relation_samples
            ],
            "hypotheses": self._hypotheses.export(),
        }

    @classmethod
    def restore(cls, payload: dict[str, Any] | None) -> "AdaptiveSenseModel":
        if not payload:
            return cls()
        model = cls(
            min_samples=int(payload.get("min_samples", _ADAPTIVE_HISTORICAL_MIN_SAMPLES)),
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

        raw_fingerprints = payload.get("known_capability_fingerprints", [])
        if not isinstance(raw_fingerprints, list):
            raise ValueError("known_capability_fingerprints must be a list")
        for fingerprint in raw_fingerprints[-model._max_candidates :]:
            if (
                not isinstance(fingerprint, str)
                or len(fingerprint) != 64
                or any(character not in "0123456789abcdef" for character in fingerprint)
            ):
                raise ValueError("known capability fingerprint must be a 64-character lowercase hex digest")
            model._known_capability_fingerprints[fingerprint] = None

        for item in payload.get("states", [])[: model._max_candidates]:
            state = SenseState.from_payload(item)
            model._states[state.capability_id] = state
            model._remember_capability(state.capability_id)
        for item in payload.get("relations", [])[: model._max_relations]:
            relation = SensoryRelation.from_payload(item)
            if relation.capability_a not in model._states or relation.capability_b not in model._states:
                continue
            key = _canonical_pair(relation.capability_a, relation.capability_b)
            model._relations[key] = relation
        model._hypotheses = HypothesisTracker.restore(payload.get("hypotheses"))
        return model
