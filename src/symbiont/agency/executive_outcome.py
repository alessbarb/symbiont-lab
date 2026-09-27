"""Executive Outcome Learning v1.1 (docs/design/core/executive-outcome-learning-v1.md).

Real intent outcomes become local executive evidence that modulates future
*admission* of the same (competence, anticipated effect).  v1 also keyed on the
context; that fragmented memory so that almost no admission met its own
history (spec §12-§14), so v1.1 keys on the relation only.  This is executive
experience ("when I recently pursued C->E, did it work?"), kept apart from
physical causal belief ("can C cause E?"):
nothing here writes causal evidence, controllability, agency or competence
evidence, and nothing here is a reward.

Evidence stores facts (samples); the modulation policy is computed at lookup
so it can change without reinterpreting checkpoints.
"""

from __future__ import annotations

import math
from collections import OrderedDict, deque
from dataclasses import asdict, dataclass
from enum import StrEnum
from statistics import fmean
from typing import Any, Mapping

WINDOW = 16
MAX_KEYS = 256

ExecutiveKey = tuple[str, str]  # (competence_id, anticipated_effect_id)


class OutcomeClass(StrEnum):
    POSITIVE = "positive"
    CONTRADICTING = "contradicting"
    TERMINAL = "terminal"
    SUPPRESS = "suppress"
    NEUTRAL = "neutral"


# Reason strings mirror core.domains.intention (agency never imports core).
_POSITIVE = frozenset({"anticipated_effect_observed"})
_CONTRADICTING = frozenset(
    {
        "repeated_high_mismatch",
        "competence_exhausted_without_anticipated_consequence",
        "stagnation",
    }
)
_TERMINAL = frozenset({"controller_terminal_failure", "commitment_terminal_failure"})
_SUPPRESS = frozenset(
    {
        "surface_incompatible",
        "competence_no_longer_executable",
        "required_causal_binding_invalidated",
        "embodiment_changed",
    }
)


def classify_outcome(
    *, status: str, reason: str | None, binding_valid_at_start: bool
) -> OutcomeClass:
    """Map one terminal lifecycle outcome to what it says about C->E (spec §5)."""
    if status == "satisfied" and reason in _POSITIVE:
        return OutcomeClass.POSITIVE
    if status == "failed" and reason in _CONTRADICTING:
        return OutcomeClass.CONTRADICTING
    if status == "failed" and reason in _TERMINAL:
        # A controller that fails on infrastructure that was already invalid
        # says nothing about the competence.
        return OutcomeClass.TERMINAL if binding_valid_at_start else OutcomeClass.NEUTRAL
    if status == "invalidated" and reason in _SUPPRESS:
        return OutcomeClass.SUPPRESS
    return OutcomeClass.NEUTRAL


@dataclass(frozen=True, slots=True)
class ExecutiveOutcomeSample:
    tick: int
    outcome_class: OutcomeClass
    reason: str | None
    effect_similarity: float | None
    prediction_mismatch: float | None
    progress_before_failure: float | None


@dataclass(frozen=True, slots=True)
class SuppressionEvidence:
    """The causal/binding state an invalidation was judged against (spec §7)."""

    invalidated_tick: int
    reason: str
    binding_fingerprint: str | None
    executable: bool
    controllability_revision: int | None
    agency_revision: int | None

    def lifted_by(self, current: "CausalRevisionState") -> bool:
        return (
            current.binding_fingerprint != self.binding_fingerprint
            or current.executable != self.executable
            or current.controllability_revision != self.controllability_revision
            or current.agency_revision != self.agency_revision
        )


@dataclass(frozen=True, slots=True)
class CausalRevisionState:
    """Material causal/binding state of one relation, supplied by the action domain."""

    binding_fingerprint: str | None
    executable: bool
    controllability_revision: int | None
    agency_revision: int | None


class ExecutiveOutcomeEvidence:
    """Facts about one key: its last WINDOW counted outcomes and any suppression."""

    __slots__ = ("samples", "suppression")

    def __init__(self) -> None:
        self.samples: deque[ExecutiveOutcomeSample] = deque(maxlen=WINDOW)
        self.suppression: SuppressionEvidence | None = None

    def _count(self, outcome_class: OutcomeClass) -> int:
        return sum(1 for sample in self.samples if sample.outcome_class is outcome_class)

    @property
    def satisfactions(self) -> int:
        return self._count(OutcomeClass.POSITIVE)

    @property
    def contradicting_failures(self) -> int:
        return self._count(OutcomeClass.CONTRADICTING)

    @property
    def terminal_failures(self) -> int:
        return self._count(OutcomeClass.TERMINAL)

    @property
    def last_failure(self) -> ExecutiveOutcomeSample | None:
        return next(
            (
                sample
                for sample in reversed(self.samples)
                if sample.outcome_class in (OutcomeClass.CONTRADICTING, OutcomeClass.TERMINAL)
            ),
            None,
        )

    @property
    def last_failure_reason(self) -> str | None:
        failure = self.last_failure
        return failure.reason if failure is not None else None

    @property
    def progress_before_failure(self) -> float | None:
        failure = self.last_failure
        return failure.progress_before_failure if failure is not None else None

    @property
    def last_outcome_tick(self) -> int | None:
        return self.samples[-1].tick if self.samples else None

    @property
    def mean_prediction_mismatch(self) -> float | None:
        values = [
            sample.prediction_mismatch
            for sample in self.samples
            if sample.prediction_mismatch is not None
        ]
        return fmean(values) if values else None

    def checkpoint(self) -> dict[str, Any]:
        return {
            "samples": [
                {**asdict(sample), "outcome_class": sample.outcome_class.value}
                for sample in self.samples
            ],
            "suppression": asdict(self.suppression) if self.suppression is not None else None,
        }

    @classmethod
    def restore(cls, payload: Mapping[str, Any]) -> "ExecutiveOutcomeEvidence":
        evidence = cls()
        raw_samples = payload.get("samples", [])
        if not isinstance(raw_samples, list) or len(raw_samples) > WINDOW:
            raise ValueError("invalid or unbounded executive outcome samples")
        for raw in raw_samples:
            values = dict(raw)
            values["outcome_class"] = OutcomeClass(str(values["outcome_class"]))
            if values["outcome_class"] is OutcomeClass.NEUTRAL:
                raise ValueError("neutral outcomes are never executive evidence")
            evidence.samples.append(ExecutiveOutcomeSample(**values))
        raw_suppression = payload.get("suppression")
        if raw_suppression is not None:
            evidence.suppression = SuppressionEvidence(**dict(raw_suppression))
        return evidence


@dataclass(frozen=True, slots=True)
class ExecutiveModulation:
    factor: float
    suppressed: bool
    had_history: bool


NO_HISTORY = ExecutiveModulation(factor=1.0, suppressed=False, had_history=False)


class ExecutiveAdmissionModulator:
    """Policy (spec §6): computed at lookup, never stored."""

    contradicting_weight: float = 1.0
    terminal_weight: float = 2.0
    min_factor: float = 0.5
    max_factor: float = 1.5

    def confidence(self, evidence: ExecutiveOutcomeEvidence) -> float:
        s = evidence.satisfactions
        c = evidence.contradicting_failures
        t = evidence.terminal_failures
        return (1.0 + s) / (2.0 + s + self.contradicting_weight * c + self.terminal_weight * t)

    def factor(self, evidence: ExecutiveOutcomeEvidence) -> float:
        return max(self.min_factor, min(self.max_factor, self.confidence(evidence) / 0.5))


def _key_ref(key: ExecutiveKey) -> list[str]:
    return [key[0], key[1]]


def _merge_into(target: ExecutiveOutcomeEvidence, source: ExecutiveOutcomeEvidence) -> None:
    """v1 -> v1.1: fold context-specific evidence into its (competence, effect) key."""
    merged = sorted((*target.samples, *source.samples), key=lambda sample: sample.tick)
    target.samples.clear()
    target.samples.extend(merged[-WINDOW:])
    candidates = [item for item in (target.suppression, source.suppression) if item is not None]
    target.suppression = max(candidates, key=lambda item: item.invalidated_tick, default=None)


class ExecutiveOutcomeLedger:
    """Bounded executive memory keyed by (competence, anticipated effect)."""

    SCHEMA_VERSION = 2

    def __init__(
        self,
        *,
        max_keys: int = MAX_KEYS,
        modulator: ExecutiveAdmissionModulator | None = None,
    ) -> None:
        if max_keys < 1:
            raise ValueError("max_keys must be positive")
        self.max_keys = int(max_keys)
        self.modulator = modulator or ExecutiveAdmissionModulator()
        self._items: OrderedDict[ExecutiveKey, ExecutiveOutcomeEvidence] = OrderedDict()
        self.keys_created = 0
        self.keys_evicted = 0
        self.lookups = 0
        self.history_hits = 0

    def __len__(self) -> int:
        return len(self._items)

    def get(self, key: ExecutiveKey) -> ExecutiveOutcomeEvidence | None:
        return self._items.get(key)

    def _evidence_for(self, key: ExecutiveKey) -> ExecutiveOutcomeEvidence:
        evidence = self._items.get(key)
        if evidence is None:
            evidence = ExecutiveOutcomeEvidence()
            self._items[key] = evidence
            self.keys_created += 1
        self._items.move_to_end(key)  # least-recently-updated is evicted first
        while len(self._items) > self.max_keys:
            self._items.popitem(last=False)
            self.keys_evicted += 1
        return evidence

    def record(
        self,
        key: ExecutiveKey,
        sample: ExecutiveOutcomeSample,
        *,
        revision: CausalRevisionState | None = None,
    ) -> None:
        """Record one real, non-neutral outcome for ``key``."""
        if sample.outcome_class is OutcomeClass.NEUTRAL:
            raise ValueError("neutral outcomes are never executive evidence")
        evidence = self._evidence_for(key)
        evidence.samples.append(sample)
        if sample.outcome_class is OutcomeClass.SUPPRESS:
            if revision is None:
                raise ValueError(
                    "suppression requires the causal revision state it is judged against"
                )
            evidence.suppression = SuppressionEvidence(
                invalidated_tick=sample.tick,
                reason=str(sample.reason),
                binding_fingerprint=revision.binding_fingerprint,
                executable=revision.executable,
                controllability_revision=revision.controllability_revision,
                agency_revision=revision.agency_revision,
            )

    def modulation(
        self, key: ExecutiveKey, *, revision: CausalRevisionState | None
    ) -> ExecutiveModulation:
        """Admission modulation for one candidate; lifts suppression on relevant revision."""
        self.lookups += 1
        evidence = self._items.get(key)
        if evidence is None:
            return NO_HISTORY
        self.history_hits += 1
        if evidence.suppression is not None:
            if revision is None or not evidence.suppression.lifted_by(revision):
                return ExecutiveModulation(factor=0.0, suppressed=True, had_history=True)
            evidence.suppression = None
        return ExecutiveModulation(
            factor=self.modulator.factor(evidence), suppressed=False, had_history=True
        )

    def metrics(self) -> dict[str, float | int | None]:
        sizes = [len(item.samples) for item in self._items.values()]
        return {
            "keys_created": self.keys_created,
            "keys_evicted": self.keys_evicted,
            "live_keys": len(self._items),
            "single_sample_key_fraction": (
                sum(1 for size in sizes if size == 1) / len(sizes) if sizes else None
            ),
            "mean_samples_per_key": fmean(sizes) if sizes else None,
            "lookups": self.lookups,
            "history_hits": self.history_hits,
            "history_hit_rate": self.history_hits / self.lookups if self.lookups else None,
        }

    def checkpoint(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "entries": [
                {"key": _key_ref(key), **evidence.checkpoint()}
                for key, evidence in self._items.items()
            ],
            "counters": {
                "keys_created": self.keys_created,
                "keys_evicted": self.keys_evicted,
                "lookups": self.lookups,
                "history_hits": self.history_hits,
            },
        }

    @classmethod
    def restore(cls, payload: Mapping[str, Any] | None) -> "ExecutiveOutcomeLedger":
        ledger = cls()
        if payload is None:
            return ledger
        version = payload.get("schema_version")
        if version not in (1, cls.SCHEMA_VERSION):
            raise ValueError("unsupported executive outcome ledger checkpoint")
        entries = payload.get("entries", [])
        if not isinstance(entries, list) or len(entries) > ledger.max_keys:
            raise ValueError("invalid or unbounded executive outcome ledger")
        for raw in entries:
            # v1 keys carried a context as third element; v1.1 folds contexts
            # of one relation together, keeping entry order as recency order.
            key = (str(raw["key"][0]), str(raw["key"][1]))
            evidence = ExecutiveOutcomeEvidence.restore(raw)
            existing = ledger._items.get(key)
            if existing is not None:
                _merge_into(existing, evidence)
                ledger._items.move_to_end(key)
            else:
                ledger._items[key] = evidence
        counters = payload.get("counters", {})
        for name in ("keys_created", "keys_evicted", "lookups", "history_hits"):
            value = int(counters.get(name, 0))
            if value < 0 or not math.isfinite(value):
                raise ValueError("invalid executive outcome counter")
            setattr(ledger, name, value)
        return ledger


__all__ = [
    "CausalRevisionState",
    "ExecutiveAdmissionModulator",
    "ExecutiveKey",
    "ExecutiveModulation",
    "ExecutiveOutcomeEvidence",
    "ExecutiveOutcomeLedger",
    "ExecutiveOutcomeSample",
    "NO_HISTORY",
    "OutcomeClass",
    "SuppressionEvidence",
    "classify_outcome",
]
