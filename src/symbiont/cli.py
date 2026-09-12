from __future__ import annotations

import argparse

from .reasoning import ReasoningEngine
from .simulation import run_simulation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Symbiont Lab safe simulation")
    parser.add_argument("--hosts", type=int, default=100); parser.add_argument("--steps", type=int, default=300); parser.add_argument("--seed", type=int, default=7); parser.add_argument("--threat-rate", type=float, default=0.018); parser.add_argument("--poison-fraction", type=float, default=0.08); parser.add_argument("--heterogeneity", type=float, default=0.12); args = parser.parse_args()
    result, collective = run_simulation(args.hosts, args.steps, args.seed, args.threat_rate, args.poison_fraction, args.heterogeneity)
    print("SYMBIONT LAB — simulation complete")
    print(f"hosts:                 {result.hosts}"); print(f"steps:                 {result.steps}"); print(f"pathogen events:       {result.pathogen_events}"); print(f"investigations:        {result.investigated}"); print(f"true positives:        {result.true_positive_investigations}"); print(f"false positives:       {result.false_positive_investigations}"); print(f"false negatives:       {result.false_negatives}"); print(f"detection rate:        {result.detection_rate:.1%}"); print(f"precision:             {result.precision:.1%}"); print(f"known patterns:        {result.collective_patterns}"); print(f"open questions:        {result.open_questions}"); print(f"mean source trust:     {result.mean_source_trust:.2f}"); print(f"trust gap:             {result.trust_gap:+.2f}"); print(f"reasoning hypotheses:  {result.reasoning_hypotheses}"); print(f"top reasoning priority:{result.top_reasoning_priority: .2f}")
    hypotheses = ReasoningEngine().analyze(collective)
    if hypotheses:
        print("\nBounded hypotheses:")
        for h in hypotheses:
            print(f"  {h.fingerprint} — {h.title} (priority={h.priority:.2f}, confidence={h.confidence:.2f})")
            for question in h.questions: print(f"    ? {question}")


if __name__ == "__main__": main()
