"""Agency Acquisition & Executive Action v1 — scientific studies E1-E6 (§112-§117).

Every study embodies newborn canonical runtimes in the opaque CausalBody
apparatus.  Ground truth (which outputs are physically consequential, and how
the mapping is perturbed) stays evaluator-side.  Control arms differ only by
explicit construction parameters; matched arms continue from one exact
organism checkpoint and one copy of the physical body state.

Nothing here supplies a competence id, an actuator or a motor pattern to the
organism.  Metrics are evaluator-only and never re-enter the organism.
"""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
from statistics import fmean
from typing import Any, Callable, Iterable, Sequence

from symbiont.actuation.acquisition import AgencyAcquisition
from symbiont.actuation.commitment import ActionCommitment, CommitmentStatus
from symbiont.actuation.intervention import opaque_channel_ref
from symbiont.actuation.model import CausalSourceKind
from symbiont.agency.intention import IntentStatus
from symbiont.cognition.limits import KernelLimits
from symbiont.core.domains.intention import ExecutiveMode, IntentionPolicy
from symbiont.core.orchestration.runtime import OrganismRuntime

from .agency_acquisition_body import BodyCondition, CausalBody, build_subject, subject_lifecycle

DEFAULT_SEEDS = (101, 127, 149)


def _seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    result = tuple(seeds)
    if not result or len(set(result)) != len(result):
        raise ValueError("seeds must be a non-empty sequence of unique integers")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in result):
        raise ValueError("seeds must contain integers only")
    return result


def _positive(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _mean(values: Iterable[float]) -> float | None:
    items = [float(value) for value in values]
    return fmean(items) if items else None


def _advance(runtime: OrganismRuntime, body: CausalBody, ticks: int, observer=None) -> None:
    for _ in range(ticks):
        runtime.tick()
        if observer is not None:
            observer(runtime)
        body.advance(runtime.last_actuations)


def _run_until(
    runtime: OrganismRuntime,
    body: CausalBody,
    predicate: Callable[[OrganismRuntime], bool],
    *,
    limit: int,
) -> int | None:
    for _ in range(limit):
        runtime.tick()
        body.advance(runtime.last_actuations)
        if predicate(runtime):
            return runtime.tick_count
    return None


def _twin(
    runtime: OrganismRuntime,
    body: CausalBody,
    **options: Any,
) -> tuple[OrganismRuntime, CausalBody]:
    """Exact matched continuation: same organism checkpoint, same body state."""
    twin_body = copy.deepcopy(body)
    twin = OrganismRuntime.from_checkpoint(
        runtime.checkpoint(),
        host_lifecycle=subject_lifecycle(twin_body),
        host_reading_providers=(twin_body,),
        kernel_limits=KernelLimits(),
        bootstrap_semantic_senses=False,
        discover_senses=True,
        min_samples=1,
        **options,
    )
    return twin, twin_body


def _acquired(runtime: OrganismRuntime) -> bool:
    domain = runtime._action_domain
    return any(domain.competence_is_executable(item) for item in domain.competence_library.items)


# ---------------------------------------------------------------------------
# Horizon behaviour recorder shared by E2-E5.
# ---------------------------------------------------------------------------
@dataclass
class _Commitment:
    commitment: ActionCommitment
    started_tick: int
    competence_id: str | None
    intent_id: str | None
    realized: bool = False


@dataclass
class HorizonMetrics:
    ticks: int
    competence_commitments: int
    realized_commitments: int
    effect_realization_rate: float | None
    action_switches: int
    switches_per_realized_effect: float | None
    mean_prediction_error: float | None
    failed_commitments: int
    interrupted_commitments: int
    completed_commitments: int
    mean_competence_commitment_ticks: float | None
    intents_formed: int
    activated_intents: int
    rejected_intents: int
    intent_outcomes: dict[str, int]
    intent_satisfaction_rate: float | None
    mean_intent_duration: float | None
    energy: float
    energy_per_realized_effect: float | None


class _Recorder:
    def __init__(self) -> None:
        self.commitments: dict[str, _Commitment] = {}
        self.prediction_errors: list[float] = []
        self.energy = 0.0
        self.ticks = 0
        self.intent_durations: list[int] = []
        self.intent_outcomes: dict[str, int] = {}
        self.intents: set[str] = set()
        # Intents that obtained motor authority; §41 keeps REJECTED separate.
        self.activated: dict[str, int] = {}
        self.activated_outcomes: dict[str, int] = {}

    def __call__(self, runtime: OrganismRuntime) -> None:
        domain = runtime._action_domain
        self.ticks += 1
        tick = runtime.tick_count
        commitment = domain.active_commitment
        if commitment is not None and commitment.commitment_id not in self.commitments:
            self.commitments[commitment.commitment_id] = _Commitment(
                commitment=commitment,
                started_tick=tick,
                competence_id=commitment.competence_id,
                intent_id=commitment.intent_id,
            )
        transition = domain.last_transition
        if transition is not None:
            if transition.prediction_error is not None:
                self.prediction_errors.append(float(transition.prediction_error.magnitude))
            record = self.commitments.get(transition.commitment_id)
            competence = (
                domain.competence_library.get(transition.competence_id)
                if transition.competence_id is not None
                else None
            )
            if (
                record is not None
                and competence is not None
                and domain.acquisition.effect_matcher.match(
                    domain.effect_space,
                    expected_effect_id=competence.effect_id,
                    observed_effect_id=transition.observed_effect_id,
                )
                >= 1.0
            ):
                record.realized = True
        self.energy += sum(float(item.delivered) for item in runtime.last_actuations)
        held = domain.intention.active
        if held is not None:
            self.intents.add(held.intent_id)
            if held.activated_tick is not None:
                self.activated.setdefault(held.intent_id, held.activated_tick)
        for outcome in domain.intention.last_outcomes:
            self.intents.add(outcome.intent_id)
            self.intent_outcomes[outcome.status.value] = (
                self.intent_outcomes.get(outcome.status.value, 0) + 1
            )
            activated_tick = self.activated.get(outcome.intent_id)
            if activated_tick is not None:
                self.activated_outcomes[outcome.status.value] = (
                    self.activated_outcomes.get(outcome.status.value, 0) + 1
                )
                self.intent_durations.append(outcome.tick - activated_tick)

    def metrics(self) -> HorizonMetrics:
        competence = [item for item in self.commitments.values() if item.competence_id]
        realized = sum(1 for item in competence if item.realized)
        statuses = [item.commitment.status for item in self.commitments.values()]
        durations = [
            (item.commitment.ended_tick or item.started_tick) - item.commitment.started_tick
            for item in competence
            if item.commitment.ended_tick is not None
        ]
        switches = max(0, len(self.commitments) - 1)
        satisfied = self.activated_outcomes.get(IntentStatus.SATISFIED.value, 0)
        terminal = sum(self.activated_outcomes.values())
        return HorizonMetrics(
            ticks=self.ticks,
            competence_commitments=len(competence),
            realized_commitments=realized,
            effect_realization_rate=realized / len(competence) if competence else None,
            action_switches=switches,
            switches_per_realized_effect=switches / realized if realized else None,
            mean_prediction_error=_mean(self.prediction_errors),
            failed_commitments=sum(status is CommitmentStatus.FAILED for status in statuses),
            interrupted_commitments=sum(
                status is CommitmentStatus.INTERRUPTED for status in statuses
            ),
            completed_commitments=sum(status is CommitmentStatus.COMPLETED for status in statuses),
            mean_competence_commitment_ticks=_mean(durations),
            intents_formed=len(self.intents),
            activated_intents=len(self.activated),
            rejected_intents=self.intent_outcomes.get(IntentStatus.REJECTED.value, 0),
            intent_outcomes=dict(sorted(self.intent_outcomes.items())),
            intent_satisfaction_rate=satisfied / terminal if terminal else None,
            mean_intent_duration=_mean(self.intent_durations),
            energy=self.energy,
            energy_per_realized_effect=self.energy / realized if realized else None,
        )


def _prepare_acquired(
    seed: int,
    *,
    actuator_count: int,
    warmup_limit: int,
    settle_ticks: int,
) -> tuple[OrganismRuntime, CausalBody, int | None]:
    body = CausalBody(actuator_count=actuator_count, seed=seed)
    runtime = build_subject(body, organism_id=f"agency-study-{seed}")
    acquired_at = _run_until(runtime, body, _acquired, limit=warmup_limit)
    if acquired_at is not None:
        _advance(runtime, body, settle_ticks)
    return runtime, body, acquired_at


def _matched_arms(
    *,
    seed: int,
    arms: dict[str, dict[str, Any]],
    actuator_count: int,
    warmup_limit: int,
    settle_ticks: int,
    horizon_ticks: int,
) -> dict[str, Any]:
    runtime, body, acquired_at = _prepare_acquired(
        seed,
        actuator_count=actuator_count,
        warmup_limit=warmup_limit,
        settle_ticks=settle_ticks,
    )
    result: dict[str, Any] = {
        "seed": seed,
        "acquired_at_tick": acquired_at,
        "arms": {},
        "testable": False,
    }
    if acquired_at is None:
        return result
    result["split_tick"] = runtime.tick_count
    for name, options in arms.items():
        twin, twin_body = _twin(runtime, body, **options)
        recorder = _Recorder()
        ledger = twin._action_domain.intention.outcome_ledger
        at_split = ledger.metrics()
        _advance(twin, twin_body, horizon_ticks, recorder)
        result["arms"][name] = {
            **asdict(recorder.metrics()),
            # Executive Outcome Learning v1 §8: saturation/fragmentation of the
            # executive memory, so a null D-vs-C result can be told apart from
            # a memory that never saw a matching key.
            "outcome_learning": {
                "enabled": twin._action_domain.intention.policy.executive_outcome_learning,
                "at_split": at_split,
                "at_end": ledger.metrics(),
            },
        }
    # A seed is testable only if some arm actually exercised a competence;
    # otherwise the comparison has no cognitive events to compare.
    result["testable"] = any(arm["competence_commitments"] > 0 for arm in result["arms"].values())
    return result


@dataclass(frozen=True)
class MatchedStudyResult:
    protocol: str
    seeds: tuple[int, ...]
    horizon_ticks: int
    per_seed: tuple[dict[str, Any], ...]
    summary: dict[str, dict[str, float | None]] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "protocol": self.protocol,
            "seeds": list(self.seeds),
            "horizon_ticks": self.horizon_ticks,
            "per_seed": list(self.per_seed),
            "summary": self.summary,
        }


_SUMMARY_KEYS = (
    "competence_commitments",
    "realized_commitments",
    "activated_intents",
    "rejected_intents",
    "effect_realization_rate",
    "action_switches",
    "switches_per_realized_effect",
    "mean_prediction_error",
    "failed_commitments",
    "interrupted_commitments",
    "completed_commitments",
    "mean_competence_commitment_ticks",
    "intent_satisfaction_rate",
    "mean_intent_duration",
    "energy",
    "energy_per_realized_effect",
)


def _summarize(per_seed: Sequence[dict[str, Any]], arms: Iterable[str]) -> dict[str, Any]:
    summary: dict[str, dict[str, float | None]] = {}
    for arm in arms:
        rows = [
            item["arms"][arm] for item in per_seed if item.get("testable") and arm in item["arms"]
        ]
        summary[arm] = {
            key: _mean(row[key] for row in rows if row[key] is not None) for key in _SUMMARY_KEYS
        }
    return summary


def _matched_study(
    protocol: str,
    arms: dict[str, dict[str, Any]],
    *,
    seeds: Sequence[int],
    actuator_count: int,
    warmup_limit: int,
    settle_ticks: int,
    horizon_ticks: int,
) -> MatchedStudyResult:
    resolved = _seeds(seeds)
    per_seed = tuple(
        _matched_arms(
            seed=seed,
            arms=arms,
            actuator_count=_positive(actuator_count, "actuator_count"),
            warmup_limit=_positive(warmup_limit, "warmup_limit"),
            settle_ticks=max(0, int(settle_ticks)),
            horizon_ticks=_positive(horizon_ticks, "horizon_ticks"),
        )
        for seed in resolved
    )
    return MatchedStudyResult(
        protocol=protocol,
        seeds=resolved,
        horizon_ticks=horizon_ticks,
        per_seed=per_seed,
        summary=_summarize(per_seed, arms),
    )


# ---------------------------------------------------------------------------
# E1 — Agency acquisition ablation (§112)
# ---------------------------------------------------------------------------
_E1_ARMS = {
    "full": {},
    "no_counterfactual_evidence": {"use_counterfactual_evidence": False},
    "no_agency_model": {"use_agency_model": False},
}


def _acquisition_metrics(runtime: OrganismRuntime, body: CausalBody) -> dict[str, Any]:
    domain = runtime._action_domain
    acquisition = domain.acquisition
    inert = {
        opaque_channel_ref(actuator_id)
        for actuator_id in body.surface.actuator_ids
        if body.driven_receptor(actuator_id) is None
    }
    dimensions = acquisition.action_dimensions.items
    false_positive = [
        item
        for item in dimensions
        if set(acquisition.action_dimensions.channel_refs(item.dimension_id)) <= inert
    ]
    specificity = [
        estimate.causal_specificity
        for estimate in acquisition.agency_model.estimates_for(CausalSourceKind.DIMENSION)
    ]
    advantages = [
        estimate.causal_advantage
        for estimate in acquisition.controllability_model.estimates_for(CausalSourceKind.DIMENSION)
        if estimate.causal_advantage is not None
    ]
    competences = domain.competence_library.items
    return {
        "action_dimensions": len(dimensions),
        "false_positive_dimensions": len(false_positive),
        "agentic_dimensions": len(acquisition.agentic_dimension_ids()),
        "mean_causal_specificity": _mean(specificity),
        "mean_causal_advantage": _mean(advantages),
        "competences_acquired": len(competences),
        "executable_competences": sum(
            1 for item in competences if domain.competence_is_executable(item)
        ),
        "mean_reproducibility": _mean(item.evidence.reproducibility for item in competences),
    }


def run_agency_acquisition_ablation_study(
    *,
    seeds: Sequence[int] = DEFAULT_SEEDS,
    ticks: int = 1500,
    actuator_count: int = 4,
    inert_actuator_count: int = 2,
) -> dict[str, Any]:
    """E1: full vs no counterfactual evidence vs no AgencyModel, same bodies and seeds."""
    resolved = _seeds(seeds)
    per_seed: list[dict[str, Any]] = []
    for seed in resolved:
        row: dict[str, Any] = {"seed": seed, "arms": {}}
        for arm, options in _E1_ARMS.items():
            body = CausalBody(
                actuator_count=_positive(actuator_count, "actuator_count"),
                seed=seed,
                inert_actuator_count=int(inert_actuator_count),
            )
            runtime = build_subject(
                body,
                organism_id=f"agency-e1-{seed}",
                agency_acquisition=AgencyAcquisition(**options),
            )
            _advance(runtime, body, _positive(ticks, "ticks"))
            row["arms"][arm] = _acquisition_metrics(runtime, body)
        per_seed.append(row)
    keys = next(iter(per_seed))["arms"]["full"].keys()
    return {
        "protocol": "learning.agency-acquisition-ablation",
        "seeds": list(resolved),
        "ticks": ticks,
        "inert_actuator_count": inert_actuator_count,
        "per_seed": per_seed,
        "summary": {
            arm: {
                key: _mean(
                    item["arms"][arm][key]
                    for item in per_seed
                    if item["arms"][arm][key] is not None
                )
                for key in keys
            }
            for arm in _E1_ARMS
        },
    }


# ---------------------------------------------------------------------------
# E2 / E3 / E5 — matched executive comparisons (§113, §114, §116)
# ---------------------------------------------------------------------------
def run_executive_bridge_ablation_study(
    *,
    seeds: Sequence[int] = DEFAULT_SEEDS,
    actuator_count: int = 4,
    warmup_limit: int = 2000,
    settle_ticks: int = 64,
    horizon_ticks: int = 1024,
) -> dict[str, Any]:
    """E2 v3: direct proposal versus ActionIntent without and with outcome learning."""
    return _matched_study(
        "learning.agency-executive-bridge-ablation",
        {
            "direct_proposal": {
                "executive_mode": ExecutiveMode.DIRECT_PROPOSAL,
                "intention_policy": IntentionPolicy(executive_outcome_learning=False),
            },
            "action_intent": {
                "executive_mode": ExecutiveMode.FULL,
                "intention_policy": IntentionPolicy(executive_outcome_learning=False),
            },
            "action_intent_outcome_learning": {"executive_mode": ExecutiveMode.FULL},
        },
        seeds=seeds,
        actuator_count=actuator_count,
        warmup_limit=warmup_limit,
        settle_ticks=settle_ticks,
        horizon_ticks=horizon_ticks,
    ).as_dict()


def run_intent_persistence_study(
    *,
    seeds: Sequence[int] = DEFAULT_SEEDS,
    actuator_count: int = 4,
    warmup_limit: int = 2000,
    settle_ticks: int = 64,
    horizon_ticks: int = 1024,
) -> dict[str, Any]:
    """E3: persistent ActionIntent versus re-deciding every tick."""
    return _matched_study(
        "learning.agency-intent-persistence",
        {
            "persistent_intent": {"executive_mode": ExecutiveMode.FULL},
            "redecide_each_tick": {"executive_mode": ExecutiveMode.REDECIDE_EACH_TICK},
        },
        seeds=seeds,
        actuator_count=actuator_count,
        warmup_limit=warmup_limit,
        settle_ticks=settle_ticks,
        horizon_ticks=horizon_ticks,
    ).as_dict()


def run_intentional_causal_advantage_study(
    *,
    seeds: Sequence[int] = DEFAULT_SEEDS,
    actuator_count: int = 4,
    warmup_limit: int = 2000,
    settle_ticks: int = 64,
    horizon_ticks: int = 1024,
) -> dict[str, Any]:
    """E5 v3: direct / unreconciled / reconciled / reconciled + outcome learning.

    C vs B asks whether reconciling real effects helps; D vs C asks whether
    using that reconciliation for future admission helps (EOL v1 §11).
    """
    return _matched_study(
        "learning.agency-intentional-causal-advantage",
        {
            "A_direct_proposal": {
                "executive_mode": ExecutiveMode.DIRECT_PROPOSAL,
                "intention_policy": IntentionPolicy(executive_outcome_learning=False),
            },
            "B_unreconciled_intent": {
                "executive_mode": ExecutiveMode.UNRECONCILED_INTENT,
                "intention_policy": IntentionPolicy(
                    reconcile_observed_effects=False, executive_outcome_learning=False
                ),
            },
            "C_reconciled_intent": {
                "executive_mode": ExecutiveMode.FULL,
                "intention_policy": IntentionPolicy(executive_outcome_learning=False),
            },
            "D_reconciled_intent_outcome_learning": {"executive_mode": ExecutiveMode.FULL},
        },
        seeds=seeds,
        actuator_count=actuator_count,
        warmup_limit=warmup_limit,
        settle_ticks=settle_ticks,
        horizon_ticks=horizon_ticks,
    ).as_dict()


# ---------------------------------------------------------------------------
# E4 — Embodied causal intervention (§115)
# ---------------------------------------------------------------------------
_Relation = tuple[str, str]  # (dimension id, effect id)


def _revision_state(runtime: OrganismRuntime) -> dict[str, Any]:
    domain = runtime._action_domain
    acquisition = domain.acquisition
    control = {
        (estimate.source_ref, estimate.effect_id): estimate.confidence
        for estimate in acquisition.controllability_model.estimates_for(CausalSourceKind.DIMENSION)
    }
    agency = {
        (estimate.source_ref, estimate.effect_id): estimate.confidence
        for estimate in acquisition.agency_model.estimates_for(CausalSourceKind.DIMENSION)
    }
    return {
        "control": control,
        "agency": agency,
        "families": {
            item.dimension_id: tuple(item.intervention_signature_refs)
            for item in acquisition.action_dimensions.items
        },
        "agentic": set(acquisition.agentic_dimension_ids()),
        "boundary_revisions": runtime._body_schema.boundary_revision_count,
        "affordances": {item.competence_id for item in domain.last_affordances},
        "intent_failures": domain.intention.counts[IntentStatus.FAILED],
    }


def _relation_classes(
    runtime: OrganismRuntime, body: CausalBody, condition: BodyCondition
) -> tuple[set[_Relation], set[_Relation]]:
    """Ground truth: believed relations the perturbation invalidates or leaves intact.

    A believed (dimension, effect) relation is invalidated when its effect
    involves a receptor that the dimension's outputs drive under the normal
    mapping but no longer drive under ``condition``; it is intact when its
    effect involves only receptors the dimension still drives.  Relations whose
    effect involves none of the dimension's driven receptors (e.g. passive
    distractor co-occurrence) belong to neither set.  The mapping from
    receptors to the organism's private signal ids is evaluator-only.
    """
    reference = copy.deepcopy(body)
    reference.set_condition(BodyCondition.NORMAL)
    perturbed = copy.deepcopy(body)
    perturbed.set_condition(condition)
    identity = runtime._signal_identity
    acquisition = runtime._action_domain.acquisition
    registry = acquisition.action_dimensions
    actuator_by_channel = {
        opaque_channel_ref(actuator_id): actuator_id for actuator_id in body.surface.actuator_ids
    }

    def driven(model: CausalBody, actuators: list[str]) -> set[str]:
        return {
            identity.signal_id(receptor_id)
            for actuator_id in actuators
            if (receptor_id := model.driven_receptor(actuator_id)) is not None
        }

    invalidated: set[_Relation] = set()
    intact: set[_Relation] = set()
    for estimate in acquisition.controllability_model.estimates_for(CausalSourceKind.DIMENSION):
        effect = acquisition.effect_space.get(estimate.effect_id)
        if estimate.confidence <= 0.0 or effect is None:
            continue
        actuators = [
            actuator_by_channel[channel]
            for channel in registry.channel_refs(estimate.source_ref)
            if channel in actuator_by_channel
        ]
        normal = driven(reference, actuators)
        lost = normal - driven(perturbed, actuators)
        features = set(effect.feature_refs)
        relation = (estimate.source_ref, estimate.effect_id)
        if features & lost:
            invalidated.add(relation)
        elif features & normal:
            intact.add(relation)
    return invalidated, intact


class _AttemptCounter:
    """Evaluator-side count of closed attempts per intervention family."""

    def __init__(self) -> None:
        self.by_signature: dict[str, int] = {}
        self._last: object | None = None

    def __call__(self, runtime: OrganismRuntime) -> None:
        attempt = runtime._action_domain.acquisition.last_attempt
        if attempt is not None and attempt is not self._last:
            self._last = attempt
            key = attempt.intervention_signature_id
            self.by_signature[key] = self.by_signature.get(key, 0) + 1


def _relation_revision(
    before: dict[str, Any],
    after: dict[str, Any],
    relations: set[_Relation],
    attempts: dict[str, int],
) -> dict[str, float | None]:
    ordered = sorted(relations)

    def drop(key: str) -> float | None:
        return _mean(
            before[key][relation] - after[key].get(relation, 0.0)
            for relation in ordered
            if relation in before[key]
        )

    retested = [
        relation
        for relation in ordered
        if any(attempts.get(ref, 0) for ref in before["families"].get(relation[0], ()))
    ]
    return {
        "relations": float(len(ordered)),
        "controllability_drop": drop("control"),
        "agency_drop": drop("agency"),
        "controllability_after": _mean(after["control"].get(r, 0.0) for r in ordered),
        "retested_fraction": (len(retested) / len(ordered)) if ordered else None,
    }


def _revision(
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    invalidated: set[_Relation],
    intact: set[_Relation],
    attempts: dict[str, int],
) -> dict[str, Any]:
    """How much the organism revised what it believed it could cause (§115)."""
    union = before["affordances"] | after["affordances"]
    return {
        "invalidated": _relation_revision(before, after, invalidated, attempts),
        "intact": _relation_revision(before, after, intact, attempts),
        "lost_agentic_dimensions": len(before["agentic"] - after["agentic"]),
        "new_dimensions": len(set(after["families"]) - set(before["families"])),
        "body_schema_revisions": after["boundary_revisions"] - before["boundary_revisions"],
        "affordance_turnover": (
            len(union - (before["affordances"] & after["affordances"])) / len(union)
            if union
            else 0.0
        ),
        "intent_failures": after["intent_failures"] - before["intent_failures"],
    }


def run_embodied_causal_intervention_study(
    *,
    seeds: Sequence[int] = DEFAULT_SEEDS,
    actuator_count: int = 4,
    warmup_limit: int = 2000,
    settle_ticks: int = 64,
    horizon_ticks: int = 1024,
) -> dict[str, Any]:
    """E4: after acquisition, the body mapping is normal, permuted or broken.

    For each perturbed condition the same ground-truth relation sets are also
    measured in the unperturbed (normal) twin, which is the matched control.
    """
    resolved = _seeds(seeds)
    per_seed: list[dict[str, Any]] = []
    perturbations = (BodyCondition.PERMUTED, BodyCondition.BROKEN_EFFECTOR)
    for seed in resolved:
        runtime, body, acquired_at = _prepare_acquired(
            seed,
            actuator_count=_positive(actuator_count, "actuator_count"),
            warmup_limit=_positive(warmup_limit, "warmup_limit"),
            settle_ticks=max(0, int(settle_ticks)),
        )
        row: dict[str, Any] = {"seed": seed, "acquired_at_tick": acquired_at, "conditions": {}}
        if acquired_at is not None:
            classes = {
                condition: _relation_classes(runtime, body, condition)
                for condition in perturbations
            }
            # Affordances are derived per tick and never checkpointed, so a
            # freshly restored twin has none yet: the pre-perturbation state is
            # read from the source organism the twins continue from.
            before = _revision_state(runtime)
            states: dict[BodyCondition, tuple[dict[str, Any], dict[str, int]]] = {}
            for condition in BodyCondition:
                twin, twin_body = _twin(runtime, body)
                twin_body.set_condition(condition)
                counter = _AttemptCounter()
                _advance(twin, twin_body, _positive(horizon_ticks, "horizon_ticks"), counter)
                states[condition] = (_revision_state(twin), counter.by_signature)
            for condition in perturbations:
                invalidated, intact = classes[condition]
                row["conditions"][condition.value] = {
                    **_revision(
                        before,
                        states[condition][0],
                        invalidated=invalidated,
                        intact=intact,
                        attempts=states[condition][1],
                    ),
                    "normal_control": _revision(
                        before,
                        states[BodyCondition.NORMAL][0],
                        invalidated=invalidated,
                        intact=intact,
                        attempts=states[BodyCondition.NORMAL][1],
                    ),
                }
        per_seed.append(row)

    relation_keys = (
        "controllability_drop",
        "agency_drop",
        "controllability_after",
        "retested_fraction",
    )
    scalar_keys = (
        "lost_agentic_dimensions",
        "new_dimensions",
        "body_schema_revisions",
        "affordance_turnover",
        "intent_failures",
    )

    def summary(path: tuple[str, ...]) -> dict[str, float | None]:
        out: dict[str, float | None] = {}
        for condition in perturbations:
            nodes = []
            for item in per_seed:
                node = item["conditions"].get(condition.value)
                for part in path:
                    node = node.get(part) if isinstance(node, dict) else None
                if isinstance(node, dict):
                    nodes.append(node)
            for arm in ("invalidated", "intact"):
                for key in relation_keys:
                    out[f"{condition.value}.{arm}.{key}"] = _mean(
                        value for node in nodes if (value := node[arm].get(key)) is not None
                    )
            for key in scalar_keys:
                out[f"{condition.value}.{key}"] = _mean(node[key] for node in nodes)
        return out

    return {
        "protocol": "learning.agency-embodied-causal-intervention",
        "seeds": list(resolved),
        "horizon_ticks": horizon_ticks,
        "per_seed": per_seed,
        "summary": {
            "perturbed_twin": summary(()),
            "normal_control_twin": summary(("normal_control",)),
        },
    }


# ---------------------------------------------------------------------------
# E4-v4 — Causal belief revision after perturbation of a consolidated relation
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ConsolidationGate:
    """Preregistered entry criterion: perturb only consolidated, observable relations."""

    min_support: int = 16
    min_controllability: float = 0.10
    min_agency: float = 0.10
    stability_ticks: int = 128
    max_wait_ticks: int = 4096
    # Protocol v2: relations are only gated once the organism is this many
    # ticks past acquisition, so perturbation does not land in the early
    # developmental drift that erased the E4 v3 contrast.
    min_age_ticks: int = 0


def _consolidated_candidates(
    runtime: OrganismRuntime, invalidated: set[_Relation], gate: ConsolidationGate
) -> set[_Relation]:
    acquisition = runtime._action_domain.acquisition
    passing: set[_Relation] = set()
    for dimension_id, effect_id in invalidated:
        control = acquisition.controllability_model.estimate(
            source_kind=CausalSourceKind.DIMENSION, source_ref=dimension_id, effect_id=effect_id
        )
        agency = acquisition.agency_model.estimate(
            source_kind=CausalSourceKind.DIMENSION, source_ref=dimension_id, effect_id=effect_id
        )
        if (
            control is not None
            and agency is not None
            and control.action_support >= gate.min_support
            and control.confidence >= gate.min_controllability
            and agency.confidence >= gate.min_agency
        ):
            passing.add((dimension_id, effect_id))
    return passing


def _relation_levels(runtime: OrganismRuntime, relations: set[_Relation]) -> dict[str, Any]:
    state = _revision_state(runtime)
    ordered = sorted(relations)
    return {
        "controllability": _mean(state["control"].get(r, 0.0) for r in ordered),
        "agency": _mean(state["agency"].get(r, 0.0) for r in ordered),
    }


def run_consolidated_causal_intervention_study(
    *,
    seeds: Sequence[int] = DEFAULT_SEEDS,
    actuator_count: int = 4,
    warmup_limit: int = 2000,
    gate: ConsolidationGate = ConsolidationGate(),
    horizons: Sequence[int] = (128, 256, 512, 1024, 2048),
    primary_horizon: int = 1024,
) -> dict[str, Any]:
    """E4-v4: perturb one twin only once a relation it invalidates is consolidated.

    After acquisition the organism develops normally.  For each perturbed
    condition, the apparatus waits until at least one relation that condition
    would invalidate (ground truth) meets the preregistered consolidation gate
    continuously for ``gate.stability_ticks``; the organism is then split into
    a perturbed twin and a normal control twin from the same checkpoint and
    both are observed at the preregistered horizons.  The primary endpoint is
    the normal-minus-perturbed residual controllability of the gated relations
    at ``primary_horizon``.  Nothing about the gate reaches the organism.
    """
    resolved = _seeds(seeds)
    ordered_horizons = tuple(sorted({_positive(h, "horizon") for h in horizons}))
    if primary_horizon not in ordered_horizons:
        raise ValueError("primary_horizon must be one of the preregistered horizons")
    perturbations = (BodyCondition.BROKEN_EFFECTOR, BodyCondition.PERMUTED)
    per_seed: list[dict[str, Any]] = []
    for seed in resolved:
        runtime, body, acquired_at = _prepare_acquired(
            seed,
            actuator_count=_positive(actuator_count, "actuator_count"),
            warmup_limit=_positive(warmup_limit, "warmup_limit"),
            settle_ticks=0,
        )
        row: dict[str, Any] = {"seed": seed, "acquired_at_tick": acquired_at, "conditions": {}}
        per_seed.append(row)
        if acquired_at is None:
            continue
        pending = set(perturbations)
        streaks: dict[BodyCondition, dict[_Relation, int]] = {c: {} for c in perturbations}
        if gate.min_age_ticks < 0 or gate.min_age_ticks >= gate.max_wait_ticks:
            raise ValueError("min_age_ticks must be within [0, max_wait_ticks)")
        for _ in range(_positive(gate.max_wait_ticks, "max_wait_ticks")):
            if not pending:
                break
            _advance(runtime, body, 1)
            if runtime.tick_count - acquired_at <= gate.min_age_ticks:
                continue
            for condition in sorted(pending):
                invalidated, intact = _relation_classes(runtime, body, condition)
                passing = _consolidated_candidates(runtime, invalidated, gate)
                streaks[condition] = {
                    relation: streaks[condition].get(relation, 0) + 1 for relation in passing
                }
                gated = {
                    relation
                    for relation, count in streaks[condition].items()
                    if count >= gate.stability_ticks
                }
                if not gated:
                    continue
                pending.discard(condition)
                before = _revision_state(runtime)
                result: dict[str, Any] = {
                    "onset_tick": runtime.tick_count,
                    "gated_relations": len(gated),
                    "at_onset": _relation_levels(runtime, gated),
                    "horizons": {},
                }
                twins = {}
                for arm, arm_condition in (
                    ("perturbed", condition),
                    ("normal_control", BodyCondition.NORMAL),
                ):
                    twin, twin_body = _twin(runtime, body)
                    twin_body.set_condition(arm_condition)
                    twins[arm] = (twin, twin_body, _AttemptCounter())
                elapsed = 0
                for horizon in ordered_horizons:
                    point: dict[str, Any] = {}
                    for arm, (twin, twin_body, counter) in twins.items():
                        _advance(twin, twin_body, horizon - elapsed, counter)
                        point[arm] = {
                            "gated": _relation_levels(twin, gated),
                            **_revision(
                                before,
                                _revision_state(twin),
                                invalidated=invalidated,
                                intact=intact,
                                attempts=counter.by_signature,
                            ),
                        }
                    normal = point["normal_control"]["gated"]["controllability"]
                    perturbed = point["perturbed"]["gated"]["controllability"]
                    point["residual_controllability_gap"] = (
                        normal - perturbed if normal is not None and perturbed is not None else None
                    )
                    result["horizons"][str(horizon)] = point
                    elapsed = horizon
                row["conditions"][condition.value] = result

    def summary(condition: BodyCondition) -> dict[str, Any]:
        rows = [
            item["conditions"][condition.value]
            for item in per_seed
            if condition.value in item["conditions"]
        ]
        by_horizon: dict[str, Any] = {}
        for horizon in ordered_horizons:
            gaps = [
                gap
                for item in rows
                if (gap := item["horizons"][str(horizon)]["residual_controllability_gap"])
                is not None
            ]
            by_horizon[str(horizon)] = {
                "mean_residual_controllability_gap": _mean(gaps),
                "positive_seeds": sum(1 for gap in gaps if gap > 0),
                "testable_seeds": len(gaps),
            }
        primary = by_horizon[str(primary_horizon)]
        supported = (
            primary["testable_seeds"] > 0
            and primary["positive_seeds"] >= 0.75 * primary["testable_seeds"]
            and (primary["mean_residual_controllability_gap"] or 0.0) > 0.0
        )
        return {"by_horizon": by_horizon, "primary_endpoint_supported": supported}

    return {
        "protocol": "learning.agency-consolidated-causal-intervention",
        "seeds": list(resolved),
        "gate": asdict(gate),
        "horizons": list(ordered_horizons),
        "primary_horizon": primary_horizon,
        "per_seed": per_seed,
        "summary": {condition.value: summary(condition) for condition in perturbations},
    }


# ---------------------------------------------------------------------------
# E8 — High-dimensional acquisition (Factorized Effect Representation v1 §10)
# ---------------------------------------------------------------------------
def _high_dimensional_metrics(runtime: OrganismRuntime) -> dict[str, Any]:
    domain = runtime._action_domain
    acquisition = domain.acquisition
    space = acquisition.effect_space
    evidence = acquisition.causal_evidence.intervention_evidence
    effectful = [item.effect_id for item in evidence if item.effect_id is not None]
    recurring = {
        effect.effect_id for effect in space.effects if effect.support >= _RECURRENCE_SUPPORT
    }
    competences = domain.competence_library.items
    intention = domain.intention
    ledger = intention.outcome_ledger.metrics()
    return {
        "attempts": acquisition.attempt_count,
        "effectful_evidence": len(effectful),
        "distinct_effects_in_evidence": len(set(effectful)),
        "recurring_effect_fraction": (
            sum(1 for effect_id in effectful if effect_id in recurring) / len(effectful)
            if effectful
            else None
        ),
        "effect_space_size": len(space.effects),
        "action_dimensions": len(acquisition.action_dimensions.items),
        "agentic_dimensions": len(acquisition.agentic_dimension_ids()),
        "competences": len(competences),
        "competences_with_effect": sum(1 for item in competences if item.effect_id is not None),
        "executable_competences": sum(
            1 for item in competences if domain.competence_is_executable(item)
        ),
        "execution_bindings": len(domain.execution_bindings.items),
        "intents_terminated": sum(intention.counts.values()),
        "intents_satisfied": intention.counts[IntentStatus.SATISFIED],
        "outcome_learning_history_hit_rate": ledger["history_hit_rate"],
        "footprints": len(acquisition.footprints.footprints),
        "footprint_competences": sum(
            1
            for item in competences
            if item.effect_id is not None
            and acquisition.effect_space.footprint_atoms(item.effect_id) is not None
        ),
    }


_RECURRENCE_SUPPORT = 4


_RECONCILIATIONS = ("recall", "chance_corrected")


def _reconciliation_options(reconciliation: str) -> dict[str, Any]:
    """Factorized Effects §16 arms: R (current recall) or AB (rules A and B)."""
    if reconciliation not in _RECONCILIATIONS:
        raise ValueError(f"reconciliation must be one of {_RECONCILIATIONS}")
    if reconciliation == "recall":
        return {}
    return {
        "intention_policy": IntentionPolicy(
            footprint_satisfaction_rule="chance_corrected",
            mismatch_known_features_only=True,
        )
    }


def _intent_terminations(runtime: OrganismRuntime, body: CausalBody) -> Callable[[], dict]:
    """Collect intent terminations and classify satisfactions against the
    body's ground truth (evaluator-only): spurious when every matched atom
    lies on a receptor no actuator drives."""
    events: list[Any] = []
    runtime.provenance.subscribe(
        lambda event: events.append(event) if event.domain == "intention" else None
    )
    driven = {
        receptor
        for actuator_id in body.surface.actuator_ids
        for receptor in body.driven_receptors(actuator_id)
    }
    identity = runtime._signal_identity
    receptor_of = {identity.signal_id(receptor): receptor for receptor in body.receptor_ids}

    def summary() -> dict[str, Any]:
        reasons: dict[str, int] = {}
        spurious = unmapped = 0
        for event in events:
            if event.operation in ("form", "learn", "lift_suppression"):
                continue
            key = f"{event.operation}:{event.rule}"
            reasons[key] = reasons.get(key, 0) + 1
            if event.operation != "satisfied":
                continue
            matched = [a for a in str(event.parameters.get("matched_atoms", "")).split(",") if a]
            receptors = [receptor_of.get(atom.rsplit("|", 1)[0]) for atom in matched]
            unmapped += sum(1 for receptor in receptors if receptor is None)
            if matched and all(r is not None and r not in driven for r in receptors):
                spurious += 1
        return {
            "terminal_reasons": dict(sorted(reasons.items())),
            "spurious_satisfactions": spurious,
            "unmapped_matched_atoms": unmapped,
        }

    return summary


def run_high_dimensional_acquisition_study(
    *,
    seeds: Sequence[int] = DEFAULT_SEEDS,
    ticks: int = 3000,
    actuator_count: int = 16,
    receptors_per_actuator: int = 4,
    drifting_receptor_count: int = 32,
    factorized_effects: bool = False,
    reconciliation: str = "recall",
) -> dict[str, Any]:
    """E8: does the acquisition -> intent chain engage in a many-receptor body?

    Outputs drive several correlated receptors and many receptors drift on
    their own, as in a physical body.  Reported: effect recurrence, dimensions,
    competences with an effect, bindings, intents formed and satisfied.
    """
    resolved = _seeds(seeds)
    per_seed = []
    for seed in resolved:
        body = CausalBody(
            actuator_count=_positive(actuator_count, "actuator_count"),
            seed=seed,
            receptors_per_actuator=receptors_per_actuator,
            drifting_receptor_count=drifting_receptor_count,
        )
        runtime = build_subject(
            body,
            organism_id=f"agency-high-dimensional-{seed}",
            factorized_effects=bool(factorized_effects),
            **_reconciliation_options(reconciliation),
        )
        terminations = _intent_terminations(runtime, body)
        _advance(runtime, body, _positive(ticks, "ticks"))
        metrics = _high_dimensional_metrics(runtime)
        terminated = metrics["intents_terminated"]
        per_seed.append(
            {
                "seed": seed,
                "receptors": len(body.receptor_ids),
                **metrics,
                "satisfied_rate": metrics["intents_satisfied"] / terminated if terminated else 0.0,
                **terminations(),
            }
        )
    keys = (
        [
            key
            for key, value in per_seed[0].items()
            if key not in ("seed", "receptors") and not isinstance(value, dict)
        ]
        if per_seed
        else []
    )
    return {
        "protocol": "learning.agency-high-dimensional-acquisition",
        "factorized_effects": bool(factorized_effects),
        "reconciliation": reconciliation,
        "seeds": list(resolved),
        "ticks": ticks,
        "body": {
            "actuator_count": actuator_count,
            "receptors_per_actuator": receptors_per_actuator,
            "drifting_receptor_count": drifting_receptor_count,
        },
        "per_seed": per_seed,
        "summary": {
            key: _mean(row[key] for row in per_seed if row[key] is not None) for key in keys
        },
    }


# ---------------------------------------------------------------------------
# E6 — Acquisition -> deliberate reuse closure: the release gate (§117-§118)
# ---------------------------------------------------------------------------
_MILESTONES = (
    "first_action_attempt",
    "first_recurring_intervention_signature",
    "first_action_dimension",
    "first_agentic_action_dimension",
    "first_motor_competence",
    "first_affordance",
    "first_action_intent",
    "first_satisfied_intent",
)


def _milestone_checks(runtime: OrganismRuntime) -> dict[str, bool]:
    domain = runtime._action_domain
    acquisition = domain.acquisition
    return {
        "first_action_attempt": acquisition.attempt_count > 0,
        "first_recurring_intervention_signature": acquisition.signatures.recurring_count > 0,
        "first_action_dimension": bool(acquisition.action_dimensions.items),
        "first_agentic_action_dimension": bool(acquisition.agentic_dimension_ids()),
        "first_motor_competence": bool(domain.competence_library.items),
        "first_affordance": bool(domain.last_affordances),
        "first_action_intent": domain.intention.active is not None,
        "first_satisfied_intent": any(
            outcome.status is IntentStatus.SATISFIED for outcome in domain.intention.last_outcomes
        ),
    }


def _traces_to_pulses(runtime: OrganismRuntime, competence_id: str) -> bool:
    """Provenance reaches pulse commitments from the competence's grounding."""
    events = runtime._action_domain.acquisition.provenance.events()
    produced = {ref: event for event in events for ref in (event.produced or (event.subject,))}
    grounding = next(
        (
            event
            for event in events
            if event.operation == "ground" and event.subject.id == competence_id
        ),
        None,
    )
    if grounding is None:
        return False
    frontier, seen = list(grounding.caused_by), set()
    while frontier:
        ref = frontier.pop()
        if ref.kind == "commitment":
            return True
        if ref in seen or ref not in produced:
            continue
        seen.add(ref)
        frontier.extend(produced[ref].caused_by)
    return False


def _closure_seed(
    seed: int,
    *,
    actuator_count: int,
    max_ticks: int,
    factorized_effects: bool = False,
    reconciliation: str = "recall",
) -> dict[str, Any]:
    body = CausalBody(actuator_count=actuator_count, seed=seed)
    runtime = build_subject(
        body,
        organism_id=f"agency-e6-{seed}",
        factorized_effects=factorized_effects,
        **_reconciliation_options(reconciliation),
    )
    domain = runtime._action_domain
    milestones: dict[str, int | None] = {name: None for name in _MILESTONES}
    trace: dict[str, Any] | None = None
    for _ in range(max_ticks):
        runtime.tick()
        for name, reached in _milestone_checks(runtime).items():
            if reached and milestones[name] is None:
                milestones[name] = runtime.tick_count
        body.advance(runtime.last_actuations)
        if milestones["first_satisfied_intent"] is not None:
            trace = domain.action_trace()
            break
    closed = trace is not None and trace.get("result") == IntentStatus.SATISFIED.value
    self_acquired = False
    if closed and trace is not None:
        competence = domain.competence_library.get(trace["competence_id"])
        binding = domain.execution_bindings.get(trace["competence_id"])
        # The reused competence is the organism's own: it was grounded in
        # ledger evidence produced by its own exploration.
        exploration_evidence = {
            item.evidence_id
            for item in domain.causal_evidence.evidence
            if item.competence_id is None and not item.is_passive
        }
        self_acquired = (
            competence is not None
            and binding is not None
            and bool(set(competence.evidence.controllability_evidence_refs) & exploration_evidence)
        )
    reached = [milestones[name] for name in _MILESTONES]
    ordered = [value for value in reached if value is not None]
    return {
        "seed": seed,
        "milestones": milestones,
        "acquisition_precedes_reuse": len(ordered) == len(reached) and ordered == sorted(ordered),
        "closed": closed,
        "self_acquired_competence": self_acquired,
        "trace": trace,
        "factorized_effects": factorized_effects,
        "traces_to_pulses": (
            _traces_to_pulses(runtime, trace["competence_id"])
            if factorized_effects and trace is not None
            else None
        ),
    }


def run_acquisition_reuse_closure_study(
    *,
    seeds: Sequence[int] = DEFAULT_SEEDS,
    actuator_count: int = 4,
    max_ticks: int = 3000,
    factorized_effects: bool = False,
    reconciliation: str = "recall",
) -> dict[str, Any]:
    """E6 release gate: one organism acquires agency, then deliberately reuses it."""
    resolved = _seeds(seeds)
    per_seed = [
        _closure_seed(
            seed,
            actuator_count=_positive(actuator_count, "actuator_count"),
            max_ticks=_positive(max_ticks, "max_ticks"),
            factorized_effects=bool(factorized_effects),
            reconciliation=reconciliation,
        )
        for seed in resolved
    ]
    return {
        "protocol": "learning.agency-acquisition-reuse-closure",
        "factorized_effects": bool(factorized_effects),
        "reconciliation": reconciliation,
        "seeds": list(resolved),
        "max_ticks": max_ticks,
        "per_seed": per_seed,
        "release_gate_passed": all(
            item["closed"] and item["self_acquired_competence"] for item in per_seed
        ),
    }


__all__ = [
    "ConsolidationGate",
    "run_acquisition_reuse_closure_study",
    "run_consolidated_causal_intervention_study",
    "run_agency_acquisition_ablation_study",
    "run_embodied_causal_intervention_study",
    "run_executive_bridge_ablation_study",
    "run_high_dimensional_acquisition_study",
    "run_intent_persistence_study",
    "run_intentional_causal_advantage_study",
]
