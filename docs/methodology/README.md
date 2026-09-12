# Scientific Methodology

## Principles of Synthetic Experimentation

1. **Deterministic RNG Stream Isolation:**
   Unrelated aspects of stochasticity must not interfere with each other. Random number generation is divided into orthogonal streams derived via SHA-256 (`symbiont-lab:{seed}:{namespace}`).

2. **Causal Attention Prefix Integrity:**
   Causal attention mechanisms process events sequentially. Selectors cannot peek into future scores, subsequent events, or global outcomes. Startup eligibility criteria must be applied uniformly across all attention variants (including random baselines).

3. **Shadow-Only Observation:**
   Observer-side experimental hooks (such as retrospective budgets and counterfactual second-look sensors) operate strictly in shadow mode. They must never perturb agent actions, collective memory, or world state.

4. **Paired Replicated Designs:**
   Multi-seed studies must preserve per-world/per-seed pairings across compared interventions to maximize statistical power and eliminate inter-world variance bias.

5. **Explanatory, Non-Operational Reasoning:**
   Hypotheses generated within `reasoning.py` serve an interpretive, information-seeking function for cognitive adaptation, never triggering external operational actions.
