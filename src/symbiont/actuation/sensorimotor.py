from __future__ import annotations

import hashlib
import math
from collections import deque
from dataclasses import dataclass
from typing import Mapping, Sequence

from .types import MotorIntent


_HORIZONS = (1, 4, 16, 64)
_PATTERN_HOLD_TICKS = 4
_MAX_PRIMITIVES = 32
_MAX_HORIZON_STATS = 1024
_MAX_PRIMITIVE_STATS = 256
_MIN_PRIMITIVE_SAMPLES = 1


def _finite_unit(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("motor value must be numeric")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("motor value must be finite")
    return max(0.0, min(1.0, value))


def _quantize(value: float) -> int:
    return max(0, min(7, round(_finite_unit(value) * 7)))


def _pattern_key(vector: Mapping[str, float]) -> tuple[tuple[str, int], ...]:
    return tuple(
        sorted(
            (str(actuator_id), _quantize(value))
            for actuator_id, value in vector.items()
            if value >= 0.08
        )
    )


@dataclass(slots=True)
class _RunningStat:
    count: int = 0
    mean: float = 0.0
    m2: float = 0.0

    def observe(self, value: float) -> None:
        self.count += 1
        delta = value - self.mean
        self.mean += delta / self.count
        self.m2 += delta * (value - self.mean)

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
            count=int(payload.get("count", 0)),
            mean=float(payload.get("mean", 0.0)),
            m2=float(payload.get("m2", 0.0)),
        )


@dataclass(frozen=True, slots=True)
class MotorPrimitive:
    primitive_id: str
    pattern: tuple[tuple[str, int], ...]
    duration_ticks: int
    samples: int
    effect_mean: float
    effect_variance: float
    controllability: float
    verification_count: int = 0

    def intents(self) -> tuple[MotorIntent, ...]:
        return tuple(
            MotorIntent(actuator_id=actuator_id, activation=level / 7.0)
            for actuator_id, level in self.pattern
            if level > 0
        )

    def checkpoint(self) -> dict[str, object]:
        return {
            "primitive_id": self.primitive_id,
            "pattern": [[aid, level] for aid, level in self.pattern],
            "duration_ticks": self.duration_ticks,
            "samples": self.samples,
            "effect_mean": self.effect_mean,
            "effect_variance": self.effect_variance,
            "controllability": self.controllability,
            "verification_count": self.verification_count,
        }

    @classmethod
    def restore(cls, payload: Mapping[str, object]) -> "MotorPrimitive":
        raw_pattern = payload.get("pattern", [])
        if not isinstance(raw_pattern, list):
            raise ValueError("invalid primitive pattern")
        pattern = tuple((str(item[0]), int(item[1])) for item in raw_pattern)
        return cls(
            primitive_id=str(payload["primitive_id"]),
            pattern=pattern,
            duration_ticks=int(payload["duration_ticks"]),
            samples=int(payload["samples"]),
            effect_mean=float(payload["effect_mean"]),
            effect_variance=float(payload["effect_variance"]),
            controllability=float(payload["controllability"]),
            verification_count=int(payload.get("verification_count", 0)),
        )


@dataclass(frozen=True, slots=True)
class SensorimotorSnapshot:
    babbling_coverage: float
    known_patterns: int
    primitives: int
    best_controllability: float
    replay_active: bool
    replay_primitive_id: str | None
    horizon_samples: tuple[tuple[int, int], ...]


@dataclass(slots=True)
class _Frame:
    tick: int
    body_state: dict[str, float]
    motor_vector: dict[str, float]


class SensorimotorLearner:
    """Semantic-free developmental motor learner.

    It provides correlated multi-channel babbling over the body's existing
    actuator constitution, learns reproducibility of body-state consequences at
    several horizons, and consolidates sufficiently repeatable held patterns
    into opaque motor primitives.
    """

    def __init__(
        self,
        actuator_ids: Sequence[str],
        *,
        organism_id: str,
        max_concurrent: int = 4,
        smoothing: float = 0.28,
    ) -> None:
        ids = tuple(str(value) for value in actuator_ids)
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("sensorimotor learner requires unique actuator ids")
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be positive")
        self._ids = ids
        self._organism_id = str(organism_id)
        self._max_concurrent = min(int(max_concurrent), len(ids))
        self._smoothing = float(smoothing)
        self._levels = {aid: 0.0 for aid in ids}
        self._use_counts = {aid: 0 for aid in ids}
        self._babble_epoch = -1
        self._babble_ids: tuple[str, ...] = ()
        self._frames: deque[_Frame] = deque(maxlen=max(_HORIZONS) + 2)
        self._horizon_stats: dict[
            tuple[int, tuple[tuple[str, int], ...]], _RunningStat
        ] = {}
        self._primitive_stats: dict[tuple[tuple[str, int], ...], _RunningStat] = {}
        self._horizon_counts = {h: 0 for h in _HORIZONS}
        self._primitives: dict[str, MotorPrimitive] = {}
        self._hold_pattern: tuple[tuple[str, int], ...] | None = None
        self._hold_ticks = 0
        self._hold_start_state: dict[str, float] | None = None
        self._replay_id: str | None = None
        self._replay_remaining = 0

    @property
    def primitives(self) -> tuple[MotorPrimitive, ...]:
        return tuple(sorted(self._primitives.values(), key=lambda item: item.primitive_id))

    @property
    def babbling_coverage(self) -> float:
        used = sum(1 for count in self._use_counts.values() if count > 0)
        return used / len(self._use_counts)

    def _hash_unit(self, actuator_id: str, epoch: int) -> float:
        digest = hashlib.sha256(
            f"sensorimotor-babble:{self._organism_id}:{actuator_id}:{epoch}".encode("utf-8")
        ).digest()
        return int.from_bytes(digest[:8], "big") / float((1 << 64) - 1)

    def _target_for(self, actuator_id: str, tick: int) -> float:
        epoch = tick // 8
        raw = self._hash_unit(actuator_id, epoch)
        # Bias toward moderate activations so babbling moves the body without
        # spending most of development at saturation.
        return 0.15 + 0.70 * raw

    def _babble_vector(self, tick: int) -> dict[str, float]:
        # Choose a body-wide synergy only at epoch boundaries, then hold that
        # channel set while activation evolves smoothly. This creates temporal
        # structure without supplying any experimenter-authored gait.
        epoch = tick // 8
        if epoch != self._babble_epoch or not self._babble_ids:
            scored = [
                (
                    self._use_counts[actuator_id],
                    -self._hash_unit(actuator_id, epoch),
                    actuator_id,
                )
                for actuator_id in self._ids
            ]
            self._babble_ids = tuple(
                item[2] for item in sorted(scored)[: self._max_concurrent]
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

    def _should_replay(self, tick: int) -> bool:
        if not self._primitives:
            return False
        digest = hashlib.sha256(
            f"sensorimotor-replay:{self._organism_id}:{tick // 16}".encode("utf-8")
        ).digest()
        return digest[0] < 24  # sparse endogenous verification, ~9%

    def motor_intents(self, tick: int) -> tuple[MotorIntent, ...]:
        if self._replay_id is not None and self._replay_remaining > 0:
            primitive = self._primitives.get(self._replay_id)
            if primitive is not None:
                self._replay_remaining -= 1
                if self._replay_remaining <= 0:
                    self._replay_id = None
                return primitive.intents()[: self._max_concurrent]
            self._replay_id = None
            self._replay_remaining = 0

        if self._should_replay(tick):
            primitive = min(
                self._primitives.values(),
                key=lambda item: (item.verification_count, -item.controllability, item.primitive_id),
            )
            self._replay_id = primitive.primitive_id
            self._replay_remaining = primitive.duration_ticks - 1
            self._primitives[primitive.primitive_id] = MotorPrimitive(
                primitive_id=primitive.primitive_id,
                pattern=primitive.pattern,
                duration_ticks=primitive.duration_ticks,
                samples=primitive.samples,
                effect_mean=primitive.effect_mean,
                effect_variance=primitive.effect_variance,
                controllability=primitive.controllability,
                verification_count=primitive.verification_count + 1,
            )
            return primitive.intents()[: self._max_concurrent]

        vector = self._babble_vector(tick)
        return tuple(
            MotorIntent(actuator_id=aid, activation=value)
            for aid, value in sorted(vector.items())
        )

    @staticmethod
    def _body_delta(before: Mapping[str, float], after: Mapping[str, float]) -> float:
        shared = set(before) & set(after)
        if not shared:
            return 0.0
        deltas = [abs(float(after[key]) - float(before[key])) for key in shared]
        return sum(deltas) / len(deltas)

    def observe(
        self,
        *,
        tick: int,
        body_state: Mapping[str, float],
        motor_vector: Mapping[str, float],
    ) -> None:
        frame = _Frame(
            tick=int(tick),
            body_state={str(k): float(v) for k, v in body_state.items()},
            motor_vector={str(k): _finite_unit(v) for k, v in motor_vector.items()},
        )
        self._frames.append(frame)

        frames = list(self._frames)
        for horizon in _HORIZONS:
            if len(frames) <= horizon:
                continue
            previous = frames[-horizon - 1]
            if not previous.motor_vector:
                continue
            effect = self._body_delta(previous.body_state, frame.body_state)
            pattern = _pattern_key(previous.motor_vector)
            if not pattern:
                continue
            stat = self._horizon_stats.setdefault((horizon, pattern), _RunningStat())
            stat.observe(effect)
            self._horizon_counts[horizon] += 1
            if len(self._horizon_stats) > _MAX_HORIZON_STATS:
                retained = sorted(
                    self._horizon_stats.items(),
                    key=lambda item: (-item[1].count, item[0]),
                )[:_MAX_HORIZON_STATS]
                self._horizon_stats = dict(retained)

        current_pattern = _pattern_key(frame.motor_vector)
        if current_pattern and current_pattern == self._hold_pattern:
            self._hold_ticks += 1
        else:
            self._hold_pattern = current_pattern or None
            self._hold_ticks = 1 if current_pattern else 0
            self._hold_start_state = dict(frame.body_state) if current_pattern else None

        if (
            self._hold_pattern
            and self._hold_start_state is not None
            and self._hold_ticks == _PATTERN_HOLD_TICKS
        ):
            effect = self._body_delta(self._hold_start_state, frame.body_state)
            stat = self._primitive_stats.setdefault(self._hold_pattern, _RunningStat())
            stat.observe(effect)
            if len(self._primitive_stats) > _MAX_PRIMITIVE_STATS:
                retained_stats = sorted(
                    self._primitive_stats.items(),
                    key=lambda item: (-item[1].count, -item[1].mean, item[0]),
                )[:_MAX_PRIMITIVE_STATS]
                self._primitive_stats = dict(retained_stats)
            if stat.count >= _MIN_PRIMITIVE_SAMPLES:
                reproducibility = 1.0 / (1.0 + 25.0 * stat.variance)
                controllability = max(0.0, stat.mean) * reproducibility
                if controllability > 0.002:
                    digest = hashlib.sha256(
                        repr(self._hold_pattern).encode("utf-8")
                    ).hexdigest()[:16]
                    primitive_id = f"primitive.{digest}"
                    candidate = MotorPrimitive(
                        primitive_id=primitive_id,
                        pattern=self._hold_pattern,
                        duration_ticks=_PATTERN_HOLD_TICKS,
                        samples=stat.count,
                        effect_mean=stat.mean,
                        effect_variance=stat.variance,
                        controllability=controllability,
                        verification_count=self._primitives.get(
                            primitive_id,
                            MotorPrimitive(
                                primitive_id, (), 1, 0, 0.0, 0.0, 0.0
                            ),
                        ).verification_count,
                    )
                    self._primitives[primitive_id] = candidate
                    if len(self._primitives) > _MAX_PRIMITIVES:
                        retained = sorted(
                            self._primitives.values(),
                            key=lambda item: (-item.controllability, -item.samples, item.primitive_id),
                        )[:_MAX_PRIMITIVES]
                        self._primitives = {
                            item.primitive_id: item for item in retained
                        }

    def snapshot(self) -> SensorimotorSnapshot:
        best = max((item.controllability for item in self._primitives.values()), default=0.0)
        return SensorimotorSnapshot(
            babbling_coverage=self.babbling_coverage,
            known_patterns=len({
                pattern for _horizon, pattern in self._horizon_stats
            } | set(self._primitive_stats)),
            primitives=len(self._primitives),
            best_controllability=float(best),
            replay_active=self._replay_id is not None,
            replay_primitive_id=self._replay_id,
            horizon_samples=tuple((h, self._horizon_counts[h]) for h in _HORIZONS),
        )

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "actuator_ids": list(self._ids),
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
                for (horizon, pattern), stat in sorted(self._horizon_stats.items())
            ],
            "primitive_stats": [
                {
                    "pattern": [[aid, level] for aid, level in pattern],
                    "stat": stat.checkpoint(),
                }
                for pattern, stat in sorted(self._primitive_stats.items())
            ],
            "horizon_counts": {str(h): count for h, count in self._horizon_counts.items()},
            "primitives": [item.checkpoint() for item in self.primitives],
            "hold_pattern": (
                [[aid, level] for aid, level in self._hold_pattern]
                if self._hold_pattern is not None else None
            ),
            "hold_ticks": self._hold_ticks,
            "replay_id": self._replay_id,
            "replay_remaining": self._replay_remaining,
        }

    @classmethod
    def restore(
        cls,
        payload: Mapping[str, object],
        *,
        actuator_ids: Sequence[str],
        organism_id: str,
    ) -> "SensorimotorLearner":
        if int(payload.get("schema_version", -1)) != 1:
            raise ValueError("unsupported sensorimotor checkpoint")
        learner = cls(actuator_ids, organism_id=organism_id)
        expected = tuple(str(value) for value in actuator_ids)
        stored = tuple(str(value) for value in payload.get("actuator_ids", []))
        if stored != expected:
            raise ValueError("sensorimotor actuator constitution mismatch")

        levels = payload.get("levels", {})
        counts = payload.get("use_counts", {})
        if isinstance(levels, Mapping):
            learner._levels = {aid: _finite_unit(float(levels.get(aid, 0.0))) for aid in expected}
        if isinstance(counts, Mapping):
            learner._use_counts = {aid: max(0, int(counts.get(aid, 0))) for aid in expected}

        learner._babble_epoch = int(payload.get("babble_epoch", -1))
        raw_babble_ids = payload.get("babble_ids", [])
        if isinstance(raw_babble_ids, list):
            restored_ids = tuple(str(value) for value in raw_babble_ids)
            if all(value in expected for value in restored_ids):
                learner._babble_ids = restored_ids[: learner._max_concurrent]

        raw_horizon_stats = payload.get("horizon_stats", [])
        if isinstance(raw_horizon_stats, list):
            for item in raw_horizon_stats:
                if not isinstance(item, Mapping):
                    continue
                horizon = int(item.get("horizon", 0))
                if horizon not in _HORIZONS:
                    continue
                raw_pattern = item.get("pattern", [])
                pattern = tuple((str(pair[0]), int(pair[1])) for pair in raw_pattern)
                if not all(aid in expected for aid, _ in pattern):
                    continue
                raw_stat = item.get("stat", {})
                if isinstance(raw_stat, Mapping):
                    learner._horizon_stats[(horizon, pattern)] = _RunningStat.restore(raw_stat)

        raw_primitive_stats = payload.get("primitive_stats", [])
        if isinstance(raw_primitive_stats, list):
            for item in raw_primitive_stats:
                if not isinstance(item, Mapping):
                    continue
                raw_pattern = item.get("pattern", [])
                pattern = tuple((str(pair[0]), int(pair[1])) for pair in raw_pattern)
                if not all(aid in expected for aid, _ in pattern):
                    continue
                raw_stat = item.get("stat", {})
                if isinstance(raw_stat, Mapping):
                    learner._primitive_stats[pattern] = _RunningStat.restore(raw_stat)

        raw_horizons = payload.get("horizon_counts", {})
        if isinstance(raw_horizons, Mapping):
            learner._horizon_counts = {
                h: max(0, int(raw_horizons.get(str(h), 0))) for h in _HORIZONS
            }

        raw_primitives = payload.get("primitives", [])
        if isinstance(raw_primitives, list):
            for item in raw_primitives[:_MAX_PRIMITIVES]:
                if not isinstance(item, Mapping):
                    continue
                primitive = MotorPrimitive.restore(item)
                if all(aid in expected for aid, _ in primitive.pattern):
                    learner._primitives[primitive.primitive_id] = primitive

        raw_hold = payload.get("hold_pattern")
        if isinstance(raw_hold, list):
            learner._hold_pattern = tuple((str(pair[0]), int(pair[1])) for pair in raw_hold)
        learner._hold_ticks = max(0, int(payload.get("hold_ticks", 0)))
        replay_id = payload.get("replay_id")
        learner._replay_id = str(replay_id) if isinstance(replay_id, str) else None
        learner._replay_remaining = max(0, int(payload.get("replay_remaining", 0)))
        return learner


__all__ = [
    "MotorPrimitive",
    "SensorimotorLearner",
    "SensorimotorSnapshot",
]
