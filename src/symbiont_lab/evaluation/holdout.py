"""Repo-wide frozen-holdout enforcement for two-phase development/evaluation studies.

``predictive_discovery.py`` hand-rolled a development/evaluation seed split
with only a documented comment enforcing disjointness -- a convention, not a
mechanism. This module makes "never touched during development" mechanically
enforced: a persistent, append-only ledger records every seed a study has
ever used for development, and a :class:`FrozenEvaluationPhase` refuses to
validate against seeds already in that history, even across separate runs
(not just within one call).

Scope of this pass: only ``predictive_discovery.py`` is retrofitted to use
this helper. Other, already-CLOSED historical studies remain on their
original ad hoc seed handling; converting them is out of scope here (see the
roadmap in ``research/audits/current/2026-09-refutation-response-protocol-v1.md``).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_LEDGER_PATH = Path("research/audits/current/holdout-seed-ledger.json")
_MAX_SEEDS_PER_PHASE = 4096
_MAX_STUDY_HISTORY = _MAX_SEEDS_PER_PHASE * 8
_MAX_STUDY_ID_LENGTH = 128


def _validate_study_id(study_id: str) -> str:
    if not isinstance(study_id, str) or not study_id or len(study_id) > _MAX_STUDY_ID_LENGTH:
        raise ValueError("study_id must be a bounded non-empty string")
    return study_id


def _validate_seeds(seeds: tuple[int, ...], *, label: str) -> tuple[int, ...]:
    if not isinstance(seeds, tuple) or not seeds or len(seeds) > _MAX_SEEDS_PER_PHASE:
        raise ValueError(f"{label} must be a non-empty bounded tuple of seeds")
    if len(set(seeds)) != len(seeds):
        raise ValueError(f"{label} must contain unique seeds")
    if any(isinstance(seed, bool) or not isinstance(seed, int) or seed < 0 for seed in seeds):
        raise ValueError(f"{label} must contain non-negative integers")
    return seeds


@dataclass(frozen=True, slots=True)
class DevelopmentPhase:
    study_id: str
    seeds: tuple[int, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "study_id", _validate_study_id(self.study_id))
        object.__setattr__(self, "seeds", _validate_seeds(self.seeds, label="development seeds"))


@dataclass(frozen=True, slots=True)
class FrozenEvaluationPhase:
    study_id: str
    seeds: tuple[int, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "study_id", _validate_study_id(self.study_id))
        object.__setattr__(self, "seeds", _validate_seeds(self.seeds, label="evaluation seeds"))

    def validate_disjoint(self, ledger: "SeedLedger") -> None:
        """Raise if any evaluation seed was ever recorded as a development seed for this study."""
        used = ledger.development_history(self.study_id)
        overlap = used & set(self.seeds)
        if overlap:
            raise ValueError(
                f"evaluation seeds for {self.study_id!r} overlap seeds already recorded as "
                f"development seeds: {sorted(overlap)}"
            )


class SeedLedger:
    """Append-only, persisted history of development seeds ever used per study."""

    def __init__(self, path: Path | str = _DEFAULT_LEDGER_PATH) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def _read(self) -> dict[str, list[int]]:
        if not self._path.exists():
            return {}
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("invalid seed ledger payload")
        for study_id, seeds in payload.items():
            if (not isinstance(study_id, str) or not isinstance(seeds, list)
                    or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds)):
                raise ValueError("invalid seed ledger entry")
        return payload

    def development_history(self, study_id: str) -> set[int]:
        return set(self._read().get(_validate_study_id(study_id), []))

    def record_development(self, phase: DevelopmentPhase) -> None:
        """Append this phase's seeds to the study's permanent development history.

        Never rewrites or shrinks existing history: the persisted value is
        always the union of past and new seeds, so a seed once used for
        development can never later be "forgotten" and reused for evaluation.
        """
        data = self._read()
        existing = set(data.get(phase.study_id, []))
        merged = sorted(existing | set(phase.seeds))
        if len(merged) > _MAX_STUDY_HISTORY:
            raise ValueError("seed ledger history exceeds bounded capacity")
        data[phase.study_id] = merged
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


__all__ = ["DevelopmentPhase", "FrozenEvaluationPhase", "SeedLedger"]
