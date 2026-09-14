"""Run a resident Symbiont and emit passive Observatory snapshot envelopes."""

from __future__ import annotations

import argparse
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

from adapter import envelope, project_tick, project_topology
from publisher import JournalSink, SnapshotPublisher, StdoutSink
from registry import derive_instance_id, new_run_id, write_heartbeat


def _rounded(value: float | None) -> float | None:
    return None if value is None else round(value, 6)


def _running_version_string() -> str:
    from symbiont import __version__

    return __version__


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
        "--observatory-dir",
        type=Path,
        default=Path("~/.local/state/symbiont/observatory").expanduser(),
        help="Base directory for the passive registry/journal artifacts Observatory reads",
    )
    args = parser.parse_args(argv)

    from symbiont.core import OrganismRuntime, ResidentConfig, ResidentOrganism

    runtime = OrganismRuntime.load_or_create(
        args.state_file,
        discover_senses=True,
        bootstrap_semantic_senses=args.semantic_bootstrap,
    )
    resolved_state_file = str(Path(args.state_file).expanduser().resolve())
    instance_id = derive_instance_id(resolved_state_file)
    run_id = new_run_id()
    started_at = datetime.now(timezone.utc).isoformat()
    publisher = SnapshotPublisher([StdoutSink(), JournalSink(args.observatory_dir, run_id=run_id)])
    topology_revision = 0
    previous_edge_classes: dict[str, tuple[int, int]] = {}

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
        )
        plan = result.sampling_plan
        active_ids = set(plan.active if plan is not None else ())
        probing_ids = set(plan.probing if plan is not None else ())

        sensory_development = []
        for state in runtime.adaptive_senses.states[:64]:
            if state.capability_id in active_ids:
                tier = "active"
            elif state.capability_id in probing_ids:
                tier = "probing"
            else:
                tier = "dormant"
            sensory_development.append(
                {
                    "name": state.percept_name,
                    "samples": state.samples,
                    "availability": round(state.availability, 6),
                    "utility": round(state.utility, 6),
                    "tier": tier,
                }
            )
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
            if latest_revision != topology_revision:
                topology_revision = latest_revision
                topology_payload = project_topology(
                    bridge.graph, genome=runtime.genome, kernel_version=_running_version_string()
                )
                topology_payload["topology_revision"] = topology_revision
                _write_topology(args.observatory_dir, instance_id, topology_payload)

        write_heartbeat(
            args.observatory_dir,
            instance_id=instance_id,
            run_id=run_id,
            pid=os.getpid(),
            display_id=args.display_id,
            started_at=started_at,
            topology_revision=topology_revision,
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
    )

    def stop(_signum, _frame) -> None:
        resident.stop()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    resident.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
