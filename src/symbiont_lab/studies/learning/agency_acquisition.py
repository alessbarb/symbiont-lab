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
        _advance(twin, twin_body, horizon_ticks, recorder)
        result["arms"][name] = asdict(recorder.metrics())
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
    """E2: competence/readout -> proposal versus competence -> ActionIntent -> proposal."""
    return _matched_study(
        "learning.agency-executive-bridge-ablation",
        {
            "direct_proposal": {"executive_mode": ExecutiveMode.DIRECT_PROPOSAL},
            "action_intent": {"executive_mode": ExecutiveMode.FULL},
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
    """E5: direct proposal vs unreconciled intent vs full reconciled intent."""
    return _matched_study(
        "learning.agency-intentional-causal-advantage",
        {
            "A_direct_proposal": {"executive_mode": ExecutiveMode.DIRECT_PROPOSAL},
            "B_unreconciled_intent": {
                "executive_mode": ExecutiveMode.UNRECONCILED_INTENT,
                "intention_policy": IntentionPolicy(reconcile_observed_effects=False),
            },
            "C_reconciled_intent": {"executive_mode": ExecutiveMode.FULL},
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


def _closure_seed(seed: int, *, actuator_count: int, max_ticks: int) -> dict[str, Any]:
    body = CausalBody(actuator_count=actuator_count, seed=seed)
    runtime = build_subject(body, organism_id=f"agency-e6-{seed}")
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
    }


def run_acquisition_reuse_closure_study(
    *,
    seeds: Sequence[int] = DEFAULT_SEEDS,
    actuator_count: int = 4,
    max_ticks: int = 3000,
) -> dict[str, Any]:
    """E6 release gate: one organism acquires agency, then deliberately reuses it."""
    resolved = _seeds(seeds)
    per_seed = [
        _closure_seed(
            seed,
            actuator_count=_positive(actuator_count, "actuator_count"),
            max_ticks=_positive(max_ticks, "max_ticks"),
        )
        for seed in resolved
    ]
    return {
        "protocol": "learning.agency-acquisition-reuse-closure",
        "seeds": list(resolved),
        "max_ticks": max_ticks,
        "per_seed": per_seed,
        "release_gate_passed": all(
            item["closed"] and item["self_acquired_competence"] for item in per_seed
        ),
    }


__all__ = [
    "run_acquisition_reuse_closure_study",
    "run_agency_acquisition_ablation_study",
    "run_embodied_causal_intervention_study",
    "run_executive_bridge_ablation_study",
    "run_intent_persistence_study",
    "run_intentional_causal_advantage_study",
]
