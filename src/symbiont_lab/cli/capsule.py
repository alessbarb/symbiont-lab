from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from symbiont.core import CapsuleKeyPair, SourceTrustModel, create_capsule, observe_capsule_trust, verify_capsule
from symbiont.core.capsule import KnowledgeCapsule
from symbiont.host import acclimate_local_host, export_checkpoint, learn_local_host_rhythms, track_local_host_drift


def build_capsule_parser(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="capsule_action", required=True)

    create_cmd = sub.add_parser(
        "create",
        help="Sign a checkpoint of safe abstract host beliefs into an offline knowledge capsule",
    )
    create_cmd.add_argument(
        "--ticks",
        type=int,
        default=5,
        help="Number of ticks to learn from before exporting (1-1000, default 5)",
    )
    create_cmd.add_argument(
        "--keyfile",
        help=(
            "Local signing keyfile: reused if present, created if missing. "
            "Omit for an ephemeral (unsaved) signer identity."
        ),
    )

    sub.add_parser(
        "verify",
        help="Verify a knowledge capsule's signature, read as JSON on stdin",
    )

    ingest_cmd = sub.add_parser(
        "ingest",
        help="Verify a capsule (stdin) and learn per-source reliability against this host's own beliefs",
    )
    ingest_cmd.add_argument(
        "--ticks",
        type=int,
        default=5,
        help="Number of ticks to acclimate this host's own baseline from before comparing (1-1000, default 5)",
    )


def _load_or_create_keypair(keyfile: str | None) -> CapsuleKeyPair:
    if keyfile is None:
        return CapsuleKeyPair.generate()
    path = Path(keyfile)
    if path.is_file():
        data = json.loads(path.read_text())
        return CapsuleKeyPair.from_private_bytes(bytes.fromhex(data["private_key"]))
    keypair = CapsuleKeyPair.generate()
    path.write_text(json.dumps({"private_key": keypair.private_bytes.hex()}))
    return keypair


def run_capsule_command(args: argparse.Namespace) -> int:
    if args.capsule_action == "create":
        ticks = min(max(int(args.ticks), 1), 1000)
        keypair = _load_or_create_keypair(args.keyfile)
        if args.keyfile is None:
            print(
                "warning: no --keyfile given; this capsule's signer identity is ephemeral and cannot be reused",
                file=sys.stderr,
            )
        acclimation, _ = acclimate_local_host(ticks=ticks)
        rhythm_model = learn_local_host_rhythms(ticks=ticks)
        drift_baselines, _ = track_local_host_drift(ticks=ticks)
        payload = export_checkpoint(
            acclimation=acclimation, rhythm_model=rhythm_model, drift_baselines=drift_baselines
        )
        capsule = create_capsule(keypair, payload)
        print(json.dumps(capsule.to_dict(), indent=2, sort_keys=True))
        return 0
    if args.capsule_action == "verify":
        try:
            data = json.loads(sys.stdin.read())
        except json.JSONDecodeError as exc:
            print(f"invalid capsule JSON: {exc}", file=sys.stderr)
            return 1
        try:
            capsule = KnowledgeCapsule.from_dict(data)
        except (KeyError, ValueError) as exc:
            print(f"malformed capsule: {exc}", file=sys.stderr)
            return 1
        valid = verify_capsule(capsule)
        payload = {
            "valid": valid,
            "schema_version": capsule.schema_version,
            "signer_public_key": capsule.signer_public_key.hex(),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if valid else 1
    if args.capsule_action == "ingest":
        ticks = min(max(int(args.ticks), 1), 1000)
        try:
            data = json.loads(sys.stdin.read())
        except json.JSONDecodeError as exc:
            print(f"invalid capsule JSON: {exc}", file=sys.stderr)
            return 1
        try:
            capsule = KnowledgeCapsule.from_dict(data)
        except (KeyError, ValueError) as exc:
            print(f"malformed capsule: {exc}", file=sys.stderr)
            return 1

        acclimation, _ = acclimate_local_host(ticks=ticks)
        model = SourceTrustModel()
        try:
            scores = observe_capsule_trust(model, acclimation=acclimation, capsule=capsule)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1

        payload = {
            "signer_public_key": capsule.signer_public_key.hex(),
            "agreement_scores": scores,
            "reliability": {
                pattern_family: {
                    "count": snapshot.count,
                    "mean": snapshot.mean,
                    "variance": snapshot.variance,
                }
                for pattern_family in scores
                if (snapshot := model.reliability(capsule.signer_public_key, pattern_family)) is not None
            },
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    return 1
