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
    rejections: int = 0
    # Context is an opaque local channel/resource token.  Relations in one
    # channel must not silently become evidence for another channel.
    channel: str = "default"
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

    def reliability(self, current_tick: int, *, half_life: float = 32.0) -> float:
        """Return bounded local evidence quality, including conflict pressure."""
        if current_tick < 0:
            raise ValueError("current_tick must be non-negative")
        evidence = (
            self.observations / (self.observations + self.conflicts)
            if self.observations else 0.0
        )
        return max(0.0, min(1.0, evidence * self.freshness(current_tick, half_life=half_life)))


@dataclass(frozen=True, slots=True)
class ResourceEvidence:
    """Local aggregate evidence about one opaque habitat resource token."""
    token: str
    requested: float = 0.0
    granted: float = 0.0
    observations: int = 0
    denied: int = 0
    last_tick: int | None = None
    consecutive_denied: int = 0

    @property
    def availability(self) -> float:
        if self.requested <= 0.0:
            return 0.0
        return min(1.0, max(0.0, self.granted / self.requested))

    def freshness(self, current_tick: int, *, half_life: float = 32.0) -> float:
        if current_tick < 0 or half_life <= 0:
            raise ValueError("invalid freshness parameters")
        if self.last_tick is None or current_tick < self.last_tick:
            return 0.0
        return math.exp(-math.log(2.0) * (current_tick - self.last_tick) / half_life)


class ResourceEvidenceLedger:
    """Bounded memory used to choose opaque resources from local outcomes.

    This is availability evidence, not a universal reward or evaluator label.
    A runtime can therefore develop a repeatable resource niche while retaining
    exploration pressure and a finite, checkpointable memory.
    """
    def __init__(self, *, max_resources: int = 64) -> None:
        if max_resources < 1:
            raise ValueError("max_resources must be positive")
        self._max = max_resources
        self._evidence: dict[str, ResourceEvidence] = {}

    @property
    def evidence(self) -> tuple[ResourceEvidence, ...]:
        return tuple(self._evidence[token] for token in sorted(self._evidence))

    def observe(self, token: str, *, requested: float, granted: float,
                tick: int | None = None) -> ResourceEvidence:
        if (not isinstance(token, str) or not token or len(token) > 64
                or not math.isfinite(requested) or not math.isfinite(granted)
                or requested <= 0.0 or granted < 0.0 or granted > requested
                or (tick is not None and (not isinstance(tick, int) or tick < 0))):
            raise ValueError("invalid resource evidence")
        if token not in self._evidence and len(self._evidence) >= self._max:
            oldest = min(self._evidence, key=lambda item: (
                self._evidence[item].last_tick if self._evidence[item].last_tick is not None else -1,
                item,
            ))
            del self._evidence[oldest]
        old = self._evidence.get(token, ResourceEvidence(token))
        item = ResourceEvidence(
            token=token,
            requested=old.requested + requested,
            granted=old.granted + granted,
            observations=old.observations + 1,
            denied=old.denied + int(granted <= 0.0),
            last_tick=tick if tick is not None else old.last_tick,
            consecutive_denied=(old.consecutive_denied + 1 if granted <= 0.0 else 0),
        )
        self._evidence[token] = item
        return item

    def choose(self, tokens: tuple[str, ...], *, current_tick: int) -> str | None:
        if current_tick < 0:
            raise ValueError("current_tick must be non-negative")
        candidates = tuple(sorted({token for token in tokens if isinstance(token, str) and token}))
        if not candidates:
            return None

        # Evidence must remain revisable.  A denied or weakly observed token
        # is therefore retried after a bounded quiet period instead of being
        # excluded forever by its first outcome.  The schedule is derived
        # only from local ticks and evidence, so it adds no evaluator policy
        # or external preference.
        stale = [
            item for token in candidates
            if (item := self._evidence.get(token)) is not None
            and item.last_tick is not None
            and current_tick - item.last_tick >= 8
        ]
        if stale:
            return min(stale, key=lambda item: (item.observations, item.last_tick or 0, item.token)).token

        def priority(token: str) -> tuple[float, str]:
            item = self._evidence.get(token)
            if item is None:
                # Unknown tokens retain a bounded exploration bonus.
                return (-0.25, token)
            # Aggregate availability alone can hide a regime change: a token
            # that was useful for a long time may now be denied repeatedly.
            # Keep that local, recent failure pressure bounded so another
            # opaque token gets a chance without turning a denial into a
            # permanent blacklist.
            score = item.availability * item.freshness(current_tick)
            score -= min(0.75, 0.15 * item.consecutive_denied)
            score += 0.25 / (1.0 + item.observations)
            return (-score, token)

        return min(candidates, key=priority)

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": 2,
            "max_resources": self._max,
            "evidence": [
                {"token": item.token, "requested": item.requested,
                 "granted": item.granted, "observations": item.observations,
                 "denied": item.denied, "last_tick": item.last_tick,
                 "consecutive_denied": item.consecutive_denied}
                for item in self.evidence
            ],
        }

    @classmethod
    def from_checkpoint(cls, payload: dict[str, object]) -> "ResourceEvidenceLedger":
        if not isinstance(payload, dict) or payload.get("schema_version") not in (1, 2):
            raise ValueError("invalid resource evidence checkpoint")
        ledger = cls(max_resources=int(payload.get("max_resources", 64)))
        rows = payload.get("evidence", [])
        if not isinstance(rows, list) or len(rows) > ledger._max:
            raise ValueError("invalid resource evidence rows")
        seen: set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("invalid resource evidence row")
            token = row.get("token")
            requested = float(row.get("requested", 0.0))
            granted = float(row.get("granted", 0.0))
            observations = int(row.get("observations", 0))
            denied = int(row.get("denied", 0))
            last_tick = row.get("last_tick")
            consecutive_denied = int(row.get("consecutive_denied", 0))
            if (not isinstance(token, str) or not token or len(token) > 64
                    or not math.isfinite(requested) or not math.isfinite(granted)
                    or requested <= 0.0 or granted < 0.0 or granted > requested
                    or observations < 1 or denied < 0 or denied > observations
                    or consecutive_denied < 0 or consecutive_denied > observations
                    or (last_tick is not None and (not isinstance(last_tick, int) or last_tick < 0))):
                raise ValueError("invalid resource evidence values")
            if token in seen:
                raise ValueError("duplicate resource evidence token")
            seen.add(token)
            item = ledger.observe(token, requested=requested, granted=granted, tick=last_tick)
            ledger._evidence[token] = ResourceEvidence(
                token, requested, granted, observations, denied, last_tick,
                consecutive_denied
            )
            del item
        return ledger

class RelationLedger:
    """Stores only aggregate interaction outcomes; no imposed social objective."""
    def __init__(self, *, max_relations: int = 1024) -> None:
        if max_relations < 1: raise ValueError("max_relations must be positive")
        self._max = max_relations; self._relations: dict[tuple[str,str,str], SocialRelation] = {}
    def observe(self, source_id: str, target_id: str, *, benefit: float = 0.0, cost: float = 0.0,
                reciprocal: bool = False, conflict: bool = False, rejected: bool = False,
                tick: int | None = None, channel: str = "default") -> SocialRelation:
        if (not isinstance(source_id, str) or not isinstance(target_id, str)
                or not source_id or not target_id or len(source_id) > 128 or len(target_id) > 128
                or source_id == target_id
                or not isinstance(benefit, (int, float)) or not math.isfinite(benefit)
                or not isinstance(cost, (int, float)) or not math.isfinite(cost)
                or benefit < 0 or cost < 0
                or not isinstance(channel, str) or not channel or len(channel) > 64
                or (tick is not None and (not isinstance(tick, int) or isinstance(tick, bool) or tick < 0))):
            raise ValueError("invalid relation observation")
        key=(source_id,target_id,channel)
        if key not in self._relations and len(self._relations) >= self._max: del self._relations[sorted(self._relations)[0]]
        old=self._relations.get(key, SocialRelation(source_id,target_id, channel=channel))
        item=SocialRelation(source_id, target_id, old.support + benefit, old.harm + cost,
                            old.observations + 1,
                            old.reciprocal_observations + int(reciprocal),
                            old.conflicts + int(conflict), tick if tick is not None else old.last_tick,
                            old.rejections + int(rejected), channel)
        self._relations[key]=item; return item
    @property
    def relations(self) -> tuple[SocialRelation,...]: return tuple(sorted(self._relations.values(), key=lambda r:(r.source_id,r.target_id,r.channel)))

    def checkpoint(self) -> dict[str, object]:
        return {"schema_version": 4, "max_relations": self._max,
                "relations": [{"source_id": r.source_id, "target_id": r.target_id,
                               "support": r.support, "harm": r.harm,
                               "observations": r.observations,
                               "reciprocal_observations": r.reciprocal_observations,
                               "conflicts": r.conflicts, "last_tick": r.last_tick,
                               "rejections": r.rejections, "channel": r.channel}
                              for r in self.relations]}

    @classmethod
    def from_checkpoint(cls, payload: dict[str, object]) -> "RelationLedger":
        if not isinstance(payload, dict) or payload.get("schema_version") not in (1, 2, 3, 4):
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
            rejections = int(row.get("rejections", 0))
            channel = row.get("channel", "default")
            last_tick = row.get("last_tick")
            if (not isinstance(row.get("source_id"), str) or not isinstance(row.get("target_id"), str)
                    or not math.isfinite(support) or not math.isfinite(harm)
                    or support < 0 or harm < 0 or observations < 0 or reciprocal < 0
                    or conflicts < 0 or rejections < 0 or rejections > observations
                    or not isinstance(channel, str) or not channel or len(channel) > 64
                    or (last_tick is not None and (not isinstance(last_tick, int)
                                                   or isinstance(last_tick, bool) or last_tick < 0))):
                raise ValueError("invalid relation values")
            item = ledger.observe(str(row["source_id"]), str(row["target_id"]), benefit=support, cost=harm, channel=channel)
            ledger._relations[(item.source_id, item.target_id, channel)] = SocialRelation(
                item.source_id, item.target_id, support, harm, observations,
                reciprocal, conflicts, int(last_tick) if last_tick is not None else None,
                rejections, channel)
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


@dataclass(frozen=True, slots=True)
class SocialCompetitionRequest:
    """A local competition proposal awaiting habitat adjudication."""
    source_id: str
    resource: str
    amount: float

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
            and item.channel == resource and item.observations > 0
            for item in self.ledger.relations
        )
        relation = self.ledger.observe(
            source_id, target_id, benefit=allocation.granted, reciprocal=reverse,
            channel=resource
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
            relation = self.ledger.observe(
                allocation.organism_id, target, cost=requested_loss, channel=allocation.resource
            )
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

    @property
    def resource_tokens(self) -> tuple[str, ...]:
        """Return bounded opaque resource tokens available in this habitat."""
        return tuple(sorted(self.engine.pool.snapshot()))

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
            SocialPresence(observer_id, target, (observer_id, target) not in self._suspended,
                           (observer_id, target) in self._suspended)
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

    def reject(self, source_id: str, target_id: str) -> None:
        """Refuse one direction of future requests until explicitly resumed."""
        self.suspend(source_id, target_id)

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
