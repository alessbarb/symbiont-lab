from __future__ import annotations

import argparse
from pathlib import Path
import sys

from symbiont_lab.dashboard.server import main as dashboard_main
from symbiont_lab.experiments.manifest import RunManifest
from symbiont_lab.experiments.runner import ExperimentRunner
from symbiont_lab.experiments.spec import spec_from_payload
from .archive import build_archive_parser, run_archive_command
from .audit import build_audit_parser, run_audit_command
from .experiment import build_experiment_parser, run_experiment_command
from .host import build_host_parser, run_host_command
from .simulate import build_simulate_parser, run_simulate_command
from .study import build_study_parser, run_study_command


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

    if manifest.world_digest != "na" and manifest.world_digest != new_manifest.world_digest:
        print("FAIL: World digest mismatch!")
        return 1
    print("SUCCESS: World digest reproduced bitwise.")
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="symbiont-lab",
        description="Symbiont Lab: Unified Scientific Interface for Distributed Intelligence Simulation",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # Subcommands
    simulate_p = subparsers.add_parser("simulate", help="Run a synthetic ecology simulation")
    build_simulate_parser(simulate_p)

    dashboard_p = subparsers.add_parser("dashboard", help="Launch interactive localhost dashboard")
    dashboard_p.add_argument("--port", type=int, default=8765, help="Port to listen on")

    experiment_p = subparsers.add_parser("experiment", help="Manage and run declarative experiments")
    build_experiment_parser(experiment_p)

    study_p = subparsers.add_parser("study", help="Run multi-seed comparative studies")
    build_study_parser(study_p)

    audit_p = subparsers.add_parser("audit", help="Verify laboratory scientific integrity")
    build_audit_parser(audit_p)

    archive_p = subparsers.add_parser("archive", help="Inspect local experiment and study memory")
    build_archive_parser(archive_p)

    reproduce_p = subparsers.add_parser("reproduce", help="Reproduce a run from manifest.json")
    reproduce_p.add_argument("manifest_path", help="Path to manifest.json")

    host_p = subparsers.add_parser("host", help="Discover safe, read-only local host capabilities")
    build_host_parser(host_p)

    args = parser.parse_args(argv)

    if args.subcommand == "simulate":
        sys.exit(run_simulate_command(args))
    elif args.subcommand == "dashboard":
        sys.argv = ["symbiont-dashboard", "--port", str(args.port)]
        dashboard_main()
    elif args.subcommand == "experiment":
        sys.exit(run_experiment_command(args))
    elif args.subcommand == "study":
        sys.exit(run_study_command(args))
    elif args.subcommand == "audit":
        sys.exit(run_audit_command(args))
    elif args.subcommand == "archive":
        sys.exit(run_archive_command(args))
    elif args.subcommand == "reproduce":
        sys.exit(run_reproduce(args.manifest_path))
    elif args.subcommand == "host":
        sys.exit(run_host_command(args))


if __name__ == "__main__":
    main()
