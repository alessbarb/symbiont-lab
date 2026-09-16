from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
import signal

from symbiont.cognition.birth import load_base_graph, load_base_genome
from symbiont.cognition.genome import Genome, GenomeCodec, GenomeError
from symbiont.cognition.graph import CognitiveGraph, GraphError, load_graph_definition
from symbiont.cognition.limits import KernelLimits
from symbiont.core import (
    ConsentRevokedError,
    DefensiveAdvisor,
    GovernedOrganism,
    OrganismRuntime,
    RateLimitedError,
    ResidentConfig,
    ResidentOrganism,
    TickBudgetExhaustedError,
    append_advisories_to_log,
)
from symbiont.core.canonical_birth import restore_resident_with_canonical_cognition
from symbiont.host.checkpoint import load_checkpoint_file


def build_organism_parser(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="organism_action", required=True)

    run_cmd = sub.add_parser("run", help="Run a finite cognitive experiment")
    run_cmd.add_argument("--ticks", type=int, default=5)
    run_cmd.add_argument("--attention-budget", type=float, default=1.0)
    run_cmd.add_argument("--investigate-ticks", type=int, default=2)
    run_cmd.add_argument("--conflict-z", type=float, default=2.0)
    run_cmd.add_argument("--min-samples", type=int, default=5)
    run_cmd.add_argument("--min-seconds-between-ticks", type=float, default=0.0)
    run_cmd.add_argument("--max-ticks", type=int, default=None)
    run_cmd.add_argument("--state-file")
    run_cmd.add_argument("--advisory-consent", action="store_true")
    run_cmd.add_argument("--advisory-uncertainty-threshold", type=float, default=1.0)
    run_cmd.add_argument("--advisory-log")
    run_cmd.add_argument("--genome-file", help="Override the canonical birth genome with an owner-authored genome JSON file")
    run_cmd.add_argument("--graph-file", help="Override the canonical germinal graph (requires --genome-file)")

    live_cmd = sub.add_parser(
        "live",
        help="Live as a transparent user process, discovering and learning safe local senses",
    )
    live_cmd.add_argument(
        "--state-file",
        default="~/.local/state/symbiont/organism.json",
        help="Durable abstract memory checkpoint",
    )
    live_cmd.add_argument("--interval", type=float, default=15.0, help="Seconds between cognitive cycles")
    live_cmd.add_argument("--checkpoint-every", type=int, default=20, help="Ticks between atomic checkpoints")
    live_cmd.add_argument("--max-ticks", type=int, default=None, help="Optional finite budget for testing")
    live_cmd.add_argument("--attention-budget", type=float, default=1.0)
    live_cmd.add_argument("--investigate-ticks", type=int, default=2)
    live_cmd.add_argument("--conflict-z", type=float, default=2.0)
    live_cmd.add_argument("--min-samples", type=int, default=5)
    live_cmd.add_argument(
        "--semantic-bootstrap",
        action="store_true",
        help="Also expose the legacy hand-labelled CPU/disk senses. Off by default: live mode develops opaque senses itself.",
    )
    live_cmd.add_argument(
        "--stdout",
        action="store_true",
        help="Emit bounded non-identifying tick summaries for local observers",
    )
    live_cmd.add_argument(
        "--genome-file",
        help="Override the canonical birth genome with an owner-authored genome JSON file (first launch only)",
    )
    live_cmd.add_argument(
        "--graph-file",
        help="Override the canonical germinal graph (first launch only, requires --genome-file)",
    )


def _running_version() -> tuple[int, int, int]:
    from symbiont import __version__ as symbiont_version

    parts = (symbiont_version.split(".") + ["0", "0"])[:3]
    return tuple(int(part) for part in parts)


def _load_genome_file(path: str, *, kernel_limits: KernelLimits) -> Genome:
    payload = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    codec = GenomeCodec()
    genome = codec.load(payload)
    from symbiont.cognition.genome import legacy_validation_version
    codec.validate(genome, kernel_limits, running_version=legacy_validation_version(genome.kernel_compatibility, _running_version()))
    return genome


def _load_graph_file(path: str, *, kernel_limits: KernelLimits) -> CognitiveGraph:
    payload = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    return load_graph_definition(payload, kernel_limits=kernel_limits)


def _load_cognition_from_args(args: argparse.Namespace, kwargs: dict) -> None:
    """Install canonical first-birth cognition, with explicit owner overrides.

    Every new organism receives the packaged base genome and empty germinal
    graph. A supplied genome replaces the base genome; a supplied graph
    replaces the base graph and still requires an explicitly supplied genome.
    Existing checkpoints restore their learned cognition unchanged; legacy
    checkpoints from before cognition existed adopt the canonical base without
    losing their already-learned sensory or host memory.
    """
    genome_file = getattr(args, "genome_file", None)
    graph_file = getattr(args, "graph_file", None)
    if graph_file and not genome_file:
        print("error: --graph-file requires --genome-file", file=sys.stderr)
        raise SystemExit(2)

    kernel_limits = KernelLimits()
    try:
        genome = (
            _load_genome_file(genome_file, kernel_limits=kernel_limits)
            if genome_file
            else load_base_genome(kernel_limits=kernel_limits, running_version=_running_version())
        )
        graph = (
            _load_graph_file(graph_file, kernel_limits=kernel_limits)
            if graph_file
            else load_base_graph(kernel_limits=kernel_limits)
        )
    except (GenomeError, GraphError, OSError, json.JSONDecodeError, ValueError) as exc:
        source = "owner cognition files" if genome_file or graph_file else "canonical birth cognition"
        print(f"error: could not load {source}: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    kwargs["genome"] = genome
    kwargs["kernel_limits"] = kernel_limits
    kwargs["cognitive_graph"] = graph


def _runtime_for_run(args: argparse.Namespace) -> OrganismRuntime:
    kwargs = dict(
        attention_budget=args.attention_budget,
        investigate_ticks=args.investigate_ticks,
        conflict_z=args.conflict_z,
        min_samples=args.min_samples,
    )
    existing_payload = load_checkpoint_file(args.state_file) if args.state_file else None
    if existing_payload is not None:
        return restore_resident_with_canonical_cognition(existing_payload, **kwargs)
    _load_cognition_from_args(args, kwargs)
    return OrganismRuntime(**kwargs)


def _run_finite(args: argparse.Namespace) -> int:
    ticks = min(max(int(args.ticks), 1), 1000)
    runtime = _runtime_for_run(args)
    governed = GovernedOrganism(
        runtime,
        min_seconds_between_ticks=args.min_seconds_between_ticks,
        max_ticks=args.max_ticks,
    )
    advisor = DefensiveAdvisor(
        consented=args.advisory_consent,
        uncertainty_threshold=args.advisory_uncertainty_threshold,
    )
    results = []
    all_advisories = []
    stopped_reason = None
    for _ in range(ticks):
        try:
            result = governed.tick()
        except (ConsentRevokedError, RateLimitedError, TickBudgetExhaustedError) as exc:
            stopped_reason = str(exc)
            break
        results.append(result)
        if advisor.is_consented:
            tick_advisories = advisor.evaluate(result)
            all_advisories.extend(tick_advisories)
            if args.advisory_log:
                append_advisories_to_log(tick_advisories, args.advisory_log)
    if args.state_file:
        runtime.save(args.state_file)
    print(json.dumps({
        "ticks": [{
            "tick": result.tick,
            "allocations": [
                {"name": allocation.name, "uncertainty": allocation.uncertainty, "cost": allocation.cost}
                for allocation in result.allocations
            ],
            "investigated_capability": result.investigated_capability,
            "evidence_gathered": result.evidence_gathered,
            "contested": result.dissent is not None,
            "narrative": [entry.summary for entry in result.narrative],
            "cognition": (
                {
                    "readouts": dict(result.cognition.readouts),
                    "prediction_errors": [
                        {"predictor_id": e.predictor_id, "target_id": e.target_id, "loss": e.loss}
                        for e in result.cognition.prediction_errors
                    ],
                    "structural_mutations_applied": result.cognition.structural_mutations_applied,
                    "frozen": result.cognition.frozen,
                }
                if result.cognition is not None
                else None
            ),
        } for result in results],
        "advisories": [{
            "tick": advisory.tick,
            "capability_id": advisory.capability_id,
            "signals": [{"kind": s.kind, "detail": s.detail} for s in advisory.signals],
            "summary": advisory.summary,
        } for advisory in all_advisories],
        "governor": {
            "ticks_run": governed.ticks_run,
            "ticks_remaining": governed.ticks_remaining,
            "is_consented": governed.is_consented,
            "stopped_early": stopped_reason,
        },
        "checkpoint": governed.checkpoint(),
    }, indent=2, sort_keys=True, default=str))
    return 0


def _run_live(args: argparse.Namespace) -> int:
    state_file = Path(args.state_file).expanduser()
    kwargs = dict(
        attention_budget=args.attention_budget,
        investigate_ticks=args.investigate_ticks,
        conflict_z=args.conflict_z,
        min_samples=args.min_samples,
        discover_senses=True,
        bootstrap_semantic_senses=bool(args.semantic_bootstrap),
    )
    existing_payload = load_checkpoint_file(state_file)
    if existing_payload is not None:
        runtime = restore_resident_with_canonical_cognition(existing_payload, **kwargs)
    else:
        _load_cognition_from_args(args, kwargs)
        runtime = OrganismRuntime(**kwargs)

    def emit(result) -> None:
        if not args.stdout:
            return
        plan = result.sampling_plan
        active_ids = set(plan.active if plan is not None else ())
        payload = {
            "type": "symbiont-resident-tick",
            "tick": result.tick,
            "state": "reflecting" if result.dissent is not None else ("exploring" if result.investigated_capability else "observing"),
            "percepts": [percept.name for percept in result.percepts[:32]],
            "active_senses": [
                {"name": state.percept_name, "samples": state.samples, "utility": round(state.utility, 6)}
                for state in runtime.adaptive_senses.states
                if state.capability_id in active_ids
            ][:32],
            "sampling": {
                "active": len(active_ids),
                "probing": len(plan.probing) if plan is not None else 0,
                "dormant": plan.dormant_count if plan is not None else 0,
                "unknown": plan.unknown_count if plan is not None else 0,
                "sampled": len(result.snapshot.sampled_capability_ids),
                "discovered": len(result.snapshot.manifest.available),
            },
        }
        if result.cognition is not None:
            payload["cognition"] = {
                "readouts": dict(result.cognition.readouts),
                "frozen": result.cognition.frozen,
                "structural_mutations_applied": result.cognition.structural_mutations_applied,
            }
        print(json.dumps(payload, separators=(",", ":")), flush=True)

    resident = ResidentOrganism(
        runtime,
        state_file=state_file,
        config=ResidentConfig(
            interval_seconds=args.interval,
            checkpoint_every_ticks=args.checkpoint_every,
            max_ticks=args.max_ticks,
        ),
        on_tick=emit,
    )

    def request_stop(_signum, _frame) -> None:
        resident.stop()

    previous_int = signal.signal(signal.SIGINT, request_stop)
    previous_term = signal.signal(signal.SIGTERM, request_stop)
    try:
        resident.run()
    finally:
        signal.signal(signal.SIGINT, previous_int)
        signal.signal(signal.SIGTERM, previous_term)
    return 0


def run_organism_command(args: argparse.Namespace) -> int:
    if args.organism_action == "run":
        return _run_finite(args)
    if args.organism_action == "live":
        return _run_live(args)
    return 1
