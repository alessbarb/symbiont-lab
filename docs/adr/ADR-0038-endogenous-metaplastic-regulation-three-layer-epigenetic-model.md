# ADR-0038: Endogenous Metaplastic Regulation: Epigenetic Three-Layer Expression Model

## Status

Accepted

## Context

Lifetime phenotypic adaptation requires adjusting behavioral exploration rates, learning plasticities, and metabolic baselines in response to environmental difficulty. However, if phenotypic regulation is driven by evaluator scores, survival metrics, or external fitness functions, the system degenerates into supervised reinforcement learning. Conversely, if inherited epigenetic marks are confounded with newly acquired somatic shifts, multi-generational lineage analysis becomes mathematically uninterpretable.

## Decision

1. **Three-layer expression hierarchy.** Phenotypic expression is structured in three strictly decoupled strata:
   $$\text{GeneticBase} + \text{InheritedEpimarks} \longrightarrow \text{BirthExpression} \xrightarrow{\text{LifetimeRegulation}} \text{CurrentExpression}$$
2. **Distinct birth expression.** An offspring does not treat inherited epigenetic marks as newly acquired lifetime adaptations. `BirthExpression` captures effective baseline expression at ontogenetic origin, ensuring that lifetime epigenetic drift is measured relative to birth state.
3. **Strictly endogenous metaplastic regulation.** Regulatory shifts in learning rates ($\eta$) and exploration rates ($\epsilon$) are driven exclusively by internal cognitive signals:
   - Prediction error magnitude and prediction error trends;
   - Internally inferred disruption and homeostatic stress;
   - Agency confidence and elapsed developmental ticks.
4. **Prohibition of external fitness inputs.** The epigenetic regulator must never receive or calculate:
   - Evaluator success scores or task reward signals;
   - World resource IDs, hazard types, or semantic labels;
   - Lineage survival scores or external offspring counts.

## Consequences

- True endogenous metaplasticity without supervised external guidance.
- Transgenerational epigenetic inheritance can be cleanly disentangled from individual ontogenetic experience.
- Protects the organism from reward-hacking and researcher bias.

## Introduced in

Milestone EME (Endogenous Metaplastic Epigenetics v1).

## Evidence

`docs/design/genome/endogenous-metaplastic-epigenetics-v1.md`, `symbiont/tests/unit/genetics/test_germline_expression_v2.py`, `lab/tests/experimental_integrity/test_genome_causal_validation.py`.
