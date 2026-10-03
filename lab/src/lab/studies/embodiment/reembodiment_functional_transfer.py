"""Re-embodiment Functional Transfer v1: apparatus, runs and decision rule.

Implements the frozen protocol
``docs/design/experimentation/reembodiment-functional-transfer-v1.md``.

The question is whether what an organism learned in one Body makes it reach a
valid execution binding sooner in a new Body than an equally old organism that
learned something unrelated, and than a newborn. Evaluator truth (the Body
relation, the arm, the mapping, every score) stays in this module; nothing here
is handed to the organism.

Mechanical helpers and the decision rule are pure and are what the contract
tests exercise. Running seeds is a governed scientific run, not a test.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import statistics
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

from lab.integration.organism import restore_canonical_organism
from lab.studies.learning.agency_acquisition_body import (
    CausalBody,
    build_subject,
    subject_lifecycle,
)
from symbiont.actuation.binding import BindingStatus
from symbiont.cognition.limits import KernelLimits
from symbiont.core.embodiment.transition import (
    EmbodimentDescriptor,
    prepare_fresh_embodiment_checkpoint,
)
from symbiont.core.organism_profile import CANONICAL
from symbiont.host.checkpoint import verify_checkpoint_identity
from symbiont.host.continuity import REGISTER, LongitudinalContract, Reembodiment
from symbiont.modeling.private_runtime import PrivateModelOrganismRuntime

# Longitudinal contract of the subject this module builds (issue #273).
LONGITUDINAL_CONTRACT = LongitudinalContract.CANONICAL_REEMBODIMENT

PROTOCOL = "embodiment.reembodiment-functional-transfer"
ACTUATORS = 4
ARMS = ("transfer", "sham_experience", "naive")
RELATIONS = ("same_structure", "partial", "unrelated")
# r7: nine development seeds, none in the confirmation list and not 127.
DEVELOPMENT_SEEDS = (101, 103, 107, 109, 113, 131, 137, 139, 149)
CONFIRMATION_SEEDS = (173, 211, 257, 307, 353, 401, 457, 503, 557, 601, 653, 701)

# Frozen decision parameters (protocol §5-§7).
D_STEP = 100
# r8: 2000 (was 1000); the D rule itself is unchanged.
D_MAX = 2000
MAX_BODY_DIFFICULTY_SPREAD = 0.15
MIN_SEEDS_IMPROVED = 10
MIN_MEDIAN_PAIRED_REDUCTION = 0.20
PRACTICAL_NULL_MARGIN = 0.10
MAX_ACTIVITY_RATE_RATIO = 1.20
MAX_CONTAMINATED_SEEDS = 2

# The balanced Body family (protocol §4.2.1). Every Body has the same shape and
# construction seed, so actuator and receptor identifiers are shared; only the
# bijection differs. Target Body B is the identity mapping.
TARGET_MAPPING = (0, 1, 2, 3)
_PARTIAL = (0, 1, 3, 2)  # two of four pairs shared with B
_UNRELATED_1 = (1, 0, 3, 2)  # no pair shared with B
_UNRELATED_2 = (2, 3, 0, 1)  # no pair shared with B
# r6 family; r7 fixes the family by rule on the development seeds
# (``choose_family``) and the confirmation stage reads it from horizons.json.
DEFAULT_FAMILY: dict[str, tuple[int, ...]] = {
    "target": TARGET_MAPPING,
    "partial": _PARTIAL,
    "unrelated_1": _UNRELATED_1,
    "unrelated_2": _UNRELATED_2,
}
_ALL_MAPPINGS = tuple(itertools.permutations(range(ACTUATORS)))
# Every mapping sharing exactly two pairs with B, and every mapping sharing none.
PARTIAL_CANDIDATES = tuple(
    m for m in _ALL_MAPPINGS if sum(a == b for a, b in zip(m, TARGET_MAPPING)) == 2
)
UNRELATED_CANDIDATES = tuple(
    m for m in _ALL_MAPPINGS if sum(a == b for a, b in zip(m, TARGET_MAPPING)) == 0
)
_SAVE_METADATA = {"checkpoint_lineage", "runtime_provenance"}


def shared_pairs(mapping: Sequence[int], other: Sequence[int] = TARGET_MAPPING) -> int:
    return sum(left == right for left, right in zip(mapping, other))


def body_family(
    relation: str,
    *,
    seed_index: int,
    family: dict[str, tuple[int, ...]] = DEFAULT_FAMILY,
) -> dict[str, tuple[int, ...]]:
    """Source, sham and target mappings for one relation level.

    At the unrelated level the source and the sham are exchangeable by
    construction, and which mapping plays which role alternates with the
    position of the seed in its list.
    """
    unrelated_1, unrelated_2 = family["unrelated_1"], family["unrelated_2"]
    if relation == "same_structure":
        source, sham = family["target"], unrelated_2
    elif relation == "partial":
        source, sham = family["partial"], unrelated_2
    elif relation == "unrelated":
        source, sham = (
            (unrelated_1, unrelated_2) if seed_index % 2 == 0 else (unrelated_2, unrelated_1)
        )
    else:
        raise ValueError(f"unknown relation: {relation}")
    return {"source": source, "sham": sham, "target": family["target"]}


def _body(seed: int, mapping: Sequence[int]) -> CausalBody:
    return CausalBody(actuator_count=ACTUATORS, seed=seed, actuator_mapping=tuple(mapping))


def _organism_id(seed: int) -> str:
    return f"reembodiment-functional-transfer-{seed}"


def _newborn(seed: int, body: CausalBody) -> PrivateModelOrganismRuntime:
    return build_subject(
        body,
        organism_id=_organism_id(seed),
        runtime_class=PrivateModelOrganismRuntime,
        # r6: the subject is the canonical organism (ADR-0062).
        profile=CANONICAL,
    )


def _restore(payload: dict[str, Any], body: CausalBody) -> PrivateModelOrganismRuntime:
    return restore_canonical_organism(
        payload,
        PrivateModelOrganismRuntime,
        host_lifecycle=subject_lifecycle(body),
        host_reading_providers=(body,),
        kernel_limits=KernelLimits(),
        actuator_constitution_override=body.surface,
        min_samples=1,
    )


def _json(payload: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(payload))


def _valid_bindings(runtime: PrivateModelOrganismRuntime) -> list[Any]:
    return [
        binding
        for binding in runtime._action_domain.execution_bindings.items
        if binding.status is BindingStatus.VALID
    ]


def _ground_truth_hash(body: CausalBody) -> str:
    truth = body.ground_truth()
    material = json.dumps(
        [body.seed, list(truth.driven_receptor_by_actuator), truth.distractor_receptor_id]
    )
    return hashlib.sha256(material.encode()).hexdigest()


def first_valid_binding_tick(seed: int, mapping: Sequence[int], *, max_ticks: int) -> int | None:
    """Ticks a newborn needs in a stand-alone Body to hold a VALID binding."""
    body = _body(seed, mapping)
    runtime = _newborn(seed, body)
    for tick in range(1, max_ticks + 1):
        runtime.tick()
        body.advance(runtime.last_actuations)
        if _valid_bindings(runtime):
            return tick
    return None


@dataclass(frozen=True, slots=True)
class ArmRun:
    seed: int
    relation: str
    arm: str
    m1: int | None  # embodiment ticks to the first VALID binding acquired in B
    horizon: int
    actuations: int
    activity_rate: float
    valid_bindings_at_horizon: int
    entry_tick: int
    target_ground_truth_hash: str
    undriven_response_hash: str
    observer_schedule: tuple[int, ...]
    integrity_failures: tuple[str, ...]

    @property
    def censored(self) -> bool:
        return self.m1 is None

    @property
    def m1_or_horizon(self) -> int:
        return self.horizon if self.m1 is None else self.m1

    def as_dict(self) -> dict[str, Any]:
        return {**asdict(self), "censored": self.censored}


def _develop(seed: int, mapping: Sequence[int], ticks: int) -> dict[str, Any]:
    body = _body(seed, mapping)
    runtime = _newborn(seed, body)
    for _ in range(ticks):
        runtime.tick()
        body.advance(runtime.last_actuations)
    return _json(runtime.checkpoint())


def _entry_checkpoint(
    seed: int, arm: str, family: dict[str, tuple[int, ...]], development_ticks: int
) -> tuple[dict[str, Any], dict[str, Any] | None, list[str]]:
    """The checkpoint each arm is restored from in Body B, and what preceded it."""
    target = _body(seed, family["target"])
    fresh = _json(_newborn(seed, target).checkpoint())
    if arm == "naive":
        # Saved at tick 0 and restored, so it passes the same restore and
        # reacclimation gate as the other arms.
        return fresh, None, []
    previous = _develop(seed, family["source" if arm == "transfer" else "sham"], development_ticks)
    transformed = prepare_fresh_embodiment_checkpoint(
        previous,
        fresh,
        contract=EmbodimentDescriptor(
            body_kind="causal-body-transfer-target",
            receptor_count=ACTUATORS,
            effector_count=ACTUATORS,
        ),
        canonical_contract_fingerprint=target.surface.contract_fingerprint,
    )
    failures: list[str] = []
    try:
        verify_checkpoint_identity(transformed)
    except Exception as exc:  # recorded as contamination, never repaired
        failures.append(f"identity:{exc.__class__.__name__}")
    lineage = transformed.get("checkpoint_lineage") or {}
    if "re-embodiment" not in (lineage.get("transforms") or []):
        failures.append("transform_not_recorded")
    if transformed.get("organism_id") != previous.get("organism_id") or transformed.get(
        "saved_at_tick"
    ) != previous.get("saved_at_tick"):
        failures.append("identity_or_time_discontinuity")
    preserved = {
        field
        for entry in REGISTER
        if entry.reembodiment is Reembodiment.PRESERVED
        for field in entry.checkpoint_fields
    } - _SAVE_METADATA
    changed = {
        field
        for field in preserved
        if field in previous and transformed.get(field) != previous[field]
    } - {"last_runtime_vital_state"}
    if changed:
        failures.append("preserved_state_changed:" + ",".join(sorted(changed)))
    return _json(transformed), previous, failures


def run_arm(
    seed: int,
    relation: str,
    arm: str,
    *,
    seed_index: int,
    development_ticks: int,
    horizon: int,
    family: dict[str, tuple[int, ...]] = DEFAULT_FAMILY,
) -> ArmRun:
    """One arm of one seed at one relation level, measured in target Body B."""
    if arm not in ARMS:
        raise ValueError(f"unknown arm: {arm}")
    family = body_family(relation, seed_index=seed_index, family=family)
    entry, _previous, failures = _entry_checkpoint(seed, arm, family, development_ticks)
    body = _body(seed, family["target"])
    runtime = _restore(entry, body)
    entry_tick = runtime.tick_count
    domain = runtime._action_domain

    if _valid_bindings(runtime) or domain.active_commitment is not None:
        failures.append("authority_at_entry")
    evidence_before = {item.evidence_id for item in domain.acquisition.causal_evidence.evidence}
    undriven = body.distractor_receptor_id
    undriven_digest = hashlib.sha256()

    m1: int | None = None
    actuations = 0
    actuations_at_m1 = 0
    for tick in range(1, horizon + 1):
        runtime.tick()
        actuations += sum(1 for actuation in runtime.last_actuations if actuation.requested != 0.0)
        body.advance(runtime.last_actuations)
        undriven_digest.update(repr(round(body._values[undriven], 12)).encode())
        if m1 is None:
            for binding in _valid_bindings(runtime):
                acquired_here = (
                    binding.surface_fingerprint == body.surface.contract_fingerprint
                    and binding.valid_from_tick > entry_tick
                    and not (set(binding.evidence_refs) & evidence_before)
                )
                if acquired_here:
                    m1, actuations_at_m1 = tick, actuations
                    break

    final = runtime.checkpoint(advance_lineage=False)
    controls = (final.get("runtime_provenance") or {}).get("session_controls") or {}
    if controls.get("changed_since_restore"):
        failures.append("session_controls_changed")
    denominator = m1 if m1 is not None else horizon
    numerator = actuations_at_m1 if m1 is not None else actuations
    return ArmRun(
        seed=seed,
        relation=relation,
        arm=arm,
        m1=m1,
        horizon=horizon,
        actuations=numerator,
        activity_rate=numerator / denominator,
        valid_bindings_at_horizon=len(_valid_bindings(runtime)),
        entry_tick=entry_tick,
        target_ground_truth_hash=_ground_truth_hash(body),
        undriven_response_hash=undriven_digest.hexdigest(),
        # The only observer read in the B phase is the final checkpoint.
        observer_schedule=(horizon,),
        integrity_failures=tuple(failures),
    )


def seed_contamination(runs: Sequence[ArmRun]) -> tuple[str, ...]:
    """Integrity failures of one seed at one level, including cross-arm checks."""
    failures = [f"{run.arm}:{item}" for run in runs for item in run.integrity_failures]
    if len({run.target_ground_truth_hash for run in runs}) != 1:
        failures.append("target_body_differs_between_arms")
    if len({run.undriven_response_hash for run in runs}) != 1:
        failures.append("undriven_response_differs_between_arms")
    if len({run.observer_schedule for run in runs}) != 1:
        failures.append("observer_schedule_differs_between_arms")
    return tuple(failures)


def paired_reduction(sham: int, transfer: int) -> float:
    return (sham - transfer) / sham


def level_outcome(runs_by_seed: dict[int, dict[str, ArmRun]]) -> dict[str, Any]:
    """Per-level component of the single confirmatory claim (protocol §7.1)."""
    contaminated = {
        seed: failures
        for seed, arms in runs_by_seed.items()
        if (failures := seed_contamination(tuple(arms.values())))
    }
    clean = {seed: arms for seed, arms in runs_by_seed.items() if seed not in contaminated}
    result: dict[str, Any] = {
        "seeds": len(runs_by_seed),
        "contaminated": {str(seed): list(items) for seed, items in contaminated.items()},
    }
    if len(contaminated) > MAX_CONTAMINATED_SEEDS:
        return {**result, "outcome": "not_assessable"}

    wins = t_before_s = s_before_t = t_after_n = t_before_n = 0
    reductions: list[float] = []
    ratios: list[float] = []
    for arms in clean.values():
        transfer, sham, naive = (arms[name] for name in ARMS)
        t, s, n = transfer.m1_or_horizon, sham.m1_or_horizon, naive.m1_or_horizon
        # A censored-versus-censored pair is a tie.
        t_lt_s = t < s and not (transfer.censored and sham.censored)
        t_lt_n = t < n and not (transfer.censored and naive.censored)
        wins += t_lt_s and t_lt_n
        t_before_s += t_lt_s
        t_before_n += t_lt_n
        s_before_t += s < t and not (transfer.censored and sham.censored)
        t_after_n += t > n and not (transfer.censored and naive.censored)
        reductions.append(paired_reduction(s, t))
        if sham.activity_rate > 0:
            ratios.append(transfer.activity_rate / sham.activity_rate)

    median_reduction = statistics.median(reductions)
    activity_ratio = statistics.median(ratios) if ratios else None
    advantage = wins >= MIN_SEEDS_IMPROVED and median_reduction >= MIN_MEDIAN_PAIRED_REDUCTION
    practical_null = (
        abs(median_reduction) <= PRACTICAL_NULL_MARGIN
        and t_before_s < MIN_SEEDS_IMPROVED
        and s_before_t < MIN_SEEDS_IMPROVED
    )
    negative = t_after_n >= MIN_SEEDS_IMPROVED
    outcome = (
        "advantage"
        if advantage
        else "practical_null"
        if practical_null
        else "negative_transfer"
        if negative
        else "inconclusive"
    )
    return {
        **result,
        "outcome": outcome,
        "advantage": advantage,
        "practical_null": practical_null,
        "negative_transfer": negative,
        "seeds_transfer_first_over_both": wins,
        "seeds_transfer_before_sham": t_before_s,
        "seeds_sham_before_transfer": s_before_t,
        "seeds_transfer_after_naive": t_after_n,
        "seeds_transfer_before_naive": t_before_n,
        "median_paired_reduction": median_reduction,
        "median_activity_rate_ratio": activity_ratio,
        "activity_excess": activity_ratio is not None and activity_ratio > MAX_ACTIVITY_RATE_RATIO,
    }


def confirmatory_claim(levels: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """The one conjunctive claim and the other preregistered outcomes (§7.2)."""
    r1, r2, r3 = (levels[name] for name in RELATIONS)
    if any(level["outcome"] == "not_assessable" for level in (r1, r2, r3)):
        return {"claim": "not_assessable", "established": False}
    ordered = (
        r1["median_paired_reduction"]
        >= r2["median_paired_reduction"]
        >= r3["median_paired_reduction"]
    )
    established = r1["advantage"] and ordered and r3["practical_null"] and not r1["activity_excess"]
    if established:
        claim = "functional_transfer_established_within_scope"
    elif r3["advantage"]:
        claim = "apparatus_asymmetry_study_invalid"
    elif r1["advantage"] and r1["activity_excess"]:
        claim = "activity_not_transfer"
    elif r1["advantage"]:
        claim = "advantage_at_same_structure_dose_pattern_not_established"
    elif r1["negative_transfer"]:
        claim = "negative_transfer_at_same_structure"
    elif (
        r1["seeds_transfer_before_naive"] >= MIN_SEEDS_IMPROVED
        and r1["seeds_transfer_before_sham"] < MIN_SEEDS_IMPROVED
    ):
        claim = "maturity_effect_not_transfer"
    else:
        claim = "no_transfer"
    return {"claim": claim, "established": bool(established), "ordered_reductions": ordered}


def fix_development_ticks(
    seeds: Sequence[int] = DEVELOPMENT_SEEDS,
    family: dict[str, tuple[int, ...]] = DEFAULT_FAMILY,
) -> int | None:
    """Rule for D (protocol §4.5): smallest multiple of 100 up to D_MAX at which
    every development organism holds a VALID binding in every source Body."""
    mappings = sorted(set(family.values()))
    subjects = []
    for seed in seeds:
        for mapping in mappings:
            body = _body(seed, mapping)
            subjects.append((_newborn(seed, body), body))
    for ticks in range(D_STEP, D_MAX + 1, D_STEP):
        for runtime, body in subjects:
            while runtime.tick_count < ticks:
                runtime.tick()
                body.advance(runtime.last_actuations)
        if all(_valid_bindings(runtime) for runtime, _body_ in subjects):
            return ticks
    return None


def median_ticks_to_first_binding(
    mapping: Sequence[int], seeds: Sequence[int] = DEVELOPMENT_SEEDS
) -> float | None:
    """Median naive ticks to a first VALID binding; None if any seed never binds."""
    ticks = [first_valid_binding_tick(seed, mapping, max_ticks=D_MAX) for seed in seeds]
    return None if None in ticks else float(statistics.median(ticks))  # type: ignore[type-var]


def _spread(values: Sequence[float]) -> float:
    return (max(values) - min(values)) / statistics.median(values)


def choose_family(medians: dict[tuple[int, ...], float | None]) -> dict[str, Any]:
    """Rule for the Body family (protocol §4.2.1, r7).

    Among every partial candidate and every pair of distinct unrelated
    candidates whose development medians exist, choose the family with the
    smallest difficulty spread including the target; ties go to the
    lexicographically smallest (partial, unrelated_1, unrelated_2). Pure: the
    medians are measured on development seeds only.
    """
    target = medians.get(TARGET_MAPPING)
    best: tuple[float, tuple[tuple[int, ...], ...]] | None = None
    if target is not None:
        partials = [m for m in PARTIAL_CANDIDATES if medians.get(m) is not None]
        unrelated = [m for m in UNRELATED_CANDIDATES if medians.get(m) is not None]
        for partial in partials:
            for first, second in itertools.combinations(unrelated, 2):
                values = [target, medians[partial], medians[first], medians[second]]
                key = (_spread(values), (partial, first, second))  # type: ignore[arg-type]
                if best is None or key < best:
                    best = key
    if best is None:
        return {"family": None, "spread": None, "within_limit": False}
    spread, (partial, first, second) = best
    return {
        "family": {
            "target": TARGET_MAPPING,
            "partial": partial,
            "unrelated_1": first,
            "unrelated_2": second,
        },
        "spread": spread,
        "within_limit": spread <= MAX_BODY_DIFFICULTY_SPREAD,
    }


def select_family(seeds: Sequence[int] = DEVELOPMENT_SEEDS) -> dict[str, Any]:
    """Measure every candidate mapping on the development seeds and apply the rule."""
    candidates = (TARGET_MAPPING, *PARTIAL_CANDIDATES, *UNRELATED_CANDIDATES)
    medians = {mapping: median_ticks_to_first_binding(mapping, seeds) for mapping in candidates}
    choice = choose_family(medians)
    return {
        **choice,
        "candidate_medians": {
            "".join(map(str, mapping)): value for mapping, value in medians.items()
        },
    }


def run_development_stage() -> dict[str, Any]:
    """Fix the Body family, D and H by rule on the development seeds (r7).

    Looks at no treatment arm and no confirmation seed.
    """
    selection = select_family()
    family = selection["family"]
    development_ticks = fix_development_ticks(family=family) if family is not None else None
    return {
        "protocol": PROTOCOL,
        "stage": "development",
        "development_seeds": list(DEVELOPMENT_SEEDS),
        "body_family": (
            {name: list(mapping) for name, mapping in family.items()} if family else None
        ),
        "body_difficulty": {
            "candidate_medians": selection["candidate_medians"],
            "spread": selection["spread"],
            "within_limit": selection["within_limit"],
        },
        "development_ticks": development_ticks,
        # r5: the measurement horizon equals the development horizon.
        "measurement_ticks": development_ticks,
        "runnable": development_ticks is not None and selection["within_limit"],
    }


def _confirmation_task(task: tuple) -> ArmRun:
    relation, index, seed, arm, development_ticks, measurement_ticks, family = task
    return run_arm(
        seed,
        relation,
        arm,
        seed_index=index,
        development_ticks=development_ticks,
        horizon=measurement_ticks,
        family=family,
    )


def run_confirmation_stage(
    *,
    development_ticks: int,
    measurement_ticks: int,
    family: dict[str, tuple[int, ...]] = DEFAULT_FAMILY,
    seeds: Sequence[int] = CONFIRMATION_SEEDS,
    workers: int = 1,
    progress: Path | None = None,
) -> dict[str, Any]:
    """All arms of every seed at every level.

    ``workers`` > 1 runs arms in separate processes; every arm run is independent
    and deterministic, so the result does not depend on it. ``progress``, if
    given, is rewritten after every finished arm run so a stop keeps what ran.
    """
    tasks = [
        (relation, index, seed, arm, development_ticks, measurement_ticks, family)
        for relation in RELATIONS
        for index, seed in enumerate(seeds)
        for arm in ARMS
    ]
    finished: list[ArmRun] = []

    def record(run: ArmRun) -> None:
        finished.append(run)
        if progress is not None:
            progress.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "stage": "confirmation-progress",
                "complete": len(finished) == len(tasks),
                "runs": [item.as_dict() for item in finished],
            }
            progress.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")

    if workers <= 1:
        for task in tasks:
            record(_confirmation_task(task))
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for run in pool.map(_confirmation_task, tasks):
                record(run)
    levels: dict[str, dict[str, Any]] = {}
    for relation in RELATIONS:
        by_seed: dict[int, dict[str, ArmRun]] = {}
        for run in finished:
            if run.relation == relation:
                by_seed.setdefault(run.seed, {})[run.arm] = run
        levels[relation] = level_outcome(by_seed)
    return {
        "protocol": PROTOCOL,
        "stage": "confirmation",
        "seeds": list(seeds),
        "development_ticks": development_ticks,
        "measurement_ticks": measurement_ticks,
        "body_family": {name: list(mapping) for name, mapping in family.items()},
        "longitudinal_contract": LONGITUDINAL_CONTRACT.value,
        "levels": levels,
        "confirmatory": confirmatory_claim(levels),
        "runs": [run.as_dict() for run in finished],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("development", "confirmation"))
    parser.add_argument(
        "--horizons", type=Path, help="horizons.json written by the development stage"
    )
    parser.add_argument("--workers", type=int, default=1, help="processes for confirmation")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.stage == "development":
        result = run_development_stage()
    else:
        if args.horizons is None:
            parser.error("the confirmation stage needs --horizons")
        horizons = json.loads(args.horizons.read_text(encoding="utf-8"))
        if not horizons.get("runnable"):
            parser.error("the development stage did not produce a runnable protocol")
        result = run_confirmation_stage(
            development_ticks=int(horizons["development_ticks"]),
            measurement_ticks=int(horizons["measurement_ticks"]),
            family={
                name: tuple(int(item) for item in mapping)
                for name, mapping in horizons["body_family"].items()
            },
            workers=args.workers,
            progress=args.output.with_name(args.output.stem + "-progress.json"),
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in result if key != "runs"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
