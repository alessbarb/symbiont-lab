"""Causal footprints (Factorized Effect Representation v1 §4.2, §13.4).

The effect of an intervention source is the set of atoms it produces beyond
what happens anyway.  The unit of attribution is the **pulse** — one
exploration commitment driving a single channel set — compared with runs of
consecutive quiet (passive) windows, because a sustained command changes the
body mostly at its onset and tick-level attribution dilutes it (spike §13.4).

Estimates use the model's own controllability and agency formulas.  Footprint
membership has hysteresis so an atom near the threshold cannot flicker the
identity that competences, bindings, intents and outcome learning refer to,
and referenced footprints are pinned.  Nothing here writes evidence.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping

from .evidence import CausalEvidence
from .model import agency_confidence, controllability_confidence

MIN_RUN = 3


@dataclass(frozen=True, slots=True)
class Pulse:
    source: tuple[str, ...]  # sorted opaque channel refs driven by the commitment
    atoms: frozenset[str]
    end_tick: int


def footprint_id(atoms: Iterable[str]) -> str:
    material = "footprint|" + "|".join(sorted(atoms))
    return "effect.footprint." + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def pulses_from(
    evidence: Iterable[CausalEvidence],
    channels_of: Callable[[str], tuple[str, ...] | None],
    *,
    min_windows: int = MIN_RUN,
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
        if len(sources) != 1 or None in sources:
            continue  # coordination, not a probe of one channel set
        (source,) = sources
        if source is None:
            continue
        atoms = frozenset(atom for item in items for atom in item.effect_atoms)
        pulses.append(
            Pulse(
                source=tuple(sorted(source)),
                atoms=atoms,
                end_tick=max(item.observation_tick for item in items),
            )
        )
    return tuple(pulses)


def quiet_runs(
    passive: Iterable[CausalEvidence], *, min_windows: int = MIN_RUN
) -> tuple[frozenset[str], ...]:
    """Atom sets of runs of consecutive passive windows (the baseline)."""
    ordered = sorted(passive, key=lambda item: item.observation_tick)
    runs: list[list[CausalEvidence]] = []
    for item in ordered:
        if runs and item.observation_tick == runs[-1][-1].observation_tick + 1:
            runs[-1].append(item)
        else:
            runs.append([item])
    return tuple(
        frozenset(atom for item in run for atom in item.effect_atoms)
        for run in runs
        if len(run) >= min_windows
    )


@dataclass(frozen=True, slots=True)
class AtomEstimate:
    atom: str
    controllability: float
    agency: float
    pulses: int
    quiet_runs: int


def atom_estimates(
    pulses: Iterable[Pulse], quiet: tuple[frozenset[str], ...]
) -> dict[tuple[str, ...], dict[str, AtomEstimate]]:
    """Per source and atom: pulse hit rate against the quiet baseline."""
    baseline = Counter(atom for run in quiet for atom in run)
    by_source: dict[tuple[str, ...], list[Pulse]] = {}
    for pulse in pulses:
        by_source.setdefault(pulse.source, []).append(pulse)
    out: dict[tuple[str, ...], dict[str, AtomEstimate]] = {}
    other_n = len(quiet)
    for source, items in by_source.items():
        n = len(items)
        hits = Counter(atom for pulse in items for atom in pulse.atoms)
        out[source] = {
            atom: AtomEstimate(
                atom=atom,
                controllability=controllability_confidence(n, count, other_n, baseline[atom]),
                agency=agency_confidence(n, count, other_n, baseline[atom], None),
                pulses=n,
                quiet_runs=other_n,
            )
            for atom, count in sorted(hits.items())
        }
    return out


class FootprintRegistry:
    """Stable per-source footprints with membership hysteresis and pinning."""

    SCHEMA_VERSION = 1

    def __init__(
        self,
        *,
        enter: float = 0.35,
        hysteresis: float = 0.05,
        max_footprints: int = 512,
    ) -> None:
        if not 0.0 < enter <= 1.0 or not 0.0 <= hysteresis < enter:
            raise ValueError("invalid footprint thresholds")
        self.enter = float(enter)
        self.exit = float(enter - hysteresis)
        self.max_footprints = int(max_footprints)
        self._members: dict[tuple[str, ...], frozenset[str]] = {}
        self._pinned: set[str] = set()

    def footprint_of(self, source: tuple[str, ...]) -> tuple[str, frozenset[str]] | None:
        members = self._members.get(tuple(sorted(source)))
        if not members:
            return None
        return footprint_id(members), members

    def update(self, estimates: dict[tuple[str, ...], dict[str, AtomEstimate]]) -> None:
        """Enter at ``enter``; leave only below ``enter - hysteresis``."""
        for source, per_atom in sorted(estimates.items()):
            current = self._members.get(source, frozenset())
            kept = {
                atom
                for atom in current
                if atom in per_atom
                and per_atom[atom].agency >= self.exit
                and per_atom[atom].controllability > 0.0
            }
            added = {
                atom
                for atom, estimate in per_atom.items()
                if estimate.agency >= self.enter and estimate.controllability > 0.0
            }
            members = frozenset(kept | added)
            if members:
                self._members[source] = members
            elif footprint_id(current) not in self._pinned:
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
                for source, atoms in self._members.items()
                if footprint_id(atoms) not in self._pinned
            ),
            key=lambda source: (len(self._members[source]), source),
        )
        for source in removable[: len(self._members) - self.max_footprints]:
            del self._members[source]

    @property
    def footprints(self) -> dict[tuple[str, ...], frozenset[str]]:
        return dict(self._members)

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "members": [
                {"source": list(source), "atoms": sorted(atoms)}
                for source, atoms in sorted(self._members.items())
            ],
            "pinned": sorted(self._pinned),
        }

    @classmethod
    def restore(cls, payload: Mapping[str, Any] | None, **options) -> "FootprintRegistry":
        registry = cls(**options)
        if payload is None:
            return registry
        if payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("unsupported footprint registry checkpoint")
        for raw in payload.get("members", []):
            registry._members[tuple(str(v) for v in raw["source"])] = frozenset(
                str(v) for v in raw["atoms"]
            )
        registry._pinned = {str(v) for v in payload.get("pinned", [])}
        return registry


__all__ = [
    "AtomEstimate",
    "FootprintRegistry",
    "Pulse",
    "atom_estimates",
    "footprint_id",
    "pulses_from",
    "quiet_runs",
]
