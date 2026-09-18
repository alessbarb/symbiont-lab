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
    from .provenance import build_observer_provenance
except ImportError:  # Direct script invocation remains a documented interface.
    from adapter import BODY_SCHEMA_SNAPSHOT_VERSION, envelope, project_tick, project_topology
    from manifest import create_capture_manifest, write_capture_manifest
    from publisher import JournalSink, SnapshotPublisher, StdoutSink
    from registry import derive_instance_id, new_run_id, write_heartbeat
    from provenance import build_observer_provenance


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
    from symbiont.cognition.genome import GenomeCodec, legacy_validation_version
    from symbiont.cognition.graph import load_graph_definition
    from symbiont.cognition.limits import KernelLimits

    kernel_limits = KernelLimits()
    if args.genome_file:
        genome_payload = json.loads(Path(args.genome_file).expanduser().read_text(encoding="utf-8"))
        codec = GenomeCodec()
        genome = codec.load(genome_payload)
        codec.validate(genome, kernel_limits, running_version=legacy_validation_version(genome.kernel_compatibility, _running_version_tuple()))
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
    from symbiont.core.runtime_defaults import (
        DEFAULT_CHECKPOINT_TICKS,
        DEFAULT_STATE_FILE,
        DEFAULT_TICK_INTERVAL_SECONDS,
    )
    try:
        from .config import DEFAULT_OBSERVATORY_DIR
    except ImportError:
        from config import DEFAULT_OBSERVATORY_DIR

    parser = argparse.ArgumentParser(description="Stream a resident self-discovering Symbiont to Observatory")
    parser.add_argument("--state-file", type=Path, default=Path(DEFAULT_STATE_FILE).expanduser())
    parser.add_argument("--interval", type=float, default=DEFAULT_TICK_INTERVAL_SECONDS)
    parser.add_argument("--checkpoint-every", type=int, default=DEFAULT_CHECKPOINT_TICKS)
    parser.add_argument("--display-id", default="local-symbiont")
    parser.add_argument("--max-ticks", type=int, default=None, help="optional finite budget for testing")
    parser.add_argument(
        "--sensory-plasticity",
        action="store_true",
        help="Enable organism-owned adaptive sensory receptors; disabled by default for historical equivalence",
    )
    parser.add_argument(
        "--semantic-bootstrap",
        action="store_true",
        help="Also expose the legacy hand-labelled CPU/disk senses as aliases for owner-authored graphs. "
        "Off by default: the native resident stays label-free and develops opaque senses itself.",
    )
    parser.add_argument(
        "--autonomous-behavior",
        action="store_true",
        help="Enable the bounded local action cycle for this explicitly requested resident run",
    )
    parser.add_argument(
        "--no-interoception",
        action="store_true",
        help="Disable internal sensing for a controlled ablation run",
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
        default=Path(DEFAULT_OBSERVATORY_DIR).expanduser(),
        help="Base directory for the passive registry/journal artifacts Observatory reads",
    )
    parser.add_argument(
        "--no-stdout",
        action="store_true",
        help="Do not stream JSON snapshots to stdout (saves to journal only)",
    )
    parser.add_argument(
        "--enable-slm",
        action="store_true",
        default=os.getenv("SYMBIONT_ENABLE_SLM", "").lower() in ("1", "true", "yes"),
        help="Enable organism-owned Private SLM experience capture and generative model training",
    )
    parser.add_argument(
        "--slm-train-interval",
        type=int,
        default=int(os.getenv("SYMBIONT_SLM_TRAIN_INTERVAL", "64")),
        help="Cadence in ticks to evaluate and train candidate SLM models",
    )
    parser.add_argument(
        "--slm-min-records",
        type=int,
        default=32,
        help="Minimum valid experience records required to build a training corpus",
    )
    parser.add_argument(
        "--slm-device",
        default="cpu",
        help="Compute device for Private SLM training (cpu or cuda)",
    )
    args = parser.parse_args(argv)

    from symbiont.core import OrganismRuntime, ResidentConfig, ResidentOrganism
    from symbiont.core.canonical_birth import restore_resident_with_canonical_cognition
    from symbiont.core.capsule import CapsuleKeyPair
    from symbiont.core.local_habitat import LocalHabitat
    from symbiont.host.checkpoint import load_checkpoint_file

    runtime_kwargs = {
        "discover_senses": True,
        "bootstrap_semantic_senses": args.semantic_bootstrap,
        "autonomous_behavior": args.autonomous_behavior,
        "interoception_enabled": not args.no_interoception,
    }
    if args.sensory_plasticity:
        runtime_kwargs["sensory_plasticity"] = True
    existing_payload = load_checkpoint_file(args.state_file)
    if args.enable_slm:
        from symbiont.cognition.birth import load_base_cognition
        from symbiont.cognition.checkpoint import export_genome_checkpoint
        from symbiont.cognition.limits import KernelLimits
        from symbiont.core.canonical_birth import _running_version
        from symbiont.core.cognition_bridge import CognitiveBridge
        from symbiont.host.checkpoint import normalize_checkpoint
        from symbiont.modeling.private_runtime import PrivateModelOrganismRuntime

        if existing_payload is None:
            try:
                _load_first_launch_cognition(args, runtime_kwargs)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                parser.error(str(exc))
            runtime = PrivateModelOrganismRuntime(**runtime_kwargs)
        else:
            normalized = normalize_checkpoint(existing_payload)
            if normalized.get("genome") is None:
                kernel_limits = runtime_kwargs.get("kernel_limits") or KernelLimits()
                genome, graph = load_base_cognition(
                    kernel_limits=kernel_limits,
                    running_version=_running_version(),
                )
                bridge = CognitiveBridge(
                    graph=graph,
                    genome=genome,
                    kernel_limits=kernel_limits,
                )
                normalized["genome"] = export_genome_checkpoint(genome)
                normalized["cognitive_bridge"] = bridge.export_checkpoint()
                runtime_kwargs["kernel_limits"] = kernel_limits
            runtime = PrivateModelOrganismRuntime.from_checkpoint(normalized, **runtime_kwargs)
    else:
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
    sinks = [journal_sink] if args.no_stdout else [StdoutSink(), journal_sink]
    publisher = SnapshotPublisher(sinks)
    topology_revision: int | None = None
    previous_edge_classes: dict[str, tuple[int, int]] = {}
    developmental_baseline = None

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
        nonlocal topology_revision, developmental_baseline
        bridge = runtime.cognitive_bridge
        if developmental_baseline is None and bridge is not None:
            developmental_baseline = bridge.graph
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
            sensory_phenotype=result.sensory_phenotype,
            observer_provenance=build_observer_provenance(runtime, result),
            social_relations=runtime.social_ledger.relations,
            social_resource_evidence=runtime.social_resource_ledger.evidence,
            resting_requested=runtime.resting_requested,
            relation_churn=runtime.adaptive_senses.drain_relation_churn(),
            developmental_baseline=developmental_baseline,
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

    key_file = Path(args.state_file).with_suffix(".key")
    if key_file.is_file():
        try:
            keypair = CapsuleKeyPair.from_private_bytes(key_file.read_bytes())
        except Exception:
            keypair = CapsuleKeyPair.generate()
            key_file.write_bytes(keypair.private_bytes)
    else:
        keypair = CapsuleKeyPair.generate()
        try:
            key_file.write_bytes(keypair.private_bytes)
        except OSError:
            pass

    habitat_dir = Path(args.state_file).parent / "habitat"
    habitat = LocalHabitat(habitat_dir)

    slm_factory = None
    slm_store = None
    if args.enable_slm:
        try:
            from symbiont_lab.modeling.artifacts import FileArtifactStore
            from symbiont_lab.modeling.factory import PrivateModelFactory
            from symbiont_lab.modeling.gateway import ArtifactInferenceGateway
            from symbiont.modeling.authority import (
                ArchitectureId,
                ModelObjective,
                TrainingRequest,
            )
            from symbiont.modeling.corpus import build_training_corpus
            from symbiont.modeling.gateway import PrivateModelBridge
            from symbiont.modeling.tokenizer import NativeTokenizer

            models_dir = Path(args.state_file).parent / "models" / runtime.organism_id
            models_dir.mkdir(parents=True, exist_ok=True)
            slm_store = FileArtifactStore(models_dir)
            slm_factory = PrivateModelFactory(store=slm_store, device=args.slm_device)

            if hasattr(runtime, "model_registry") and runtime.model_registry.models:
                if len(runtime.experience_ledger.records) >= 3:
                    try:
                        corpus = build_training_corpus(runtime.experience_ledger.records)
                        tokenizer = NativeTokenizer.from_records(corpus.train)
                        gateway = ArtifactInferenceGateway(
                            slm_store,
                            vocab_size=len(tokenizer.vocabulary),
                            pad_id=0,
                            device=args.slm_device,
                        )
                        bridge = PrivateModelBridge(
                            registry=runtime.model_registry,
                            tokenizer=tokenizer,
                            gateway=gateway,
                        )
                        runtime.attach_private_model_bridge(bridge)
                    except Exception:
                        pass
        except Exception:
            slm_factory = None
            slm_store = None

    def step_slm_training(current_tick: int) -> None:
        if slm_factory is None or slm_store is None:
            return
        if not hasattr(runtime, "experience_ledger"):
            return
        records = runtime.experience_ledger.records
        if len(records) < args.slm_min_records:
            return
        if current_tick % args.slm_train_interval != 0:
            return

        try:
            from symbiont_lab.modeling.gateway import ArtifactInferenceGateway
            from symbiont.modeling.authority import (
                ArchitectureId,
                ModelObjective,
                TrainingRequest,
            )
            from symbiont.modeling.corpus import build_training_corpus
            from symbiont.modeling.gateway import PrivateModelBridge
            from symbiont.modeling.tokenizer import NativeTokenizer

            corpus = build_training_corpus(records)
            tokenizer = NativeTokenizer.from_records(corpus.train)
            request = TrainingRequest(
                organism_id=runtime.organism_id,
                corpus_hash=corpus.manifest.corpus_hash,
                tokenizer_hash=tokenizer.tokenizer_hash,
                architecture_id=ArchitectureId.GRU_V1,
                objective=ModelObjective.NEXT_TOKEN,
                seed=(hash(runtime.organism_id) + current_tick) & 0x7FFFFFFF,
                context_window=32,
                requested_parameters=1_000_000,
                requested_epochs=2,
                requested_steps=12,
                created_tick_class=current_tick,
            )
            factory_result = slm_factory.build(request=request, corpus=corpus, tokenizer=tokenizer)
            slm_factory.adopt(runtime, factory_result)
            gateway = ArtifactInferenceGateway(
                slm_store,
                vocab_size=len(tokenizer.vocabulary),
                pad_id=0,
                device=args.slm_device,
            )
            bridge = PrivateModelBridge(
                registry=runtime.model_registry,
                tokenizer=tokenizer,
                gateway=gateway,
            )
            runtime.attach_private_model_bridge(bridge)
        except Exception:
            pass

    def on_checkpoint_hook() -> None:
        if args.enable_slm:
            step_slm_training(runtime.tick_count)
        sync_manifest()

    resident = ResidentOrganism(
        runtime,
        state_file=args.state_file,
        config=ResidentConfig(
            interval_seconds=args.interval,
            checkpoint_every_ticks=args.checkpoint_every,
            max_ticks=args.max_ticks,
        ),
        habitat=habitat,
        keypair=keypair,
        on_tick=publish,
        on_checkpoint=on_checkpoint_hook,
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
