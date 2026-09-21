from __future__ import annotations

import hashlib
import math
from collections import deque
from dataclasses import dataclass
from typing import Mapping, Sequence

from .types import MotorIntent


_HORIZONS = (1, 4, 16, 64)
_PRIMITIVE_TICKS = 4
_BABBLE_EPOCH_TICKS = 8
_PASSIVE_PROBE_PERIOD = 128
_PASSIVE_PROBE_OFFSET = 8
_PASSIVE_PROBE_TICKS = 4
_INVESTIGATION_EPOCH_TICKS = 16
_MAX_HYPOTHESIS_VERIFICATIONS = 4
_MAX_PRIMITIVES = 32
_MAX_HORIZON_STATS = 512
_MAX_PRIMITIVE_STATS = 64

MotorPattern = tuple[tuple[str, int], ...]
MotorSequence = tuple[MotorPattern, ...]


def _require_int(
    value: object,
    *,
    field: str,
    minimum: int = 0,
    maximum: int = 1_000_000_000,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{field} out of bounds")
    return value


def _require_finite(
    value: object,
    *,
    field: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    if minimum is not None and number < minimum:
        raise ValueError(f"{field} below minimum")
    if maximum is not None and number > maximum:
        raise ValueError(f"{field} above maximum")
    return number


def _finite_unit(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("motor value must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("motor value must be finite")
    return max(0.0, min(1.0, number))


def _quantize(value: float) -> int:
    return max(0, min(7, round(_finite_unit(value) * 7)))


def _pattern_key(vector: Mapping[str, float]) -> MotorPattern:
    return tuple(
        sorted(
            (str(actuator_id), _quantize(value))
            for actuator_id, value in vector.items()
            if value >= 0.08
        )
    )


def _sequence_payload(sequence: MotorSequence) -> list[list[list[object]]]:
    return [
        [[actuator_id, level] for actuator_id, level in pattern]
        for pattern in sequence
    ]


def _restore_sequence(
    payload: object,
    *,
    allowed_ids: set[str],
) -> MotorSequence:
    if not isinstance(payload, list):
        raise ValueError("invalid motor sequence")
    sequence: list[MotorPattern] = []
    for raw_pattern in payload:
        if not isinstance(raw_pattern, list):
            raise ValueError("invalid motor sequence pattern")
        parsed: list[tuple[str, int]] = []
        for item in raw_pattern:
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                raise ValueError("invalid motor sequence channel")
            actuator_id = item[0]
            level = item[1]
            if not isinstance(actuator_id, str) or not actuator_id:
                raise ValueError("invalid motor actuator id")
            parsed.append(
                (
                    actuator_id,
                    _require_int(
                        level,
                        field="motor quantization level",
                        minimum=0,
                        maximum=7,
                    ),
                )
            )
        pattern = tuple(parsed)
        actuator_ids = [actuator_id for actuator_id, _level in pattern]
        if (
            not pattern
            or len(pattern) != len(raw_pattern)
            or len(set(actuator_ids)) != len(actuator_ids)
            or any(
                actuator_id not in allowed_ids or not 0 <= level <= 7
                for actuator_id, level in pattern
            )
        ):
            raise ValueError("invalid motor sequence channel")
        sequence.append(pattern)
    if not sequence:
        raise ValueError("motor sequence must not be empty")
    return tuple(sequence)


@dataclass(slots=True)
class _RunningStat:
    count: int = 0
    mean: float = 0.0
    m2: float = 0.0

    def observe(self, value: float) -> None:
        number = float(value)
        if not math.isfinite(number):
            return
        self.count += 1
        delta = number - self.mean
        self.mean += delta / self.count
        self.m2 += delta * (number - self.mean)

    @property
    def variance(self) -> float:
        if self.count < 2:
            return 0.0
        return self.m2 / (self.count - 1)

    def checkpoint(self) -> dict[str, float | int]:
        return {"count": self.count, "mean": self.mean, "m2": self.m2}

    @classmethod
    def restore(cls, payload: Mapping[str, object]) -> "_RunningStat":
        return cls(
            count=_require_int(
                payload.get("count", 0),
                field="running-stat count",
            ),
            mean=_require_finite(
                payload.get("mean", 0.0),
                field="running-stat mean",
            ),
            m2=_require_finite(
                payload.get("m2", 0.0),
                field="running-stat m2",
                minimum=0.0,
            ),
        )


@dataclass(frozen=True, slots=True)
class MotorPrimitive:
    """An organism-discovered opaque temporal motor chunk."""

    primitive_id: str
    sequence: MotorSequence
    samples: int
    effect_mean: float
    effect_variance: float
    controllability: float
    directional_consistency: float
    verification_count: int = 0

    @property
    def duration_ticks(self) -> int:
        return len(self.sequence)

    @property
    def is_competence(self) -> bool:
        """Whether repeated evidence supports cognitive reuse.

        This is deliberately semantic-free: competence means that invoking the
        opaque motor chunk has produced a reproducible residual body-state
        transition. It says nothing about locomotion, anatomy or utility.
        """
        return (
            self.samples >= 2
            and self.controllability > 0.002
            and self.effect_variance <= 0.02
            and self.directional_consistency >= 0.60
        )

    @property
    def investigation_priority(self) -> float:
        """Rank unresolved causal hypotheses for active re-testing.

        One observation is a hypothesis, not a skill. Priority combines the
        magnitude of the residual controllable effect with directional
        repeatability, while preferring hypotheses that have not already
        consumed the bounded verification budget.
        """
        if self.is_competence:
            return 0.0
        remaining = max(
            0.0,
            1.0 - self.verification_count / _MAX_HYPOTHESIS_VERIFICATIONS,
        )
        evidence = max(0.0, self.controllability)
        direction = max(0.0, min(1.0, self.directional_consistency))
        return remaining * evidence * (0.25 + 0.75 * direction)

    def intents_at(self, step: int) -> tuple[MotorIntent, ...]:
        if not 0 <= step < len(self.sequence):
            return ()
        return tuple(
            MotorIntent(actuator_id=actuator_id, activation=level / 7.0)
            for actuator_id, level in self.sequence[step]
            if level > 0
        )

    def checkpoint(self) -> dict[str, object]:
        return {
            "primitive_id": self.primitive_id,
            "sequence": _sequence_payload(self.sequence),
            "samples": self.samples,
            "effect_mean": self.effect_mean,
            "effect_variance": self.effect_variance,
            "controllability": self.controllability,
            "directional_consistency": self.directional_consistency,
            "verification_count": self.verification_count,
        }

    @classmethod
    def restore(
        cls,
        payload: Mapping[str, object],
        *,
        allowed_ids: set[str],
    ) -> "MotorPrimitive":
        raw_sequence = payload.get("sequence")
        if raw_sequence is None and isinstance(payload.get("pattern"), list):
            # v1 migration: a primitive was one static pattern held N ticks.
            raw_pattern = payload["pattern"]
            raw_sequence = [
                raw_pattern for _ in range(_PRIMITIVE_TICKS)
            ]
        sequence = _restore_sequence(raw_sequence, allowed_ids=allowed_ids)
        if len(sequence) != _PRIMITIVE_TICKS:
            raise ValueError("motor primitive has invalid temporal duration")
        primitive_id = payload.get("primitive_id")
        if not isinstance(primitive_id, str) or not primitive_id:
            raise ValueError("invalid motor primitive id")
        return cls(
            primitive_id=primitive_id,
            sequence=sequence,
            samples=_require_int(
                payload.get("samples", 0),
                field="primitive samples",
            ),
            effect_mean=_require_finite(
                payload.get("effect_mean", 0.0),
                field="primitive effect mean",
                minimum=0.0,
            ),
            effect_variance=_require_finite(
                payload.get("effect_variance", 0.0),
                field="primitive effect variance",
                minimum=0.0,
            ),
            controllability=_require_finite(
                payload.get("controllability", 0.0),
                field="primitive controllability",
                minimum=0.0,
            ),
            directional_consistency=_require_finite(
                payload.get("directional_consistency", 0.0),
                field="primitive directional consistency",
                minimum=0.0,
                maximum=1.0,
            ),
            verification_count=_require_int(
                payload.get("verification_count", 0),
                field="primitive verification count",
            ),
        )


@dataclass(frozen=True, slots=True)
class SensorimotorSnapshot:
    babbling_coverage: float
    known_patterns: int
    primitives: int
    hypotheses: int
    cognitive_primitives: int
    investigation_active: bool
    investigation_primitive_id: str | None
    best_controllability: float
    best_directional_consistency: float
    replay_active: bool
    replay_primitive_id: str | None
    horizon_samples: tuple[tuple[int, int], ...]
    passive_baseline_samples: int


@dataclass(slots=True)
class _Frame:
    tick: int
    body_state: dict[str, float]
    motor_vector: dict[str, float]
    discovery_eligible: bool
    execution_primitive_id: str | None


class SensorimotorLearner:
    """Learn body dynamics and reusable actions without anatomy semantics.

    Development begins with deterministic organism-owned correlated motor
    babbling. Four consecutive actually-delivered motor vectors form a
    candidate temporal chunk. The chunk becomes cognitively available only
    after an independent replay reproduces a directionally consistent bodily
    consequence.
    """

    def __init__(
        self,
        actuator_ids: Sequence[str],
        *,
        organism_id: str,
        max_concurrent: int | None = None,
        smoothing: float = 0.28,
    ) -> None:
        ids = tuple(str(value) for value in actuator_ids)
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("sensorimotor learner requires unique actuator ids")
        if max_concurrent is not None and (
            isinstance(max_concurrent, bool)
            or not isinstance(max_concurrent, int)
            or max_concurrent < 1
        ):
            raise ValueError("max_concurrent must be a positive int or None")
        if not 0.0 < float(smoothing) <= 1.0:
            raise ValueError("smoothing must be within (0, 1]")

        self._ids = ids
        self._organism_id = str(organism_id)
        self._max_concurrent = (
            len(ids)
            if max_concurrent is None
            else min(max_concurrent, len(ids))
        )
        self._smoothing = float(smoothing)

        self._levels = {aid: 0.0 for aid in ids}
        self._use_counts = {aid: 0 for aid in ids}
        self._babble_epoch = -1
        self._babble_ids: tuple[str, ...] = ()

        self._frames: deque[_Frame] = deque(maxlen=max(_HORIZONS) + _PRIMITIVE_TICKS + 2)
        self._horizon_stats: dict[tuple[int, MotorPattern], _RunningStat] = {}
        self._horizon_counts = {horizon: 0 for horizon in _HORIZONS}

        self._primitive_stats: dict[MotorSequence, _RunningStat] = {}
        self._passive_effect_stat = _RunningStat()
        self._passive_direction_stats: dict[str, _RunningStat] = {}
        self._primitive_direction_stats: dict[
            MotorSequence, dict[str, _RunningStat]
        ] = {}
        self._last_episode_end_tick: dict[MotorSequence, int] = {}
        self._primitives: dict[str, MotorPrimitive] = {}

        self._replay_id: str | None = None
        self._replay_step = 0
        self._replay_source: str | None = None
        self._last_verification_epoch = -1
        self._investigation_id: str | None = None
        self._last_output_primitive_id: str | None = None
        self._last_output_source = "babbling"

    @property
    def primitives(self) -> tuple[MotorPrimitive, ...]:
        return tuple(
            sorted(self._primitives.values(), key=lambda item: item.primitive_id)
        )

    @property
    def cognitive_primitives(self) -> tuple[MotorPrimitive, ...]:
        """Return every currently supported motor competence.

        Cognitive availability is evidence-gated by ``is_competence`` but is
        not arbitrarily truncated. The finite primitive pool remains the
        resource bound; structural contention separately limits what can enter
        the cognitive graph.
        """
        eligible = [
            primitive
            for primitive in self.primitives
            if primitive.is_competence
        ]
        return tuple(
            sorted(
                eligible,
                key=lambda primitive: (
                    -primitive.controllability,
                    -primitive.directional_consistency,
                    -primitive.samples,
                    primitive.primitive_id,
                ),
            )
        )

    @property
    def active_primitive_id(self) -> str | None:
        return self._replay_id

    @property
    def active_investigation_id(self) -> str | None:
        """Opaque hypothesis currently receiving active causal probes."""
        return self._investigation_id

    @property
    def hypotheses(self) -> tuple[MotorPrimitive, ...]:
        """Unresolved motor hypotheses still worth bounded investigation."""
        return tuple(
            primitive
            for primitive in self.primitives
            if (
                not primitive.is_competence
                and primitive.verification_count
                < _MAX_HYPOTHESIS_VERIFICATIONS
                and primitive.investigation_priority > 0.0
            )
        )

    @property
    def last_output_primitive_id(self) -> str | None:
        return self._last_output_primitive_id

    @property
    def last_output_source(self) -> str:
        return self._last_output_source

    @property
    def babbling_coverage(self) -> float:
        used = sum(1 for count in self._use_counts.values() if count > 0)
        return used / len(self._use_counts)

    def primitive_intents(self, primitive_id: str) -> tuple[MotorIntent, ...]:
        primitive = self._primitives.get(str(primitive_id))
        if primitive is None or primitive not in self.cognitive_primitives:
            return ()
        return primitive.intents_at(0)[: self._max_concurrent]

    def activate_primitive(
        self,
        primitive_id: str,
        *,
        source: str = "cognition",
    ) -> bool:
        primitive = self._primitives.get(str(primitive_id))
        if primitive is None or primitive not in self.cognitive_primitives:
            return False
        if source not in {"cognition", "verification"}:
            raise ValueError("primitive source must be cognition or verification")
        self._replay_id = primitive.primitive_id
        self._replay_step = 0
        self._replay_source = source
        return True

    def _hash_unit(self, actuator_id: str, epoch: int) -> float:
        digest = hashlib.sha256(
            f"sensorimotor-babble:{self._organism_id}:{actuator_id}:{epoch}".encode(
                "utf-8"
            )
        ).digest()
        return int.from_bytes(digest[:8], "big") / float((1 << 64) - 1)

    def _target_for(self, actuator_id: str, tick: int) -> float:
        raw = self._hash_unit(actuator_id, tick // _BABBLE_EPOCH_TICKS)
        return 0.15 + 0.70 * raw

    def _babble_cardinality(self, epoch: int) -> int:
        """Explore coordination dimensionality instead of imposing one size."""
        digest = hashlib.sha256(
            f"sensorimotor-cardinality:{self._organism_id}:{epoch}".encode(
                "utf-8"
            )
        ).digest()
        return 1 + (
            int.from_bytes(digest[:8], "big") % self._max_concurrent
        )

    def _babble_vector(self, tick: int) -> dict[str, float]:
        epoch = tick // _BABBLE_EPOCH_TICKS
        if epoch != self._babble_epoch or not self._babble_ids:
            scored = [
                (
                    self._use_counts[actuator_id],
                    -self._hash_unit(actuator_id, epoch),
                    actuator_id,
                )
                for actuator_id in self._ids
            ]
            cardinality = self._babble_cardinality(epoch)
            self._babble_ids = tuple(
                item[2] for item in sorted(scored)[:cardinality]
            )
            self._babble_epoch = epoch

        vector: dict[str, float] = {}
        for actuator_id in self._ids:
            target = (
                self._target_for(actuator_id, tick)
                if actuator_id in self._babble_ids
                else 0.0
            )
            current = self._levels[actuator_id]
            current += self._smoothing * (target - current)
            self._levels[actuator_id] = current

        for actuator_id in self._babble_ids:
            value = self._levels[actuator_id]
            if value >= 0.08:
                vector[actuator_id] = value
                self._use_counts[actuator_id] += 1
        return vector

    @staticmethod
    def _is_passive_probe(tick: int) -> bool:
        if tick < _PASSIVE_PROBE_OFFSET:
            return False
        phase = (tick - _PASSIVE_PROBE_OFFSET) % _PASSIVE_PROBE_PERIOD
        return phase < _PASSIVE_PROBE_TICKS

    def _investigation_candidate(self) -> MotorPrimitive | None:
        """Choose one unresolved hypothesis and keep testing it coherently."""
        current = (
            self._primitives.get(self._investigation_id)
            if self._investigation_id is not None
            else None
        )
        if (
            current is not None
            and not current.is_competence
            and current.verification_count < _MAX_HYPOTHESIS_VERIFICATIONS
            and current.investigation_priority > 0.0
        ):
            return current

        unresolved = [
            primitive
            for primitive in self._primitives.values()
            if (
                not primitive.is_competence
                and primitive.verification_count
                < _MAX_HYPOTHESIS_VERIFICATIONS
                and primitive.investigation_priority > 0.0
            )
        ]
        if not unresolved:
            self._investigation_id = None
            return None

        candidate = max(
            unresolved,
            key=lambda primitive: (
                primitive.investigation_priority,
                primitive.controllability,
                primitive.directional_consistency,
                -primitive.verification_count,
                primitive.primitive_id,
            ),
        )
        self._investigation_id = candidate.primitive_id
        return candidate

    def _should_replay(self, tick: int) -> bool:
        """Return whether this epoch can host one active causal probe.

        The old implementation used a hash lottery, which let hypothesis
        production outrun verification: a large candidate pool could remain
        forever at one sample. Investigation is now deterministic and bounded:
        at most one four-tick probe starts per epoch, and only while an
        unresolved causal hypothesis exists.
        """
        epoch = tick // _INVESTIGATION_EPOCH_TICKS
        if epoch == self._last_verification_epoch:
            return False
        return self._investigation_candidate() is not None

    def motor_intents(
        self,
        tick: int,
        *,
        allow_verification: bool = True,
    ) -> tuple[MotorIntent, ...]:
        self._last_output_primitive_id = None
        self._last_output_source = "babbling"

        if self._replay_id is not None:
            primitive = self._primitives.get(self._replay_id)
            if primitive is not None and self._replay_step < primitive.duration_ticks:
                primitive_id = primitive.primitive_id
                source = self._replay_source or "verification"
                self._last_output_primitive_id = primitive_id
                self._last_output_source = (
                    "primitive" if source == "cognition" else "verification"
                )
                intents = primitive.intents_at(self._replay_step)[
                    : self._max_concurrent
                ]
                self._replay_step += 1
                if self._replay_step >= primitive.duration_ticks:
                    self._replay_id = None
                    self._replay_step = 0
                    self._replay_source = None
                return intents
            self._replay_id = None
            self._replay_step = 0
            self._replay_source = None

        if self._is_passive_probe(tick):
            self._last_output_source = "passive"
            return ()

        if allow_verification and self._should_replay(tick):
            primitive = self._investigation_candidate()
            if primitive is None:
                raise RuntimeError("active investigation lost its hypothesis")
            self._replay_id = primitive.primitive_id
            self._replay_step = 0
            self._replay_source = "verification"
            self._last_verification_epoch = tick // _INVESTIGATION_EPOCH_TICKS
            self._primitives[primitive.primitive_id] = MotorPrimitive(
                primitive_id=primitive.primitive_id,
                sequence=primitive.sequence,
                samples=primitive.samples,
                effect_mean=primitive.effect_mean,
                effect_variance=primitive.effect_variance,
                controllability=primitive.controllability,
                directional_consistency=primitive.directional_consistency,
                verification_count=primitive.verification_count + 1,
            )
            return self.motor_intents(
                tick,
                allow_verification=allow_verification,
            )

        vector = self._babble_vector(tick)
        return tuple(
            MotorIntent(actuator_id=actuator_id, activation=value)
            for actuator_id, value in sorted(vector.items())
        )

    @staticmethod
    def _body_delta(
        before: Mapping[str, float],
        after: Mapping[str, float],
    ) -> float:
        shared = set(before) & set(after)
        if not shared:
            return 0.0
        return sum(
            abs(float(after[key]) - float(before[key]))
            for key in shared
        ) / len(shared)

    @staticmethod
    def _signed_body_delta(
        before: Mapping[str, float],
        after: Mapping[str, float],
    ) -> dict[str, float]:
        return {
            key: float(after[key]) - float(before[key])
            for key in sorted(set(before) & set(after))
        }

    @staticmethod
    def _directional_consistency(
        stats: Mapping[str, _RunningStat],
    ) -> float:
        if not stats:
            return 0.0
        values: list[float] = []
        for stat in stats.values():
            magnitude = abs(stat.mean)
            if magnitude <= 1e-12:
                continue
            dispersion = math.sqrt(max(0.0, stat.variance))
            values.append(magnitude / (magnitude + dispersion + 1e-12))
        return sum(values) / len(values) if values else 0.0

    def _record_primitive_episode(
        self,
        *,
        sequence: MotorSequence,
        before: Mapping[str, float],
        after: Mapping[str, float],
        end_tick: int,
        may_create: bool,
    ) -> None:
        previous_end = self._last_episode_end_tick.get(sequence)
        if previous_end is not None and end_tick - previous_end < _PRIMITIVE_TICKS:
            return
        existing = sequence in self._primitive_stats
        if not existing and not may_create:
            return

        raw_effect = self._body_delta(before, after)
        effect = max(0.0, raw_effect - self._passive_effect_stat.mean)
        stat = self._primitive_stats.setdefault(sequence, _RunningStat())
        stat.observe(effect)
        direction_stats = self._primitive_direction_stats.setdefault(sequence, {})
        for signal_id, delta in self._signed_body_delta(before, after).items():
            passive_stat = self._passive_direction_stats.get(signal_id)
            passive_mean = passive_stat.mean if passive_stat is not None else 0.0
            residual_delta = delta - passive_mean
            direction_stats.setdefault(signal_id, _RunningStat()).observe(
                residual_delta
            )
        self._last_episode_end_tick[sequence] = end_tick

        if len(self._primitive_stats) > _MAX_PRIMITIVE_STATS:
            retained_sequences = {
                sequence_key
                for sequence_key, _ in sorted(
                    self._primitive_stats.items(),
                    key=lambda item: (-item[1].count, -item[1].mean, item[0]),
                )[:_MAX_PRIMITIVE_STATS]
            }
            self._primitive_stats = {
                key: value
                for key, value in self._primitive_stats.items()
                if key in retained_sequences
            }
            self._primitive_direction_stats = {
                key: value
                for key, value in self._primitive_direction_stats.items()
                if key in retained_sequences
            }
            retained_primitive_ids = {
                f"primitive.{hashlib.sha256(repr(key).encode('utf-8')).hexdigest()[:16]}"
                for key in retained_sequences
            }
            self._primitives = {
                primitive_id: primitive
                for primitive_id, primitive in self._primitives.items()
                if primitive_id in retained_primitive_ids
            }

        reproducibility = 1.0 / (1.0 + 25.0 * stat.variance)
        directional_consistency = self._directional_consistency(direction_stats)
        controllability = (
            max(0.0, stat.mean)
            * reproducibility
            * directional_consistency
        )
        digest = hashlib.sha256(repr(sequence).encode("utf-8")).hexdigest()[:16]
        primitive_id = f"primitive.{digest}"
        if controllability <= 0.002:
            self._primitives.pop(primitive_id, None)
            if self._investigation_id == primitive_id:
                self._investigation_id = None
            return

        previous = self._primitives.get(primitive_id)
        self._primitives[primitive_id] = MotorPrimitive(
            primitive_id=primitive_id,
            sequence=sequence,
            samples=stat.count,
            effect_mean=stat.mean,
            effect_variance=stat.variance,
            controllability=controllability,
            directional_consistency=directional_consistency,
            verification_count=(
                previous.verification_count if previous is not None else 0
            ),
        )
        if (
            self._investigation_id == primitive_id
            and self._primitives[primitive_id].is_competence
        ):
            self._investigation_id = None

        if len(self._primitives) > _MAX_PRIMITIVES:
            retained = sorted(
                self._primitives.values(),
                key=lambda item: (
                    -item.controllability,
                    -item.samples,
                    item.primitive_id,
                ),
            )[:_MAX_PRIMITIVES]
            self._primitives = {
                primitive.primitive_id: primitive for primitive in retained
            }
            if (
                self._investigation_id is not None
                and self._investigation_id not in self._primitives
            ):
                self._investigation_id = None

    def observe(
        self,
        *,
        tick: int,
        body_state: Mapping[str, float],
        motor_vector: Mapping[str, float],
        discovery_eligible: bool = True,
        execution_primitive_id: str | None = None,
    ) -> None:
        frame = _Frame(
            tick=int(tick),
            body_state={str(key): float(value) for key, value in body_state.items()},
            motor_vector={
                str(key): _finite_unit(value)
                for key, value in motor_vector.items()
            },
            discovery_eligible=bool(discovery_eligible),
            execution_primitive_id=(
                str(execution_primitive_id)
                if execution_primitive_id is not None
                else None
            ),
        )
        self._frames.append(frame)
        frames = list(self._frames)

        for horizon in _HORIZONS:
            if len(frames) <= horizon:
                continue
            previous = frames[-horizon - 1]
            if frame.tick - previous.tick != horizon:
                continue
            pattern = _pattern_key(previous.motor_vector)
            if not pattern:
                continue
            effect = self._body_delta(previous.body_state, frame.body_state)
            stat = self._horizon_stats.setdefault(
                (horizon, pattern),
                _RunningStat(),
            )
            stat.observe(effect)
            self._horizon_counts[horizon] += 1

        if len(self._horizon_stats) > _MAX_HORIZON_STATS:
            self._horizon_stats = dict(
                sorted(
                    self._horizon_stats.items(),
                    key=lambda item: (-item[1].count, item[0]),
                )[:_MAX_HORIZON_STATS]
            )

        if len(frames) < _PRIMITIVE_TICKS + 1:
            return

        action_frames = frames[-_PRIMITIVE_TICKS - 1 : -1]
        temporal_window = (*action_frames, frame)
        if any(
            later.tick - earlier.tick != 1
            for earlier, later in zip(
                temporal_window,
                temporal_window[1:],
            )
        ):
            return

        if all(not action_frame.motor_vector for action_frame in action_frames):
            passive_effect = self._body_delta(
                action_frames[0].body_state,
                frame.body_state,
            )
            self._passive_effect_stat.observe(passive_effect)
            for signal_id, delta in self._signed_body_delta(
                action_frames[0].body_state,
                frame.body_state,
            ).items():
                self._passive_direction_stats.setdefault(
                    signal_id,
                    _RunningStat(),
                ).observe(delta)
            return

        primitive_ids = {
            action_frame.execution_primitive_id
            for action_frame in action_frames
            if action_frame.execution_primitive_id is not None
        }

        # During explicit primitive replay, identity comes from the invoked
        # learned action, not from re-quantizing delivered actuator values.
        # Delivery may legitimately vary with actuator health/reliability.
        replay_sequence: MotorSequence | None = None
        if len(primitive_ids) == 1 and all(
            action_frame.execution_primitive_id is not None
            for action_frame in action_frames
        ):
            primitive_id = next(iter(primitive_ids))
            primitive = self._primitives.get(primitive_id)
            if primitive is not None:
                replay_sequence = primitive.sequence

        if replay_sequence is not None:
            self._record_primitive_episode(
                sequence=replay_sequence,
                before=action_frames[0].body_state,
                after=frame.body_state,
                end_tick=frame.tick,
                may_create=False,
            )
            return

        sequence = tuple(
            _pattern_key(action_frame.motor_vector)
            for action_frame in action_frames
        )
        if len(sequence) != _PRIMITIVE_TICKS or any(
            not pattern for pattern in sequence
        ):
            return

        # New candidates arise only from organism-generated non-primitive
        # activity and only on non-overlapping chunk boundaries.
        # Candidate windows are sampled every two ticks. This preserves
        # bounded growth while allowing four-step chunks to straddle babbling
        # epoch boundaries, so learned primitives can contain changing actuator
        # combinations rather than only amplitude changes on one fixed subset.
        may_create = (
            all(action_frame.discovery_eligible for action_frame in action_frames)
            and frame.tick % 2 == 0
        )
        self._record_primitive_episode(
            sequence=sequence,
            before=action_frames[0].body_state,
            after=frame.body_state,
            end_tick=frame.tick,
            may_create=may_create,
        )

    def snapshot(self) -> SensorimotorSnapshot:
        best = max(
            (primitive.controllability for primitive in self._primitives.values()),
            default=0.0,
        )
        best_direction = max(
            (
                primitive.directional_consistency
                for primitive in self._primitives.values()
            ),
            default=0.0,
        )
        known_patterns = {
            pattern for _horizon, pattern in self._horizon_stats
        }
        return SensorimotorSnapshot(
            babbling_coverage=self.babbling_coverage,
            known_patterns=len(known_patterns),
            primitives=len(self._primitives),
            hypotheses=len(self.hypotheses),
            cognitive_primitives=len(self.cognitive_primitives),
            investigation_active=self._investigation_id is not None,
            investigation_primitive_id=self._investigation_id,
            best_controllability=float(best),
            best_directional_consistency=float(best_direction),
            replay_active=self._replay_id is not None,
            replay_primitive_id=self._replay_id,
            horizon_samples=tuple(
                (horizon, self._horizon_counts[horizon])
                for horizon in _HORIZONS
            ),
            passive_baseline_samples=self._passive_effect_stat.count,
        )

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": 3,
            "actuator_ids": list(self._ids),
            "smoothing": self._smoothing,
            "levels": dict(self._levels),
            "use_counts": dict(self._use_counts),
            "babble_epoch": self._babble_epoch,
            "babble_ids": list(self._babble_ids),
            "horizon_stats": [
                {
                    "horizon": horizon,
                    "pattern": [[aid, level] for aid, level in pattern],
                    "stat": stat.checkpoint(),
                }
                for (horizon, pattern), stat
                in sorted(self._horizon_stats.items())
            ],
            "horizon_counts": {
                str(horizon): count
                for horizon, count in self._horizon_counts.items()
            },
            "passive_effect_stat": self._passive_effect_stat.checkpoint(),
            "passive_direction_stats": {
                signal_id: stat.checkpoint()
                for signal_id, stat in sorted(
                    self._passive_direction_stats.items()
                )
            },
            "primitive_stats": [
                {
                    "sequence": _sequence_payload(sequence),
                    "stat": stat.checkpoint(),
                    "signals": {
                        signal_id: signal_stat.checkpoint()
                        for signal_id, signal_stat
                        in sorted(
                            self._primitive_direction_stats.get(
                                sequence,
                                {},
                            ).items()
                        )
                    },
                }
                for sequence, stat in sorted(self._primitive_stats.items())
            ],
            "primitives": [
                primitive.checkpoint() for primitive in self.primitives
            ],
            "replay_id": self._replay_id,
            "replay_step": self._replay_step,
            "replay_source": self._replay_source,
            "last_verification_epoch": self._last_verification_epoch,
            "investigation_id": self._investigation_id,
        }

    @classmethod
    def restore(
        cls,
        payload: Mapping[str, object],
        *,
        actuator_ids: Sequence[str],
        organism_id: str,
    ) -> "SensorimotorLearner":
        schema = _require_int(
            payload.get("schema_version", -1),
            field="sensorimotor schema_version",
            minimum=1,
            maximum=3,
        )
        if schema not in {1, 2, 3}:
            raise ValueError("unsupported sensorimotor checkpoint")

        expected = tuple(str(value) for value in actuator_ids)
        stored = tuple(str(value) for value in payload.get("actuator_ids", []))
        if stored != expected:
            raise ValueError("sensorimotor actuator constitution mismatch")
        allowed = set(expected)

        # Concurrency is a property of the available body, not learned state.
        # v1/v2 checkpoints persisted an implementation cap (typically 4);
        # normalize it away on restore instead of perpetuating that artificial
        # constitutional restriction.
        learner = cls(
            expected,
            organism_id=organism_id,
            max_concurrent=None,
            smoothing=_require_finite(
                payload.get("smoothing", 0.28),
                field="sensorimotor smoothing",
                minimum=1e-12,
                maximum=1.0,
            ),
        )

        raw_levels = payload.get("levels", {})
        if isinstance(raw_levels, Mapping):
            learner._levels = {
                actuator_id: _finite_unit(
                    _require_finite(
                        raw_levels.get(actuator_id, 0.0),
                        field=f"sensorimotor level {actuator_id}",
                        minimum=0.0,
                        maximum=1.0,
                    )
                )
                for actuator_id in expected
            }
        raw_counts = payload.get("use_counts", {})
        if isinstance(raw_counts, Mapping):
            learner._use_counts = {
                actuator_id: _require_int(
                    raw_counts.get(actuator_id, 0),
                    field=f"sensorimotor use count {actuator_id}",
                )
                for actuator_id in expected
            }

        raw_babble_epoch = payload.get("babble_epoch", -1)
        if (
            isinstance(raw_babble_epoch, bool)
            or not isinstance(raw_babble_epoch, int)
            or raw_babble_epoch < -1
        ):
            raise ValueError("invalid sensorimotor babble epoch")
        learner._babble_epoch = raw_babble_epoch
        raw_babble_ids = payload.get("babble_ids", [])
        if isinstance(raw_babble_ids, list):
            restored_ids = tuple(str(value) for value in raw_babble_ids)
            if all(value in allowed for value in restored_ids):
                # Force the next babbling epoch to derive its concurrent set
                # from the full actuator constitution rather than preserving
                # a legacy truncated checkpoint subset.
                learner._babble_ids = ()

        raw_horizon_stats = payload.get("horizon_stats", [])
        if isinstance(raw_horizon_stats, list):
            for item in raw_horizon_stats[:_MAX_HORIZON_STATS]:
                if not isinstance(item, Mapping):
                    continue
                horizon = _require_int(
                    item.get("horizon", 0),
                    field="sensorimotor horizon",
                    minimum=1,
                    maximum=max(_HORIZONS),
                )
                if horizon not in _HORIZONS:
                    continue
                raw_pattern = item.get("pattern", [])
                try:
                    pattern = _restore_sequence(
                        [raw_pattern],
                        allowed_ids=allowed,
                    )[0]
                except ValueError:
                    continue
                raw_stat = item.get("stat", {})
                if isinstance(raw_stat, Mapping):
                    learner._horizon_stats[(horizon, pattern)] = (
                        _RunningStat.restore(raw_stat)
                    )

        raw_passive_effect = payload.get("passive_effect_stat")
        if isinstance(raw_passive_effect, Mapping):
            learner._passive_effect_stat = _RunningStat.restore(
                raw_passive_effect
            )
        raw_passive_directions = payload.get("passive_direction_stats", {})
        if isinstance(raw_passive_directions, Mapping):
            learner._passive_direction_stats = {
                str(signal_id): _RunningStat.restore(raw_stat)
                for signal_id, raw_stat in raw_passive_directions.items()
                if isinstance(raw_stat, Mapping)
            }

        raw_primitive_stats = payload.get("primitive_stats", [])
        if isinstance(raw_primitive_stats, list):
            for item in raw_primitive_stats[:_MAX_PRIMITIVE_STATS]:
                if not isinstance(item, Mapping):
                    continue
                try:
                    if schema == 1:
                        raw_pattern = item.get("pattern", [])
                        sequence = _restore_sequence(
                            [raw_pattern for _ in range(_PRIMITIVE_TICKS)],
                            allowed_ids=allowed,
                        )
                    else:
                        sequence = _restore_sequence(
                            item.get("sequence"),
                            allowed_ids=allowed,
                        )
                except ValueError:
                    continue
                raw_stat = item.get("stat", {})
                if isinstance(raw_stat, Mapping):
                    learner._primitive_stats[sequence] = _RunningStat.restore(
                        raw_stat
                    )
                raw_signals = item.get("signals", {})
                if isinstance(raw_signals, Mapping):
                    learner._primitive_direction_stats[sequence] = {
                        str(signal_id): _RunningStat.restore(raw_signal_stat)
                        for signal_id, raw_signal_stat in raw_signals.items()
                        if isinstance(raw_signal_stat, Mapping)
                    }

        raw_horizons = payload.get("horizon_counts", {})
        if isinstance(raw_horizons, Mapping):
            learner._horizon_counts = {
                horizon: _require_int(
                    raw_horizons.get(str(horizon), 0),
                    field=f"sensorimotor horizon count {horizon}",
                )
                for horizon in _HORIZONS
            }

        raw_primitives = payload.get("primitives", [])
        if isinstance(raw_primitives, list):
            for item in raw_primitives[:_MAX_PRIMITIVES]:
                if not isinstance(item, Mapping):
                    raise ValueError("invalid motor primitive entry")
                # A malformed or tampered primitive entry (wrong type, out of
                # range, coerced field) must fail the whole restore rather
                # than be silently dropped: a partially-corrupted checkpoint
                # is indistinguishable from a foreign one and must not
                # masquerade as a smaller, legitimately-learned repertoire.
                primitive = MotorPrimitive.restore(
                    item,
                    allowed_ids=allowed,
                )
                learner._primitives[primitive.primitive_id] = primitive

        replay_id = payload.get("replay_id")
        if replay_id is not None and not isinstance(replay_id, str):
            raise ValueError("invalid sensorimotor replay id")
        if isinstance(replay_id, str) and replay_id in learner._primitives:
            learner._replay_id = replay_id
            learner._replay_step = _require_int(
                payload.get("replay_step", 0),
                field="sensorimotor replay step",
                minimum=0,
                maximum=learner._primitives[replay_id].duration_ticks - 1,
            )
            replay_source = payload.get("replay_source")
            learner._replay_source = (
                str(replay_source)
                if replay_source in {"cognition", "verification"}
                else None
            )
        raw_last_verification_epoch = payload.get(
            "last_verification_epoch",
            -1,
        )
        if (
            isinstance(raw_last_verification_epoch, bool)
            or not isinstance(raw_last_verification_epoch, int)
            or raw_last_verification_epoch < -1
        ):
            raise ValueError("invalid sensorimotor last verification epoch")
        learner._last_verification_epoch = raw_last_verification_epoch

        investigation_id = payload.get("investigation_id")
        if investigation_id is not None and not isinstance(investigation_id, str):
            raise ValueError("invalid sensorimotor investigation id")
        if (
            isinstance(investigation_id, str)
            and investigation_id in learner._primitives
        ):
            learner._investigation_id = investigation_id

        # Frame history and episode boundaries are deliberately cold-started:
        # raw body-state baselines are not checkpointed.
        learner._frames.clear()
        learner._last_episode_end_tick.clear()
        return learner


__all__ = [
    "MotorPattern",
    "MotorPrimitive",
    "MotorSequence",
    "SensorimotorLearner",
    "SensorimotorSnapshot",
]
