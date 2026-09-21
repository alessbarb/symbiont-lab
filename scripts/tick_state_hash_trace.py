#!/usr/bin/env python3
"""L6.9.8 tool: per-tick state_hash() trace for optimization equivalence checks.

Prints one state_hash per line for a fixed-seed, fixed-genome, cognition-
attached organism over N ticks. Run before and after an optimization on the
same tick budget and diff the two outputs -- any divergence means the
change was not semantically transparent.

``bootstrap_semantic_senses=False, discover_senses=False`` is required, not
cosmetic: with real host sensing active (CPU%, RSS, etc. via
StandardLibraryProvider), the organism reads genuinely different real
system state from run to run and from tick to tick, feeding real variance
into cost-based attention/sampling decisions. That diverges two runs of
*identical, unmodified* code within a few dozen ticks -- confirmed
empirically (same process, two instances, same seed/genome/code: diverged
by tick ~10 even with time.perf_counter/time.monotonic frozen, and
immediately in earlier, buggier freezing attempts). Freezing the clock
alone does not fix it; the sampled *values* themselves are real and live,
not just their timing. A fully synthetic organism (no real host reads,
already the standard pattern across this repo's own test suite) is
deterministic across runs -- verified over 500 ticks, two instances.
"""
from __future__ import annotations

import argparse

from symbiont.cognition.birth import load_base_cognition
from symbiont.cognition.limits import KernelLimits
from symbiont.core.physiology import LivingBodyState
from symbiont.core.runtime import OrganismRuntime


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticks", type=int, default=300)
    parser.add_argument("--organism-id", default="equivalence-probe")
    args = parser.parse_args()

    limits = KernelLimits()
    genome, graph = load_base_cognition(kernel_limits=limits, running_version=(0, 80, 0))
    body = LivingBodyState(energy_reserve=1_000_000.0, max_energy=1_000_000.0)
    runtime = OrganismRuntime(
        organism_id=args.organism_id,
        genome=genome,
        cognitive_graph=graph,
        kernel_limits=limits,
        actuation_enabled=True,
        motor_exploration_mode="babbling",
        bootstrap_semantic_senses=False,
        discover_senses=False,
        min_samples=1,
        investigate_ticks=0,
        living_body_state=body,
    )

    for _ in range(args.ticks):
        runtime.tick()
        print(runtime.state_hash())


if __name__ == "__main__":
    main()
