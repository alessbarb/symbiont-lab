from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn

from symbiont_lab.experiments.loader import load_experiment_file
from symbiont_lab.experiments.runner import ExperimentRunner


def build_experiment_parser(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="experiment_action", required=True)
    run_cmd = sub.add_parser("run", help="Run a declarative experiment from TOML spec")
    run_cmd.add_argument("spec_path", type=Path, help="Path to experiment.toml")


def run_experiment_command(args: argparse.Namespace) -> int:
    if args.experiment_action == "run":
        spec = load_experiment_file(args.spec_path)
        print(f"Loaded experiment '{spec.experiment_id}' (protocol: {spec.protocol}/v{spec.protocol_version})")
        print(f"Hypothesis: {spec.hypothesis.strip()}")
        runner = ExperimentRunner()
        result, manifest, run_dir = _run_with_progress(runner, spec)
        print(f"Execution complete: {manifest.run_id}")
        print(f"Artifacts recorded in: {run_dir}")
        print(f"Manifest: {run_dir / 'manifest.json'}")
        print(f"World digest: {manifest.world_digest}")
        return 0
    return 1


def _run_with_progress(runner: ExperimentRunner, spec):
    console = Console()
    if spec.protocol == "simulate":
        total = max(spec.steps, 1)
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(f"Running {spec.protocol}", total=total)
            seen_steps: set[int] = set()

            def _on_event(ev) -> None:
                seen_steps.add(ev.step)
                progress.update(task, completed=min(len(seen_steps), total))

            return runner.run(spec, progress_cb=_on_event)
    with console.status(f"Running {spec.protocol}..."):
        return runner.run(spec)
