from __future__ import annotations

import argparse

# Canonical imports from research subject and scientific apparatus
from symbiont.core.curiosity import CuriosityPlanner
from symbiont.core.reasoning import ReasoningEngine
from symbiont.simulation import run_simulation
from symbiont_lab.archive.runs import ExperimentArchive
from symbiont_lab.archive.studies import StudyArchive
from symbiont_lab.dashboard.server import main as dashboard_main
from symbiont_lab.experiments.spec import ExperimentSpec
from symbiont_lab.studies.attention.causal import run_causal_attention_budget
from symbiont_lab.studies.attention.replicated import (
    CAUSAL_METRICS,
    run_replicated_causal_budget_study,
)
from symbiont_lab.studies.attention.retrospective import run_attention_budget_analysis
from symbiont_lab.studies.campaigns.campaign import analyze_campaign
from symbiont_lab.studies.campaigns.comparative import (
    COMPARABLE_PARAMETERS,
    METRICS,
    run_comparative_study,
)
from symbiont_lab.studies.campaigns.interpretation import interpret_study
from symbiont_lab.studies.evidence.noise_sweep import (
    NOISE_METRICS,
    run_evidence_noise_sweep,
)
from symbiont_lab.studies.evidence.replicated import (
    EVIDENCE_METRICS,
    run_replicated_evidence_study,
)
from symbiont_lab.studies.evidence.second_look import run_second_look_study
from symbiont_lab.studies.heritage.longitudinal import run_longitudinal_species
from symbiont_lab.studies.heritage.replicated import (
    HERITAGE_DIAGNOSTICS,
    PERFORMANCE_METRICS,
    run_replicated_heritage_stress_study,
)
from symbiont_lab.studies.heritage.stress import run_heritage_stress_study


# ---------------------------------------------------------------------------
# 1. symbiont-sim
# ---------------------------------------------------------------------------

def _sim_pct(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.1%}"


def sim_main() -> None:
    p = argparse.ArgumentParser(description="Run a Symbiont Lab safe simulation")
    p.add_argument("--title", default="CLI experiment")
    p.add_argument("--hypothesis", default="")
    p.add_argument("--success-criteria", default="")
    p.add_argument("--notes", default="")
    p.add_argument("--hosts", type=int, default=100)
    p.add_argument("--steps", type=int, default=300)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--threat-rate", type=float, default=0.018)
    p.add_argument("--poison-fraction", type=float, default=0.08)
    p.add_argument("--heterogeneity", type=float, default=0.12)
    p.add_argument("--drift-step", type=int, default=-1)
    p.add_argument("--drift-fraction", type=float, default=0.35)
    p.add_argument("--drift-magnitude", type=float, default=0.22)
    p.add_argument("--archive", default=".symbiont/experiments.jsonl")
    p.add_argument("--no-record", action="store_true")
    args = p.parse_args()

    spec = ExperimentSpec(
        title=args.title,
        hypothesis=args.hypothesis,
        success_criteria=args.success_criteria,
        notes=args.notes,
        hosts=args.hosts,
        steps=args.steps,
        seed=args.seed,
        threat_rate=args.threat_rate,
        poison_fraction=args.poison_fraction,
        heterogeneity=args.heterogeneity,
        drift_step=None if args.drift_step < 0 else args.drift_step,
        drift_fraction=args.drift_fraction,
        drift_magnitude=args.drift_magnitude,
        delay=0.0,
    )
    result, collective = run_simulation(
        spec.hosts,
        spec.steps,
        spec.seed,
        spec.threat_rate,
        spec.poison_fraction,
        spec.heterogeneity,
        spec.drift_step,
        spec.drift_fraction,
        spec.drift_magnitude,
    )

    record = None
    if not args.no_record:
        record = ExperimentArchive(args.archive).append(spec, result, source="cli")

    print("SYMBIONT LAB — simulation complete")
    print(f"experiment:               {spec.title}")
    if record:
        print(f"record id:                {record.record_id}")
    if spec.hypothesis:
        print(f"hypothesis:               {spec.hypothesis}")
    if spec.success_criteria:
        print(f"success criteria:         {spec.success_criteria}")
    if spec.notes:
        print(f"notes:                    {spec.notes}")
    print(f"hosts / steps / seed:     {spec.hosts} / {spec.steps} / {spec.seed}")
    print("\nAttention allocation")
    print(f"  threat recall:           {_sim_pct(result.attention_recall)}")
    print(f"  precision:               {_sim_pct(result.attention_precision)}")
    print(f"  benign attention FPR:    {_sim_pct(result.attention_false_positive_rate)}")
    print("Classification")
    print(f"  threat recall:           {_sim_pct(result.classification_recall)}")
    print(f"  precision:               {_sim_pct(result.classification_precision)}")
    print(f"  benign classification FPR:{_sim_pct(result.classification_false_positive_rate):>8}")
    print(f"  high-confidence misses:  {_sim_pct(result.high_confidence_miss_rate)}")
    print("Calibration")
    print(f"  ECE:                     {result.calibration_error:.3f}")
    print(f"  Brier score:             {result.brier_score:.3f}")
    print(f"open questions:           {result.open_questions}")
    print(f"self confidence:          {result.self_confidence:.2f}")
    print(f"epistemic pressure:       {result.epistemic_pressure:.2f}")
    print(f"metacognitive status:     {result.metacognitive_status}")
    print(f"drift adaptations:        {result.drift_adaptations}")
    print(f"recent drift FP rate:     {result.recent_drift_false_positive_rate:.1%}")
    print(f"curiosity probes:         {result.curiosity_probes}")
    print(f"top probe utility:        {result.top_probe_utility:.2f}")

    families = dict(result.evaluation_breakdown.get("families", {}))
    if families:
        print("\nEvaluator-only family breakdown")
        print(f"{'family':28} {'events':>7} {'attn':>8} {'class':>8}")
        for family, metrics in families.items():
            print(
                f"{family:28} {int(metrics['events']):7d} "
                f"{_sim_pct(metrics.get('attention_recall')):>8} "
                f"{_sim_pct(metrics.get('classification_recall')):>8}"
            )

    hypotheses = ReasoningEngine().analyze(collective)
    probes = CuriosityPlanner().plan(hypotheses, collective)
    if probes:
        print("\nCuriosity agenda (shadow-only):")
        for probe in probes:
            print(
                f"  {probe.feature} {probe.change} — "
                f"utility={probe.utility:.2f}, EIG={probe.expected_information_gain:.2f}"
            )
            print(f"    ? {probe.question}")


# ---------------------------------------------------------------------------
# 2. symbiont-study
# ---------------------------------------------------------------------------

def _parse_seeds(raw: str) -> tuple[int, ...]:
    values = tuple(int(part.strip()) for part in raw.split(",") if part.strip())
    if not values:
        raise argparse.ArgumentTypeError("provide at least one seed")
    return values


def _study_number(value: float | None, *, signed: bool = False) -> str:
    if value is None:
        return "N/A"
    return f"{value:+.4f}" if signed else f"{value:.4f}"


def _study_percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.0%}"


def study_main() -> None:
    parser = argparse.ArgumentParser(description="Run a reproducible Symbiont Lab comparative study")
    parser.add_argument("--title", default="Comparative study")
    parser.add_argument("--parameter", choices=sorted(COMPARABLE_PARAMETERS), required=True)
    parser.add_argument("--baseline", type=float, required=True)
    parser.add_argument("--variant", type=float, required=True)
    parser.add_argument("--seeds", type=_parse_seeds, default=(3, 7, 11, 17, 23))
    parser.add_argument("--hosts", type=int, default=100)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--threat-rate", type=float, default=0.018)
    parser.add_argument("--poison-fraction", type=float, default=0.08)
    parser.add_argument("--heterogeneity", type=float, default=0.12)
    parser.add_argument("--drift-step", type=int, default=-1)
    parser.add_argument("--drift-fraction", type=float, default=0.35)
    parser.add_argument("--drift-magnitude", type=float, default=0.22)
    parser.add_argument("--archive", default=".symbiont/studies.jsonl")
    parser.add_argument("--parent-study-id", default=None)
    parser.add_argument("--no-record", action="store_true")
    args = parser.parse_args()

    spec = ExperimentSpec(
        title=args.title,
        hosts=args.hosts,
        steps=args.steps,
        seed=args.seeds[0],
        threat_rate=args.threat_rate,
        poison_fraction=args.poison_fraction,
        heterogeneity=args.heterogeneity,
        drift_step=None if args.drift_step < 0 else args.drift_step,
        drift_fraction=args.drift_fraction,
        drift_magnitude=args.drift_magnitude,
        delay=0.0,
    )
    study = run_comparative_study(
        spec,
        parameter=args.parameter,
        baseline_value=args.baseline,
        variant_value=args.variant,
        seeds=args.seeds,
        title=args.title,
    )
    interpretation = interpret_study(study)

    record = None
    if not args.no_record:
        archive = StudyArchive(args.archive)
        record = archive.append(
            spec,
            study,
            interpretation,
            source="cli",
            parent_record_id=args.parent_study_id,
        )

    print(f"SYMBIONT LAB — {study.title}")
    if record:
        print(f"study id:  {record.record_id}")
        if record.parent_record_id:
            print(f"parent:    {record.parent_record_id}")
    print(f"parameter: {study.parameter}")
    print(f"seeds:     {', '.join(map(str, study.seeds))}")
    print(f"baseline:  {study.baseline.parameter_value}")
    print(f"variant:   {study.variant.parameter_value}")
    print()
    print(
        f"{'metric':38} {'baseline':>11} {'variant':>11} {'delta':>11} "
        f"{'agree':>8} {'pairs':>7} {'σ Δ':>9}"
    )
    for metric in METRICS:
        base = study.baseline.metrics[metric]
        variant = study.variant.metrics[metric]
        paired = study.paired_deltas[metric]
        print(
            f"{metric:38} {_study_number(base.mean):>11} {_study_number(variant.mean):>11} "
            f"{_study_number(study.delta(metric), signed=True):>11} "
            f"{_study_percent(paired.direction_agreement):>8} {paired.pairs:7d} "
            f"{_study_number(paired.stdev):>9}"
        )

    print("\nObserver interpretation")
    print(f"  {interpretation.summary}")
    print(f"  confidence: {interpretation.confidence:.0%}")
    for finding in interpretation.findings[:6]:
        if finding.classification != "stable" or finding.evidence != "weak":
            print(f"  - [{finding.evidence}] {finding.text}")

    follow = interpretation.follow_up
    print("\nSuggested next study")
    print(
        f"  {follow.parameter}: {follow.baseline:.4f} -> {follow.variant:.4f} "
        f"with ~{follow.recommended_seed_count} paired seeds"
    )
    print(f"  {follow.rationale}")
    if record:
        print(f"  continue lineage with --parent-study-id {record.record_id}")


# ---------------------------------------------------------------------------
# 3. symbiont-campaign
# ---------------------------------------------------------------------------

def campaign_main() -> None:
    parser = argparse.ArgumentParser(description="Assess a Symbiont Lab observer-side research lineage")
    parser.add_argument("--study-id", required=True, help="Newest study record ID in the lineage")
    parser.add_argument("--archive", default=".symbiont/studies.jsonl")
    args = parser.parse_args()

    archive = StudyArchive(args.archive)
    lineage = archive.lineage(args.study_id)
    if not lineage:
        parser.error(f"study ID not found in archive: {args.study_id}")

    assessment = analyze_campaign(lineage)
    print("SYMBIONT LAB — research campaign")
    print(f"root:       {assessment.root_record_id}")
    print(f"current:    {assessment.current_record_id}")
    print(f"studies:    {assessment.studies}")
    print(f"parameter:  {assessment.parameter}")
    print(f"status:     {assessment.status}")
    print(f"confidence: {assessment.latest_confidence:.0%}")
    print(f"span:       {assessment.initial_span:.4f} -> {assessment.latest_span:.4f}")
    print()
    print(assessment.summary)

    print("\nLineage")
    for record in reversed(lineage):
        study = record.study
        baseline = dict(study.get("baseline", {})).get("parameter_value", "?")
        variant = dict(study.get("variant", {})).get("parameter_value", "?")
        print(
            f"  {record.record_id} parent={record.parent_record_id or '-'} "
            f"{study.get('parameter', '?')} {baseline}->{variant} "
            f"{study.get('title', '')}"
        )

    if assessment.proposal is None:
        print("\nNo follow-up study is recommended for this campaign state.")
    else:
        proposal = assessment.proposal
        print("\nResearcher-approved next comparison")
        print(
            f"  {proposal.parameter}: {proposal.baseline:.4f} -> {proposal.variant:.4f} "
            f"with ~{proposal.recommended_seed_count} paired seeds"
        )
        print(f"  parent: {proposal.parent_record_id}")
        print(f"  {proposal.rationale}")
        print("  This is a proposal only; nothing is launched automatically.")


# ---------------------------------------------------------------------------
# 4. symbiont-generations
# ---------------------------------------------------------------------------

def _gen_delta(value: float | None) -> str:
    return "N/A" if value is None else f"{value:+.4f}"


def generations_main() -> None:
    parser = argparse.ArgumentParser(
        description="Run paired synthetic generations with bounded abstract heritage"
    )
    parser.add_argument("--generations", type=int, default=5)
    parser.add_argument("--hosts", type=int, default=100)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--threat-rate", type=float, default=0.018)
    parser.add_argument("--poison-fraction", type=float, default=0.08)
    parser.add_argument("--heterogeneity", type=float, default=0.12)
    parser.add_argument("--drift-step", type=int, default=-1)
    parser.add_argument("--drift-fraction", type=float, default=0.35)
    parser.add_argument("--drift-magnitude", type=float, default=0.22)
    parser.add_argument("--heritage-limit", type=int, default=24)
    args = parser.parse_args()

    result = run_longitudinal_species(
        generations=args.generations,
        hosts=args.hosts,
        steps=args.steps,
        seed=args.seed,
        threat_rate=args.threat_rate,
        poison_fraction=args.poison_fraction,
        heterogeneity=args.heterogeneity,
        drift_step=None if args.drift_step < 0 else args.drift_step,
        drift_fraction=args.drift_fraction,
        drift_magnitude=args.drift_magnitude,
        heritage_limit=args.heritage_limit,
    )

    print("SYMBIONT LAB — longitudinal species")
    print(
        f"{'gen':>3} {'seed':>6} {'in':>4} {'out':>4} {'retain':>8} "
        f"{'Δ detect':>10} {'Δ precision':>12} {'Δ FP':>9} {'Δ calib':>10} {'Δ blind':>10}"
    )
    for item in result.generations:
        print(
            f"{item.generation:3d} {item.seed:6d} {item.inherited_patterns:4d} "
            f"{item.exported_patterns:4d} {item.retention_rate:8.1%} "
            f"{_gen_delta(item.detection_delta):>10} {_gen_delta(item.precision_delta):>12} "
            f"{_gen_delta(item.false_positive_delta):>9} {_gen_delta(item.calibration_delta):>10} "
            f"{_gen_delta(item.blind_spot_delta):>10}"
        )

    print("\nMean inherited − naive control (heritage-active generations only)")
    print(f"  generations:    {result.heritage_effect_generations}")
    print(f"  detection:      {_gen_delta(result.mean_detection_delta)}")
    print(f"  precision:      {_gen_delta(result.mean_precision_delta)}")
    print(f"  false positives:{_gen_delta(result.mean_false_positive_delta)}")
    print(f"  classification recall:    {_gen_delta(result.mean_classification_recall_delta)}")
    print(f"  classification precision: {_gen_delta(result.mean_classification_precision_delta)}")
    print(f"  calibration:    {_gen_delta(result.mean_calibration_delta)}")
    print(f"  blind spots:    {_gen_delta(result.mean_blind_spot_delta)}")
    print(f"  final heritage: {len(result.final_heritage.patterns)} abstract patterns")
    print("\nHeritage contains only bounded synthetic fingerprint priors; no code, host memory or source reputation is inherited.")


# ---------------------------------------------------------------------------
# 5. symbiont-budget
# ---------------------------------------------------------------------------

def _budget_pct(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.1%}"


def budget_main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare observer-side attention strategies at equal investigation budgets"
    )
    parser.add_argument("--hosts", type=int, default=100)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--threat-rate", type=float, default=0.018)
    parser.add_argument("--poison-fraction", type=float, default=0.08)
    parser.add_argument("--heterogeneity", type=float, default=0.12)
    parser.add_argument("--drift-step", type=int, default=-1)
    parser.add_argument("--drift-fraction", type=float, default=0.35)
    parser.add_argument("--drift-magnitude", type=float, default=0.22)
    args = parser.parse_args()

    analysis = run_attention_budget_analysis(
        hosts=args.hosts,
        steps=args.steps,
        seed=args.seed,
        threat_rate=args.threat_rate,
        poison_fraction=args.poison_fraction,
        heterogeneity=args.heterogeneity,
        drift_step=None if args.drift_step < 0 else args.drift_step,
        drift_fraction=args.drift_fraction,
        drift_magnitude=args.drift_magnitude,
    )

    print("SYMBIONT LAB — equal-attention budget analysis")
    print(f"hosts / steps / seed: {analysis.hosts} / {analysis.steps} / {analysis.seed}")
    print(
        f"natural policy budget: {analysis.natural_budget} investigations "
        f"({analysis.natural_budget_per_1000:.2f} / 1000 events)"
    )
    print()
    print(
        f"{'strategy':16} {'budget/1k':>10} {'recall':>9} {'precision':>10} "
        f"{'benign FPR':>10} {'stealth':>9} {'special benign':>15}"
    )
    for row in analysis.matched:
        print(
            f"{row.strategy:16} {row.investigations_per_1000:10.2f} "
            f"{_budget_pct(row.threat_recall):>9} {_budget_pct(row.precision):>10} "
            f"{_budget_pct(row.benign_false_positive_rate):>10} {_budget_pct(row.stealth_recall):>9} "
            f"{_budget_pct(row.benign_special_share):>15}"
        )

    print("\nThreat-family recall at matched budget")
    for row in analysis.matched:
        ransomware = row.family_recall.get("pathogen:ransom_sim")
        bot = row.family_recall.get("pathogen:bot_sim")
        stealth = row.family_recall.get("pathogen:stealth_sim")
        print(
            f"  {row.strategy:14} ransom={_budget_pct(ransomware):>7} "
            f"bot={_budget_pct(bot):>7} stealth={_budget_pct(stealth):>7}"
        )

    print("\nBudget curves (observer-side rankings)")
    for strategy, points in analysis.curves.items():
        print(f"  {strategy}")
        for point in points:
            print(
                f"    {point.investigations_per_1000:6.1f}/1k  "
                f"recall={_budget_pct(point.threat_recall):>7}  "
                f"precision={_budget_pct(point.precision):>7}  "
                f"stealth={_budget_pct(point.stealth_recall):>7}"
            )


# ---------------------------------------------------------------------------
# 6. symbiont-causal-budget
# ---------------------------------------------------------------------------

def _causal_number(value: float | None, *, percent: bool = False) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1%}" if percent else f"{value:.4f}"


def causal_budget_main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare irreversible online attention selectors under one ex-ante budget"
    )
    parser.add_argument("--hosts", type=int, default=100)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--threat-rate", type=float, default=0.018)
    parser.add_argument("--poison-fraction", type=float, default=0.08)
    parser.add_argument("--heterogeneity", type=float, default=0.12)
    parser.add_argument("--drift-step", type=int, default=-1)
    parser.add_argument("--drift-fraction", type=float, default=0.35)
    parser.add_argument("--drift-magnitude", type=float, default=0.22)
    parser.add_argument("--budget-per-1000", type=float, default=12.0)
    args = parser.parse_args()

    result = run_causal_attention_budget(
        hosts=args.hosts,
        steps=args.steps,
        seed=args.seed,
        threat_rate=args.threat_rate,
        poison_fraction=args.poison_fraction,
        heterogeneity=args.heterogeneity,
        drift_step=None if args.drift_step < 0 else args.drift_step,
        drift_fraction=args.drift_fraction,
        drift_magnitude=args.drift_magnitude,
        budget_per_1000=args.budget_per_1000,
    )

    print("SYMBIONT LAB — causal online attention budget")
    print(
        f"events={result.events} eligible={result.eligible_events} budget={result.budget} "
        f"({result.budget_per_1000:.2f}/1000) seed={result.seed}"
    )
    print(
        f"{'strategy':14} {'selected':>8} {'forced':>7} {'zero':>6} "
        f"{'warmup':>7} {'pre':>6} {'post':>6} {'recall':>8} "
        f"{'precision':>9} {'benign FPR':>10} {'stealth':>8}"
    )
    for row in result.outcomes:
        print(
            f"{row.strategy:14} {row.selected:8d} {row.forced_selections:7d} "
            f"{row.zero_score_selections:6d} "
            f"{row.selected_by_phase.get('warmup', 0):7d} "
            f"{row.selected_by_phase.get('pre_drift', 0):6d} "
            f"{row.selected_by_phase.get('post_drift', 0):6d} "
            f"{_causal_number(row.threat_recall, percent=True):>8} "
            f"{_causal_number(row.precision, percent=True):>9} "
            f"{_causal_number(row.benign_false_positive_rate, percent=True):>10} "
            f"{_causal_number(row.stealth_recall, percent=True):>8}"
        )

    print(
        "\nSelectors share startup eligibility and see only the current/past synthetic stream. "
        "They cannot rank future scores."
    )


# ---------------------------------------------------------------------------
# 7. symbiont-causal-budget-study
# ---------------------------------------------------------------------------

def _parse_ints(raw: str) -> tuple[int, ...]:
    values = tuple(int(part.strip()) for part in raw.split(",") if part.strip())
    if not values:
        raise argparse.ArgumentTypeError("provide at least one integer")
    return values


def _parse_floats(raw: str) -> tuple[float, ...]:
    values = tuple(float(part.strip()) for part in raw.split(",") if part.strip())
    if not values:
        raise argparse.ArgumentTypeError("provide at least one float")
    return values


def _cb_number(value: float | None, *, percent: bool = False, signed: bool = False) -> str:
    if value is None:
        return "N/A"
    if percent:
        return f"{value:+.1%}" if signed else f"{value:.1%}"
    return f"{value:+.4f}" if signed else f"{value:.4f}"


def causal_budget_study_main() -> None:
    parser = argparse.ArgumentParser(
        description="Replicate causal online attention selectors across paired seeds and budgets"
    )
    parser.add_argument("--seeds", type=_parse_ints, default=(101, 127, 149, 173, 199))
    parser.add_argument("--budgets-per-1000", type=_parse_floats, default=(5.0, 12.0, 20.0))
    parser.add_argument("--hosts", type=int, default=100)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--threat-rate", type=float, default=0.018)
    parser.add_argument("--poison-fraction", type=float, default=0.08)
    parser.add_argument("--heterogeneity", type=float, default=0.12)
    parser.add_argument("--drift-step", type=int, default=-1)
    parser.add_argument("--drift-fraction", type=float, default=0.35)
    parser.add_argument("--drift-magnitude", type=float, default=0.22)
    parser.add_argument("--reference-strategy", default="random")
    args = parser.parse_args()

    study = run_replicated_causal_budget_study(
        seeds=args.seeds,
        budgets_per_1000=args.budgets_per_1000,
        hosts=args.hosts,
        steps=args.steps,
        threat_rate=args.threat_rate,
        poison_fraction=args.poison_fraction,
        heterogeneity=args.heterogeneity,
        drift_step=None if args.drift_step < 0 else args.drift_step,
        drift_fraction=args.drift_fraction,
        drift_magnitude=args.drift_magnitude,
        reference_strategy=args.reference_strategy,
    )

    print("SYMBIONT LAB — replicated causal attention")
    print(f"seeds: {', '.join(map(str, study.seeds))}")
    print(f"budgets / 1000: {', '.join(f'{value:g}' for value in study.budgets_per_1000)}")
    print(f"reference: {study.reference_strategy}")

    for budget in study.budgets_per_1000:
        print(f"\nBudget {budget:g} / 1000")
        print(
            f"{'strategy':14} {'recall':>8} {'precision':>9} {'benign FPR':>10} "
            f"{'stealth':>8} {'forced':>8}"
        )
        for strategy in study.strategies:
            metrics = study.summaries[budget][strategy].metrics
            print(
                f"{strategy:14} "
                f"{_cb_number(metrics['threat_recall'].mean, percent=True):>8} "
                f"{_cb_number(metrics['precision'].mean, percent=True):>9} "
                f"{_cb_number(metrics['benign_false_positive_rate'].mean, percent=True):>10} "
                f"{_cb_number(metrics['stealth_recall'].mean, percent=True):>8} "
                f"{_cb_number(metrics['forced_share'].mean, percent=True):>8}"
            )

        print(f"  Paired deltas vs {study.reference_strategy}")
        for strategy, metrics in study.paired_vs_reference[budget].items():
            pieces: list[str] = []
            for metric in ("threat_recall", "precision", "stealth_recall", "forced_share"):
                delta = metrics[metric]
                agreement = (
                    "N/A" if delta.direction_agreement is None else f"{delta.direction_agreement:.0%}"
                )
                pieces.append(
                    f"{metric}={_cb_number(delta.mean, signed=True)} ({agreement}, n={delta.pairs})"
                )
            print(f"    {strategy}: " + "; ".join(pieces))

    print("\nDirection agreement is descriptive, not statistical significance.")
    print("All selectors make irreversible online choices and receive equal ex-ante capacity within each world.")


# ---------------------------------------------------------------------------
# 8. symbiont-evidence
# ---------------------------------------------------------------------------

def _ev_value(value: float | None, *, percent: bool = False) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1%}" if percent else f"{value:.4f}"


def evidence_main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a shadow-only synthetic second-look evidence study"
    )
    parser.add_argument("--hosts", type=int, default=100)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--threat-rate", type=float, default=0.018)
    parser.add_argument("--poison-fraction", type=float, default=0.08)
    parser.add_argument("--heterogeneity", type=float, default=0.12)
    parser.add_argument("--drift-step", type=int, default=-1)
    parser.add_argument("--drift-fraction", type=float, default=0.35)
    parser.add_argument("--drift-magnitude", type=float, default=0.22)
    parser.add_argument("--budget", type=int, default=-1)
    parser.add_argument("--sensor-noise", type=float, default=0.18)
    args = parser.parse_args()

    study = run_second_look_study(
        hosts=args.hosts,
        steps=args.steps,
        seed=args.seed,
        threat_rate=args.threat_rate,
        poison_fraction=args.poison_fraction,
        heterogeneity=args.heterogeneity,
        drift_step=None if args.drift_step < 0 else args.drift_step,
        drift_fraction=args.drift_fraction,
        drift_magnitude=args.drift_magnitude,
        budget=None if args.budget < 0 else args.budget,
        sensor_noise=args.sensor_noise,
    )

    print("SYMBIONT LAB — bounded synthetic second look")
    print(f"hosts / steps / seed: {study.hosts} / {study.steps} / {study.seed}")
    print(
        f"second-look budget: {study.budget} measurements "
        f"({study.budget_per_1000:.2f} / 1000 events)"
    )
    print(f"sensor noise: {study.sensor_noise:.3f}")
    print("shadow-only: measurements do not feed back into agents\n")
    print(
        f"{'selector':18} {'threat share':>12} {'pre Brier':>11} {'post Brier':>12} "
        f"{'gain':>9} {'Δ entropy':>10} {'fixed':>7} {'broken':>7} {'stealth':>8}"
    )
    for row in study.outcomes:
        print(
            f"{row.strategy:18} {_ev_value(row.selected_threat_share, percent=True):>12} "
            f"{_ev_value(row.pre_brier):>11} {_ev_value(row.post_brier):>12} "
            f"{_ev_value(row.brier_gain):>9} {_ev_value(row.mean_entropy_reduction):>10} "
            f"{row.corrected_errors:7d} {row.introduced_errors:7d} {row.stealth_selected:8d}"
        )


# ---------------------------------------------------------------------------
# 9. symbiont-evidence-study
# ---------------------------------------------------------------------------

def evidence_study_main() -> None:
    parser = argparse.ArgumentParser(
        description="Run paired multi-seed Symbiont Lab second-look studies"
    )
    parser.add_argument("--seeds", type=_parse_ints, default=(3, 7, 11, 17, 23))
    parser.add_argument("--hosts", type=int, default=100)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--threat-rate", type=float, default=0.018)
    parser.add_argument("--poison-fraction", type=float, default=0.08)
    parser.add_argument("--heterogeneity", type=float, default=0.12)
    parser.add_argument("--drift-step", type=int, default=-1)
    parser.add_argument("--drift-fraction", type=float, default=0.35)
    parser.add_argument("--drift-magnitude", type=float, default=0.22)
    parser.add_argument("--budget", type=int, default=-1)
    parser.add_argument("--sensor-noise", type=float, default=0.18)
    parser.add_argument("--reference", default="random")
    args = parser.parse_args()

    study = run_replicated_evidence_study(
        seeds=args.seeds,
        hosts=args.hosts,
        steps=args.steps,
        threat_rate=args.threat_rate,
        poison_fraction=args.poison_fraction,
        heterogeneity=args.heterogeneity,
        drift_step=None if args.drift_step < 0 else args.drift_step,
        drift_fraction=args.drift_fraction,
        drift_magnitude=args.drift_magnitude,
        budget=None if args.budget < 0 else args.budget,
        sensor_noise=args.sensor_noise,
        reference_strategy=args.reference,
    )

    print("SYMBIONT LAB — replicated bounded-evidence study")
    print(f"seeds:      {', '.join(map(str, study.seeds))}")
    print(f"reference:  {study.reference_strategy}")
    print(f"budgets:    {', '.join(map(str, study.budgets))}")
    print()
    print(
        f"{'selector':18} {'Brier gain':>11} {'entropy Δ':>11} {'net fixes':>10} "
        f"{'threat share':>13} {'stealth share':>13}"
    )
    for strategy in study.strategies:
        summary = study.summaries[strategy].metrics
        print(
            f"{strategy:18} {_cb_number(summary['brier_gain'].mean):>11} "
            f"{_cb_number(summary['mean_entropy_reduction'].mean):>11} "
            f"{_cb_number(summary['net_correction_rate'].mean, percent=True):>10} "
            f"{_cb_number(summary['selected_threat_share'].mean, percent=True):>13} "
            f"{_cb_number(summary['stealth_share'].mean, percent=True):>13}"
        )

    print(f"\nPaired deltas vs {study.reference_strategy}")
    for strategy, metrics in study.paired_vs_reference.items():
        print(f"  {strategy}")
        for metric in EVIDENCE_METRICS:
            delta = metrics[metric]
            if metric not in {
                "brier_gain",
                "mean_entropy_reduction",
                "net_correction_rate",
                "stealth_share",
            }:
                continue
            agreement = "N/A" if delta.direction_agreement is None else f"{delta.direction_agreement:.0%}"
            print(
                f"    {metric:28} Δ={_cb_number(delta.mean, signed=True):>9} "
                f"agree={agreement:>5} pairs={delta.pairs}"
            )


# ---------------------------------------------------------------------------
# 10. symbiont-evidence-noise-sweep
# ---------------------------------------------------------------------------

def evidence_noise_sweep_main() -> None:
    parser = argparse.ArgumentParser(
        description="Sweep synthetic second-look sensor noise across paired validation seeds"
    )
    parser.add_argument("--seeds", type=_parse_ints, default=(211, 223, 239, 251, 269))
    parser.add_argument("--noise-levels", type=_parse_floats, default=(0.08, 0.18, 0.30, 0.45))
    parser.add_argument("--hosts", type=int, default=100)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--threat-rate", type=float, default=0.018)
    parser.add_argument("--poison-fraction", type=float, default=0.08)
    parser.add_argument("--heterogeneity", type=float, default=0.12)
    parser.add_argument("--drift-step", type=int, default=-1)
    parser.add_argument("--drift-fraction", type=float, default=0.35)
    parser.add_argument("--drift-magnitude", type=float, default=0.22)
    parser.add_argument("--budget-per-1000", type=float, default=12.0)
    args = parser.parse_args()

    sweep = run_evidence_noise_sweep(
        seeds=args.seeds,
        noise_levels=args.noise_levels,
        hosts=args.hosts,
        steps=args.steps,
        threat_rate=args.threat_rate,
        poison_fraction=args.poison_fraction,
        heterogeneity=args.heterogeneity,
        drift_step=None if args.drift_step < 0 else args.drift_step,
        drift_fraction=args.drift_fraction,
        drift_magnitude=args.drift_magnitude,
        budget_per_1000=args.budget_per_1000,
    )

    print("SYMBIONT LAB — second-look sensor noise sweep")
    print(f"seeds: {', '.join(map(str, sweep.seeds))}")
    print(f"noise: {', '.join(f'{value:g}' for value in sweep.noise_levels)}")
    print(f"budget: {sweep.budget} ({sweep.budget_per_1000:g}/1000)")

    for noise in sweep.noise_levels:
        print(f"\nNoise {noise:g}")
        print(f"{'strategy':18} {'Brier gain':>11} {'Brier +':>8} {'net corr':>9} {'stealth corr':>12}")
        for strategy in sweep.strategies:
            metrics = sweep.summaries[noise][strategy].metrics
            print(
                f"{strategy:18} "
                f"{_cb_number(metrics['brier_gain'].mean, signed=True):>11} "
                f"{_cb_number(metrics['brier_gain'].positive_fraction, percent=True):>8} "
                f"{_cb_number(metrics['net_correction_rate'].mean, percent=True, signed=True):>9} "
                f"{_cb_number(metrics['stealth_correction_rate'].mean, percent=True):>12}"
            )

    if len(sweep.noise_levels) > 1:
        reference = sweep.noise_levels[0]
        print(f"\nPaired degradation vs noise {reference:g}")
        for noise, strategies in sweep.paired_vs_lowest_noise.items():
            print(f"  noise {noise:g}")
            for strategy, metrics in strategies.items():
                delta = metrics['brier_gain']
                agreement = "N/A" if delta.direction_agreement is None else f"{delta.direction_agreement:.0%}"
                print(
                    f"    {strategy:18} Δ Brier gain={_cb_number(delta.mean, signed=True)} "
                    f"direction={agreement} n={delta.pairs}"
                )

    print("\nSensor evidence remains shadow-only; no measurement changes a live agent decision.")


# ---------------------------------------------------------------------------
# 11. symbiont-heritage-stress
# ---------------------------------------------------------------------------

def heritage_stress_main() -> None:
    parser = argparse.ArgumentParser(
        description="Stress synthetic inherited priors against a fixed target world"
    )
    parser.add_argument("--source-seed", type=int, default=7)
    parser.add_argument("--target-seed", type=int, default=1016)
    parser.add_argument("--hosts", type=int, default=100)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--threat-rate", type=float, default=0.018)
    parser.add_argument("--poison-fraction", type=float, default=0.08)
    parser.add_argument("--heterogeneity", type=float, default=0.12)
    parser.add_argument("--drift-step", type=int, default=-1)
    parser.add_argument("--drift-fraction", type=float, default=0.35)
    parser.add_argument("--drift-magnitude", type=float, default=0.22)
    parser.add_argument("--heritage-limit", type=int, default=24)
    args = parser.parse_args()

    study = run_heritage_stress_study(
        source_seed=args.source_seed,
        target_seed=args.target_seed,
        hosts=args.hosts,
        steps=args.steps,
        threat_rate=args.threat_rate,
        poison_fraction=args.poison_fraction,
        heterogeneity=args.heterogeneity,
        drift_step=None if args.drift_step < 0 else args.drift_step,
        drift_fraction=args.drift_fraction,
        drift_magnitude=args.drift_magnitude,
        heritage_limit=args.heritage_limit,
    )

    print("SYMBIONT LAB — heritage stress")
    print(f"source / target seed: {study.source_seed} / {study.target_seed}")
    print(f"learned source patterns: {study.source_patterns}")
    print()
    print(
        f"{'condition':12} {'priors':>6} {'attn R':>8} {'class R':>8} {'Brier':>8} "
        f"{'prior MAE':>10} {'final MAE':>10} {'gain':>9} {'override':>9} {'reexport':>9}"
    )
    for row in study.conditions:
        print(
            f"{row.name:12} {row.inherited_patterns:6d} "
            f"{_cb_number(row.attention_recall, percent=True):>8} "
            f"{_cb_number(row.classification_recall, percent=True):>8} "
            f"{row.brier_score:8.4f} {_cb_number(row.prior_mae):>10} "
            f"{_cb_number(row.combined_mae):>10} {_cb_number(row.correction_gain):>9} "
            f"{_cb_number(row.live_override_rate, percent=True):>9} "
            f"{_cb_number(row.reexport_rate, percent=True):>9}"
        )
        if row.reexported_patterns:
            print(
                f"  re-exported {row.reexported_patterns}; direction flips={row.direction_flips}; "
                f"truth-evaluable={row.evaluable_reexports}; improved={row.improved_reexports}; "
                f"worsened={row.worsened_reexports}; "
                f"mean MAE gain={_cb_number(row.mean_reexport_mae_gain, signed=True)}"
            )

    digests = {row.world_digest for row in study.conditions}
    print(f"\nfixed target world: {'yes' if len(digests) == 1 else 'NO'}")


# ---------------------------------------------------------------------------
# 12. symbiont-heritage-stress-study
# ---------------------------------------------------------------------------

def heritage_stress_study_main() -> None:
    parser = argparse.ArgumentParser(
        description="Run paired multi-world Symbiont heritage stress studies"
    )
    parser.add_argument("--source-seeds", type=_parse_ints, default=(3, 7, 11, 17, 23))
    parser.add_argument("--target-offset", type=int, default=1009)
    parser.add_argument("--hosts", type=int, default=100)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--threat-rate", type=float, default=0.018)
    parser.add_argument("--poison-fraction", type=float, default=0.08)
    parser.add_argument("--heterogeneity", type=float, default=0.12)
    parser.add_argument("--drift-step", type=int, default=-1)
    parser.add_argument("--drift-fraction", type=float, default=0.35)
    parser.add_argument("--drift-magnitude", type=float, default=0.22)
    parser.add_argument("--heritage-limit", type=int, default=24)
    args = parser.parse_args()

    study = run_replicated_heritage_stress_study(
        source_seeds=args.source_seeds,
        target_offset=args.target_offset,
        hosts=args.hosts,
        steps=args.steps,
        threat_rate=args.threat_rate,
        poison_fraction=args.poison_fraction,
        heterogeneity=args.heterogeneity,
        drift_step=None if args.drift_step < 0 else args.drift_step,
        drift_fraction=args.drift_fraction,
        drift_magnitude=args.drift_magnitude,
        heritage_limit=args.heritage_limit,
    )

    print("SYMBIONT LAB — replicated heritage stress")
    print(f"source seeds: {', '.join(map(str, study.source_seeds))}")
    print(f"target seeds: {', '.join(map(str, study.target_seeds))}")
    print(f"target offset: {study.target_offset}")
    print(f"source pattern counts: {', '.join(map(str, study.source_pattern_counts))}")
    print()

    print(
        f"{'condition':12} {'attn R':>8} {'class R':>8} {'Brier':>8} "
        f"{'prior MAE':>10} {'final MAE':>10} {'gain':>9} {'reexport':>9}"
    )
    for name in study.conditions:
        metrics = study.summaries[name].metrics
        print(
            f"{name:12} "
            f"{_cb_number(metrics['attention_recall'].mean, percent=True):>8} "
            f"{_cb_number(metrics['classification_recall'].mean, percent=True):>8} "
            f"{_cb_number(metrics['brier_score'].mean):>8} "
            f"{_cb_number(metrics['prior_mae'].mean):>10} "
            f"{_cb_number(metrics['combined_mae'].mean):>10} "
            f"{_cb_number(metrics['correction_gain'].mean):>9} "
            f"{_cb_number(metrics['reexport_rate'].mean, percent=True):>9}"
        )

    print("\nPaired performance deltas vs naive")
    for name, metrics in study.paired_vs_naive.items():
        print(f"  {name}")
        for metric in PERFORMANCE_METRICS:
            if metric not in {
                "attention_recall",
                "attention_precision",
                "classification_recall",
                "classification_precision",
                "brier_score",
                "high_confidence_miss_rate",
            }:
                continue
            delta = metrics[metric]
            agreement = (
                "N/A"
                if delta.direction_agreement is None
                else f"{delta.direction_agreement:.0%}"
            )
            print(
                f"    {metric:34} Δ={_cb_number(delta.mean, signed=True):>9} "
                f"agree={agreement:>5} pairs={delta.pairs}"
            )

    print("\nHeritage diagnostics are summarized separately from performance deltas")
    for name in ("learned", "inverted", "misaligned"):
        metrics = study.summaries[name].metrics
        print(f"  {name}")
        for metric in HERITAGE_DIAGNOSTICS:
            if metric not in {
                "prior_mae",
                "live_mae",
                "combined_mae",
                "correction_gain",
                "live_override_rate",
                "reexport_rate",
                "direction_flips",
                "evaluable_reexports",
                "improved_reexports",
                "worsened_reexports",
                "mean_reexport_mae_gain",
            }:
                continue
            percent = metric in {"live_override_rate", "reexport_rate"}
            signed = metric in {"correction_gain", "mean_reexport_mae_gain"}
            print(
                f"    {metric:24} "
                f"{_cb_number(metrics[metric].mean, percent=percent, signed=signed)}"
            )
