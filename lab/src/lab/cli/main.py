from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lab.cli.capsule import build_capsule_parser, run_capsule_command
from lab.cli.evaluate import build_evaluate_parser, run_evaluate_command
from lab.cli.experiment import build_experiment_parser, run_experiment_command
from lab.cli.host import build_host_parser, run_host_command
from lab.cli.organism import build_organism_parser, run_organism_command
from lab.cli.study import build_study_parser, run_study_command
from lab.experiments.manifest import RunManifest
from lab.experiments.runner import ExperimentRunner
from lab.experiments.spec import spec_from_payload


def run_reproduce(manifest_path: str | Path, base_dir: Path | str | None = None) -> int:
    path = Path(manifest_path)
    if not path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    manifest = RunManifest.load(path)
    print(f"Reproducing run {manifest.run_id}...")
    print(f"Original protocol: {manifest.protocol} (v{manifest.protocol_version})")
    print(f"Original world digest: {manifest.world_digest}")

    spec = spec_from_payload(manifest.config)
    if base_dir is None:
        resolved = path.resolve()
        if len(resolved.parents) >= 3 and resolved.parents[1].name == "runs":
            base_dir = resolved.parents[2]
        else:
            base_dir = ".symbiont"
    runner = ExperimentRunner(base_dir=base_dir)
    result, new_manifest, _ = runner.run(spec)
    print(f"Re-execution completed with new run_id: {new_manifest.run_id}")
    print(f"New world digest: {new_manifest.world_digest}")

    if manifest.world_digest == "na":
        # No digest was ever recorded for the original run — there is
        # nothing to compare, so this is neither a verified reproduction
        # nor a mismatch. An absent digest must never be read as "equal"
        # (roadmap safety finding A01).
        print(
            "UNVERIFIABLE: the original run recorded no world digest; nothing to compare it against."
        )
        return 2
    if manifest.world_digest != new_manifest.world_digest:
        print("FAIL: World digest mismatch!")
        return 1
    print("SUCCESS: World digest reproduced bitwise.")
    return 0


def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    is_help = "-h" in argv or "--help" in argv
    if not is_help and (not argv or argv[0].startswith("--")):
        from lab.server.server import main as unified_main

        unified_main(argv)
        return

    parser = argparse.ArgumentParser(
        prog="symbiont-lab",
        description="Symbiont Lab: Unified Scientific Interface for Distributed Intelligence Simulation",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    subparsers.add_parser("app", help="Launch the legacy desktop workbench")
    server_p = subparsers.add_parser("server", help="Launch the unified local browser workbench")
    server_p.add_argument("--port", type=int, default=8765, help="Port to listen on")
    server_p.add_argument(
        "--no-browser", action="store_true", help="Don't open the browser automatically"
    )
    server_p.add_argument(
        "--physics3d", action="store_true", help="Run canonical Physics3D in the web app"
    )
    server_p.add_argument("--observatory-dir", default=None, help="Observatory state directory")

    # Subcommands
    experiment_p = subparsers.add_parser(
        "experiment", help="Manage and run declarative experiments"
    )
    build_experiment_parser(experiment_p)

    study_p = subparsers.add_parser("study", help="Run a study protocol")
    build_study_parser(study_p)

    reproduce_p = subparsers.add_parser("reproduce", help="Reproduce a run from manifest.json")
    reproduce_p.add_argument("manifest_path", help="Path to manifest.json")

    host_p = subparsers.add_parser("host", help="Discover safe, read-only local host capabilities")
    build_host_parser(host_p)

    capsule_p = subparsers.add_parser(
        "capsule", help="Sign/verify offline, identity-minimized knowledge capsules"
    )
    build_capsule_parser(capsule_p)

    organism_p = subparsers.add_parser(
        "organism", help="Run the organism's continuous cognitive cycle"
    )
    build_organism_parser(organism_p)

    evaluate_p = subparsers.add_parser(
        "evaluate", help="Laboratory apparatus: measure the organism against real operator judgment"
    )
    build_evaluate_parser(evaluate_p)

    provenance_p = subparsers.add_parser(
        "provenance", help="Query a causal provenance journal (why did this happen?)"
    )
    from lab.cli.provenance import build_provenance_parser

    build_provenance_parser(provenance_p)

    world_p = subparsers.add_parser(
        "world", help="Launch or resume persistent Symbiont World and Observatory"
    )
    world_p.add_argument(
        "world", nargs="?", default="Genesis", help="World name (default: Genesis)"
    )
    world_p.add_argument("--seed", type=int, default=101)
    world_p.add_argument("--founders", type=int, default=8)
    world_p.add_argument("--width", type=int, default=8)
    world_p.add_argument("--height", type=int, default=8)
    world_p.add_argument("--tick-delay", type=float, default=0.5, help="seconds between ticks")
    world_p.add_argument("--port", type=int, default=8766)
    world_p.add_argument(
        "--storage-dir", type=str, default=None, help="Directory for checkpoint storage"
    )
    world_p.add_argument(
        "--observatory-dir", type=str, default=None, help="Observatory state directory"
    )
    world_p.add_argument(
        "--checkpoint-interval", type=int, default=50, help="Ticks between automatic checkpoints"
    )

    args = parser.parse_args(argv)

    if args.subcommand == "app":
        from lab.app.main import main as app_main

        app_main()
        return
    if args.subcommand == "server":
        from lab.server.server import main as unified_main

        server_argv = [
            "--port",
            str(args.port),
        ]
        if args.no_browser:
            server_argv.append("--no-browser")
        if args.physics3d:
            server_argv.append("--physics3d")
        if args.observatory_dir:
            server_argv.extend(["--observatory-dir", str(args.observatory_dir)])
        unified_main(server_argv)
        return
    if args.subcommand == "provenance":
        from lab.cli.provenance import run_provenance_command

        sys.exit(run_provenance_command(args))
    if args.subcommand == "world":
        from lab.cli.world import main as world_main

        world_argv = [
            args.world,
            "--seed",
            str(args.seed),
            "--founders",
            str(args.founders),
            "--width",
            str(args.width),
            "--height",
            str(args.height),
            "--tick-delay",
            str(args.tick_delay),
            "--port",
            str(args.port),
            "--checkpoint-interval",
            str(args.checkpoint_interval),
        ]
        if args.storage_dir:
            world_argv.extend(["--storage-dir", args.storage_dir])
        if args.observatory_dir:
            world_argv.extend(["--observatory-dir", args.observatory_dir])
        world_main(world_argv)
    elif args.subcommand == "experiment":
        sys.exit(run_experiment_command(args))
    elif args.subcommand == "study":
        sys.exit(run_study_command(args))
    elif args.subcommand == "reproduce":
        sys.exit(run_reproduce(args.manifest_path))
    elif args.subcommand == "host":
        sys.exit(run_host_command(args))
    elif args.subcommand == "capsule":
        sys.exit(run_capsule_command(args))
    elif args.subcommand == "organism":
        sys.exit(run_organism_command(args))
    elif args.subcommand == "evaluate":
        sys.exit(run_evaluate_command(args))


if __name__ == "__main__":
    main()
