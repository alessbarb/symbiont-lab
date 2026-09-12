from __future__ import annotations

import argparse

from .curiosity import CuriosityPlanner
from .reasoning import ReasoningEngine
from .simulation import run_simulation


def main() -> None:
    parser=argparse.ArgumentParser(description="Run the Symbiont Lab safe simulation"); parser.add_argument("--hosts",type=int,default=100); parser.add_argument("--steps",type=int,default=300); parser.add_argument("--seed",type=int,default=7); parser.add_argument("--threat-rate",type=float,default=0.018); parser.add_argument("--poison-fraction",type=float,default=0.08); parser.add_argument("--heterogeneity",type=float,default=0.12); parser.add_argument("--drift-step",type=int,default=-1); parser.add_argument("--drift-fraction",type=float,default=0.35); parser.add_argument("--drift-magnitude",type=float,default=0.22); args=parser.parse_args()
    result,collective=run_simulation(args.hosts,args.steps,args.seed,args.threat_rate,args.poison_fraction,args.heterogeneity,None if args.drift_step<0 else args.drift_step,args.drift_fraction,args.drift_magnitude)
    print("SYMBIONT LAB — simulation complete"); print(f"hosts:                    {result.hosts}"); print(f"steps:                    {result.steps}"); print(f"detection rate:           {result.detection_rate:.1%}"); print(f"precision:                {result.precision:.1%}"); print(f"open questions:           {result.open_questions}"); print(f"self confidence:          {result.self_confidence:.2f}"); print(f"epistemic pressure:       {result.epistemic_pressure:.2f}"); print(f"metacognitive status:     {result.metacognitive_status}"); print(f"calibration error:        {result.calibration_error:.3f}"); print(f"blind-spot rate:          {result.blind_spot_rate:.1%}"); print(f"drift adaptations:        {result.drift_adaptations}"); print(f"recent drift FP rate:     {result.recent_drift_false_positive_rate:.1%}"); print(f"curiosity probes:         {result.curiosity_probes}"); print(f"top probe utility:        {result.top_probe_utility:.2f}")
    reasoner=ReasoningEngine(); hypotheses=reasoner.analyze(collective); probes=CuriosityPlanner().plan(hypotheses,collective)
    if probes:
        print("\nCuriosity agenda (shadow-only):")
        for probe in probes: print(f"  {probe.feature} {probe.change} — utility={probe.utility:.2f}, EIG={probe.expected_information_gain:.2f}\n    ? {probe.question}")


if __name__=="__main__": main()
