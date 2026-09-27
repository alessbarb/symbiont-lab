"""Causal footprints (Factorized Effect Representation v1 §4.2, §13.4, §13.7).

The effect of an intervention source is the set of atoms it produces beyond
what happens anyway.  The unit of attribution is the **pulse** — one
exploration commitment driving a single channel set — because a sustained
command changes the body mostly at its onset (spike §13.4).

Membership (§13.7, owner decision): an atom belongs to a source's footprint
when the lower 95% Wilson bound of its pulse hit rate exceeds the rate
expected for a quiet window of the same length, ``1 - (1 - q) ** L`` (q: the
atom's per-tick rate over passive windows; L: mean pulse length), by the entry
margin, with at least ``min_pulses`` pulses.  It leaves only when the bound
falls to the exit margin (hysteresis), so identities referred to by
competences, bindings, intents and outcome learning do not flicker.

Every decision is traceable: each member keeps the estimate that justified
it (pulses, hits, length, passive rate, expected rate, bound, and the model's
controllability and agency), exposed by ``explain`` and checkpointed.
Nothing here writes evidence.
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter, deque
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any, Callable, Iterable, Mapping

from ..provenance import CausalEvent, CausalRef, ProvenanceLog
from .evidence import CausalEvidence
from .model import agency_confidence, controllability_confidence

MIN_PULSE_WINDOWS = 3
MAX_ANCESTRY_PULSES = 32
_Z95 = 1.96


@dataclass(frozen=True, slots=True)
class Pulse:
    source: tuple[str, ...]  # sorted opaque channel refs driven by the commitment
    atoms: frozenset[str]
    windows: int
    end_tick: int
    commitment_id: str


def footprint_id(atoms: Iterable[str]) -> str:
    material = "footprint|" + "|".join(sorted(atoms))
    return "effect.footprint." + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def pulses_from(
    evidence: Iterable[CausalEvidence],
    channels_of: Callable[[str], tuple[str, ...] | None],
    *,
    min_windows: int = MIN_PULSE_WINDOWS,
) -> tuple[Pulse, ...]:
    """One pulse per commitment whose windows all drive the same channel set."""
    by_commitment: dict[str, list[CausalEvidence]] = {}
    for item in evidence:
        if item.commitment_id is not None and not item.is_passive:
            by_commitment.setdefault(item.commitment_id, []).append(item)
    pulses = []
    for commitment_id in sorted(by_commitment):
        items = by_commitment[commitment_id]
        if len(items) < min_windows:
            continue
        sources = {
            channels_of(item.intervention_signature_id)
            for item in items
            if item.intervention_signature_id is not None
        }
        if len(sources) != 1:
            continue  # coordination, not a probe of one channel set
        (source,) = sources
        if source is None:
            continue
        pulses.append(
            Pulse(
                source=tuple(sorted(source)),
                atoms=frozenset(atom for item in items for atom in item.effect_atoms),
                windows=len(items),
                end_tick=max(item.observation_tick for item in items),
                commitment_id=commitment_id,
            )
        )
    return tuple(pulses)


def wilson_lower_bound(hits: int, trials: int, z: float = _Z95) -> float:
    if trials <= 0:
        return 0.0
    rate = hits / trials
    denominator = 1.0 + z * z / trials
    centre = rate + z * z / (2.0 * trials)
    spread = z * math.sqrt(rate * (1.0 - rate) / trials + z * z / (4.0 * trials * trials))
    return max(0.0, (centre - spread) / denominator)


@dataclass(frozen=True, slots=True)
class AtomEstimate:
    """Why an atom is (or is not) part of a source's footprint."""

    atom: str
    pulses: int
    hits: int
    mean_pulse_windows: float
    passive_windows: int
    passive_hits: int
    expected_quiet_rate: float
    pulse_rate_lower_bound: float
    controllability: float
    agency: float
    # Provenance: when this estimate was computed and the latest pulse behind it.
    estimated_tick: int = -1
    last_pulse_tick: int = -1
    # Ancestry (Causal Provenance v1 rule 3): the contributing pulses by
    # commitment id (most recent, bounded) and the passive-window tick range.
    pulse_commitments: tuple[str, ...] = ()
    passive_tick_range: tuple[int, int] | None = None

    def __post_init__(self) -> None:
        # Checkpoints carry lists; identity and equality use tuples.
        object.__setattr__(self, "pulse_commitments", tuple(self.pulse_commitments))
        if self.passive_tick_range is not None:
            first, last = self.passive_tick_range
            object.__setattr__(self, "passive_tick_range", (int(first), int(last)))

    @property
    def contrast(self) -> float:
        return self.pulse_rate_lower_bound - self.expected_quiet_rate


def atom_estimates(
    pulses: Iterable[Pulse],
    passive: Iterable[CausalEvidence],
    *,
    tick: int = -1,
) -> dict[tuple[str, ...], dict[str, AtomEstimate]]:
    """Per source and atom: pulse hits against a length-matched quiet baseline."""
    quiet = [item for item in passive if item.is_passive]
    passive_n = len(quiet)
    passive_range = (
        (min(item.observation_tick for item in quiet), max(item.observation_tick for item in quiet))
        if quiet
        else None
    )
    passive_hits = Counter(atom for item in quiet for atom in item.effect_atoms)
    by_source: dict[tuple[str, ...], list[Pulse]] = {}
    for pulse in pulses:
        by_source.setdefault(pulse.source, []).append(pulse)
    out: dict[tuple[str, ...], dict[str, AtomEstimate]] = {}
    for source, items in sorted(by_source.items()):
        n = len(items)
        length = sum(pulse.windows for pulse in items) / n
        hits = Counter(atom for pulse in items for atom in pulse.atoms)
        estimates = {}
        for atom, count in sorted(hits.items()):
            per_tick = passive_hits[atom] / passive_n if passive_n else 0.0
            expected = 1.0 - (1.0 - per_tick) ** length
            # The model's own confidence against the same length-matched
            # baseline, expressed as expected hits over the passive windows.
            quiet_equivalent = round(expected * passive_n)
            estimates[atom] = AtomEstimate(
                atom=atom,
                pulses=n,
                hits=count,
                mean_pulse_windows=length,
                passive_windows=passive_n,
                passive_hits=passive_hits[atom],
                expected_quiet_rate=expected,
                pulse_rate_lower_bound=wilson_lower_bound(count, n),
                controllability=controllability_confidence(n, count, passive_n, quiet_equivalent),
                agency=agency_confidence(n, count, passive_n, quiet_equivalent, None),
                estimated_tick=int(tick),
                last_pulse_tick=max(pulse.end_tick for pulse in items if atom in pulse.atoms),
                pulse_commitments=tuple(
                    pulse.commitment_id
                    for pulse in sorted(items, key=lambda item: (item.end_tick, item.commitment_id))
                )[-MAX_ANCESTRY_PULSES:],
                passive_tick_range=passive_range,
            )
        out[source] = estimates
    return out


def footprint_entity_id(source: Iterable[str]) -> str:
    """Stable identity of the footprint *entity* of one source (its versions share it)."""
    material = "footprint-entity|" + "|".join(sorted(source))
    return "footprint." + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


@dataclass(frozen=True, slots=True)
class FootprintVersion:
    """One version of a footprint entity: its content and when it began."""

    entity_id: str
    version: int
    content_id: str | None
    atoms: frozenset[str]
    since_tick: int


@dataclass(frozen=True, slots=True)
class MemberRecord:
    """One atom's membership: when it entered and the evidence behind it now."""

    atom: str
    entered_tick: int
    estimate: AtomEstimate


class TransitionKind(StrEnum):
    ENTER = "enter"
    EXIT = "exit"
    PIN = "pin"
    UNPIN = "unpin"
    EVICT = "evict"


@dataclass(frozen=True, slots=True)
class FootprintTransition:
    """One causal change of a footprint, with the evidence and rule that caused it."""

    tick: int
    kind: TransitionKind
    source: tuple[str, ...]
    entity_id: str
    version: int  # entity version after the transition
    footprint_before: str | None
    footprint_after: str | None
    atom: str | None = None
    previous_member: bool | None = None
    margin: float | None = None
    estimate: AtomEstimate | None = None


@dataclass(frozen=True, slots=True)
class PinnedFootprintSnapshot:
    """A referenced footprint content, frozen with the evidence it had when pinned."""

    footprint: str
    source: tuple[str, ...]
    entity_id: str
    version: int
    pinned_tick: int
    members: tuple[MemberRecord, ...]

    @property
    def atoms(self) -> frozenset[str]:
        return frozenset(record.atom for record in self.members)


_RULE = "wilson_lower_bound_vs_length_matched_quiet_rate"


def version_ref(entity_id: str, version: int) -> CausalRef:
    return CausalRef("footprint_version", f"{entity_id}@v{version}")


def estimate_ref(entity_id: str, estimate: AtomEstimate) -> CausalRef:
    return CausalRef("atom_estimate", f"{entity_id}|{estimate.atom}|t{estimate.estimated_tick}")


def snapshot_ref(footprint: str) -> CausalRef:
    return CausalRef("pinned_footprint_snapshot", footprint)


def _estimate_payload(estimate: AtomEstimate | None) -> dict[str, Any] | None:
    return asdict(estimate) if estimate is not None else None


def _estimate_from(payload: Mapping[str, Any] | None) -> AtomEstimate | None:
    return AtomEstimate(**payload) if payload is not None else None


def _record_payload(record: MemberRecord) -> dict[str, Any]:
    return {
        "atom": record.atom,
        "entered_tick": record.entered_tick,
        "estimate": asdict(record.estimate),
    }


def _record_from(payload: Mapping[str, Any]) -> MemberRecord:
    estimate = AtomEstimate(**payload["estimate"])
    if estimate.atom != payload["atom"]:
        raise ValueError("footprint member and its estimate disagree on the atom")
    return MemberRecord(str(payload["atom"]), int(payload["entered_tick"]), estimate)


class FootprintRegistry:
    """Footprints with full causal provenance (§13.7, owner traceability requirement).

    * Membership always reflects current evidence (enter/exit hysteresis).
    * Each member keeps the tick it entered and its latest estimate.
    * Every ENTER / EXIT / PIN / UNPIN / EVICT is recorded as a transition
      carrying the rule, margin and estimate that caused it (bounded log).
    * A footprint has an entity identity (per source, stable across versions)
      and a content identity (``footprint_id`` of its atoms only).
    * Pinning freezes a referenced content with the evidence it had when
      pinned; ``resolve`` keeps answering for it while membership evolves, and
      ``explain_pin`` distinguishes that snapshot from current evidence.
    """

    SCHEMA_VERSION = 3
    TRANSITION_LOG = 4096

    def __init__(
        self,
        *,
        enter_margin: float = 0.05,
        exit_margin: float = 0.0,
        min_pulses: int = 4,
        max_footprints: int = 512,
        provenance: ProvenanceLog | None = None,
    ) -> None:
        if not 0.0 <= exit_margin <= enter_margin < 1.0 or min_pulses < 1:
            raise ValueError("invalid footprint membership parameters")
        # Causal Provenance v1: emission never changes registry behaviour.
        self.provenance = provenance
        self._live_estimates: dict[tuple[str, ...], tuple[CausalRef, ...]] = {}
        self.enter_margin = float(enter_margin)
        self.exit_margin = float(exit_margin)
        self.min_pulses = int(min_pulses)
        self.max_footprints = int(max_footprints)
        self._members: dict[tuple[str, ...], dict[str, MemberRecord]] = {}
        self._versions: dict[tuple[str, ...], int] = {}
        self._version_ticks: dict[tuple[str, ...], int] = {}
        self._pins: dict[str, PinnedFootprintSnapshot] = {}
        self._transitions: deque[FootprintTransition] = deque(maxlen=self.TRANSITION_LOG)
        self.transitions_recorded = 0

    # -- identities ---------------------------------------------------------
    @staticmethod
    def _content(members: Mapping[str, MemberRecord]) -> str | None:
        return footprint_id(frozenset(members.keys())) if members else None

    def _log(self, transition: FootprintTransition) -> None:
        self._transitions.append(transition)
        self.transitions_recorded += 1

    # -- queries ------------------------------------------------------------
    def footprint_of(self, source: tuple[str, ...]) -> tuple[str, frozenset[str]] | None:
        members = self._members.get(tuple(sorted(source)))
        if not members:
            return None
        atoms = frozenset(members.keys())
        return footprint_id(atoms), atoms

    def version_of(self, source: tuple[str, ...]) -> FootprintVersion | None:
        """The current version of a source's footprint entity (content may be empty)."""
        source = tuple(sorted(source))
        if source not in self._versions:
            return None
        members = self._members.get(source, {})
        return FootprintVersion(
            entity_id=footprint_entity_id(source),
            version=self._versions[source],
            content_id=self._content(members),
            atoms=frozenset(members.keys()),
            since_tick=self._version_ticks.get(source, -1),
        )

    def resolve(self, footprint: str) -> frozenset[str] | None:
        """Atoms of a content id: current membership, else its pinned snapshot."""
        for members in self._members.values():
            if self._content(members) == footprint:
                return frozenset(members.keys())
        pin = self._pins.get(footprint)
        return pin.atoms if pin is not None else None

    def explain(self, source: tuple[str, ...]) -> tuple[dict[str, Any], ...]:
        """Current evidence for each atom of this source's footprint."""
        members = self._members.get(tuple(sorted(source)), {})
        return tuple(
            {
                **asdict(record.estimate),
                "contrast": record.estimate.contrast,
                "entered_tick": record.entered_tick,
                "entity_id": footprint_entity_id(source),
                "version": self._versions.get(tuple(sorted(source)), 0),
            }
            for _, record in sorted(members.items())
        )

    def explain_pin(self, footprint: str) -> dict[str, Any] | None:
        """The frozen evidence a pinned content had when it was pinned."""
        pin = self._pins.get(footprint)
        if pin is None:
            return None
        current = self._members.get(pin.source, {})
        return {
            "footprint": pin.footprint,
            "entity_id": pin.entity_id,
            "version_at_pin": pin.version,
            "pinned_tick": pin.pinned_tick,
            "still_current": self._content(current) == pin.footprint,
            "members_at_pin": [_record_payload(record) for record in pin.members],
        }

    def transitions(self) -> tuple[FootprintTransition, ...]:
        return tuple(self._transitions)

    @property
    def footprints(self) -> dict[tuple[str, ...], frozenset[str]]:
        return {source: frozenset(members.keys()) for source, members in self._members.items()}

    # -- provenance -----------------------------------------------------------
    def _emit_estimate(self, entity: str, estimate: AtomEstimate, tick: int) -> CausalRef:
        ref = estimate_ref(entity, estimate)
        if self.provenance is not None and self.provenance.causes_of(ref) is None:
            causes = [CausalRef("commitment", item) for item in estimate.pulse_commitments]
            if estimate.passive_tick_range is not None:
                first, last = estimate.passive_tick_range
                causes.append(CausalRef("passive_windows", f"t{first}-t{last}"))
            self.provenance.emit(
                CausalEvent(
                    tick=int(tick),
                    domain="footprint",
                    operation="estimate",
                    subject=ref,
                    caused_by=tuple(causes),
                    produced=(ref,),
                    rule=_RULE,
                    parameters={
                        "pulses": estimate.pulses,
                        "hits": estimate.hits,
                        "mean_pulse_windows": estimate.mean_pulse_windows,
                        "passive_windows": estimate.passive_windows,
                        "passive_hits": estimate.passive_hits,
                        "expected_quiet_rate": estimate.expected_quiet_rate,
                        "pulse_rate_lower_bound": estimate.pulse_rate_lower_bound,
                    },
                )
            )
        return ref

    def _emit_version(
        self,
        *,
        source: tuple[str, ...],
        tick: int,
        previous_version: int,
        estimates: list[AtomEstimate],
        operation: str,
        rule: str,
        parameters: Mapping[str, Any],
    ) -> None:
        if self.provenance is None:
            return
        entity = footprint_entity_id(source)
        new = version_ref(entity, self._versions.get(source, 0))
        causes = [version_ref(entity, previous_version)] if previous_version > 0 else []
        estimate_refs = tuple(self._emit_estimate(entity, estimate, tick) for estimate in estimates)
        causes.extend(estimate_refs)
        self.provenance.emit(
            CausalEvent(
                tick=int(tick),
                domain="footprint",
                operation=operation,
                subject=new,
                caused_by=tuple(causes),
                produced=(new,),
                rule=rule,
                parameters=parameters,
            )
        )
        # The superseded version and the estimates behind it are explained by
        # the durable journal; the frontier keeps only what is live.
        stale = set(self._live_estimates.get(source, ())) - set(estimate_refs)
        if previous_version > 0:
            stale.add(version_ref(entity, previous_version))
        self.provenance.retire(sorted(stale))
        self._live_estimates[source] = estimate_refs

    # -- updates ------------------------------------------------------------
    def update(
        self,
        estimates: Mapping[tuple[str, ...], Mapping[str, AtomEstimate]],
        *,
        tick: int,
    ) -> None:
        """Enter above ``enter_margin``; leave only at or below ``exit_margin``."""
        for source, per_atom in sorted(estimates.items()):
            source = tuple(sorted(source))
            current = self._members.get(source, {})
            before = self._content(current)
            entity = footprint_entity_id(source)
            updated: dict[str, MemberRecord] = {}
            changes: list[tuple[TransitionKind, str, float, AtomEstimate | None]] = []
            for atom, estimate in sorted(per_atom.items()):
                previous = current.get(atom)
                margin = self.exit_margin if previous is not None else self.enter_margin
                qualifies = estimate.pulses >= self.min_pulses and estimate.contrast > margin
                if qualifies:
                    entered = previous.entered_tick if previous is not None else int(tick)
                    updated[atom] = MemberRecord(atom, entered, estimate)
                    if previous is None:
                        changes.append((TransitionKind.ENTER, atom, margin, estimate))
                elif previous is not None:
                    changes.append((TransitionKind.EXIT, atom, margin, estimate))
            for atom in sorted(set(current) - set(per_atom)):
                # No longer estimated at all (its evidence left the ledger).
                changes.append((TransitionKind.EXIT, atom, self.exit_margin, None))
            if updated:
                self._members[source] = updated
            else:
                self._members.pop(source, None)
            after = self._content(updated)
            if after != before:
                self._versions[source] = self._versions.get(source, 0) + 1
                self._version_ticks[source] = int(tick)
            version = self._versions.get(source, 0)
            if after != before:
                self._emit_version(
                    source=source,
                    tick=tick,
                    previous_version=version - 1,
                    estimates=[estimate for _, _, _, estimate in changes if estimate is not None],
                    operation="version",
                    rule=_RULE,
                    parameters={
                        "enter_margin": self.enter_margin,
                        "exit_margin": self.exit_margin,
                        "min_pulses": self.min_pulses,
                        "content_before": before or "",
                        "content_after": after or "",
                        "entered": sum(1 for kind, *_ in changes if kind is TransitionKind.ENTER),
                        "exited": sum(1 for kind, *_ in changes if kind is TransitionKind.EXIT),
                    },
                )
            for kind, atom, margin, estimate in changes:
                self._log(
                    FootprintTransition(
                        tick=int(tick),
                        kind=kind,
                        source=source,
                        entity_id=entity,
                        version=version,
                        footprint_before=before,
                        footprint_after=after,
                        atom=atom,
                        previous_member=kind is TransitionKind.EXIT,
                        margin=margin,
                        estimate=estimate,
                    )
                )
        self._enforce_bound(tick=tick)

    def pin(self, footprint: str, *, tick: int) -> PinnedFootprintSnapshot:
        """Freeze a current content because something now refers to it."""
        if footprint in self._pins:
            return self._pins[footprint]
        for source, members in self._members.items():
            if self._content(members) == footprint:
                version = self._versions.get(source, 0)
                record = PinnedFootprintSnapshot(
                    footprint=footprint,
                    source=source,
                    entity_id=footprint_entity_id(source),
                    version=version,
                    pinned_tick=int(tick),
                    members=tuple(record for _, record in sorted(members.items())),
                )
                self._pins[footprint] = record
                if self.provenance is not None:
                    snapshot = snapshot_ref(footprint)
                    self.provenance.emit(
                        CausalEvent(
                            tick=int(tick),
                            domain="footprint",
                            operation="pin",
                            subject=snapshot,
                            caused_by=(version_ref(record.entity_id, version),),
                            produced=(snapshot,),
                            parameters={"content": footprint},
                        )
                    )
                self._log(
                    FootprintTransition(
                        tick=int(tick),
                        kind=TransitionKind.PIN,
                        source=source,
                        entity_id=record.entity_id,
                        version=version,
                        footprint_before=footprint,
                        footprint_after=footprint,
                    )
                )
                return record
        raise KeyError("only a current footprint can be pinned")

    def unpin(self, footprint: str, *, tick: int) -> None:
        record = self._pins.pop(footprint, None)
        if record is None:
            return
        if self.provenance is not None:
            self.provenance.retire((snapshot_ref(footprint),))
        self._log(
            FootprintTransition(
                tick=int(tick),
                kind=TransitionKind.UNPIN,
                source=record.source,
                entity_id=record.entity_id,
                version=self._versions.get(record.source, 0),
                footprint_before=footprint,
                footprint_after=self._content(self._members.get(record.source, {})),
            )
        )

    def _enforce_bound(self, *, tick: int) -> None:
        if len(self._members) <= self.max_footprints:
            return
        removable = sorted(
            (
                source
                for source, members in self._members.items()
                if self._content(members) not in self._pins
            ),
            key=lambda source: (len(self._members[source]), source),
        )
        for source in removable[: len(self._members) - self.max_footprints]:
            before = self._content(self._members.pop(source))
            self._versions[source] = self._versions.get(source, 0) + 1
            self._version_ticks[source] = int(tick)
            self._emit_version(
                source=source,
                tick=tick,
                previous_version=self._versions[source] - 1,
                estimates=[],
                operation="evict",
                rule="footprint_bound",
                parameters={"max_footprints": self.max_footprints, "content_before": before or ""},
            )
            self._log(
                FootprintTransition(
                    tick=int(tick),
                    kind=TransitionKind.EVICT,
                    source=source,
                    entity_id=footprint_entity_id(source),
                    version=self._versions[source],
                    footprint_before=before,
                    footprint_after=None,
                )
            )

    # -- persistence --------------------------------------------------------
    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "members": [
                {
                    "source": list(source),
                    "version": self._versions.get(source, 0),
                    "records": [_record_payload(r) for _, r in sorted(members.items())],
                }
                for source, members in sorted(self._members.items())
            ],
            "versions": [
                {
                    "source": list(source),
                    "version": version,
                    "since_tick": self._version_ticks.get(source, -1),
                }
                for source, version in sorted(self._versions.items())
            ],
            "pins": [
                {
                    "footprint": pin.footprint,
                    "source": list(pin.source),
                    "entity_id": pin.entity_id,
                    "version": pin.version,
                    "pinned_tick": pin.pinned_tick,
                    "members": [_record_payload(r) for r in pin.members],
                }
                for _, pin in sorted(self._pins.items())
            ],
            "transitions": [
                {
                    **{
                        k: v
                        for k, v in asdict(t).items()
                        if k not in ("kind", "estimate", "source")
                    },
                    "kind": t.kind.value,
                    "source": list(t.source),
                    "estimate": _estimate_payload(t.estimate),
                }
                for t in self._transitions
            ],
            "transitions_recorded": self.transitions_recorded,
            "live_estimates": [
                {"source": list(source), "refs": [ref.payload() for ref in refs]}
                for source, refs in sorted(self._live_estimates.items())
            ],
        }

    @classmethod
    def restore(cls, payload: Mapping[str, Any] | None, **options: Any) -> "FootprintRegistry":
        registry = cls(**options)
        if payload is None:
            return registry
        if payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("unsupported footprint registry checkpoint")
        for raw in payload.get("versions", []):
            source = tuple(str(v) for v in raw["source"])
            registry._versions[source] = int(raw["version"])
            registry._version_ticks[source] = int(raw.get("since_tick", -1))
        for raw in payload.get("members", []):
            records = [_record_from(item) for item in raw["records"]]
            registry._members[tuple(str(v) for v in raw["source"])] = {
                record.atom: record for record in records
            }
        for raw in payload.get("pins", []):
            members = tuple(_record_from(item) for item in raw["members"])
            pin = PinnedFootprintSnapshot(
                footprint=str(raw["footprint"]),
                source=tuple(str(v) for v in raw["source"]),
                entity_id=str(raw["entity_id"]),
                version=int(raw["version"]),
                pinned_tick=int(raw["pinned_tick"]),
                members=members,
            )
            if footprint_id(pin.atoms) != pin.footprint:
                raise ValueError("pinned footprint content does not match its identity")
            registry._pins[pin.footprint] = pin
        for raw in payload.get("transitions", [])[-cls.TRANSITION_LOG :]:
            registry._transitions.append(
                FootprintTransition(
                    tick=int(raw["tick"]),
                    kind=TransitionKind(raw["kind"]),
                    source=tuple(str(v) for v in raw["source"]),
                    entity_id=str(raw["entity_id"]),
                    version=int(raw["version"]),
                    footprint_before=raw.get("footprint_before"),
                    footprint_after=raw.get("footprint_after"),
                    atom=raw.get("atom"),
                    previous_member=raw.get("previous_member"),
                    margin=raw.get("margin"),
                    estimate=_estimate_from(raw.get("estimate")),
                )
            )
        registry.transitions_recorded = int(payload.get("transitions_recorded", 0))
        for raw in payload.get("live_estimates", []):
            registry._live_estimates[tuple(str(v) for v in raw["source"])] = tuple(
                CausalRef.from_payload(item) for item in raw["refs"]
            )
        return registry


__all__ = [
    "AtomEstimate",
    "FootprintRegistry",
    "FootprintTransition",
    "FootprintVersion",
    "MemberRecord",
    "PinnedFootprintSnapshot",
    "Pulse",
    "TransitionKind",
    "atom_estimates",
    "estimate_ref",
    "footprint_entity_id",
    "footprint_id",
    "pulses_from",
    "snapshot_ref",
    "version_ref",
    "wilson_lower_bound",
]
