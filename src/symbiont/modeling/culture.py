"""Bounded, provenance-preserving cultural claims.

This module is deliberately separate from :mod:`experience` and from private
model training.  A claim is a social report, never a replacement for local
evidence.  The graph stores causal ancestry; the ledger stores one organism's
local reception and assessments.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
import math
from typing import Iterable, Mapping


MAX_CLAIMS = 2048
MAX_ROOTS = 32
MAX_PARENTS = 8
MAX_TOKENS = 32
MAX_ID = 128
MAX_DEPTH = 64


class SocialEpistemicStatus(StrEnum):
    SOCIAL_CLAIM = "social_claim"
    SOCIAL_SUPPORTED = "social_supported"
    SOCIAL_CONTRADICTED = "social_contradicted"
    RETIRED = "retired"


def _id(value: str, name: str) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_ID:
        raise ValueError(f"{name} must be a bounded non-empty identifier")
    if any(ord(c) < 33 or ord(c) > 126 for c in value):
        raise ValueError(f"{name} must contain printable ASCII only")
    return value


def _tokens(values: tuple[str, ...], name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple) or not 1 <= len(values) <= MAX_TOKENS:
        raise ValueError(f"{name} must contain between 1 and {MAX_TOKENS} tokens")
    for value in values:
        _id(value, f"{name} token")
    return values


def _roots(values: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(values, tuple) or len(values) > MAX_ROOTS:
        raise ValueError("root_evidence_ids exceeds its bound")
    if len(set(values)) != len(values):
        raise ValueError("root_evidence_ids must be unique")
    return tuple(_id(value, "root evidence id") for value in values)


@dataclass(frozen=True, slots=True)
class SocialClaim:
    claim_id: str
    proposition_tokens: tuple[str, ...]
    source_organism_id: str
    immediate_sender_id: str
    root_evidence_ids: tuple[str, ...]
    parent_claim_ids: tuple[str, ...]
    created_tick_class: int
    received_tick_class: int | None
    epistemic_status: SocialEpistemicStatus
    confidence_class: int
    transmission_depth: int
    mutation_depth: int

    def __post_init__(self) -> None:
        _id(self.claim_id, "claim_id")
        _tokens(self.proposition_tokens, "proposition_tokens")
        _id(self.source_organism_id, "source_organism_id")
        _id(self.immediate_sender_id, "immediate_sender_id")
        _roots(self.root_evidence_ids)
        if not isinstance(self.parent_claim_ids, tuple) or len(self.parent_claim_ids) > MAX_PARENTS:
            raise ValueError("parent_claim_ids exceeds its bound")
        if len(set(self.parent_claim_ids)) != len(self.parent_claim_ids):
            raise ValueError("parent_claim_ids must be unique")
        for parent in self.parent_claim_ids:
            _id(parent, "parent claim id")
        if isinstance(self.created_tick_class, bool) or not isinstance(self.created_tick_class, int) or self.created_tick_class < 0:
            raise ValueError("created_tick_class must be non-negative")
        if self.received_tick_class is not None and (isinstance(self.received_tick_class, bool) or not isinstance(self.received_tick_class, int) or self.received_tick_class < 0):
            raise ValueError("received_tick_class must be non-negative or None")
        if not isinstance(self.epistemic_status, SocialEpistemicStatus):
            raise ValueError("invalid social epistemic status")
        if isinstance(self.confidence_class, bool) or not isinstance(self.confidence_class, int) or not 0 <= self.confidence_class <= 7:
            raise ValueError("confidence_class must be within [0, 7]")
        for value, name in ((self.transmission_depth, "transmission_depth"), (self.mutation_depth, "mutation_depth")):
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_DEPTH:
                raise ValueError(f"{name} exceeds its bound")

    def canonical_payload(self, *, include_id: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "proposition_tokens": list(self.proposition_tokens),
            "source_organism_id": self.source_organism_id,
            "immediate_sender_id": self.immediate_sender_id,
            "root_evidence_ids": list(self.root_evidence_ids),
            "parent_claim_ids": list(self.parent_claim_ids),
            "created_tick_class": self.created_tick_class,
            "received_tick_class": self.received_tick_class,
            "epistemic_status": self.epistemic_status.value,
            "confidence_class": self.confidence_class,
            "transmission_depth": self.transmission_depth,
            "mutation_depth": self.mutation_depth,
        }
        if include_id:
            payload["claim_id"] = self.claim_id
        return payload

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(json.dumps(self.canonical_payload(include_id=False), sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    @classmethod
    def originate(cls, *, organism_id: str, proposition_tokens: tuple[str, ...], evidence_id: str, tick: int, confidence_class: int = 0) -> "SocialClaim":
        _id(evidence_id, "evidence_id")
        draft = cls("pending", proposition_tokens, organism_id, organism_id, (evidence_id,), (), tick, None, SocialEpistemicStatus.SOCIAL_CLAIM, confidence_class, 0, 0)
        claim_id = "claim." + draft.content_hash[:48]
        return cls(claim_id, draft.proposition_tokens, draft.source_organism_id, draft.immediate_sender_id, draft.root_evidence_ids, draft.parent_claim_ids, draft.created_tick_class, draft.received_tick_class, draft.epistemic_status, draft.confidence_class, draft.transmission_depth, draft.mutation_depth)

    def retransmit(self, *, sender_id: str, receiver_id: str, tick: int) -> "SocialClaim":
        _id(sender_id, "sender_id")
        _id(receiver_id, "receiver_id")
        if not 0 <= tick <= 2**31 - 1 or self.transmission_depth >= MAX_DEPTH:
            raise ValueError("claim transmission depth or tick exceeds its bound")
        draft = SocialClaim("pending", self.proposition_tokens, self.source_organism_id, sender_id, self.root_evidence_ids, (self.claim_id,), self.created_tick_class, tick, SocialEpistemicStatus.SOCIAL_CLAIM, self.confidence_class, self.transmission_depth + 1, self.mutation_depth)
        return SocialClaim("claim." + draft.content_hash[:48], draft.proposition_tokens, draft.source_organism_id, draft.immediate_sender_id, draft.root_evidence_ids, draft.parent_claim_ids, draft.created_tick_class, draft.received_tick_class, draft.epistemic_status, draft.confidence_class, draft.transmission_depth, draft.mutation_depth)

    def mutate(self, *, sender_id: str, receiver_id: str, proposition_tokens: tuple[str, ...], tick: int) -> "SocialClaim":
        # The caller supplies only native bounded tokens; no arbitrary payload or
        # executable transform crosses the channel.
        if proposition_tokens == self.proposition_tokens:
            raise ValueError("mutation must change proposition tokens")
        if self.mutation_depth >= MAX_DEPTH:
            raise ValueError("claim mutation depth exceeds its bound")
        derived = SocialClaim("pending", proposition_tokens, self.source_organism_id, sender_id, self.root_evidence_ids, (self.claim_id,), self.created_tick_class, tick, SocialEpistemicStatus.SOCIAL_CLAIM, self.confidence_class, self.transmission_depth + 1, self.mutation_depth + 1)
        return SocialClaim("claim." + derived.content_hash[:48], derived.proposition_tokens, derived.source_organism_id, derived.immediate_sender_id, derived.root_evidence_ids, derived.parent_claim_ids, derived.created_tick_class, derived.received_tick_class, derived.epistemic_status, derived.confidence_class, derived.transmission_depth, derived.mutation_depth)

    @classmethod
    def restore(cls, payload: Mapping[str, object]) -> "SocialClaim":
        if not isinstance(payload, Mapping):
            raise ValueError("invalid social claim checkpoint entry")
        try:
            return cls(str(payload["claim_id"]), tuple(payload["proposition_tokens"]), str(payload["source_organism_id"]), str(payload["immediate_sender_id"]), tuple(payload["root_evidence_ids"]), tuple(payload["parent_claim_ids"]), payload["created_tick_class"], payload.get("received_tick_class"), SocialEpistemicStatus(payload["epistemic_status"]), payload["confidence_class"], payload["transmission_depth"], payload["mutation_depth"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid social claim checkpoint entry") from exc


class ClaimGraph:
    """A bounded DAG. Edges are causal parent -> derived claim edges."""
    SCHEMA_VERSION = 1

    def __init__(self, *, max_claims: int = MAX_CLAIMS) -> None:
        if isinstance(max_claims, bool) or not 1 <= max_claims <= MAX_CLAIMS:
            raise ValueError("max_claims exceeds its bound")
        self._max_claims = max_claims
        self._claims: dict[str, SocialClaim] = {}

    @property
    def claims(self) -> tuple[SocialClaim, ...]:
        return tuple(self._claims[key] for key in sorted(self._claims))

    def get(self, claim_id: str) -> SocialClaim | None:
        return self._claims.get(claim_id)

    def add(self, claim: SocialClaim) -> None:
        if not isinstance(claim, SocialClaim):
            raise ValueError("claim must be a SocialClaim")
        if claim.claim_id in self._claims:
            if self._claims[claim.claim_id] != claim:
                raise ValueError("claim_id collision")
            raise ValueError("duplicate claim rejected")
        if len(self._claims) >= self._max_claims:
            raise ValueError("claim graph capacity exceeded")
        if any(parent not in self._claims for parent in claim.parent_claim_ids):
            raise ValueError("claim parent is not present")
        if claim.claim_id in claim.parent_claim_ids:
            raise ValueError("claim graph cycle rejected")
        # A bounded DFS catches cycles even if a future caller changes the
        # insertion order or restores a malformed graph.
        visiting: set[str] = set()
        def visit(node: str) -> None:
            if node in visiting:
                raise ValueError("claim graph cycle rejected")
            visiting.add(node)
            current = self._claims.get(node)
            if current:
                for parent in current.parent_claim_ids:
                    visit(parent)
            visiting.remove(node)
        for parent in claim.parent_claim_ids:
            visit(parent)
        self._claims[claim.claim_id] = claim

    def ancestors(self, claim_id: str) -> tuple[str, ...]:
        if claim_id not in self._claims:
            raise KeyError(claim_id)
        found: set[str] = set()
        stack = list(self._claims[claim_id].parent_claim_ids)
        while stack:
            current = stack.pop()
            if current in found:
                continue
            found.add(current)
            stack.extend(self._claims[current].parent_claim_ids)
        return tuple(sorted(found))

    def root_evidence_ids(self, claim: SocialClaim | str) -> tuple[str, ...]:
        item = self._claims[claim] if isinstance(claim, str) else claim
        roots = set(item.root_evidence_ids)
        for parent in item.parent_claim_ids:
            roots.update(self.root_evidence_ids(parent))
        return tuple(sorted(roots))

    def independent_root_count(self, claims: Iterable[SocialClaim | str]) -> int:
        roots: set[str] = set()
        for claim in claims:
            roots.update(self.root_evidence_ids(claim))
        return len(roots)

    def shares_root(self, a: SocialClaim | str, b: SocialClaim | str) -> bool:
        return bool(set(self.root_evidence_ids(a)) & set(self.root_evidence_ids(b)))

    def checkpoint(self) -> dict[str, object]:
        return {"schema_version": self.SCHEMA_VERSION, "max_claims": self._max_claims, "claims": [claim.canonical_payload() for claim in self.claims]}

    @classmethod
    def restore(cls, payload: Mapping[str, object] | None) -> "ClaimGraph":
        if payload is None:
            return cls()
        if payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("invalid claim graph checkpoint")
        graph = cls(max_claims=payload.get("max_claims", MAX_CLAIMS))
        rows = payload.get("claims", [])
        if not isinstance(rows, list) or len(rows) > graph._max_claims:
            raise ValueError("invalid claim graph claims")
        restored = [SocialClaim.restore(row) for row in rows]
        for claim in sorted(restored, key=lambda item: (item.transmission_depth, item.mutation_depth, item.claim_id)):
            graph.add(claim)
        return graph


@dataclass(frozen=True, slots=True)
class LocalAssessment:
    claim_id: str
    organism_id: str
    evidence_id: str
    status: SocialEpistemicStatus
    tick_class: int

    def __post_init__(self) -> None:
        _id(self.claim_id, "claim_id"); _id(self.organism_id, "organism_id"); _id(self.evidence_id, "evidence_id")
        if self.status not in (SocialEpistemicStatus.SOCIAL_SUPPORTED, SocialEpistemicStatus.SOCIAL_CONTRADICTED):
            raise ValueError("assessment must support or contradict a social claim")
        if isinstance(self.tick_class, bool) or not isinstance(self.tick_class, int) or self.tick_class < 0:
            raise ValueError("assessment tick must be non-negative")


class SocialEvidenceLedger:
    """Organism-local social memory; never used as a private training corpus."""
    SCHEMA_VERSION = 1

    def __init__(self, organism_id: str, *, max_claims: int = 512, max_assessments: int = 1024) -> None:
        _id(organism_id, "organism_id")
        if not 1 <= max_claims <= MAX_CLAIMS or not 1 <= max_assessments <= 4096:
            raise ValueError("social ledger capacity exceeds its bound")
        self._organism_id = organism_id
        self._max_claims = max_claims
        self._max_assessments = max_assessments
        self._graph = ClaimGraph(max_claims=max_claims)
        self._held: dict[str, SocialClaim] = {}
        self._assessments: deque[LocalAssessment] = deque(maxlen=max_assessments)
        self._costs = {"emission": 0, "reception": 0, "storage": 0, "validation": 0, "retransmission": 0}

    @property
    def organism_id(self) -> str: return self._organism_id
    @property
    def graph(self) -> ClaimGraph: return self._graph
    @property
    def claims(self) -> tuple[SocialClaim, ...]: return tuple(self._held.values())
    @property
    def assessments(self) -> tuple[LocalAssessment, ...]: return tuple(self._assessments)
    @property
    def costs(self) -> dict[str, int]: return dict(self._costs)

    def originate(self, *, proposition_tokens: tuple[str, ...], evidence_id: str, tick: int, confidence_class: int = 0) -> SocialClaim:
        claim = SocialClaim.originate(organism_id=self._organism_id, proposition_tokens=proposition_tokens, evidence_id=evidence_id, tick=tick, confidence_class=confidence_class)
        self._graph.add(claim); self._held[claim.claim_id] = claim; self._costs["emission"] += 1; self._costs["storage"] += 1
        return claim

    def receive(self, claim: SocialClaim, *, sender_id: str, tick: int, ancestry: Iterable[SocialClaim] = ()) -> SocialClaim:
        if not isinstance(claim, SocialClaim) or claim.immediate_sender_id != sender_id:
            raise ValueError("spoofed or malformed social claim")
        if claim.claim_id in self._held:
            raise ValueError("duplicate social claim rejected")
        for ancestor in ancestry:
            if ancestor.claim_id not in self._graph._claims:
                self._graph.add(ancestor)
        self._graph.add(claim); self._held[claim.claim_id] = claim
        self._costs["reception"] += 1; self._costs["storage"] += 1
        return claim

    def retransmit(self, claim_id: str, *, receiver_id: str, tick: int) -> SocialClaim:
        claim = self._held.get(claim_id)
        if claim is None:
            raise ValueError("claim is not held by this organism")
        self._costs["retransmission"] += 1
        forwarded = claim.retransmit(sender_id=self._organism_id, receiver_id=receiver_id, tick=tick)
        self._graph.add(forwarded)
        self._held[forwarded.claim_id] = forwarded
        self._costs["storage"] += 1
        return forwarded

    def mutate_and_retransmit(self, claim_id: str, *, receiver_id: str, proposition_tokens: tuple[str, ...], tick: int) -> SocialClaim:
        claim = self._held.get(claim_id)
        if claim is None:
            raise ValueError("claim is not held by this organism")
        self._costs["retransmission"] += 1
        mutated = claim.mutate(sender_id=self._organism_id, receiver_id=receiver_id, proposition_tokens=proposition_tokens, tick=tick)
        self._graph.add(mutated)
        self._held[mutated.claim_id] = mutated
        self._costs["storage"] += 1
        return mutated

    def assess(self, claim_id: str, *, evidence_id: str, supported: bool, tick: int) -> LocalAssessment:
        if claim_id not in self._held:
            raise ValueError("cannot assess an unknown social claim")
        _id(evidence_id, "evidence_id")
        if evidence_id in {item.evidence_id for item in self._assessments}:
            raise ValueError("assessment evidence id already exists")
        assessment = LocalAssessment(claim_id, self._organism_id, evidence_id, SocialEpistemicStatus.SOCIAL_SUPPORTED if supported else SocialEpistemicStatus.SOCIAL_CONTRADICTED, tick)
        self._assessments.append(assessment); self._costs["validation"] += 1
        return assessment

    def freshness(self, claim_id: str, *, current_tick: int, half_life: float = 32.0) -> float:
        claim = self._held[claim_id]
        if current_tick < claim.created_tick_class or half_life <= 0 or not math.isfinite(half_life):
            raise ValueError("invalid freshness parameters")
        return math.exp(-math.log(2.0) * (current_tick - claim.created_tick_class) / half_life)

    def forget(self, *, current_tick: int, max_age: int) -> tuple[str, ...]:
        if current_tick < 0 or max_age < 0:
            raise ValueError("invalid forgetting parameters")
        forgotten = tuple(sorted(claim_id for claim_id, claim in self._held.items() if current_tick - claim.created_tick_class > max_age))
        for claim_id in forgotten:
            del self._held[claim_id]
        return forgotten

    def checkpoint(self) -> dict[str, object]:
        return {"schema_version": self.SCHEMA_VERSION, "organism_id": self._organism_id, "max_claims": self._max_claims, "max_assessments": self._max_assessments, "graph": self._graph.checkpoint(), "held": sorted(self._held), "assessments": [{"claim_id": a.claim_id, "organism_id": a.organism_id, "evidence_id": a.evidence_id, "status": a.status.value, "tick_class": a.tick_class} for a in self._assessments], "costs": self.costs}

    @classmethod
    def restore(cls, payload: Mapping[str, object] | None, *, organism_id: str) -> "SocialEvidenceLedger":
        if payload is None: return cls(organism_id)
        if payload.get("schema_version") != cls.SCHEMA_VERSION or payload.get("organism_id") != organism_id:
            raise ValueError("invalid social evidence checkpoint")
        ledger = cls(organism_id, max_claims=payload.get("max_claims", 512), max_assessments=payload.get("max_assessments", 1024))
        ledger._graph = ClaimGraph.restore(payload.get("graph"))
        held = payload.get("held", [])
        if not isinstance(held, list) or len(held) > ledger._max_claims:
            raise ValueError("invalid held social claims")
        for claim_id in held:
            if not isinstance(claim_id, str) or (claim := ledger._graph.get(claim_id)) is None:
                raise ValueError("held social claim is absent from graph")
            ledger._held[claim_id] = claim
        rows = payload.get("assessments", [])
        if not isinstance(rows, list): raise ValueError("invalid social assessments")
        for row in rows:
            if not isinstance(row, Mapping): raise ValueError("invalid social assessment")
            ledger._assessments.append(LocalAssessment(row["claim_id"], row["organism_id"], row["evidence_id"], SocialEpistemicStatus(row["status"]), row["tick_class"]))
        costs = payload.get("costs", {})
        if not isinstance(costs, Mapping) or set(costs) != set(ledger._costs): raise ValueError("invalid social costs")
        ledger._costs = {key: int(costs[key]) for key in ledger._costs}
        if any(value < 0 for value in ledger._costs.values()): raise ValueError("invalid social costs")
        return ledger


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    delivered: bool
    claim_id: str
    sender_id: str
    receiver_id: str
    cost: int


class SocialChannel:
    """Laboratory-controlled local transport; no sockets or peer discovery."""
    def __init__(self, *, authorized_pairs: Iterable[tuple[str, str]], max_depth: int = MAX_DEPTH, max_deliveries: int = 4096) -> None:
        self._pairs = frozenset(authorized_pairs)
        self._max_depth = max_depth
        self._max_deliveries = max_deliveries
        self._deliveries = 0

    @property
    def deliveries(self) -> int: return self._deliveries

    def deliver(self, claim: SocialClaim, *, sender_id: str, receiver: SocialEvidenceLedger, tick: int, source: SocialEvidenceLedger | None = None) -> DeliveryResult:
        if (sender_id, receiver.organism_id) not in self._pairs:
            raise ValueError("social delivery pair is not authorized")
        if claim.transmission_depth >= self._max_depth or self._deliveries >= self._max_deliveries:
            raise ValueError("social channel budget exceeded")
        if claim.immediate_sender_id != sender_id or claim.received_tick_class != tick:
            raise ValueError("delivery claim was not created for this sender and tick")
        ancestry: list[SocialClaim] = []
        if source is not None:
            for ancestor_id in sorted(source.graph.ancestors(claim.claim_id), key=lambda item: (
                source.graph.get(item).transmission_depth if source.graph.get(item) is not None else 0,
                source.graph.get(item).mutation_depth if source.graph.get(item) is not None else 0,
                item,
            )):
                ancestor = source.graph.get(ancestor_id)
                if ancestor is not None:
                    ancestry.append(ancestor)
        receiver.receive(claim, sender_id=sender_id, tick=tick, ancestry=ancestry)
        self._deliveries += 1
        return DeliveryResult(True, claim.claim_id, sender_id, receiver.organism_id, 1)
