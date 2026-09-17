from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json


_MAX_CONTEXT_TOKENS = 256
_MAX_OUTCOME_TOKENS = 32
_MAX_EVIDENCE_REFS = 16
_MAX_TOKEN_LENGTH = 96
_MAX_RECORD_ID_LENGTH = 128
_MAX_ORGANISM_ID_LENGTH = 128


class EpistemicStatus(str, Enum):
    OBSERVED = "observed"
    ASSOCIATED = "associated"
    HYPOTHESIZED = "hypothesized"
    PREDICTED = "predicted"
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    RETIRED = "retired"


class SourceKind(str, Enum):
    DIRECT = "direct"
    INTERNAL = "internal"
    ACTION_OUTCOME = "action_outcome"
    COGNITIVE = "cognitive"
    MODEL = "model"


def _validate_identifier(value: str, *, name: str, max_length: int) -> str:
    if not isinstance(value, str) or not value or len(value) > max_length:
        raise ValueError(f"{name} must be a non-empty bounded string")
    if any(ord(char) < 33 or ord(char) > 126 for char in value):
        raise ValueError(f"{name} must contain printable non-whitespace ASCII only")
    return value


def _validate_tokens(values: tuple[str, ...], *, name: str, maximum: int) -> tuple[str, ...]:
    if not isinstance(values, tuple) or len(values) > maximum:
        raise ValueError(f"{name} must be a tuple with at most {maximum} tokens")
    for token in values:
        _validate_identifier(token, name=f"{name} token", max_length=_MAX_TOKEN_LENGTH)
    return values


@dataclass(frozen=True, slots=True)
class ExperienceRecord:
    """One bounded organism-owned episode eligible for private model curation.

    The record deliberately stores abstract native tokens and evidence references,
    never evaluator labels or arbitrary raw host payloads. ``source_kind=MODEL``
    marks model-originated proposals so the corpus builder can enforce the
    anti-self-confirmation invariant.
    """

    record_id: str
    organism_id: str
    tick_class: int
    context_tokens: tuple[str, ...]
    action_token: str | None
    outcome_tokens: tuple[str, ...]
    epistemic_status: EpistemicStatus
    evidence_refs: tuple[str, ...]
    confidence_class: int
    source_kind: SourceKind

    def __post_init__(self) -> None:
        _validate_identifier(self.record_id, name="record_id", max_length=_MAX_RECORD_ID_LENGTH)
        _validate_identifier(self.organism_id, name="organism_id", max_length=_MAX_ORGANISM_ID_LENGTH)
        if isinstance(self.tick_class, bool) or not isinstance(self.tick_class, int) or self.tick_class < 0:
            raise ValueError("tick_class must be a non-negative integer")
        _validate_tokens(self.context_tokens, name="context_tokens", maximum=_MAX_CONTEXT_TOKENS)
        _validate_tokens(self.outcome_tokens, name="outcome_tokens", maximum=_MAX_OUTCOME_TOKENS)
        _validate_tokens(self.evidence_refs, name="evidence_refs", maximum=_MAX_EVIDENCE_REFS)
        if self.action_token is not None:
            _validate_identifier(self.action_token, name="action_token", max_length=_MAX_TOKEN_LENGTH)
        if not isinstance(self.epistemic_status, EpistemicStatus):
            raise ValueError("epistemic_status must be an EpistemicStatus")
        if not isinstance(self.source_kind, SourceKind):
            raise ValueError("source_kind must be a SourceKind")
        if isinstance(self.confidence_class, bool) or not isinstance(self.confidence_class, int):
            raise ValueError("confidence_class must be an integer")
        if not 0 <= self.confidence_class <= 7:
            raise ValueError("confidence_class must be within [0, 7]")
        if not self.context_tokens and self.action_token is None and not self.outcome_tokens:
            raise ValueError("experience record must contain context, action or outcome")
        if self.epistemic_status in {
            EpistemicStatus.OBSERVED,
            EpistemicStatus.SUPPORTED,
            EpistemicStatus.CONTRADICTED,
        } and not self.evidence_refs:
            raise ValueError("evidence-backed epistemic states require evidence_refs")
        if self.source_kind is SourceKind.MODEL and self.epistemic_status is EpistemicStatus.OBSERVED:
            raise ValueError("model-generated content cannot be marked observed")

    def canonical_payload(self, *, include_record_id: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "organism_id": self.organism_id,
            "tick_class": self.tick_class,
            "context_tokens": list(self.context_tokens),
            "action_token": self.action_token,
            "outcome_tokens": list(self.outcome_tokens),
            "epistemic_status": self.epistemic_status.value,
            "evidence_refs": list(self.evidence_refs),
            "confidence_class": self.confidence_class,
            "source_kind": self.source_kind.value,
        }
        if include_record_id:
            payload["record_id"] = self.record_id
        return payload

    @classmethod
    def restore(cls, payload: dict[str, object]) -> "ExperienceRecord":
        if not isinstance(payload, dict):
            raise ValueError("experience checkpoint entry must be an object")
        try:
            tick_class = payload["tick_class"]
            confidence_class = payload["confidence_class"]
            if isinstance(tick_class, bool) or not isinstance(tick_class, int):
                raise ValueError("tick_class must be an integer")
            if isinstance(confidence_class, bool) or not isinstance(confidence_class, int):
                raise ValueError("confidence_class must be an integer")
            raw_context = payload.get("context_tokens", [])
            raw_outcome = payload.get("outcome_tokens", [])
            raw_evidence = payload.get("evidence_refs", [])
            if not all(isinstance(value, list) for value in (raw_context, raw_outcome, raw_evidence)):
                raise ValueError("experience token collections must be lists")
            if any(not isinstance(token, str) for token in (*raw_context, *raw_outcome, *raw_evidence)):
                raise ValueError("experience token collections must contain strings")
            action = payload.get("action_token")
            if action is not None and not isinstance(action, str):
                raise ValueError("action_token must be a string or null")
            raw_record_id = payload["record_id"]
            raw_organism_id = payload["organism_id"]
            raw_status = payload["epistemic_status"]
            raw_source = payload["source_kind"]
            if not all(isinstance(value, str) for value in (raw_record_id, raw_organism_id, raw_status, raw_source)):
                raise ValueError("experience checkpoint identifiers must be strings")
            return cls(
                record_id=raw_record_id,
                organism_id=raw_organism_id,
                tick_class=tick_class,
                context_tokens=tuple(raw_context),
                action_token=action,
                outcome_tokens=tuple(raw_outcome),
                epistemic_status=EpistemicStatus(raw_status),
                evidence_refs=tuple(raw_evidence),
                confidence_class=confidence_class,
                source_kind=SourceKind(raw_source),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid experience checkpoint entry") from exc

    @property
    def content_hash(self) -> str:
        encoded = json.dumps(
            self.canonical_payload(include_record_id=False),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
