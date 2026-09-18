# W02 retry — audit

Script: `run_w02_retry.py`. Raw output: `w02_retry_results.json`.

## Result: H0 still stands, with a sharper diagnosis

v1's audit found no divergence between replicas differing only in
`organism_seed`, and hypothesized that `exploration=0.0` /
`discover_senses=False` / no reproduction were why. This retry enabled
`sensory_plasticity=True` and `discover_senses=True` — real mechanisms
that exist in `symbiont`, no core change — and re-ran two replicas
(`organism_seed` = `world_seed+1000` and `world_seed+2000`, same
`world_seed`, same `GroundTruth`, same starting cell).

**Still no divergence** — neither in `action_counts` nor in
`developed_percept_names` (both replicas independently discover and
develop the exact same four `habitat_surface.*` percepts, in the same
distribution of actions).

**Sharper root cause, not just a re-confirmation of ignorance:** plasticity
and sense-discovery adapt to *what is observed*. Both replicas observe an
identical sequence of `WorldObservation`s, because the entire
organism↔world loop is a deterministic function of `world_seed` (which
drives environment/hazard RNG identically for both replicas) and the
organism's own actions (which are themselves deterministic given
identical percepts). `organism_seed` only ever reaches `mutation_seed`,
and mutation is only exercised during reproduction — which never happens
for a lone organism. There is no per-tick source of divergence anywhere
in this loop that `organism_seed` can reach, plasticity/discovery on or
off.

**Conclusion for v2/v3 design:** a real test of W02 needs one of:
(a) reproduction actually occurring (so mutation fires), or (b) two
replicas seeing genuinely different world trajectories (which stops being
"the same world" as v1 §8's W02 literally asks for), or (c) an
intentionally decorrelated per-organism RNG stream feeding some part of
cognition that isn't derived from `world_seed` at all — none of which
exist today. This is recorded as a real, load-bearing limitation, not
swept under a second "convergence" label.
