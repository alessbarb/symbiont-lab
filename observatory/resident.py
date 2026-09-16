"""Run a resident Symbiont and emit passive Observatory snapshot envelopes."""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

try:  # Package invocation: ``python -m observatory.resident``.
    from .adapter import BODY_SCHEMA_SNAPSHOT_VERSION, envelope, project_tick, project_topology
    from .manifest import create_capture_manifest, write_capture_manifest
    from .publisher import JournalSink, SnapshotPublisher, StdoutSink
    from .registry import derive_instance_id, new_run_id, write_heartbeat
except ImportError:  # Direct script invocation remains a documented interface.
    from adapter import BODY_SCHEMA_SNAPSHOT_VERSION, envelope, project_tick, project_topology
    from manifest import create_capture_manifest, write_capture_manifest
    from publisher import JournalSink, SnapshotPublisher, StdoutSink
    from registry import derive_instance_id, new_run_id, write_heartbeat


def _rounded(value: float | None) -> float | None:
    return None if value is None else round(value, 6)


def _running_version_string() -> str:
    from symbiont import __version__

    return __version__


def _running_version_tuple() -> tuple[int, int, int]:
    parts = (_running_version_string().split(".") + ["0", "0"])[:3]
    return tuple(int(part) for part in parts)


def _write_topology(observatory_dir: Path, instance_id: str, payload: dict) -> None:
    import json as _json
    import tempfile as _tempfile

    target = Path(observatory_dir) / "instances" / f"{instance_id}.topology.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = _tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            _json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _load_first_launch_cognition(args: argparse.Namespace, runtime_kwargs: dict) -> None:
    """Give every new Observatory resident canonical cognition.

    Owner files are explicit first-birth overrides. Existing checkpoints with
    cognition keep their learned topology; legacy cognition-less checkpoints
    are adopted separately without discarding their already learned memory.
    """
    if args.graph_file and not args.genome_file:
        raise ValueError("--graph-file requires --genome-file")

    from symbiont.cognition.birth import load_base_graph, load_base_genome
    from symbiont.cognition.genome import GenomeCodec
    from symbiont.cognition.graph import load_graph_definition
    from symbiont.cognition.limits import KernelLimits

    kernel_limits = KernelLimits()
    if args.genome_file:
        genome_payload = json.loads(Path(args.genome_file).expanduser().read_text(encoding="utf-8"))
        codec = GenomeCodec()
        genome = codec.load(genome_payload)
        codec.validate(genome, kernel_limits, running_version=_running_version_tuple())
    else:
        genome = load_base_genome(
            kernel_limits=kernel_limits,
            running_version=_running_version_tuple(),
        )

    if args.graph_file:
        graph_payload = json.loads(Path(args.graph_file).expanduser().read_text(encoding="utf-8"))
        graph = load_graph_definition(graph_payload, kernel_limits=kernel_limits)
    else:
        graph = load_base_graph(kernel_limits=kernel_limits)

    runtime_kwargs["genome"] = genome
    runtime_kwargs["kernel_limits"] = kernel_limits
    runtime_kwargs["cognitive_graph"] = graph


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stream a resident self-discovering Symbiont to Observatory")
    parser.add_argument("--state-file", type=Path, default=Path("~/.local/state/symbiont/organism.json").expanduser())
    parser.add_argument("--interval", type=float, default=15.0)
    parser.add_argument("--checkpoint-every", type=int, default=20)
    parser.add_argument("--display-id", default="local-symbiont")
    parser.add_argument("--max-ticks", type=int, default=None, help="optional finite budget for testing")
    parser.add_argument(
        "--semantic-bootstrap",
        action="store_true",
        help="Also expose the legacy hand-labelled CPU/disk senses as aliases for owner-authored graphs. "
        "Off by default: the native resident stays label-free and develops opaque senses itself.",
    )
    parser.add_argument(
        "--genome-file",
        help="Override the canonical birth genome with an owner-authored genome JSON (first launch only)",
    )
    parser.add_argument(
        "--graph-file",
        help="Override the canonical germinal graph (first launch only; requires --genome-file)",
    )
    parser.add_argument(
        "--observatory-dir",
        type=Path,
        default=Path("~/.local/state/symbiont/observatory").expanduser(),
        help="Base directory for the passive registry/journal artifacts Observatory reads",
    )
    args = parser.parse_args(argv)

    from symbiont.core import OrganismRuntime, ResidentConfig, ResidentOrganism
    from symbiont.core.canonical_birth import restore_resident_with_canonical_cognition
    from symbiont.host.checkpoint import load_checkpoint_file

    runtime_kwargs = {
        "discover_senses": True,
        "bootstrap_semantic_senses": args.semantic_bootstrap,
    }
    existing_payload = load_checkpoint_file(args.state_file)
    if existing_payload is None:
        try:
            _load_first_launch_cognition(args, runtime_kwargs)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            parser.error(str(exc))
        runtime = OrganismRuntime(**runtime_kwargs)
    else:
        runtime = restore_resident_with_canonical_cognition(existing_payload, **runtime_kwargs)

    resolved_state_file = str(Path(args.state_file).expanduser().resolve())
    instance_id = derive_instance_id(resolved_state_file)
    run_id = new_run_id()
    started_at = datetime.now(timezone.utc).isoformat()
    journal_sink = JournalSink(args.observatory_dir, run_id=run_id)
    publisher = SnapshotPublisher([StdoutSink(), journal_sink])
    topology_revision: int | None = None
    previous_edge_classes: dict[str, tuple[int, int]] = {}

    topology_path = Path(args.observatory_dir) / "instances" / f"{instance_id}.topology.json"
    if runtime.cognitive_bridge is None:
        topology_path.unlink(missing_ok=True)

    manifest_path = Path(args.observatory_dir) / "manifests" / f"{instance_id}.manifest.json"

    def sync_manifest() -> None:
        try:
            manifest = create_capture_manifest(
                organism_id=runtime.organism_id,
                instance_id=instance_id,
                run_id=run_id,
                last_sequence=journal_sink.sequence,
                tick=runtime.tick_count,
                topology_revision=topology_revision if topology_revision is not None else 0,
                schema_version=BODY_SCHEMA_SNAPSHOT_VERSION,
                kernel_version=_running_version_string(),
                checkpoint_path=resolved_state_file,
                topology_path=topology_path,
                effective_config=runtime.effective_configuration(),
            )
            write_capture_manifest(manifest_path, manifest)
        except Exception:
            pass

    def publish(result) -> None:
        nonlocal topology_revision
        bridge = runtime.cognitive_bridge
        snapshot = project_tick(
            result,
            acclimation=runtime.acclimation,
            display_id=args.display_id,
            ticks_remaining=None,
            genome=runtime.genome,
            graph=bridge.graph if bridge is not None else None,
            previous_edge_classes=previous_edge_classes,
            body_schema=runtime.body_schema.export_representation(current_tick=runtime.tick_count),
            signal_knowledge=result.signal_knowledge,
            knowledge_events=result.knowledge_events,
            signal_references=result.signal_references,
            social_relations=runtime.social_ledger.relations,
            resting_requested=runtime.resting_requested,
        )
        plan = result.sampling_plan
        active_ids = set(plan.active if plan is not None else ())
        probing_ids = set(plan.probing if plan is not None else ())

        active_states = []
        probing_states = []
        dormant_states = []
        for sense_state in runtime.adaptive_senses.states:
            if sense_state.capability_id in active_ids:
                active_states.append((sense_state, "active"))
            elif sense_state.capability_id in probing_ids:
                probing_states.append((sense_state, "probing"))
            else:
                dormant_states.append((sense_state, "dormant"))
        dormant_states.sort(
            key=lambda item: (item[0].utility, item[0].samples),
            reverse=True,
        )
        selected_states = (active_states + probing_states + dormant_states)[:64]
        sensory_development = [
            {
                "name": s.percept_name,
                "samples": s.samples,
                "availability": round(s.availability, 6),
                "utility": round(s.utility, 6),
                "tier": tier,
            }
            for s, tier in selected_states
        ]
        snapshot["organism"]["sensory_development"] = sensory_development
        snapshot["organism"]["sensory_relations"] = [
            {
                "sense_a": relation.sense_a,
                "sense_b": relation.sense_b,
                "synchronous": _rounded(relation.synchronous),
                "a_to_b": _rounded(relation.a_to_b),
                "b_to_a": _rounded(relation.b_to_a),
                "samples": relation.samples,
            }
            for relation in runtime.adaptive_senses.strongest_relations(limit=24)
        ]
        snapshot["organism"]["sampling"] = {
            "active": len(active_ids),
            "probing": len(probing_ids),
            "dormant": plan.dormant_count if plan is not None else 0,
            "unknown": plan.unknown_count if plan is not None else 0,
            "sampled_this_tick": len(result.snapshot.sampled_capability_ids),
            "discovered": len(result.snapshot.manifest.available),
        }
        envelope_payload = envelope(snapshot)
        publisher.publish(envelope_payload, snapshot)

        if bridge is not None and runtime.genome is not None and result.cognition is not None:
            latest_revision = result.cognition.topology_revision
            if topology_revision is None or latest_revision != topology_revision:
                topology_payload = project_topology(
                    bridge.graph,
                    genome=runtime.genome,
                    kernel_version=_running_version_string(),
                )
                topology_payload["topology_revision"] = latest_revision
                _write_topology(args.observatory_dir, instance_id, topology_payload)
                topology_revision = latest_revision

        write_heartbeat(
            args.observatory_dir,
            instance_id=instance_id,
            run_id=run_id,
            pid=os.getpid(),
            display_id=args.display_id,
            started_at=started_at,
            topology_revision=topology_revision if topology_revision is not None else 0,
            organism_id=runtime.organism_id,
        )

    resident = ResidentOrganism(
        runtime,
        state_file=args.state_file,
        config=ResidentConfig(
            interval_seconds=args.interval,
            checkpoint_every_ticks=args.checkpoint_every,
            max_ticks=args.max_ticks,
        ),
        on_tick=publish,
        on_checkpoint=sync_manifest,
    )

    def stop(_signum, _frame) -> None:
        resident.stop()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    sync_manifest()
    resident.run()
    journal_sink.finalize()
    sync_manifest()
    return 0


if __name__ == "__main__":
    sys.exit(main())
