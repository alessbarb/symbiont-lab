from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ...host.checkpoint import load_checkpoint_file, save_checkpoint_atomic
from ...host.drift import DriftKind
from ..orchestration.runtime import RuntimeTickResult

_BANNED_WORDS = ("threat", "malicious", "attack", "infected", "malware", "virus", "hack", "compromise")


class AdvisoryConsentRequiredError(RuntimeError):
    """Raised when advisory evaluation is attempted without explicit,
    independent advisory consent — separate from v0.45's sensing consent."""


@dataclass(slots=True, frozen=True)
class AdvisorySignal:
    """One condition that contributed to a defensive advisory — purely
    descriptive, never itself a threat judgment."""

    kind: str
    detail: str


@dataclass(slots=True, frozen=True)
class DefensiveAdvisory:
    """A consultative, explainable recommendation that a human review one
    capability — never autonomous action, never irreversible, always
    requiring human review (roadmap v0.48, decision-gated per CLAUDE.md's
    "no threat classification" boundary).

    Escalation-only by design: this recommends *looking*, never a
    remediation action. Every field is composed from signals v0.36
    (drift), v0.38 (attention/uncertainty) and v0.40 (dissent) already
    produce; nothing here computes a new risk score — a fixed combination
    of already-existing, already-tested signals either applies or it
    doesn't.
    """

    tick: int
    capability_id: str
    signals: tuple[AdvisorySignal, ...]
    summary: str


def _join_clauses(clauses: list[str]) -> str:
    if len(clauses) == 1:
        return clauses[0]
    if len(clauses) == 2:
        return f"{clauses[0]} and {clauses[1]}"
    return ", ".join(clauses[:-1]) + f" and {clauses[-1]}"


def _evaluate_signals(result: RuntimeTickResult, *, uncertainty_threshold: float) -> tuple[DefensiveAdvisory, ...]:
    narrative_by_capability = {entry.capability_id: entry for entry in result.narrative}
    advisories: list[DefensiveAdvisory] = []

    for capability_id, observation in sorted(result.drift_observations.items()):
        if observation.kind != DriftKind.REGIME_SHIFT:
            continue

        signals = [AdvisorySignal(kind="persistent_deviation", detail=f"{capability_id} confirmed a regime shift")]
        clauses = ["a persistent deviation"]

        entry = narrative_by_capability.get(capability_id)
        if entry is not None and entry.uncertainty != float("inf") and entry.uncertainty > uncertainty_threshold:
            signals.append(
                AdvisorySignal(
                    kind="unusual_activity",
                    detail=f"{capability_id}'s relative uncertainty ({entry.uncertainty:.3f}) exceeds the threshold",
                )
            )
            clauses.append("unusual activity")

        if result.dissent is not None and result.investigated_capability == capability_id:
            signals.append(
                AdvisorySignal(
                    kind="contradictory_evidence",
                    detail=f"{capability_id}'s recent evidence contradicted its prior belief",
                )
            )
            clauses.append("contradictory evidence")

        if len(signals) < 2:
            continue  # persistent deviation alone never fires an advisory

        summary = f"{capability_id} merits human review because it combines {_join_clauses(clauses)}."
        advisories.append(
            DefensiveAdvisory(tick=result.tick, capability_id=capability_id, signals=tuple(signals), summary=summary)
        )

    return tuple(advisories)


class DefensiveAdvisor:
    """Evaluates :class:`RuntimeTickResult`\\ s for defensive advisories,
    under its own independent consent and its own rate limit (roadmap
    v0.48).

    Consent here is deliberately separate from v0.45's sensing consent —
    a host owner may consent to being perceived without consenting to
    receive recommendations, or vice versa. Rate limiting here throttles
    *output* (don't re-notify too often), not computation: unlike v0.45's
    ``GovernedOrganism`` (which refuses a tick outright when rate-limited,
    since a tick is an action with a cost), a rate-limited advisory
    evaluation here simply returns no advisories for that call rather than
    raising — an advisory being silent this tick is a normal outcome, not
    an error to catch on every loop iteration.
    """

    def __init__(
        self,
        *,
        consented: bool = False,
        uncertainty_threshold: float = 1.0,
        min_seconds_between_advisories: float = 0.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if uncertainty_threshold <= 0.0:
            raise ValueError("uncertainty_threshold must be positive")
        if min_seconds_between_advisories < 0.0:
            raise ValueError("min_seconds_between_advisories must be non-negative")
        self._consented = consented
        self._uncertainty_threshold = uncertainty_threshold
        self._min_seconds_between_advisories = min_seconds_between_advisories
        self._clock = clock
        self._last_advisory_at: float | None = None

    @property
    def is_consented(self) -> bool:
        return self._consented

    def grant(self) -> None:
        self._consented = True

    def revoke(self) -> None:
        self._consented = False

    def evaluate(self, result: RuntimeTickResult) -> tuple[DefensiveAdvisory, ...]:
        if not self._consented:
            raise AdvisoryConsentRequiredError(
                "advisory consent has not been granted; call grant() to enable defensive advisories"
            )

        now = self._clock()
        if self._last_advisory_at is not None and (now - self._last_advisory_at) < self._min_seconds_between_advisories:
            return ()

        advisories = _evaluate_signals(result, uncertainty_threshold=self._uncertainty_threshold)
        if advisories:
            self._last_advisory_at = now
        return advisories


def _advisory_to_dict(advisory: DefensiveAdvisory) -> dict[str, Any]:
    return {
        "tick": advisory.tick,
        "capability_id": advisory.capability_id,
        "signals": [{"kind": signal.kind, "detail": signal.detail} for signal in advisory.signals],
        "summary": advisory.summary,
    }


def append_advisories_to_log(advisories: tuple[DefensiveAdvisory, ...], path: str | Path) -> None:
    """Append new advisories to a durable, atomically-written log
    (roadmap v0.48). A no-op when ``advisories`` is empty — an empty tick
    never touches the log file."""
    if not advisories:
        return
    existing = load_checkpoint_file(path) or {"advisories": []}
    existing.setdefault("advisories", [])
    existing["advisories"].extend(_advisory_to_dict(advisory) for advisory in advisories)
    save_checkpoint_atomic(existing, path)


def load_advisory_log(path: str | Path) -> tuple[dict[str, Any], ...]:
    """Read back a durable advisory log written by
    :func:`append_advisories_to_log`; an empty tuple if none exists yet."""
    payload = load_checkpoint_file(path)
    if payload is None:
        return ()
    return tuple(payload.get("advisories", []))
