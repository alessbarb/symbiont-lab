"""Endogenous valuation of newly perceived information (v0.61).

Only organism-produced signals are accepted: novelty, surprise, attention,
reliability and a bounded acquisition cost.  No evaluator label or semantic
host meaning enters the decision.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class AssimilationAction(StrEnum):
    INCORPORATE = "incorporate"
    DEFER = "defer"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class AssimilationDecision:
    utility: float
    action: AssimilationAction


class InformationAssimilator:
    """Bounded endogenous information valuation with no external labels."""

    SCHEMA_VERSION = 1

    def __init__(self, *, incorporate_threshold: float = 0.60,
                 defer_threshold: float = 0.30, max_deferred: int = 64,
                 assimilated: int = 0, rejected: int = 0, deferred: int = 0) -> None:
        if not 0.0 <= defer_threshold < incorporate_threshold <= 1.0:
            raise ValueError("thresholds must satisfy 0 <= defer < incorporate <= 1")
        if max_deferred < 1:
            raise ValueError("max_deferred must be positive")
        self.incorporate_threshold = incorporate_threshold
        self.defer_threshold = defer_threshold
        self.max_deferred = max_deferred
        self.assimilated = assimilated
        self.rejected = rejected
        self.deferred = min(deferred, max_deferred)

    def evaluate(self, *, novelty: float, surprise: float, attention: float,
                 reliability: float, cost: float = 0.0) -> AssimilationDecision:
        values = (novelty, surprise, attention, reliability, cost)
        if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not 0.0 <= float(v) <= 1.0 for v in values):
            raise ValueError("assimilation inputs must be finite values in [0, 1]")
        utility = max(0.0, min(1.0, 0.30 * novelty + 0.25 * surprise + 0.20 * attention + 0.30 * reliability - 0.15 * cost))
        if utility >= self.incorporate_threshold:
            action = AssimilationAction.INCORPORATE
            self.assimilated += 1
        elif utility >= self.defer_threshold and self.deferred < self.max_deferred:
            action = AssimilationAction.DEFER
            self.deferred += 1
        else:
            action = AssimilationAction.REJECT
            self.rejected += 1
        return AssimilationDecision(utility, action)

    def checkpoint(self) -> dict[str, Any]:
        return {"schema_version": self.SCHEMA_VERSION, "incorporate_threshold": self.incorporate_threshold,
                "defer_threshold": self.defer_threshold, "max_deferred": self.max_deferred,
                "assimilated": self.assimilated, "rejected": self.rejected, "deferred": self.deferred}

    @classmethod
    def from_checkpoint(cls, payload: dict[str, Any]) -> "InformationAssimilator":
        if not isinstance(payload, dict) or payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("invalid assimilation checkpoint")
        return cls(**{key: payload[key] for key in ("incorporate_threshold", "defer_threshold", "max_deferred", "assimilated", "rejected", "deferred")})


__all__ = ["AssimilationAction", "AssimilationDecision", "InformationAssimilator"]
