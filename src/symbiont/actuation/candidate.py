from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from symbiont.host.adaptive import PairAccumulator

from .types import ActuatorId, _require_nonneg_finite, _require_nonneg_int

ProbingState = Literal["active", "probing", "dormant"]
_VALID_PROBING_STATES: frozenset[str] = frozenset({"active", "probing", "dormant"})
_MAX_EFFECT_RELATIONS_PER_CANDIDATE = 16
# The principled floor, not an arbitrary convention: at count == 1 a Welford
# mean IS the raw reading (mean_x/mean_y equal the single observed sample
# exactly), so persisting it would persist raw telemetry under a different
# name — the same privacy argument AdaptiveSenseModel.export() states
# verbatim in host/adaptive.py ("with one sample the mean is the reading
# itself"). That argument dissolves at count >= 2. A higher threshold (the
# original P0 revision used 6, mirroring SensoryRelation's unrelated
# cross-session-recognition use case) trades checkpoint/restore replay
# exactness for a margin no invariant actually requires here — verified by
# test_continuity_gate.py's seed/split matrix (docs/design/
# symbiont-actuation-v1.md §16.6): the higher the threshold, the wider the
# tick range in which a checkpoint silently discards genuine accumulated
# statistics, since it's the SAME cumulative accumulator continuing (not a
# report to an external observer) that gets shortened. 2 minimizes that
# window to the single tick where the principled floor still applies.
_MIN_RELATION_SAMPLES_FOR_EXPORT = 2


@dataclass(slots=True)
class ActuatorCandidateState:
    """Bounded, per-actuator record of observed activation -> Δpercept effect.

    Tracks effect/controllability evidence only (spec §5): whether
    activating this channel has a measurable, reproducible consequence.
    Whether that consequence is desirable is never decided here.

    Two distinct notions of "window" evidence are tracked:
    - ``effect_relations`` is a cumulative, all-time record per percept
      (bounded, bounded-relation-count) — used for ``effect_strength``.
    - ``_current_window_relations`` is a transient, per-window-only record,
      reset every window boundary, never exported — used by
      ``complete_window`` to decide whether THIS window independently
      showed effect, so promotion can require replication across multiple
      distinct windows (spec §6 revisión 3), not just a single high
      cumulative correlation sustained by one strong window.
    """

    actuator_id: ActuatorId
    activations: int = 0
    effect_relations: dict[str, PairAccumulator] = field(default_factory=dict)
    cost_evidence: float = 0.0
    probing_state: ProbingState = "dormant"
    last_seen_tick: int = 0
    windows_completed: int = 0
    windows_with_effect: int = 0
    tick_in_window: int = 0
    _current_window_relations: dict[str, PairAccumulator] = field(default_factory=dict, repr=False)

    def observe_effect(self, percept_id: str, *, activation: float, delta_percept: float) -> None:
        """Record one activation/effect pair for ``percept_id``.

        Contract (spec §6 revisión 4): the caller owns computing
        ``delta_percept`` as ``percept(t+1) - percept(t)`` for the SAME
        actuator activation issued at tick ``t`` — i.e. the percept reading
        taken one tick AFTER the activation, minus the reading taken at (or
        immediately before) the activation. This method does not and
        cannot verify that contract itself; it only accumulates whatever
        pair it is handed.

        Passing a same-tick delta (e.g. ``percept(t) - percept(t)``, which
        is ~0 for any stable percept) defeats the entire purpose of this
        accumulator: it manufactures a constant-zero ``y`` series that can
        never show causal covariance with ``activation``, silently masking
        real effect relations as "no detectable effect" regardless of
        whether the actuator is actually causal. Always derive
        ``delta_percept`` from two chronologically distinct percept
        readings taken across the tick boundary that follows the
        activation being recorded.
        """
        self.activations += 1
        relation = self.effect_relations.get(percept_id)
        if relation is None:
            if len(self.effect_relations) >= _MAX_EFFECT_RELATIONS_PER_CANDIDATE:
                self._evict_weakest_relation()
            relation = PairAccumulator()
            self.effect_relations[percept_id] = relation
        relation.observe(activation, delta_percept)

        window_relation = self._current_window_relations.get(percept_id)
        if window_relation is None:
            window_relation = PairAccumulator()
            self._current_window_relations[percept_id] = window_relation
        window_relation.observe(activation, delta_percept)

    def complete_window(self, effect_threshold: float) -> None:
        """Close out one probing window (spec §6 revisión 3 replication gate).

        Evaluates ONLY this window's own transient evidence — never the
        all-time cumulative ``effect_relations`` — and increments
        ``windows_with_effect`` if this window independently cleared
        ``effect_threshold``. A candidate whose one loud window drove the
        cumulative correlation, with nothing but noise in every other
        window, must not satisfy the replication requirement: this counter
        is what makes that distinction, separately from ``windows_completed``
        (which only counts elapsed windows, not windows with real effect).
        Resets the transient per-window accumulators for the next window.
        """
        window_strengths = [
            abs(relation.correlation)
            for relation in self._current_window_relations.values()
            if relation.correlation is not None
        ]
        window_effect_strength = max(window_strengths, default=0.0)
        if window_effect_strength >= effect_threshold:
            self.windows_with_effect += 1
        self._current_window_relations.clear()

    def _evict_weakest_relation(self) -> None:
        def strength(item: tuple[str, PairAccumulator]) -> float:
            correlation = item[1].correlation
            return abs(correlation) if correlation is not None else -1.0

        weakest_id, _ = min(self.effect_relations.items(), key=strength)
        del self.effect_relations[weakest_id]

    @property
    def effect_strength(self) -> float:
        strengths = [
            abs(relation.correlation)
            for relation in self.effect_relations.values()
            if relation.correlation is not None
        ]
        return max(strengths, default=0.0)

    def to_payload(self) -> dict[str, Any]:
        exported_relations = {
            percept_id: relation.to_payload()
            for percept_id, relation in self.effect_relations.items()
            if relation.count >= _MIN_RELATION_SAMPLES_FOR_EXPORT
        }
        # windows_completed / windows_with_effect / tick_in_window /
        # current_window_relations are exported UNCONDITIONALLY, exactly as
        # they are — spec §6 revisión 5 supersedes revisión 3/4's "reset
        # together when relations are withheld" rule (I4's original fix).
        # That reset made checkpoint/restore non-replay-equivalent: it
        # zeroed a real, nonzero windows_completed/tick_in_window even when
        # nothing was actually wrong, desyncing the restored window_index
        # (used to recompute probing_calendar) from the index the evidence
        # was genuinely recorded under, and silently dropping a real
        # mid-window tick_in_window position that was never "unearned" —
        # it's pure scheduling phase, not a promotion claim (P0.1 — a
        # checkpoint must resume, not restart, per
        # docs/design/symbiont-actuation-v1.md §11/P0.1; caught empirically
        # by test_continuity_gate.py, which failed on any split before a
        # relation reached the export sample minimum).
        #
        # I4's original hazard — a restored candidate promoting on a single
        # post-restore window with no real evidence behind it — is now
        # closed by a different, non-conflicting mechanism instead:
        # windows_with_effect (spec §6 revisión 3) is a plain counter
        # finalized incrementally at each PAST window's own completion via
        # complete_window(), independent of whether the cumulative
        # effect_relations later gets withheld from export. A restored
        # candidate cannot satisfy windows_with_effect >= min_probing_windows
        # from a single fresh post-restore window; it can only be at or
        # above that count because real replication genuinely happened in
        # real prior windows. See
        # test_promotion_requires_re_earned_effect_strength_after_restore.
        exported_relations_dict = exported_relations
        # Atomic per-relation discard: a current-window fragment for a
        # percept_id whose cumulative relation was just withheld above
        # carries no independent meaning — the candidate doesn't yet
        # officially track that relation, so its in-progress window
        # fragment shouldn't survive the checkpoint either. Fragments for
        # percept_ids that DID clear the gate are exported unconditionally,
        # regardless of their own current-window sample count.
        current_window_payload = {
            percept_id: relation.to_payload()
            for percept_id, relation in self._current_window_relations.items()
            if percept_id in exported_relations_dict
        }
        return {
            "actuator_id": self.actuator_id,
            "activations": self.activations,
            "cost_evidence": self.cost_evidence,
            "probing_state": self.probing_state,
            "last_seen_tick": self.last_seen_tick,
            "windows_completed": self.windows_completed,
            "windows_with_effect": self.windows_with_effect,
            "tick_in_window": self.tick_in_window,
            "effect_relations": exported_relations_dict,
            # Bounded Welford summary statistics (mean/m2/c_xy), not raw
            # per-sample telemetry — exported in full, WITHOUT the
            # min-sample-for-export gate that applies to the all-time
            # cumulative effect_relations above. That gate exists to stop an
            # immature single-sample correlation from masquerading as
            # established knowledge to external consumers; this is purely
            # internal bookkeeping for complete_window()'s replication
            # counter, and withholding it would reintroduce the same
            # non-replay-equivalence problem for mid-window restores.
            "current_window_relations": current_window_payload,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ActuatorCandidateState":
        required = {
            "actuator_id",
            "activations",
            "cost_evidence",
            "probing_state",
            "last_seen_tick",
            "windows_completed",
            "windows_with_effect",
            "tick_in_window",
            "effect_relations",
            "current_window_relations",
        }
        missing = required - set(payload)
        if missing:
            raise ValueError(f"ActuatorCandidateState payload missing fields: {sorted(missing)}")

        actuator_id = payload["actuator_id"]
        if not isinstance(actuator_id, str) or not actuator_id:
            raise ValueError("actuator_id must be a non-empty string")

        probing_state = payload["probing_state"]
        if probing_state not in _VALID_PROBING_STATES:
            raise ValueError(f"probing_state must be one of {sorted(_VALID_PROBING_STATES)}, got {probing_state!r}")
        raw_relations = payload["effect_relations"]
        if not isinstance(raw_relations, dict):
            raise ValueError("effect_relations must be an object")
        effect_relations = {
            percept_id: PairAccumulator.from_payload(dict(raw))
            for percept_id, raw in raw_relations.items()
        }
        if len(effect_relations) > _MAX_EFFECT_RELATIONS_PER_CANDIDATE:
            raise ValueError(
                "effect_relations exceeds max of "
                f"{_MAX_EFFECT_RELATIONS_PER_CANDIDATE}, got {len(effect_relations)}"
            )

        raw_window_relations = payload["current_window_relations"]
        if not isinstance(raw_window_relations, dict):
            raise ValueError("current_window_relations must be an object")
        current_window_relations = {
            percept_id: PairAccumulator.from_payload(dict(raw))
            for percept_id, raw in raw_window_relations.items()
        }
        if len(current_window_relations) > _MAX_EFFECT_RELATIONS_PER_CANDIDATE:
            raise ValueError(
                "current_window_relations exceeds max of "
                f"{_MAX_EFFECT_RELATIONS_PER_CANDIDATE}, got {len(current_window_relations)}"
            )

        return cls(
            actuator_id=actuator_id,
            activations=_require_nonneg_int(payload["activations"], "activations"),
            effect_relations=effect_relations,
            cost_evidence=_require_nonneg_finite(payload["cost_evidence"], "cost_evidence"),
            probing_state=probing_state,  # type: ignore[arg-type]
            last_seen_tick=_require_nonneg_int(payload["last_seen_tick"], "last_seen_tick"),
            windows_completed=_require_nonneg_int(payload["windows_completed"], "windows_completed"),
            windows_with_effect=_require_nonneg_int(payload["windows_with_effect"], "windows_with_effect"),
            tick_in_window=_require_nonneg_int(payload["tick_in_window"], "tick_in_window"),
            _current_window_relations=current_window_relations,
        )
