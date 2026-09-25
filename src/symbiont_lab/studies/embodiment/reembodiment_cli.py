"""CLI runner for the preregistered A→B→A Physics3D study."""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from symbiont_lab.physics3d.engine import run as run_physics3d
from symbiont_lab.studies.embodiment.reembodiment_reacclimation import (
    ReembodimentObservation,
    analyze_reembodiment_observations,
    observation_from_checkpoint,
)

_BODY_ALIASES = {
    "humanoid": "anthropomorphic-v6",
    "anthropomorphic": "anthropomorphic-v6",
    "anthropomorphic-v6": "anthropomorphic-v6",
    "crawler": "crawler-v1",
    "crawler-v1": "crawler-v1",
    "asymmetric": "asymmetric-v1",
    "asymmetric-v1": "asymmetric-v1",
}


def _parse_sequence(raw: str) -> tuple[str, str, str]:
    values = tuple(
        _BODY_ALIASES.get(item.strip().lower(), item.strip())
        for item in raw.split(",")
        if item.strip()
    )
    if len(values) != 3:
        raise ValueError("sequence must contain exactly three bodies: A,B,A")
    if values[0] != values[2]:
        raise ValueError("A→B→A requires the first and third body contracts to match")
    if values[1] == values[0]:
        raise ValueError("B must use a different body contract from A")
    return values


def _observation_payload(
    observation: ReembodimentObservation,
) -> dict[str, object]:
    payload = asdict(observation)
    payload["historical_candidate_ids"] = list(observation.historical_candidate_ids)
    payload["executable_binding_ids"] = list(observation.executable_binding_ids)
    return payload


def _run_epoch(
    *,
    label: str,
    body_kind: str,
    ticks: int,
    seed: int,
    root: Path,
    symbiont_file: Path,
    new_symbiont: bool,
    fresh_body: bool,
    enable_slm: bool,
) -> tuple[ReembodimentObservation, ...]:
    trace: list[ReembodimentObservation] = []

    def observe(_tick: int, checkpoint: dict) -> None:
        trace.append(observation_from_checkpoint(checkpoint))

    epoch_dir = root / label.lower()
    epoch_dir.mkdir(parents=True, exist_ok=True)
    exit_code = run_physics3d(
        headless=True,
        ticks=ticks,
        seed=seed,
        body_kind=body_kind,
        symbiont_file=symbiont_file,
        body_file=epoch_dir / "body.json",
        telemetry_file=epoch_dir / "telemetry-v4.1",
        checkpoint_interval=max(1, ticks),
        fresh_body=fresh_body,
        new_symbiont=new_symbiont,
        show_monitor=False,
        enable_slm=enable_slm,
        checkpoint_observer=observe,
    )
    if exit_code != 0:
        raise RuntimeError(f"Physics3D epoch {label} exited with status {exit_code}")
    if not trace:
        raise RuntimeError(f"Physics3D epoch {label} produced no observations")
    return tuple(trace)


def run_study(
    *,
    sequence: tuple[str, str, str],
    ticks: int,
    seed: int,
    output: Path,
    overwrite: bool,
    enable_slm: bool,
) -> dict[str, object]:
    if ticks < 1:
        raise ValueError("ticks must be positive")
    if output.exists():
        if not overwrite:
            raise FileExistsError(f"output directory already exists: {output}; use --overwrite")
        shutil.rmtree(output)
    output.mkdir(parents=True)

    symbiont_file = output / "subject.symbiont"
    a1 = _run_epoch(
        label="A1",
        body_kind=sequence[0],
        ticks=ticks,
        seed=seed,
        root=output,
        symbiont_file=symbiont_file,
        new_symbiont=True,
        fresh_body=False,
        enable_slm=enable_slm,
    )
    b = _run_epoch(
        label="B",
        body_kind=sequence[1],
        ticks=ticks,
        seed=seed,
        root=output,
        symbiont_file=symbiont_file,
        new_symbiont=False,
        fresh_body=True,
        enable_slm=enable_slm,
    )
    a2 = _run_epoch(
        label="A2",
        body_kind=sequence[2],
        ticks=ticks,
        seed=seed,
        root=output,
        symbiont_file=symbiont_file,
        new_symbiont=False,
        fresh_body=True,
        enable_slm=enable_slm,
    )

    result = analyze_reembodiment_observations(
        a1_trace=a1,
        b_trace=b,
        a2_trace=a2,
    )
    payload = {
        "protocol": "embodiment.reembodiment-reacclimation",
        "protocol_version": 1,
        "seed": seed,
        "ticks_per_epoch": ticks,
        "sequence": list(sequence),
        "slm_enabled": enable_slm,
        **result.as_dict(),
    }
    (output / "result.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    traces = {
        "A1": [_observation_payload(item) for item in a1],
        "B": [_observation_payload(item) for item in b],
        "A2": [_observation_payload(item) for item in a2],
    }
    (output / "observations.json").write_text(
        json.dumps(traces, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="symbiont-reembodiment-study",
        description="Run the preregistered Physics3D A→B→A reacclimation study.",
    )
    parser.add_argument(
        "--sequence",
        default="humanoid,crawler,humanoid",
        help="Three bodies A,B,A; aliases: humanoid,crawler,asymmetric",
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=512,
        help="Maximum cognition ticks per embodiment epoch",
    )
    parser.add_argument("--seed", type=int, default=991)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reembodiment-study"),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing output directory",
    )
    parser.add_argument(
        "--enable-slm",
        action="store_true",
        help="Enable the private SLM during the study (off by default)",
    )
    args = parser.parse_args(argv)

    try:
        sequence = _parse_sequence(args.sequence)
        payload = run_study(
            sequence=sequence,
            ticks=args.ticks,
            seed=args.seed,
            output=args.output,
            overwrite=args.overwrite,
            enable_slm=args.enable_slm,
        )
    except Exception as exc:
        parser.exit(2, f"symbiont-reembodiment-study: {exc}\n")

    print(json.dumps(payload, indent=2, sort_keys=True))
    print(f"\nResult: {args.output / 'result.json'}")
    print(f"Verdict: {payload['verdict']}")
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
