from __future__ import annotations

import argparse

from symbiont.environment.rng import make_rng_streams
from symbiont.environment.world import make_profiles
from symbiont.simulation import run_simulation


def build_audit_parser(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="audit_action", required=True)
    sub.add_parser("verify", help="Verify laboratory experimental invariants")


def run_audit_command(args: argparse.Namespace) -> int:
    if args.audit_action == "verify":
        print("Auditing experimental integrity invariants...")

        # 1. Deterministic RNG stream isolation
        s1 = make_rng_streams(42)
        p1 = make_profiles(10, s1.profiles)

        s2 = make_rng_streams(42)
        # Even if agent stream is drawn differently, profiles stream must be identical
        s2.agents.sample([1, 2, 3], 1)
        p2 = make_profiles(10, s2.profiles)

        assert [p.cpu for p in p1] == [p.cpu for p in p2], "RNG stream orthogonality violation!"
        print("✓ RNG stream isolation: verified.")

        # 2. Same-seed same-world simulation parity
        res_a, _ = run_simulation(hosts=20, steps=60, seed=123)
        res_b, _ = run_simulation(hosts=20, steps=60, seed=123)
        assert res_a.pathogen_events == res_b.pathogen_events, (
            "Same seed produced different pathogen count!"
        )
        assert res_a.benign_events == res_b.benign_events, (
            "Same seed produced different benign count!"
        )
        print("✓ Deterministic simulation parity: verified.")

        print("All experimental invariants verified successfully.")
        return 0
    return 1
