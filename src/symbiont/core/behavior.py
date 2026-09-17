"""Pure local selection among already-authorized action opportunities."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
import math


class ActionKind(StrEnum):
    REST = "rest"
    INTAKE = "intake"
    REPAIR = "repair"
    OBSERVE = "observe"
    INVESTIGATE = "investigate"
    SOCIAL_EXCHANGE = "social_exchange"
    COMPETE = "compete"
    REPRODUCE = "reproduce"
    WAIT = "wait"


@dataclass(frozen=True, slots=True)
class ExpectedOutcome:
    """Local, bounded expectations for one candidate action.

    These dimensions are deliberately not reduced to a project-wide reward.
    """

    viability: float
    integrity: float
    resource_change: float
    information_gain: float
    uncertainty_reduction: float
    reproductive_feasibility: float
    social_expectation: float

    def __post_init__(self) -> None:
        values = (self.viability, self.integrity, self.resource_change,
                  self.information_gain, self.uncertainty_reduction,
                  self.reproductive_feasibility, self.social_expectation)
        if any(isinstance(value, bool) or not isinstance(value, (int, float))
               or not math.isfinite(float(value)) for value in values):
            raise ValueError("expected outcome values must be finite numbers")
        if any(not -1.0 <= float(value) <= 1.0 for value in values):
            raise ValueError("expected outcome values must be within [-1, 1]")

    def dominates(self, other: "ExpectedOutcome") -> bool:
        mine = (self.viability, self.integrity, self.resource_change,
                self.information_gain, self.uncertainty_reduction,
                self.reproductive_feasibility, self.social_expectation)
        theirs = (other.viability, other.integrity, other.resource_change,
                  other.information_gain, other.uncertainty_reduction,
                  other.reproductive_feasibility, other.social_expectation)
        return all(a >= b for a, b in zip(mine, theirs)) and any(a > b for a, b in zip(mine, theirs))


@dataclass(frozen=True, slots=True)
class ActionOpportunity:
    action_id: str
    kind: ActionKind
    authorized: bool
    preconditions_met: bool
    expected: ExpectedOutcome
    cost: float
    novelty: float = 0.0
    uncertainty: float = 0.0
    prediction_advantage: float = 0.0

    def __post_init__(self) -> None:
        if not self.action_id or len(self.action_id) > 96:
            raise ValueError("action_id must be non-empty and bounded")
        if isinstance(self.cost, bool) or not math.isfinite(float(self.cost)) or self.cost < 0.0 or self.cost > 1.0:
            raise ValueError("cost must be within [0, 1]")
        for value, name in ((self.novelty, "novelty"), (self.uncertainty, "uncertainty"),
                            (self.prediction_advantage, "prediction_advantage")):
            if isinstance(value, bool) or not math.isfinite(float(value)) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within [0, 1]")


@dataclass(frozen=True, slots=True)
class SelectionResult:
    selected: ActionOpportunity | None
    frontier: tuple[ActionOpportunity, ...]
    rejected_count: int


@dataclass(frozen=True, slots=True)
class ActionExecutionResult:
    """Result of one explicit local action execution.

    ``result`` is intentionally opaque to the selector.  The runtime boundary
    owns effects; selection never mutates physiology or habitat.
    """

    action_id: str
    executed: bool
    result: object | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ActionEvidence:
    """Small, replay-safe record of an action attempt.

    Only bounded labels cross the checkpoint boundary.  In particular, the
    runtime result object is never persisted as action evidence.
    """

    tick: int
    action_id: str
    kind: ActionKind
    executed: bool
    outcome: str
    reason: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.tick, bool) or not isinstance(self.tick, int) or self.tick < 0:
            raise ValueError("action evidence tick must be a non-negative integer")
        if not self.action_id or len(self.action_id) > 96:
            raise ValueError("action evidence action_id must be non-empty and bounded")
        if not isinstance(self.kind, ActionKind):
            raise ValueError("action evidence kind must be an ActionKind")
        if not isinstance(self.executed, bool):
            raise ValueError("action evidence executed must be boolean")
        if not self.outcome or len(self.outcome) > 64:
            raise ValueError("action evidence outcome must be non-empty and bounded")
        if self.reason is not None and (not isinstance(self.reason, str) or len(self.reason) > 96):
            raise ValueError("action evidence reason must be bounded text")

    def checkpoint(self) -> dict[str, object]:
        return {
            "tick": self.tick,
            "action_id": self.action_id,
            "kind": self.kind.value,
            "executed": self.executed,
            "outcome": self.outcome,
            "reason": self.reason,
        }

    @classmethod
    def from_checkpoint(cls, payload: object) -> "ActionEvidence":
        if not isinstance(payload, dict):
            raise ValueError("action evidence must be an object")
        try:
            return cls(
                tick=payload["tick"], action_id=payload["action_id"],
                kind=ActionKind(payload["kind"]), executed=payload["executed"],
                outcome=payload["outcome"], reason=payload.get("reason"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid action evidence") from exc

    @classmethod
    def restore_many(cls, payload: object, *, max_items: int = 128) -> list["ActionEvidence"]:
        if payload is None:
            return []
        if not isinstance(payload, list) or len(payload) > max_items:
            raise ValueError("action evidence exceeds bounded checkpoint capacity")
        return [cls.from_checkpoint(item) for item in payload]


@dataclass(slots=True)
class ActionOutcomeStats:
    """Coarse endogenous experience for one action kind."""

    attempts: int = 0
    successes: int = 0
    mean_viability_delta: float = 0.0
    mean_integrity_delta: float = 0.0
    mean_resource_delta: float = 0.0
    mean_prediction_error: float = 0.0

    def observe(self, *, executed: bool, viability_delta: float,
                integrity_delta: float, resource_delta: float,
                expected: ExpectedOutcome | None = None) -> None:
        self.attempts = min(1024, self.attempts + 1)
        if executed:
            self.successes = min(self.attempts, self.successes + 1)
        weight = 1.0 / self.attempts
        self.mean_viability_delta += (max(-1.0, min(1.0, viability_delta)) - self.mean_viability_delta) * weight
        self.mean_integrity_delta += (max(-1.0, min(1.0, integrity_delta)) - self.mean_integrity_delta) * weight
        self.mean_resource_delta += (max(-1.0, min(1.0, resource_delta)) - self.mean_resource_delta) * weight
        if expected is not None:
            observed = (viability_delta, integrity_delta, resource_delta)
            predicted = (expected.viability, expected.integrity, expected.resource_change)
            error = sum(abs(actual - prediction) for actual, prediction in zip(observed, predicted)) / 3.0
            self.mean_prediction_error += (max(0.0, min(1.0, error)) - self.mean_prediction_error) * weight

    def checkpoint(self) -> dict[str, object]:
        return {
            "attempts": self.attempts, "successes": self.successes,
            "mean_viability_delta": self.mean_viability_delta,
            "mean_integrity_delta": self.mean_integrity_delta,
            "mean_resource_delta": self.mean_resource_delta,
            "mean_prediction_error": self.mean_prediction_error,
        }

    @classmethod
    def from_checkpoint(cls, payload: object) -> "ActionOutcomeStats":
        if not isinstance(payload, dict):
            raise ValueError("action outcome statistics must be an object")
        attempts = payload.get("attempts", 0)
        successes = payload.get("successes", 0)
        if (isinstance(attempts, bool) or not isinstance(attempts, int) or not 0 <= attempts <= 1024
                or isinstance(successes, bool) or not isinstance(successes, int)
                or not 0 <= successes <= attempts):
            raise ValueError("invalid action outcome counts")
        values = []
        for name in ("mean_viability_delta", "mean_integrity_delta", "mean_resource_delta", "mean_prediction_error"):
            value = payload.get(name, 0.0)
            low = 0.0 if name == "mean_prediction_error" else -1.0
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or not low <= value <= 1.0:
                raise ValueError("invalid action outcome mean")
            values.append(float(value))
        return cls(attempts, successes, *values)


class LocalActionModel:
    """Bounded learned expectations used as a local action adjustment.

    It learns only from action outcomes observed by the runtime.  It has no
    evaluator fitness, external reward, or executable payload.
    """

    MAX_ACTION_KINDS = 16
    MAX_ACTION_IDS = 64

    def __init__(self, stats: dict[ActionKind, ActionOutcomeStats] | None = None,
                 action_stats: dict[str, ActionOutcomeStats] | None = None) -> None:
        self._stats = dict(stats or {})
        self._action_stats = dict(action_stats or {})

    @staticmethod
    def _normalized_action_id(action_id: str | None, kind: ActionKind | None = None) -> str | None:
        if action_id is None:
            return None
        if not isinstance(action_id, str) or not action_id or len(action_id) > 96:
            raise ValueError("action_id must be non-empty and bounded")
        # Preserve the compact kind-level representation for the canonical
        # action IDs.  Only genuinely distinct opportunities (for example
        # intake:resource_a versus intake:resource_b) get their own model.
        if kind is not None and action_id == kind.value:
            return None
        return action_id

    def predict(self, kind: ActionKind, expected: ExpectedOutcome, *, action_id: str | None = None) -> ExpectedOutcome:
        action_id = self._normalized_action_id(action_id, kind)
        stats = self._action_stats.get(action_id) if action_id is not None else None
        if stats is None:
            stats = self._stats.get(kind)
        if stats is None or stats.attempts == 0:
            return expected
        confidence = min(1.0, stats.attempts / 8.0)
        return replace(
            expected,
            # The supplied expectation is a prior.  Blend it toward observed
            # deltas rather than adding the delta to the prior on every
            # attempt; repeated successful intake must not manufacture energy
            # and permanently dominate other viable actions.
            viability=max(-1.0, min(1.0, expected.viability +
                                    (stats.mean_viability_delta - expected.viability) * confidence)),
            integrity=max(-1.0, min(1.0, expected.integrity +
                                    (stats.mean_integrity_delta - expected.integrity) * confidence)),
            resource_change=max(-1.0, min(1.0, expected.resource_change +
                                          (stats.mean_resource_delta - expected.resource_change) * confidence)),
        )

    def prediction_advantage(self, kind: ActionKind, prior: ExpectedOutcome, *, action_id: str | None = None) -> float:
        """Return endogenous evidence that this forecast beats its prior.

        The prior is the expectation supplied by the local opportunity
        builder.  It is not an evaluator baseline: it is the organism's
        pre-learning expectation.  Comparing it with the model's observed
        error lets action selection rely on a predictor only when experience
        has made it less wrong than that prior.
        """
        action_id = self._normalized_action_id(action_id, kind)
        stats = self._action_stats.get(action_id) if action_id is not None else None
        if stats is None:
            stats = self._stats.get(kind)
        if stats is None or stats.attempts < 2:
            return 0.0
        baseline_error = sum((
            abs(stats.mean_viability_delta - prior.viability),
            abs(stats.mean_integrity_delta - prior.integrity),
            abs(stats.mean_resource_delta - prior.resource_change),
        )) / 3.0
        gain = baseline_error - stats.mean_prediction_error
        # Require a small margin so a nearly identical forecast does not
        # receive behavioral credit.  Confidence grows with local trials.
        margin = max(0.0, min(1.0, gain - 0.02))
        return margin * min(1.0, stats.attempts / 8.0)

    def adjust(self, opportunity: ActionOpportunity) -> ActionOpportunity:
        return replace(
            opportunity,
            expected=self.predict(opportunity.kind, opportunity.expected, action_id=opportunity.action_id),
            prediction_advantage=self.prediction_advantage(
                opportunity.kind, opportunity.expected, action_id=opportunity.action_id
            ),
        )

    @property
    def attempts(self) -> int:
        return min(1_000_000, sum(stats.attempts for stats in self._stats.values())
                   + sum(stats.attempts for stats in self._action_stats.values()))

    def observe(self, kind: ActionKind, *, executed: bool,
                viability_delta: float = 0.0, integrity_delta: float = 0.0,
                resource_delta: float = 0.0,
                expected: ExpectedOutcome | None = None,
                action_id: str | None = None) -> None:
        action_id = self._normalized_action_id(action_id, kind)
        if action_id is not None:
            if action_id not in self._action_stats and len(self._action_stats) >= self.MAX_ACTION_IDS:
                return
            stats = self._action_stats.setdefault(action_id, ActionOutcomeStats())
        else:
            if kind not in self._stats and len(self._stats) >= self.MAX_ACTION_KINDS:
                return
            stats = self._stats.setdefault(kind, ActionOutcomeStats())
        stats.observe(executed=executed, viability_delta=viability_delta,
                      integrity_delta=integrity_delta, resource_delta=resource_delta,
                      expected=expected)

    def checkpoint(self) -> dict[str, object]:
        return {"schema_version": 1,
                "stats": {kind.value: stats.checkpoint() for kind, stats in self._stats.items()},
                "actions": {action_id: stats.checkpoint() for action_id, stats in self._action_stats.items()}}

    @classmethod
    def from_checkpoint(cls, payload: object) -> "LocalActionModel":
        if payload is None:
            return cls()
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise ValueError("invalid action model checkpoint")
        raw_stats = payload.get("stats")
        if not isinstance(raw_stats, dict) or len(raw_stats) > cls.MAX_ACTION_KINDS:
            raise ValueError("action model statistics exceed bounded capacity")
        raw_actions = payload.get("actions", {})
        if not isinstance(raw_actions, dict) or len(raw_actions) > cls.MAX_ACTION_IDS:
            raise ValueError("action model action statistics exceed bounded capacity")
        stats: dict[ActionKind, ActionOutcomeStats] = {}
        for raw_kind, raw_stat in raw_stats.items():
            try:
                kind = ActionKind(raw_kind)
            except (TypeError, ValueError) as exc:
                raise ValueError("invalid action model kind") from exc
            stats[kind] = ActionOutcomeStats.from_checkpoint(raw_stat)
        action_stats: dict[str, ActionOutcomeStats] = {}
        for action_id, raw_stat in raw_actions.items():
            cls._normalized_action_id(action_id)
            action_stats[action_id] = ActionOutcomeStats.from_checkpoint(raw_stat)
        return cls(stats, action_stats)


class InteroceptiveActionModel:
    """Learn action consequences conditioned on a coarse internal signal.

    The signal is quantized only to keep the checkpoint bounded.  No semantic
    label such as hunger or fatigue is introduced: the model receives a
    scalar organism-owned pressure and learns from the state after its own
    actions.  The per-bucket models reuse the same causal outcome learner as
    ordinary action selection.
    """

    SCHEMA_VERSION = 1
    MAX_BUCKETS = 8

    def __init__(self, models: dict[int, LocalActionModel] | None = None) -> None:
        self._models = dict(models or {})

    @staticmethod
    def bucket(signal: float) -> int:
        if isinstance(signal, bool) or not math.isfinite(float(signal)) or not 0.0 <= signal <= 1.0:
            raise ValueError("interoceptive signal must be within [0, 1]")
        return min(7, int(float(signal) * 8.0))

    def adjust(self, opportunity: ActionOpportunity, *, signal: float) -> ActionOpportunity:
        model = self._models.get(self.bucket(signal))
        return model.adjust(opportunity) if model is not None else opportunity

    def observe(self, signal: float, kind: ActionKind, *, executed: bool,
                viability_delta: float = 0.0, integrity_delta: float = 0.0,
                resource_delta: float = 0.0,
                expected: ExpectedOutcome | None = None,
                action_id: str | None = None) -> None:
        bucket = self.bucket(signal)
        if bucket not in self._models and len(self._models) >= self.MAX_BUCKETS:
            return
        model = self._models.setdefault(bucket, LocalActionModel())
        model.observe(kind, executed=executed, viability_delta=viability_delta,
                      integrity_delta=integrity_delta, resource_delta=resource_delta,
                      expected=expected, action_id=action_id)

    def checkpoint(self) -> dict[str, object]:
        return {"schema_version": self.SCHEMA_VERSION,
                "models": {str(bucket): model.checkpoint()
                           for bucket, model in self._models.items()}}

    @classmethod
    def from_checkpoint(cls, payload: object) -> "InteroceptiveActionModel":
        if payload is None:
            return cls()
        if not isinstance(payload, dict) or payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("invalid interoceptive action model checkpoint")
        raw_models = payload.get("models")
        if not isinstance(raw_models, dict) or len(raw_models) > cls.MAX_BUCKETS:
            raise ValueError("interoceptive action models exceed bounded capacity")
        models: dict[int, LocalActionModel] = {}
        for raw_bucket, raw_model in raw_models.items():
            try:
                bucket = int(raw_bucket)
            except (TypeError, ValueError) as exc:
                raise ValueError("invalid interoceptive action model bucket") from exc
            if bucket not in range(cls.MAX_BUCKETS):
                raise ValueError("invalid interoceptive action model bucket")
            models[bucket] = LocalActionModel.from_checkpoint(raw_model)
        return cls(models)


def select_action(opportunities: tuple[ActionOpportunity, ...] | list[ActionOpportunity], *,
                  exploration: float = 0.0) -> SelectionResult:
    """Select one opportunity from the local Pareto frontier.

    ``exploration`` only changes tie-breaking within the non-dominated
    frontier: it cannot authorize an action or override a hard precondition.
    The result is deterministic for a given local input, which makes replay
    possible without evaluator feedback.
    """
    if isinstance(exploration, bool) or not math.isfinite(float(exploration)) or not 0.0 <= exploration <= 1.0:
        raise ValueError("exploration must be within [0, 1]")
    if len(opportunities) > 64:
        raise ValueError("opportunities exceed bounded selection capacity")
    valid = tuple(item for item in opportunities if item.authorized and item.preconditions_met)
    frontier = tuple(
        item for item in valid
        if not any(other.expected.dominates(item.expected) for other in valid if other is not item)
    )
    if not frontier:
        return SelectionResult(None, (), len(opportunities))
    def rank(item: ActionOpportunity) -> tuple[float, float, float, float, float, float, str]:
        exploration_value = item.novelty * item.uncertainty
        # Keep every organism-local consequence dimension in the tie-breaker.
        # In particular, reproductive feasibility must not be silently
        # discarded once reproduction is authorized and locally ready.
        safety_value = (item.expected.viability + item.expected.integrity
                        + item.expected.resource_change
                        + item.expected.reproductive_feasibility
                        + item.expected.social_expectation - item.cost)
        return (exploration * exploration_value + (1.0 - exploration) * safety_value
                + item.prediction_advantage * 0.25,
                item.expected.viability, item.expected.integrity,
                item.expected.information_gain, item.prediction_advantage,
                -item.cost, item.action_id)
    selected = max(frontier, key=rank)
    return SelectionResult(selected, tuple(sorted(frontier, key=lambda item: item.action_id)), len(opportunities) - len(valid))
