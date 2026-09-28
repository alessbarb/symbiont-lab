# ADR-0033: Endogenous Stress-Induced Reproduction and Clonal Lineage

## Status

Accepted

## Context

In evolutionary simulations and artificial life studies, reproduction is frequently managed externally: a simulator script counts population fitness from an all-seeing oracle, kills unfit agents, and spawns clones based on an external schedule. This destroys autonomous agency, breaches ground-truth isolation (ADR-0002), and invalidates ecological evolutionary dynamics.

## Decision

1. **Endogenous reproductive trigger.** Reproduction is initiated strictly from within the organism's autonomous physiological domain. Neither Lab nor World can trigger birth directly.
2. **Stress-induced persistent threshold.** Clonal budding requires sustained physiological stress above threshold for at least 8 consecutive ticks (`Reproductive Threshold = 8` ticks) coupled with sufficient metabolic reserves. This models emergency adaptive lineage propagation under severe ecological pressure.
3. **Expensive metabolic investment.** Reproduction is physiologically costly: the parent organism transfers a mandatory fraction (typically $\ge 40\%$) of its accumulated metabolic reserve to initialize the offspring's body and basic vital functions. Parents cannot reproduce carelessly without risking starvation.
4. **Epigenetic reset with germline transmission.** During clonal budding, the offspring receives an exact copy of the parent's germline `GenomeV2` (subject to point mutations via decoupled RNG streams, ADR-0004), while transient somatic epigenetic states are selectively reset to constitutional baselines.
5. **Irreversible lineage extinction.** When all members of an organism's lineage suffer death, the lineage is permanently extinguished. The simulation does not auto-respawn extinct lineages.

## Consequences

- Evolution and population dynamics are driven entirely by genuine ecological fitness and metabolic viability.
- Prevents runaway population explosions through strict energetic budgeting.
- Lineage trees and genealogical branches reflect authentic developmental history.

## Introduced in

v0.26.0 (Lineage & Reproduction Architecture).

## Evidence

`src/symbiont/core/orchestration/canonical_birth.py`, `docs/architecture.md` (L592), `docs/explanation/06-reproduction-and-lineage.md`.
