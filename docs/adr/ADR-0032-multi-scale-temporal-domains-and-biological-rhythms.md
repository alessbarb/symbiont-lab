# ADR-0032: Multi-Scale Temporal Domains and Biological Rhythms

## Status

Accepted

## Context

In complex host systems and continuous synthetic environments, physical and sensory dynamics manifest across radically different time horizons: high-frequency actuator jitter and synaptic firing occur on millisecond scales, homeostatic energy balance shifts across seconds, and circadian host activity or environmental seasons evolve over hours. If all statistical estimators and drift detectors operate directly on raw micro-ticks, high-frequency noise causes aliasing, jittery decisions, and false-positive regime shift alarms.

## Decision

1. **Three-tier hierarchical temporal domains.** The organism's internal clocks and dynamics are partitioned into three explicit, non-interfering temporal layers:
   - **Micro-Domain (Fast Causal Integration):** Operates on each raw tick ($\tau \in [0.1, 1.0]$). Governs reflex responses, continuous sensor ingestion, leaky integrator dynamics, and instantaneous efference copy validation.
   - **Meso-Domain (Homeostatic & Behavioral Cadence):** Operates across windows of 10–50 ticks. Governs executive action arbitration, motor commitment windows, metabolic burn accounting, and running variance estimation.
   - **Macro-Domain (Circadian & Epistemic Acclimation):** Operates across multi-hundred or multi-thousand tick epochs. Governs baseline mean shifting, slow drift detection, circadian phase alignment, and memory consolidation sweeps.
2. **Phase decoupling.** Fast micro-estimators never directly update slow macro-baselines. Statistical aggregation flows upward through low-pass filters (EWMA with scale-appropriate decay coefficients $\alpha$), preventing single-tick transients from destabilizing long-term adaptation.
3. **Biological circadian tracking.** Symbiont tracks an internal cyclic phase without querying OS wall-clock time, synchronizing endogenous metabolic cycles to observed recurring patterns in host load and resource availability.

## Consequences

- Robust drift detection that discriminates between transient sensory spikes and genuine structural regime changes.
- Eliminates temporal aliasing in long-term statistical models.
- Organism adapts smoothly to cyclical host and ecological patterns.

## Introduced in

v0.28.0 (Temporal Domains Architecture).

## Evidence

`symbiont/docs/explanation/02-temporal-domains.md`, `symbiont/tests/unit/core/test_temporal_domains.py`, `src/symbiont/host/rhythms.py`.
