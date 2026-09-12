from __future__ import annotations

import argparse

from .simulation import run_simulation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Symbiont Lab safe simulation")
    parser.add_argument("--hosts", type=int, default=100)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    result, collective = run_simulation(args.hosts, args.steps, args.seed)
    print("SYMBIONT LAB — simulation complete")
    print(f"hosts:             {result.hosts}")
    print(f"steps:             {result.steps}")
    print(f"pathogen events:   {result.pathogen_events}")
    print(f"investigations:    {result.investigated}")
    print(f"true positives:    {result.true_positive_investigations}")
    print(f"false positives:   {result.false_positive_investigations}")
    print(f"detection rate:    {result.detection_rate:.1%}")
    print(f"precision:         {result.precision:.1%}")
    print(f"known patterns:    {result.collective_patterns}")
    print(f"open questions:    {result.open_questions}")

    questions = collective.open_questions()[:5]
    if questions:
        print("\nTop open questions:")
        for q in questions:
            print(f"  {q.fingerprint}: reports={q.reports}, confidence={q.confidence:.2f}")


if __name__ == "__main__":
    main()
