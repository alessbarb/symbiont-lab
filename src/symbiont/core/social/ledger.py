from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

LEDGER_CHECKPOINT_SCHEMA_VERSION = 1

from .source_evidence import SourceEvidenceOutcome, SourceEvidenceSample, SourceEvidenceState


@dataclass(frozen=True, slots=True)
class SocialClaim:
    claim_id: str
    source_id: str
    root_evidence_ids: frozenset[str]
    parent_claim_ids: frozenset[str]
    payload: Any  # Native relation representation
    received_tick: int
    freshness: float


@dataclass(slots=True)
class SocialEvidenceLedger:
    claims: dict[str, SocialClaim] = field(default_factory=dict)
    source_states: dict[str, SourceEvidenceState] = field(default_factory=dict)
    reconciliations: dict[str, SourceEvidenceOutcome] = field(default_factory=dict)
    # (source_id, evidence_ref) already counted: replayed evidence is not fresh.
    seen_evidence: set[tuple[str, str]] = field(default_factory=set)

    def receive_claim(self, claim: SocialClaim) -> None:
        if claim.claim_id not in self.claims:
            self.claims[claim.claim_id] = claim
            if claim.source_id not in self.source_states:
                self.source_states[claim.source_id] = SourceEvidenceState(source_id=claim.source_id)

    def assess_claim(self, claim_id: str) -> SourceEvidenceOutcome:
        """Returns the current known assessment for a claim, defaulting to UNRESOLVED."""
        return self.reconciliations.get(claim_id, SourceEvidenceOutcome.UNRESOLVED)

    def record_local_reconciliation(
        self,
        claim_id: str,
        tick: int,
        outcome: SourceEvidenceOutcome,
        compatibility: float,
        quality: float,
        freshness: float,
        evidence_ref: str | None,
    ) -> None:
        """Record real empirical validation against a social claim."""
        if claim_id not in self.claims:
            raise ValueError(f"Unknown claim: {claim_id}")

        claim = self.claims[claim_id]
        if evidence_ref is not None:
            key = (claim.source_id, evidence_ref)
            if key in self.seen_evidence:
                return
            self.seen_evidence.add(key)
        self.reconciliations[claim_id] = outcome

        sample = SourceEvidenceSample(
            tick=tick,
            outcome=outcome,
            compatibility=compatibility,
            quality=quality,
            freshness=freshness,
            independence=1.0,  # Could be derived from root_evidence_ids
            evidence_ref=evidence_ref,
        )
        self.source_states[claim.source_id].add_sample(sample)

    def checkpoint(self) -> dict[str, Any]:
        """Serialize acquired social knowledge (Longitudinal Integrity v1 §7.2).

        INTERIM: this ledger overlaps the modeled social ledger (audit LI-05).
        The field exists so received claims do not vanish on restart while the
        ARCH-1 ownership decision is pending; it must not become a permanent
        second source of truth.
        """
        return {
            "schema_version": LEDGER_CHECKPOINT_SCHEMA_VERSION,
            "claims": [
                {
                    "claim_id": claim.claim_id,
                    "source_id": claim.source_id,
                    "root_evidence_ids": sorted(claim.root_evidence_ids),
                    "parent_claim_ids": sorted(claim.parent_claim_ids),
                    "payload": claim.payload,
                    "received_tick": claim.received_tick,
                    "freshness": claim.freshness,
                }
                for claim in self.claims.values()
            ],
            "source_states": [
                {
                    "source_id": state.source_id,
                    "samples": [
                        {
                            "tick": sample.tick,
                            "outcome": sample.outcome.value,
                            "compatibility": sample.compatibility,
                            "quality": sample.quality,
                            "freshness": sample.freshness,
                            "independence": sample.independence,
                            "evidence_ref": sample.evidence_ref,
                        }
                        for sample in state.samples
                    ],
                    "independent_roots": state.independent_roots,
                }
                for state in self.source_states.values()
            ],
            "reconciliations": {
                claim_id: outcome.value for claim_id, outcome in self.reconciliations.items()
            },
            "seen_evidence": sorted([source, ref] for source, ref in self.seen_evidence),
        }

    @classmethod
    def restore(cls, payload: Any) -> "SocialEvidenceLedger":
        """Rebuild a ledger from :meth:`checkpoint`; ``None`` is an empty ledger."""
        if payload is None:
            return cls()
        if (
            not isinstance(payload, dict)
            or payload.get("schema_version") != LEDGER_CHECKPOINT_SCHEMA_VERSION
        ):
            raise ValueError("unsupported checkpoint schema")
        raw_claims = payload.get("claims", [])
        raw_states = payload.get("source_states", [])
        raw_reconciliations = payload.get("reconciliations", {})
        raw_seen = payload.get("seen_evidence", [])
        if (
            not isinstance(raw_claims, list)
            or not isinstance(raw_states, list)
            or not isinstance(raw_reconciliations, dict)
            or not isinstance(raw_seen, list)
        ):
            raise ValueError("malformed checkpoint collections")

        ledger = cls()
        for item in raw_claims:
            if not isinstance(item, dict):
                raise ValueError("claim must be an object")
            claim = SocialClaim(
                claim_id=_text(item.get("claim_id"), "claim_id"),
                source_id=_text(item.get("source_id"), "source_id"),
                root_evidence_ids=frozenset(_texts(item.get("root_evidence_ids"), "roots")),
                parent_claim_ids=frozenset(_texts(item.get("parent_claim_ids"), "parents")),
                payload=item.get("payload"),
                received_tick=_count(item.get("received_tick"), "received_tick"),
                freshness=_unit(item.get("freshness"), "freshness"),
            )
            if claim.claim_id in ledger.claims:
                raise ValueError("duplicate claim")
            ledger.claims[claim.claim_id] = claim
        for item in raw_states:
            if not isinstance(item, dict) or not isinstance(item.get("samples"), list):
                raise ValueError("source state must be an object with samples")
            state = SourceEvidenceState(source_id=_text(item.get("source_id"), "source_id"))
            for raw_sample in item["samples"]:
                if not isinstance(raw_sample, dict):
                    raise ValueError("sample must be an object")
                evidence_ref = raw_sample.get("evidence_ref")
                state.add_sample(
                    SourceEvidenceSample(
                        tick=_count(raw_sample.get("tick"), "tick"),
                        outcome=SourceEvidenceOutcome(raw_sample.get("outcome")),
                        compatibility=_unit(raw_sample.get("compatibility"), "compatibility"),
                        quality=_unit(raw_sample.get("quality"), "quality"),
                        freshness=_unit(raw_sample.get("freshness"), "freshness"),
                        independence=_unit(raw_sample.get("independence"), "independence"),
                        evidence_ref=(
                            None if evidence_ref is None else _text(evidence_ref, "evidence_ref")
                        ),
                    )
                )
            state.independent_roots = _count(item.get("independent_roots"), "independent_roots")
            if state.source_id in ledger.source_states:
                raise ValueError("duplicate source state")
            ledger.source_states[state.source_id] = state
        for claim in ledger.claims.values():
            if claim.source_id not in ledger.source_states:
                raise ValueError("claim source has no source state")
        for claim_id, outcome in raw_reconciliations.items():
            if claim_id not in ledger.claims:
                raise ValueError("reconciliation references an unknown claim")
            ledger.reconciliations[claim_id] = SourceEvidenceOutcome(outcome)
        for pair in raw_seen:
            if not isinstance(pair, list) or len(pair) != 2:
                raise ValueError("seen evidence must be [source, reference] pairs")
            ledger.seen_evidence.add((_text(pair[0], "source"), _text(pair[1], "reference")))
        return ledger

    def claim_evidence(self, claim_id: str) -> dict[str, Any]:
        """Expose descriptive evidence about a claim."""
        claim = self.claims.get(claim_id)
        if not claim:
            return {}
        return {
            "claim": claim,
            "outcome": self.assess_claim(claim_id),
            "source_reliability": self.source_states[claim.source_id].source_reliability,
        }

    def unresolved_claims(self) -> list[SocialClaim]:
        """Return claims that have no local reconciliation yet."""
        return [
            claim
            for claim_id, claim in self.claims.items()
            if self.assess_claim(claim_id) == SourceEvidenceOutcome.UNRESOLVED
        ]

    def open_questions(self) -> list[SocialQuestion]:
        """Convert unresolved or highly contested claims into SocialQuestions."""
        questions = []
        for claim_id, claim in self.claims.items():
            outcome = self.assess_claim(claim_id)
            if outcome == SourceEvidenceOutcome.UNRESOLVED:
                state = self.source_states[claim.source_id]
                questions.append(
                    SocialQuestion(
                        claim_ref=claim_id,
                        independent_support_roots=state.agreements,
                        independent_contradiction_roots=state.contradictions,
                        unresolved_roots=state.unresolved,
                        compatibility=state.mean_compatibility,
                        freshness=state.mean_freshness,
                        uncertainty=1.0 - state.source_reliability,
                    )
                )
        return questions


@dataclass(slots=True, frozen=True)
class SocialQuestion:
    claim_ref: str
    independent_support_roots: int
    independent_contradiction_roots: int
    unresolved_roots: int
    compatibility: float
    freshness: float
    uncertainty: float


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _texts(value: Any, name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    return [_text(item, name) for item in value]


def _count(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _unit(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError(f"{name} must be within [0, 1]")
    return number
