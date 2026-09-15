"""Bounded, evidence-based relations between resident Symbionts (Milestone K)."""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
import math

class RelationValence(StrEnum):
    UNKNOWN = "unknown"
    POSITIVE = "positive"
    NEGATIVE = "negative"

@dataclass(frozen=True, slots=True)
class SocialRelation:
    source_id: str
    target_id: str
    support: float = 0.0
    harm: float = 0.0
    observations: int = 0
    reciprocal_observations: int = 0
    conflicts: int = 0
    last_tick: int | None = None
    @property
    def valence(self) -> RelationValence:
        if self.observations == 0 or abs(self.support - self.harm) < 0.1: return RelationValence.UNKNOWN
        return RelationValence.POSITIVE if self.support > self.harm else RelationValence.NEGATIVE

    def freshness(self, current_tick: int, *, half_life: float = 32.0) -> float:
        """Return bounded evidence freshness without changing stored history."""
        if current_tick < 0 or half_life <= 0:
            raise ValueError("invalid freshness parameters")
        if self.last_tick is None or current_tick < self.last_tick:
            return 0.0
        return math.exp(-math.log(2.0) * (current_tick - self.last_tick) / half_life)

class RelationLedger:
    """Stores only aggregate interaction outcomes; no imposed social objective."""
    def __init__(self, *, max_relations: int = 1024) -> None:
        if max_relations < 1: raise ValueError("max_relations must be positive")
        self._max = max_relations; self._relations: dict[tuple[str,str], SocialRelation] = {}
    def observe(self, source_id: str, target_id: str, *, benefit: float = 0.0, cost: float = 0.0,
                reciprocal: bool = False, conflict: bool = False, tick: int | None = None) -> SocialRelation:
        if (not source_id or not target_id or source_id == target_id or benefit < 0 or cost < 0
                or (tick is not None and tick < 0)):
            raise ValueError("invalid relation observation")
        key=(source_id,target_id)
        if key not in self._relations and len(self._relations) >= self._max: del self._relations[sorted(self._relations)[0]]
        old=self._relations.get(key, SocialRelation(source_id,target_id))
        item=SocialRelation(source_id, target_id, old.support + benefit, old.harm + cost,
                            old.observations + 1,
                            old.reciprocal_observations + int(reciprocal),
                            old.conflicts + int(conflict), tick if tick is not None else old.last_tick)
        self._relations[key]=item; return item
    @property
    def relations(self) -> tuple[SocialRelation,...]: return tuple(sorted(self._relations.values(), key=lambda r:(r.source_id,r.target_id)))

    def checkpoint(self) -> dict[str, object]:
        return {"schema_version": 2, "max_relations": self._max,
                "relations": [{"source_id": r.source_id, "target_id": r.target_id,
                               "support": r.support, "harm": r.harm,
                               "observations": r.observations,
                               "reciprocal_observations": r.reciprocal_observations,
                               "conflicts": r.conflicts, "last_tick": r.last_tick}
                              for r in self.relations]}

    @classmethod
    def from_checkpoint(cls, payload: dict[str, object]) -> "RelationLedger":
        if not isinstance(payload, dict) or payload.get("schema_version") not in (1, 2):
            raise ValueError("invalid relation checkpoint")
        ledger = cls(max_relations=int(payload.get("max_relations", 1024)))
        rows = payload.get("relations", [])
        if not isinstance(rows, list) or len(rows) > ledger._max:
            raise ValueError("invalid relation rows")
        for row in rows:
            required = {"source_id", "target_id", "support", "harm", "observations"}
            if not isinstance(row, dict) or not required.issubset(row):
                raise ValueError("invalid relation row")
            support, harm, observations = float(row["support"]), float(row["harm"]), int(row["observations"])
            reciprocal = int(row.get("reciprocal_observations", 0))
            conflicts = int(row.get("conflicts", 0))
            last_tick = row.get("last_tick")
            if support < 0 or harm < 0 or observations < 0 or reciprocal < 0 or conflicts < 0 or (last_tick is not None and int(last_tick) < 0):
                raise ValueError("invalid relation values")
            item = ledger.observe(str(row["source_id"]), str(row["target_id"]), benefit=support, cost=harm)
            ledger._relations[(item.source_id, item.target_id)] = SocialRelation(
                item.source_id, item.target_id, support, harm, observations,
                reciprocal, conflicts, int(last_tick) if last_tick is not None else None)
        return ledger

@dataclass(frozen=True, slots=True)
class InteractionOutcome:
    source_id: str
    target_id: str
    resource: str
    granted: float
    relation: SocialRelation


@dataclass(frozen=True, slots=True)
class SocialPresence:
    """Opaque, bounded presence signal exposed by an authorized habitat."""
    observer_id: str
    target_id: str
    available: bool
    interaction_suspended: bool

class SocialInteractionEngine:
    """Local, explicit interaction using a finite resource pool.

    Positive exchange is represented by a voluntary transfer request; negative
    interaction is simply competition for the same finite resource. No policy
    chooses which relation an organism should prefer.
    """
    def __init__(self, pool, *, ledger: RelationLedger | None = None) -> None:
        self.pool = pool
        self.ledger = ledger if ledger is not None else RelationLedger()

    def exchange(self, source_id: str, target_id: str, resource: str, amount: float) -> InteractionOutcome:
        allocation = self.pool.allocate([(target_id, resource, amount)])[0]
        # Reciprocity is evidence, not a social reward: mark this observation
        # when the target has previously interacted in the opposite direction.
        reverse = any(
            item.source_id == target_id and item.target_id == source_id
            and item.observations > 0
            for item in self.ledger.relations
        )
        relation = self.ledger.observe(
            source_id, target_id, benefit=allocation.granted, reciprocal=reverse
        )
        return InteractionOutcome(source_id, target_id, resource, allocation.granted, relation)

    def compete(self, requests: list[tuple[str, str, float]]) -> tuple[InteractionOutcome, ...]:
        allocations = self.pool.allocate(requests)
        peers_by_resource: dict[str, tuple[str, ...]] = {}
        for resource in {resource for _, resource, _ in requests}:
            peers_by_resource[resource] = tuple(sorted({organism_id for organism_id, item, _ in requests if item == resource}))
        outcomes = []
        for allocation in allocations:
            requested_loss = max(0.0, allocation.requested - allocation.granted)
            peers = peers_by_resource[allocation.resource]
            # Attribute scarcity to a competing resident when one exists.  A
            # solitary request remains an ecological cost against the habitat;
            # no universal social valence is imposed.
            target = next((peer for peer in peers if peer != allocation.organism_id), "habitat")
            relation = self.ledger.observe(allocation.organism_id, target, cost=requested_loss)
            outcomes.append(InteractionOutcome(allocation.organism_id, "habitat", allocation.resource, allocation.granted, relation))
        return tuple(outcomes)


class SocialHabitat:
    """Explicitly authorized local population boundary for interactions.

    This is a mediator, not a social planner: callers choose which requests to
    issue and the finite pool decides only what can be granted.
    """
    def __init__(self, pool, *, max_members: int = 128, ledger: RelationLedger | None = None) -> None:
        if max_members < 1:
            raise ValueError("max_members must be positive")
        self.engine = SocialInteractionEngine(pool, ledger=ledger)
        self.max_members = max_members
        self._members: set[str] = set()
        self._suspended: set[tuple[str, str]] = set()

    @property
    def members(self) -> tuple[str, ...]:
        return tuple(sorted(self._members))

    def admit(self, organism_id: str) -> bool:
        if not organism_id or organism_id in self._members:
            return organism_id in self._members
        if len(self._members) >= self.max_members:
            return False
        self._members.add(organism_id)
        return True

    def release(self, organism_id: str) -> bool:
        if organism_id not in self._members:
            return False
        self._members.remove(organism_id)
        self._suspended = {pair for pair in self._suspended if organism_id not in pair}
        return True

    def observe_presence(self, observer_id: str) -> tuple[SocialPresence, ...]:
        """Return opaque presence/channel signals; never returns peer metadata."""
        if observer_id not in self._members:
            raise ValueError("observer must be admitted")
        return tuple(
            SocialPresence(observer_id, target, True, (observer_id, target) in self._suspended)
            for target in sorted(self._members)
            if target != observer_id
        )

    def suspend(self, source_id: str, target_id: str) -> None:
        if source_id not in self._members or target_id not in self._members or source_id == target_id:
            raise ValueError("both organisms must be admitted")
        self._suspended.add((source_id, target_id))

    def resume(self, source_id: str, target_id: str) -> bool:
        key = (source_id, target_id)
        existed = key in self._suspended
        self._suspended.discard(key)
        return existed

    def exchange(self, source_id: str, target_id: str, resource: str, amount: float) -> InteractionOutcome:
        if source_id not in self._members or target_id not in self._members:
            raise ValueError("both organisms must be admitted")
        if (source_id, target_id) in self._suspended:
            raise ValueError("interaction is suspended")
        return self.engine.exchange(source_id, target_id, resource, amount)

    def compete(self, requests: list[tuple[str, str, float]]) -> tuple[InteractionOutcome, ...]:
        if any(organism_id not in self._members for organism_id, _, _ in requests):
            raise ValueError("all competitors must be admitted")
        return self.engine.compete(requests)

    def checkpoint(self) -> dict[str, object]:
        """Persist membership, finite resources and aggregate evidence together."""
        return {
            "schema_version": 2,
            "max_members": self.max_members,
            "members": list(self.members),
            "pool": self.engine.pool.checkpoint(),
            "ledger": self.engine.ledger.checkpoint(),
            "suspended": [list(pair) for pair in sorted(self._suspended)],
        }

    @classmethod
    def from_checkpoint(cls, payload: dict[str, object]) -> "SocialHabitat":
        from .interactions import EcologicalResourcePool

        if not isinstance(payload, dict) or payload.get("schema_version") not in (1, 2):
            raise ValueError("invalid social habitat checkpoint")
        members = payload.get("members")
        if not isinstance(members, list) or any(not isinstance(item, str) or not item for item in members):
            raise ValueError("invalid social habitat members")
        if len(set(members)) != len(members):
            raise ValueError("duplicate social habitat member")
        max_members = int(payload.get("max_members", 128))
        if len(members) > max_members:
            raise ValueError("social habitat member limit exceeded")
        pool_payload, ledger_payload = payload.get("pool"), payload.get("ledger")
        if not isinstance(pool_payload, dict) or not isinstance(ledger_payload, dict):
            raise ValueError("invalid social habitat checkpoint")
        habitat = cls(EcologicalResourcePool.from_checkpoint(pool_payload), max_members=max_members,
                      ledger=RelationLedger.from_checkpoint(ledger_payload))
        for member in members:
            habitat.admit(member)
        suspended = payload.get("suspended", [])
        if not isinstance(suspended, list):
            raise ValueError("invalid suspended interactions")
        for pair in suspended:
            if (not isinstance(pair, list) or len(pair) != 2 or
                    any(not isinstance(item, str) for item in pair) or
                    pair[0] not in habitat._members or pair[1] not in habitat._members or pair[0] == pair[1]):
                raise ValueError("invalid suspended interaction")
            habitat._suspended.add((pair[0], pair[1]))
        return habitat
