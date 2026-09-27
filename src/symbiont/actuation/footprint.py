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
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Callable, Iterable, Mapping

from .evidence import CausalEvidence
from .model import agency_confidence, controllability_confidence

MIN_PULSE_WINDOWS = 3
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

    @property
    def contrast(self) -> float:
        return self.pulse_rate_lower_bound - self.expected_quiet_rate


def atom_estimates(
    pulses: Iterable[Pulse], passive: Iterable[CausalEvidence]
) -> dict[tuple[str, ...], dict[str, AtomEstimate]]:
    """Per source and atom: pulse hits against a length-matched quiet baseline."""
    quiet = [item for item in passive if item.is_passive]
    passive_n = len(quiet)
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
            )
        out[source] = estimates
    return out


class FootprintRegistry:
    """Stable, traceable per-source footprints with hysteresis and pinning."""

    SCHEMA_VERSION = 2

    def __init__(
        self,
        *,
        enter_margin: float = 0.05,
        exit_margin: float = 0.0,
        min_pulses: int = 4,
        max_footprints: int = 512,
    ) -> None:
        if not 0.0 <= exit_margin <= enter_margin < 1.0 or min_pulses < 1:
            raise ValueError("invalid footprint membership parameters")
        self.enter_margin = float(enter_margin)
        self.exit_margin = float(exit_margin)
        self.min_pulses = int(min_pulses)
        self.max_footprints = int(max_footprints)
        self._members: dict[tuple[str, ...], dict[str, AtomEstimate]] = {}
        self._pinned: set[str] = set()

    def _qualifies(self, estimate: AtomEstimate, margin: float) -> bool:
        return estimate.pulses >= self.min_pulses and estimate.contrast > margin

    def footprint_of(self, source: tuple[str, ...]) -> tuple[str, frozenset[str]] | None:
        members = self._members.get(tuple(sorted(source)))
        if not members:
            return None
        atoms = frozenset(members)
        return footprint_id(atoms), atoms

    def explain(self, source: tuple[str, ...]) -> tuple[dict[str, Any], ...]:
        """The evidence that justifies each atom of this source's footprint."""
        members = self._members.get(tuple(sorted(source)), {})
        return tuple(
            {**asdict(estimate), "contrast": estimate.contrast}
            for _, estimate in sorted(members.items())
        )

    def update(self, estimates: Mapping[tuple[str, ...], Mapping[str, AtomEstimate]]) -> None:
        """Enter above ``enter_margin``; leave only at or below ``exit_margin``."""
        for source, per_atom in sorted(estimates.items()):
            current = self._members.get(source, {})
            members: dict[str, AtomEstimate] = {}
            for atom, estimate in per_atom.items():
                margin = self.exit_margin if atom in current else self.enter_margin
                if self._qualifies(estimate, margin):
                    members[atom] = estimate
            if members:
                self._members[source] = members
            elif current and footprint_id(current) in self._pinned:
                continue  # referenced: keeps resolving to its atom set
            else:
                self._members.pop(source, None)
        self._enforce_bound()

    def pin(self, footprint: str) -> None:
        self._pinned.add(footprint)

    def unpin(self, footprint: str) -> None:
        self._pinned.discard(footprint)

    def _enforce_bound(self) -> None:
        if len(self._members) <= self.max_footprints:
            return
        removable = sorted(
            (
                source
                for source, members in self._members.items()
                if footprint_id(members) not in self._pinned
            ),
            key=lambda source: (len(self._members[source]), source),
        )
        for source in removable[: len(self._members) - self.max_footprints]:
            del self._members[source]

    @property
    def footprints(self) -> dict[tuple[str, ...], frozenset[str]]:
        return {source: frozenset(members) for source, members in self._members.items()}

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "members": [
                {"source": list(source), "estimates": [asdict(e) for _, e in sorted(m.items())]}
                for source, m in sorted(self._members.items())
            ],
            "pinned": sorted(self._pinned),
        }

    @classmethod
    def restore(cls, payload: Mapping[str, Any] | None, **options: Any) -> "FootprintRegistry":
        registry = cls(**options)
        if payload is None:
            return registry
        if payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("unsupported footprint registry checkpoint")
        for raw in payload.get("members", []):
            source = tuple(str(v) for v in raw["source"])
            registry._members[source] = {
                str(item["atom"]): AtomEstimate(**item) for item in raw["estimates"]
            }
        registry._pinned = {str(v) for v in payload.get("pinned", [])}
        return registry


__all__ = [
    "AtomEstimate",
    "FootprintRegistry",
    "Pulse",
    "atom_estimates",
    "footprint_id",
    "pulses_from",
    "wilson_lower_bound",
]
