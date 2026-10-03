# ADR-0019: Genome v2 Germline Immutability and Epigenetic Demarcation

## Status

Accepted

## Context

In Genome v1, phenotypic configurations, baseline regulatory parameters, and somatic adaptations were stored in a single mutable vector. This led to Lamarckian leakage: transient somatic adaptations directly altered inheritable parameters, destroying phylogenetic signal integrity and rendering evolutionary lineage analysis uninterpretable.

## Decision

1. **Germline immutability.** The canonical genome (`GenomeV2`) is strictly immutable during the lifetime of an individual organism. No ontogenetic event, learning update, or environmental shock may mutate the germline sequence.
2. **Reproductive mutation only.** Genetic mutations (point mutations, structural variations, crossovers) occur exclusively during reproductive events (clonal bud or sexual recombination) via decoupled random streams (ADR-0004).
3. **Endogenous epigenetic layer.** Somatic adaptation and environmental plasticity are expressed through an explicit epigenetic layer:
   - Metaplasticity coefficients modulate learning rates without altering underlying algorithms;
   - Epigenetic tags (methylation/acetylation equivalents) regulate gene expression levels dynamically;
   - Somatic epigenetic drift is tracked as separate state.
4. **Epigenetic inheritance boundary.** At reproduction, epigenetic states are reset by default or filtered through strict germline inheritance rules. Somatic parameters never overwrite germline loci directly.

## Consequences

- Clear theoretical and computational demarcation between evolutionary adaptation (phylogeny) and lifetime learning (ontogeny).
- Enables robust population genetics, phylogenetic tree reconstruction, and lineage tracking across long simulations.
- Prevents catastrophic genetic drift caused by transient environmental noise.

## Introduced in

Milestone G (Genome v2).

## Evidence

`symbiont/tests/unit/genetics/test_genome_v2.py`, `lab/tests/experimental_integrity/test_genome_causal_validation.py`.
