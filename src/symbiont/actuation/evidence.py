"""Canonical factual evidence for Sensorimotor v2 / Agency Acquisition v1.

The causal subject of a piece of evidence is not necessarily a competence.
Evidence keeps the concrete attempt, the provisional intervention family, the
commitment and (when one exists) the competence simultaneously so that
single-command, multi-tick commitment and recurrent-family analyses all read
the same factual source (§10, §14, §77-§78).

Passive windows — observed bodily change while no command was issued — are
retained separately and bounded so that "does this also happen when I do
nothing?" can be answered without letting idle ticks evict intervention
evidence (§16).
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping, Protocol


@dataclass(frozen=True, slots=True)
class PredictionError:
    magnitude: float
    directional_error: float | None = None
    timing_error: float | None = None
    uncertainty: float = 1.0
    novelty: float = 0.0

    def __post_init__(self) -> None:
        for name in ("magnitude", "uncertainty", "novelty"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class SensorimotorTransition:
    """One observed consequence of one issued MotorCommand."""

    transition_id: str
    tick_start: int
    tick_end: int
    context_ref: str
    commitment_id: str
    controller_id: str
    competence_id: str | None
    attempt_id: str | None
    intervention_signature_id: str | None
    state_before_ref: str
    motor_command_ref: str
    actuation_ref: str
    prediction_ref: str | None
    state_after_ref: str
    observed_effect_id: str | None = None
    prediction_error: PredictionError | None = None
    physiological_delta_ref: str | None = None

    def __post_init__(self) -> None:
        if self.tick_start < 0 or self.tick_end < self.tick_start:
            raise ValueError("invalid transition ticks")
        for value in (
            self.transition_id,
            self.context_ref,
            self.commitment_id,
            self.controller_id,
            self.state_before_ref,
            self.motor_command_ref,
            self.actuation_ref,
            self.state_after_ref,
        ):
            if not value:
                raise ValueError("transition references must not be empty")
        # §13.1: every transition caused by a motor command names its attempt
        # and provisional intervention family.  Passive change never becomes a
        # SensorimotorTransition; it enters the ledger as a passive window.
        if not self.attempt_id or not self.intervention_signature_id:
            raise ValueError("a motor-caused transition requires attempt and signature")
        if self.observed_effect_id is not None and not self.observed_effect_id.startswith(
            "effect."
        ):
            raise ValueError("observed effect must be organism-owned")


@dataclass(frozen=True, slots=True)
class CausalEvidence:
    evidence_id: str

    attempt_id: str | None
    intervention_signature_id: str | None
    commitment_id: str | None
    competence_id: str | None

    effect_id: str | None
    context_ref: str | None

    observation_tick: int

    transition_id: str | None = None
    action_ref: str | None = None
    prior_state_ref: str | None = None
    resulting_state_ref: str | None = None
    prediction_ref: str | None = None
    window_start_tick: int | None = None

    def __post_init__(self) -> None:
        if self.observation_tick < 0:
            raise ValueError("observation_tick must be non-negative")
        if self.action_ref is None and (
            self.attempt_id is not None
            or self.intervention_signature_id is not None
            or self.commitment_id is not None
            or self.competence_id is not None
        ):
            raise ValueError("a passive window cannot name an intervention")

    @property
    def is_passive(self) -> bool:
        """No command was issued: counterfactual (no-intervention) evidence."""
        return self.action_ref is None


# Index keys over which opportunities are counted incrementally.
_COMPETENCE = "competence_id"
_SIGNATURE = "intervention_signature_id"
_COMMITMENT = "commitment_id"
_ATTEMPT = "attempt_id"
_INDEXED_FIELDS = (_COMPETENCE, _SIGNATURE, _COMMITMENT, _ATTEMPT)

Opportunities = tuple[int, int, int, int]


class CausalEvidenceLedger:
    """Single bounded factual source for all sensorimotor inference views.

    Opportunity queries are answered from incrementally maintained counters
    rather than a scan over all retained evidence, so per-tick causal updates
    stay bounded as the ledger fills.
    """

    SCHEMA_VERSION = 3

    def __init__(self, *, capacity: int = 4096, passive_capacity: int | None = None) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        passive = max(1, capacity // 4) if passive_capacity is None else int(passive_capacity)
        if passive < 1:
            raise ValueError("passive_capacity must be positive")
        self._capacity = int(capacity)
        self._passive_capacity = passive
        self._interventions: list[CausalEvidence] = []
        self._passive: list[CausalEvidence] = []
        # (field, value, context|None) -> effect counter / totals
        self._source_effects: dict[tuple[str, str, str | None], Counter[str | None]] = {}
        self._global_effects: dict[str | None, Counter[str | None]] = {}
        self._by_commitment: dict[str, list[CausalEvidence]] = {}

    # -- index maintenance -------------------------------------------------
    def _index(self, item: CausalEvidence, delta: int) -> None:
        contexts: tuple[str | None, ...] = (
            (None,)
            if item.context_ref is None
            else (
                None,
                item.context_ref,
            )
        )
        for context in contexts:
            counter = self._global_effects.setdefault(context, Counter())
            counter[item.effect_id] += delta
            if counter[item.effect_id] <= 0:
                del counter[item.effect_id]
            for field in _INDEXED_FIELDS:
                value = getattr(item, field)
                if value is None:
                    continue
                key = (field, value, context)
                source = self._source_effects.setdefault(key, Counter())
                source[item.effect_id] += delta
                if source[item.effect_id] <= 0:
                    del source[item.effect_id]
                if not source:
                    del self._source_effects[key]
        if item.commitment_id is not None:
            bucket = self._by_commitment.setdefault(item.commitment_id, [])
            if delta > 0:
                bucket.append(item)
            else:
                bucket.remove(item)
                if not bucket:
                    del self._by_commitment[item.commitment_id]

    def _append(self, item: CausalEvidence) -> CausalEvidence:
        store, bound = (
            (self._passive, self._passive_capacity)
            if item.is_passive
            else (self._interventions, self._capacity)
        )
        store.append(item)
        self._index(item, +1)
        while len(store) > bound:
            self._index(store.pop(0), -1)
        return item

    # -- writes -------------------------------------------------------------
    def observe(self, transition: SensorimotorTransition) -> CausalEvidence:
        return self._append(
            CausalEvidence(
                evidence_id=f"causal.{transition.transition_id}",
                attempt_id=transition.attempt_id,
                intervention_signature_id=transition.intervention_signature_id,
                commitment_id=transition.commitment_id,
                competence_id=transition.competence_id,
                effect_id=transition.observed_effect_id,
                context_ref=transition.context_ref,
                observation_tick=transition.tick_end,
                transition_id=transition.transition_id,
                action_ref=transition.motor_command_ref,
                prior_state_ref=transition.state_before_ref,
                resulting_state_ref=transition.state_after_ref,
                prediction_ref=transition.prediction_ref,
                window_start_tick=transition.tick_start,
            )
        )

    def observe_passive_window(
        self,
        *,
        tick_start: int,
        tick_end: int,
        context_ref: str | None,
        prior_state_ref: str,
        resulting_state_ref: str,
        effect_id: str | None,
    ) -> CausalEvidence:
        """Record bodily change observed while no motor command was issued."""
        if tick_start < 0 or tick_end <= tick_start:
            raise ValueError("invalid passive window ticks")
        if effect_id is not None and not effect_id.startswith("effect."):
            raise ValueError("observed effect must be organism-owned")
        digest = hashlib.sha256(
            f"passive:{tick_start}:{tick_end}:{context_ref}:{prior_state_ref}".encode("utf-8")
        ).hexdigest()[:24]
        return self._append(
            CausalEvidence(
                evidence_id=f"causal.passive.{digest}",
                attempt_id=None,
                intervention_signature_id=None,
                commitment_id=None,
                competence_id=None,
                effect_id=effect_id,
                context_ref=context_ref,
                observation_tick=tick_end,
                prior_state_ref=prior_state_ref,
                resulting_state_ref=resulting_state_ref,
                window_start_tick=tick_start,
            )
        )

    # -- read views ---------------------------------------------------------
    @property
    def evidence(self) -> tuple[CausalEvidence, ...]:
        """All retained evidence in observation order (interventions + passive)."""
        return tuple(
            sorted(
                (*self._interventions, *self._passive),
                key=lambda item: (item.observation_tick, item.is_passive, item.evidence_id),
            )
        )

    @property
    def intervention_evidence(self) -> tuple[CausalEvidence, ...]:
        return tuple(self._interventions)

    @property
    def passive_evidence(self) -> tuple[CausalEvidence, ...]:
        return tuple(self._passive)

    def _opportunities(
        self,
        effect_id: str,
        *,
        field: str,
        values: Iterable[str],
        context_ref: str | None,
    ) -> Opportunities:
        """Action opportunities/successes versus every other retained window."""
        action_n = action_success = 0
        for value in dict.fromkeys(values):
            counter = self._source_effects.get((field, value, context_ref))
            if counter:
                action_n += sum(counter.values())
                action_success += counter.get(effect_id, 0)
        global_counter = self._global_effects.get(context_ref, Counter())
        total_n = sum(global_counter.values())
        total_success = global_counter.get(effect_id, 0)
        return action_n, action_success, total_n - action_n, total_success - action_success

    def effect_opportunities(
        self,
        effect_id: str,
        *,
        competence_id: str,
        context_ref: str | None = None,
    ) -> Opportunities:
        """Return action opportunities/successes and alternative opportunities/successes."""
        return self._opportunities(
            effect_id, field=_COMPETENCE, values=(competence_id,), context_ref=context_ref
        )

    def signature_effect_opportunities(
        self,
        effect_id: str,
        *,
        intervention_signature_id: str,
        context_ref: str | None = None,
    ) -> Opportunities:
        return self._opportunities(
            effect_id,
            field=_SIGNATURE,
            values=(intervention_signature_id,),
            context_ref=context_ref,
        )

    def signatures_effect_opportunities(
        self,
        effect_id: str,
        *,
        intervention_signature_ids: tuple[str, ...],
        context_ref: str | None = None,
    ) -> Opportunities:
        """Opportunities of a family of signatures taken jointly (dimension level)."""
        return self._opportunities(
            effect_id,
            field=_SIGNATURE,
            values=intervention_signature_ids,
            context_ref=context_ref,
        )

    def commitment_effect_opportunities(
        self,
        effect_id: str,
        *,
        commitment_id: str,
        context_ref: str | None = None,
    ) -> Opportunities:
        return self._opportunities(
            effect_id, field=_COMMITMENT, values=(commitment_id,), context_ref=context_ref
        )

    def attempt_effect_opportunities(
        self,
        effect_id: str,
        *,
        attempt_id: str,
        context_ref: str | None = None,
    ) -> Opportunities:
        return self._opportunities(
            effect_id, field=_ATTEMPT, values=(attempt_id,), context_ref=context_ref
        )

    def signature_effects(self, intervention_signature_id: str) -> Mapping[str | None, int]:
        """Context-free effect histogram observed after one intervention family."""
        return dict(self._source_effects.get((_SIGNATURE, intervention_signature_id, None), {}))

    def signature_support(self, intervention_signature_id: str) -> int:
        return sum(self.signature_effects(intervention_signature_id).values())

    def signature_evidence_ids(
        self,
        intervention_signature_ids: tuple[str, ...],
        *,
        effect_id: str,
        limit: int = 8,
    ) -> tuple[str, ...]:
        """Most recent factual evidence of these families producing ``effect_id``."""
        members = set(intervention_signature_ids)
        found: list[str] = []
        for item in reversed(self._interventions):
            if item.effect_id == effect_id and item.intervention_signature_id in members:
                found.append(item.evidence_id)
                if len(found) >= limit:
                    break
        return tuple(reversed(found))

    def commitment_evidence(self, commitment_id: str) -> tuple[CausalEvidence, ...]:
        """What happened across one commitment/controller episode (§78)."""
        return tuple(self._by_commitment.get(commitment_id, ()))

    def effect_support(self, effect_id: str) -> int:
        return self._global_effects.get(None, Counter()).get(effect_id, 0)

    # -- persistence --------------------------------------------------------
    @staticmethod
    def _payload(item: CausalEvidence) -> dict[str, object]:
        return {
            "evidence_id": item.evidence_id,
            "attempt_id": item.attempt_id,
            "intervention_signature_id": item.intervention_signature_id,
            "commitment_id": item.commitment_id,
            "competence_id": item.competence_id,
            "effect_id": item.effect_id,
            "context_ref": item.context_ref,
            "observation_tick": item.observation_tick,
            "transition_id": item.transition_id,
            "action_ref": item.action_ref,
            "prior_state_ref": item.prior_state_ref,
            "resulting_state_ref": item.resulting_state_ref,
            "prediction_ref": item.prediction_ref,
            "window_start_tick": item.window_start_tick,
        }

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "capacity": self._capacity,
            "passive_capacity": self._passive_capacity,
            "evidence": [self._payload(item) for item in self._interventions],
            "passive_evidence": [self._payload(item) for item in self._passive],
        }

    @classmethod
    def restore(cls, payload: dict[str, object]) -> "CausalEvidenceLedger":
        """Restore v3, or migrate v1/v2 motor evidence.

        Historical evidence predates attempts and intervention families; those
        identities are left unknown (None) rather than reconstructed.  Every
        historical item carried a motor command, so none becomes passive.
        """
        version = payload.get("schema_version")
        if version not in (1, 2, cls.SCHEMA_VERSION):
            raise ValueError("unsupported causal-evidence checkpoint")
        capacity = int(payload.get("capacity", 4096))
        passive_capacity = payload.get("passive_capacity")
        obj = cls(
            capacity=capacity,
            passive_capacity=(int(passive_capacity) if isinstance(passive_capacity, int) else None),
        )
        raw_items = payload.get("evidence", [])
        raw_passive = payload.get("passive_evidence", []) if version == cls.SCHEMA_VERSION else []
        if not isinstance(raw_items, list) or not isinstance(raw_passive, list):
            raise ValueError("invalid causal evidence")
        for raw, passive in ((raw_items[-obj._capacity :], False), (raw_passive, True)):
            for item in raw:
                if not isinstance(item, dict):
                    raise ValueError("invalid causal evidence item")
                normalized = dict(item)
                if version != cls.SCHEMA_VERSION:
                    if not normalized.get("action_ref"):
                        raise ValueError("historical causal evidence lacks its motor command")
                    normalized.setdefault("competence_id", None)
                    normalized.setdefault("effect_id", None)
                    normalized["attempt_id"] = None
                    normalized["intervention_signature_id"] = None
                    normalized["commitment_id"] = None
                    normalized["window_start_tick"] = None
                evidence = CausalEvidence(**normalized)
                if evidence.is_passive is not passive:
                    raise ValueError("causal evidence stored in the wrong window class")
                obj._append(evidence)
        return obj


class OpportunityView(Protocol):
    """Read-only opportunity queries used by controllability/agency/dimension inference."""

    def effect_opportunities(
        self, effect_id: str, *, competence_id: str, context_ref: str | None = None
    ) -> Opportunities: ...

    def signature_effect_opportunities(
        self,
        effect_id: str,
        *,
        intervention_signature_id: str,
        context_ref: str | None = None,
    ) -> Opportunities: ...

    def signatures_effect_opportunities(
        self,
        effect_id: str,
        *,
        intervention_signature_ids: tuple[str, ...],
        context_ref: str | None = None,
    ) -> Opportunities: ...

    def signature_effects(self, intervention_signature_id: str) -> Mapping[str | None, int]: ...


class CounterfactualFreeView:
    """E1 ablation: the same factual ledger with every counterfactual window hidden.

    Inference through this view sees only what followed the source's own
    interventions, never what happened without them.  It is an experimental
    control, never the organism default.
    """

    def __init__(self, ledger: CausalEvidenceLedger) -> None:
        self._ledger = ledger

    def effect_opportunities(
        self, effect_id: str, *, competence_id: str, context_ref: str | None = None
    ) -> Opportunities:
        action_n, action_hits, _, _ = self._ledger.effect_opportunities(
            effect_id, competence_id=competence_id, context_ref=context_ref
        )
        return action_n, action_hits, 0, 0

    def signature_effect_opportunities(
        self,
        effect_id: str,
        *,
        intervention_signature_id: str,
        context_ref: str | None = None,
    ) -> Opportunities:
        action_n, action_hits, _, _ = self._ledger.signature_effect_opportunities(
            effect_id,
            intervention_signature_id=intervention_signature_id,
            context_ref=context_ref,
        )
        return action_n, action_hits, 0, 0

    def signatures_effect_opportunities(
        self,
        effect_id: str,
        *,
        intervention_signature_ids: tuple[str, ...],
        context_ref: str | None = None,
    ) -> Opportunities:
        action_n, action_hits, _, _ = self._ledger.signatures_effect_opportunities(
            effect_id,
            intervention_signature_ids=intervention_signature_ids,
            context_ref=context_ref,
        )
        return action_n, action_hits, 0, 0

    def signature_effects(self, intervention_signature_id: str) -> Mapping[str | None, int]:
        return self._ledger.signature_effects(intervention_signature_id)
