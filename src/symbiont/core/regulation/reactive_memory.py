"""Bounded memory of acquired fast protective motor consequences."""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReactiveAssociation:
    signature: str
    primitive_id: str
    samples: int
    relief_mean: float
    relief_variance: float

    @property
    def reliable(self) -> bool:
        return (
            self.samples >= 2
            and self.relief_mean >= 0.03
            and self.relief_variance <= 0.04
        )


@dataclass(slots=True)
class _Stat:
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
        return 0.0 if self.count < 2 else self.m2 / (self.count - 1)


class ReactiveMemory:
    """Learn which already-discovered primitives rapidly reduce pressure."""

    SCHEMA_VERSION = 1
    MAX_ASSOCIATIONS = 128

    def __init__(self) -> None:
        self._stats: dict[tuple[str, str], _Stat] = {}

    def observe(self, *, signature: str, primitive_id: str, relief: float) -> None:
        if not signature or not primitive_id:
            return
        if not isinstance(relief, (int, float)) or isinstance(relief, bool):
            return
        value = float(relief)
        if not math.isfinite(value):
            return
        key = (str(signature), str(primitive_id))
        stat = self._stats.setdefault(key, _Stat())
        stat.observe(max(-1.0, min(1.0, value)))
        if len(self._stats) > self.MAX_ASSOCIATIONS:
            ranked = sorted(
                self._stats.items(),
                key=lambda item: (
                    -(item[1].count >= 2),
                    -item[1].mean,
                    -item[1].count,
                    item[0],
                ),
            )[: self.MAX_ASSOCIATIONS]
            self._stats = dict(ranked)

    def associations(self) -> tuple[ReactiveAssociation, ...]:
        return tuple(
            ReactiveAssociation(
                signature=signature,
                primitive_id=primitive_id,
                samples=stat.count,
                relief_mean=stat.mean,
                relief_variance=stat.variance,
            )
            for (signature, primitive_id), stat in sorted(self._stats.items())
        )

    def best(self, *, signature: str, candidates: tuple[str, ...]) -> str | None:
        allowed = set(candidates)
        eligible = [
            assoc
            for assoc in self.associations()
            if assoc.signature == signature
            and assoc.primitive_id in allowed
            and assoc.reliable
        ]
        if not eligible:
            return None
        eligible.sort(
            key=lambda item: (
                -item.relief_mean,
                item.relief_variance,
                -item.samples,
                item.primitive_id,
            )
        )
        return eligible[0].primitive_id

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "associations": [
                {
                    "signature": signature,
                    "primitive_id": primitive_id,
                    "count": stat.count,
                    "mean": stat.mean,
                    "m2": stat.m2,
                }
                for (signature, primitive_id), stat in sorted(self._stats.items())
            ],
        }

    @classmethod
    def restore(cls, payload: object) -> "ReactiveMemory":
        if not isinstance(payload, dict) or payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("invalid reactive memory checkpoint")
        items = payload.get("associations", [])
        if not isinstance(items, list) or len(items) > cls.MAX_ASSOCIATIONS:
            raise ValueError("invalid reactive associations")
        obj = cls()
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("invalid reactive association")
            signature = item.get("signature")
            primitive_id = item.get("primitive_id")
            count = item.get("count")
            mean = item.get("mean")
            m2 = item.get("m2")
            if (
                not isinstance(signature, str) or not signature
                or not isinstance(primitive_id, str) or not primitive_id
                or isinstance(count, bool) or not isinstance(count, int) or count < 1
                or isinstance(mean, bool) or not isinstance(mean, (int, float))
                or isinstance(m2, bool) or not isinstance(m2, (int, float))
                or not math.isfinite(float(mean))
                or not math.isfinite(float(m2))
                or float(m2) < 0.0
            ):
                raise ValueError("invalid reactive association fields")
            obj._stats[(signature, primitive_id)] = _Stat(
                count=count, mean=float(mean), m2=float(m2)
            )
        return obj
