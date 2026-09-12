from __future__ import annotations

import argparse

from .reasoning import ReasoningEngine
from .simulation import run_simulation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Symbiont Lab safe simulation")
    parser.add_argument("--hosts", type=int, default=100)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--threat-rate", type=float, default=0.018)
    parser.add_argument("--poison-fraction", type=float, default=0.08)
    parser.add_argument("--heterogeneity", type=float, default=0.12)
    parser.add_argument("--drift-step", type=int, default=-1, help="-1 means 55% of the experiment")
    parser.add_argument("--drift-fraction", type=float, default=0.35)
    parser.add_argument("--drift-magnitude", type=float, default=0.22)
    args = parser.parse_args()

    result, collective = run_simulation(
        args.hosts,
        args.steps,
        args.seed,
        args.threat_rate,
        args.poison_fraction,
        args.heterogeneity,
        None if args.drift_step < 0 else args.drift_step,
        args.drift_fraction,
        args.drift_magnitude,
    )
    print("SYMBIONT LAB — simulation complete")
    print(f"hosts:                    {result.hosts}")
    print(f"steps:                    {result.steps}")
    print(f"pathogen events:          {result.pathogen_events}")
    print(f"investigations:           {result.investigated}")
    print(f"true positives:           {result.true_positive_investigations}")
    print(f"false positives:          {result.false_positive_investigations}")
    print(f"false negatives:          {result.false_negatives}")
    print(f"detection rate:           {result.detection_rate:.1%}")
    print(f"precision:                {result.precision:.1%}")
    print(f"known patterns:           {result.collective_patterns}")
    print(f"open questions:           {result.open_questions}")
    print(f"self confidence:          {result.self_confidence:.2f}")
    print(f"epistemic pressure:       {result.epistemic_pressure:.2f}")
    print(f"metacognitive status:     {result.metacognitive_status}")
    print(f"calibration error:        {result.calibration_error:.3f}")
    print(f"blind-spot rate:          {result.blind_spot_rate:.1%}")
    print(f"drift step:               {result.drift_step}")
    print(f"drifted hosts:            {result.drifted_hosts}")
    print(f"drift adaptations:        {result.drift_adaptations}")
    print(f"drift false-positive rate:{result.drift_false_positive_rate: .1%}")
    print(f"recent drift FP rate:     {result.recent_drift_false_positive_rate:.1%}")

    hypotheses = ReasoningEngine().analyze(collective)
    if hypotheses:
        print("\nBounded hypotheses:")
        for h in hypotheses:
            print(f"  {h.fingerprint} — {h.title} (priority={h.priority:.2f}, confidence={h.confidence:.2f})")
            for question in h.questions:
                print(f"    ? {question}")


if __name__ == "__main__":
    main()
