from __future__ import annotations

import argparse

from .curiosity import CuriosityPlanner
from .experiment import ExperimentSpec
from .reasoning import ReasoningEngine
from .simulation import run_simulation


def main() -> None:
    p = argparse.ArgumentParser(description="Run a Symbiont Lab safe simulation")
    p.add_argument("--title", default="CLI experiment")
    p.add_argument("--hypothesis", default="")
    p.add_argument("--success-criteria", default="")
    p.add_argument("--notes", default="")
    p.add_argument("--hosts", type=int, default=100); p.add_argument("--steps", type=int, default=300); p.add_argument("--seed", type=int, default=7)
    p.add_argument("--threat-rate", type=float, default=0.018); p.add_argument("--poison-fraction", type=float, default=0.08); p.add_argument("--heterogeneity", type=float, default=0.12)
    p.add_argument("--drift-step", type=int, default=-1); p.add_argument("--drift-fraction", type=float, default=0.35); p.add_argument("--drift-magnitude", type=float, default=0.22)
    args = p.parse_args()
    spec = ExperimentSpec(title=args.title,hypothesis=args.hypothesis,success_criteria=args.success_criteria,notes=args.notes,hosts=args.hosts,steps=args.steps,seed=args.seed,threat_rate=args.threat_rate,poison_fraction=args.poison_fraction,heterogeneity=args.heterogeneity,drift_step=None if args.drift_step<0 else args.drift_step,drift_fraction=args.drift_fraction,drift_magnitude=args.drift_magnitude,delay=0.0)
    result, collective = run_simulation(spec.hosts,spec.steps,spec.seed,spec.threat_rate,spec.poison_fraction,spec.heterogeneity,spec.drift_step,spec.drift_fraction,spec.drift_magnitude)
    print("SYMBIONT LAB — simulation complete")
    print(f"experiment:               {spec.title}")
    if spec.hypothesis: print(f"hypothesis:               {spec.hypothesis}")
    if spec.success_criteria: print(f"success criteria:         {spec.success_criteria}")
    if spec.notes: print(f"notes:                    {spec.notes}")
    print(f"hosts / steps / seed:     {spec.hosts} / {spec.steps} / {spec.seed}")
    print(f"detection rate:           {result.detection_rate:.1%}")
    print(f"precision:                {result.precision:.1%}")
    print(f"open questions:           {result.open_questions}")
    print(f"self confidence:          {result.self_confidence:.2f}")
    print(f"epistemic pressure:       {result.epistemic_pressure:.2f}")
    print(f"metacognitive status:     {result.metacognitive_status}")
    print(f"calibration error:        {result.calibration_error:.3f}")
    print(f"blind-spot rate:          {result.blind_spot_rate:.1%}")
    print(f"drift adaptations:        {result.drift_adaptations}")
    print(f"recent drift FP rate:     {result.recent_drift_false_positive_rate:.1%}")
    print(f"curiosity probes:         {result.curiosity_probes}")
    print(f"top probe utility:        {result.top_probe_utility:.2f}")
    hypotheses = ReasoningEngine().analyze(collective)
    probes = CuriosityPlanner().plan(hypotheses, collective)
    if probes:
        print("\nCuriosity agenda (shadow-only):")
        for probe in probes:
            print(f"  {probe.feature} {probe.change} — utility={probe.utility:.2f}, EIG={probe.expected_information_gain:.2f}")
            print(f"    ? {probe.question}")


if __name__ == "__main__":
    main()
