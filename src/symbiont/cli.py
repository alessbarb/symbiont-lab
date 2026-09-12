from __future__ import annotations

import argparse

from .simulation import run_simulation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Symbiont Lab safe simulation")
    parser.add_argument("--hosts", type=int, default=100)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--threat-rate", type=float, default=0.018)
    parser.add_argument("--poison-fraction", type=float, default=0.08)
    parser.add_argument("--heterogeneity", type=float, default=0.12)
    args = parser.parse_args()

    result, collective = run_simulation(
        args.hosts,
        args.steps,
        args.seed,
        args.threat_rate,
        args.poison_fraction,
        args.heterogeneity,
    )
    print("SYMBIONT LAB — simulation complete")
    print(f"hosts:               {result.hosts}")
    print(f"steps:               {result.steps}")
    print(f"pathogen events:     {result.pathogen_events}")
    print(f"benign events:       {result.benign_events}")
    print(f"investigations:      {result.investigated}")
    print(f"true positives:      {result.true_positive_investigations}")
    print(f"false positives:     {result.false_positive_investigations}")
    print(f"false negatives:     {result.false_negatives}")
    print(f"detection rate:      {result.detection_rate:.1%}")
    print(f"precision:           {result.precision:.1%}")
    print(f"false-positive rate: {result.false_positive_rate:.1%}")
    print(f"known patterns:      {result.collective_patterns}")
    print(f"open questions:      {result.open_questions}")
    print(f"mean source trust:   {result.mean_source_trust:.2f}")
    print(f"low-trust sources:   {result.low_trust_sources}")
    print(f"poisoned agents:     {result.poisoned_agents}")
    print(f"trust gap:           {result.trust_gap:+.2f}")

    questions = collective.open_questions()[:5]
    if questions:
        print("\nTop open questions:")
        for q in questions:
            print(
                f"  {q.fingerprint}: reports={q.reports}, sources={q.sources}, "
                f"threat={q.threat_probability:.2f}, certainty={q.certainty:.2f}"
            )


if __name__ == "__main__":
    main()
