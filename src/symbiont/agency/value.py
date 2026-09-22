"""Outcome-value ledger for L8 Prospective Agency.

Maps opaque outcome tokens to endogenous historical value derived
exclusively from homeostatic deviation changes. No environmental,
semantic, or evaluator-supplied signals appear here.

Signal of interest:
    baseline_homeostatic_deviation - later_homeostatic_deviation

Positive value → outcome historically improved physiological state.
Negative value → outcome historically worsened physiological state.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .types import OutcomeValueEstimate

MAX_OUTCOME_VALUES = 256

# Confidence saturates at this many samples
_CONFIDENCE_SATURATION_SAMPLES = 16


@dataclass(slots=True)
class OutcomeValueStat:
    """Online Welford statistics for one outcome token's historical value."""

    samples: int
    mean: float
    m2: float  # Welford's running sum of squared deviations
    positive: int  # count of positive-value observations
    negative: int  # count of negative-value observations
    last_tick: int  # tick of most recent observation for eviction ordering

    def update(self, value: float) -> None:
        """Welford online update — never call with NaN/Inf (caller must guard)."""
        self.samples += 1
        delta = value - self.mean
        self.mean += delta / self.samples
        delta2 = value - self.mean
        self.m2 += delta * delta2
        if value > 0.0:
            self.positive += 1
        elif value < 0.0:
            self.negative += 1

    @property
    def variance(self) -> float:
        """Bessel-corrected sample variance; 0.0 when fewer than 2 samples."""
        if self.samples < 2:
            return 0.0
        return self.m2 / (self.samples - 1)

    def to_estimate(self, outcome_id: str) -> OutcomeValueEstimate:
        confidence = min(1.0, self.samples / float(_CONFIDENCE_SATURATION_SAMPLES))
        return OutcomeValueEstimate(
            outcome_id=outcome_id,
            samples=self.samples,
            mean_value=self.mean,
            variance=self.variance,
            confidence=max(1e-9, confidence),
        )

    def checkpoint(self) -> dict[str, object]:
        return {
            "samples": self.samples,
            "mean": self.mean,
            "m2": self.m2,
            "positive": self.positive,
            "negative": self.negative,
            "last_tick": self.last_tick,
        }

    @classmethod
    def restore(cls, payload: dict[str, Any]) -> "OutcomeValueStat":
        def _int(v: object, name: str, minimum: int = 0) -> int:
            if isinstance(v, bool) or not isinstance(v, int) or v < minimum:
                raise ValueError(f"invalid {name} in outcome-value stat: {v!r}")
            return int(v)

        def _float(v: object, name: str) -> float:
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise ValueError(f"invalid {name} in outcome-value stat")
            if not math.isfinite(float(v)):
                raise ValueError(f"{name} must be finite in outcome-value stat")
            return float(v)

        return cls(
            samples=_int(payload.get("samples", 0), "samples", minimum=1),
            mean=_float(payload.get("mean", 0.0), "mean"),
            m2=_float(payload.get("m2", 0.0), "m2"),
            positive=_int(payload.get("positive", 0), "positive"),
            negative=_int(payload.get("negative", 0), "negative"),
            last_tick=_int(payload.get("last_tick", 0), "last_tick"),
        )


class OutcomeValueLedger:
    """Learn historical endogenous value of opaque outcome tokens.

    Each observed (outcome_id, intrinsic_value) pair updates Welford running
    statistics. The intrinsic value must be pre-computed outside this class as:

        baseline_homeostatic_deviation - later_homeostatic_deviation

    Nothing here knows about resources, locomotion, or evaluator metrics.
    Eviction is purely evidence- and recency-based (never semantic).
    """

    _SCHEMA_VERSION = 1

    def __init__(self) -> None:
        self._stats: dict[str, OutcomeValueStat] = {}

    @property
    def known_outcome_count(self) -> int:
        return len(self._stats)

    def observe(
        self,
        outcome_id: str,
        intrinsic_value: float,
        *,
        tick: int,
    ) -> None:
        """Record one intrinsic-value observation for an outcome token.

        Silently rejects NaN, Inf, or out-of-range values to prevent
        poisoning the running statistics.
        """
        if (
            not isinstance(outcome_id, str)
            or not outcome_id
            or len(outcome_id) > 128
        ):
            raise ValueError("outcome_id must be a bounded non-empty string")
        if (
            isinstance(intrinsic_value, bool)
            or not isinstance(intrinsic_value, (int, float))
            or not math.isfinite(float(intrinsic_value))
        ):
            # Silently discard non-finite observations; they must not corrupt
            # the Welford accumulator.
            return
        if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
            raise ValueError("tick must be a non-negative integer")

        value = float(intrinsic_value)
        # Clamp to [-1, 1] — same range as homeostatic deviation difference
        value = max(-1.0, min(1.0, value))

        stat = self._stats.get(outcome_id)
        if stat is None:
            # Enforce capacity before creating a new entry
            if len(self._stats) >= MAX_OUTCOME_VALUES:
                self._evict_one()
            stat = OutcomeValueStat(
                samples=0,
                mean=0.0,
                m2=0.0,
                positive=0,
                negative=0,
                last_tick=tick,
            )
            self._stats[outcome_id] = stat

        stat.update(value)
        stat.last_tick = tick

    def _evict_one(self) -> None:
        """Remove the weakest outcome entry by evidence count, then recency."""
        if not self._stats:
            return
        # Evict by (fewest samples, oldest last_tick) — never by semantics
        worst_key = min(
            self._stats,
            key=lambda k: (self._stats[k].samples, self._stats[k].last_tick, k),
        )
        del self._stats[worst_key]

    def estimate(self, outcome_id: str) -> OutcomeValueEstimate | None:
        """Return an estimate for the outcome, or None if unknown."""
        stat = self._stats.get(outcome_id)
        if stat is None or stat.samples < 1:
            return None
        return stat.to_estimate(outcome_id)

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": self._SCHEMA_VERSION,
            "stats": {
                outcome_id: stat.checkpoint()
                for outcome_id, stat in self._stats.items()
            },
        }

    @classmethod
    def restore(cls, payload: object) -> "OutcomeValueLedger":
        """Restore from a checkpoint payload. Fails closed on schema mismatch."""
        if not isinstance(payload, dict):
            raise ValueError("invalid outcome-value ledger checkpoint")
        version = payload.get("schema_version")
        if version != cls._SCHEMA_VERSION:
            raise ValueError(
                f"unsupported outcome-value ledger schema version: {version!r}"
            )
        raw_stats = payload.get("stats", {})
        if not isinstance(raw_stats, dict):
            raise ValueError("invalid outcome-value ledger stats checkpoint")

        ledger = cls()
        for outcome_id, raw_stat in raw_stats.items():
            if not isinstance(outcome_id, str) or not isinstance(raw_stat, dict):
                raise ValueError("invalid outcome-value stat entry")
            if len(ledger._stats) >= MAX_OUTCOME_VALUES:
                break
            try:
                ledger._stats[outcome_id] = OutcomeValueStat.restore(raw_stat)
            except (ValueError, TypeError, KeyError):
                # Skip corrupted individual entries; do not abort full restore
                continue
        return ledger


__all__ = [
    "MAX_OUTCOME_VALUES",
    "OutcomeValueStat",
    "OutcomeValueLedger",
]
