# W03 audit — 8 founders, no mutation, regional heterogeneity

Script: `run_w03.py`. Raw output: `w03_results.json`. World: `genesis_v2.
build_ground_truth_v2()` (two regions, north q<4 / south q>=4, different
`ResourceLaw` capacity for two of the four resources; otherwise identical
to Genesis v1). Seed 101, 300 ticks, 8 founders placed by
`founder_placement`.

## Result: **H0 rejected — real within-region differentiation observed**

Preregistered rule: reject H0 only if founders sharing the *same* region
disagree on `dominant_resource` (the resource each intakes most). Cross-
region disagreement is expected and uninteresting (the law itself
differs); within-region disagreement, where the law is identical, is the
actual candidate signal.

Result: the two founders placed in `region-south-hash` (cells `(5,3)` and
`(6,0)`) disagree — one dominates on `f957f3aeaa92bf4b`
(`resource-immediate-deferred`), the other on `cc64ec14718851e0`
(`resource-neutral`) — while sharing an identical `ResourceLaw` for every
resource in their region. `reject_h0 = True`.

## Control ablation: the first hypothesis was wrong, and the control proved it

The initial hypothesis was that `hazard-density-coupled`'s
density-coupling created position-dependent selective pressure (different
local occupancy density -> different hazard hit rate -> different reserve
trajectory -> different action preference). This is exactly the kind of
mechanism this project's own discipline requires testing before claiming,
so a control was run with `density_coupling` zeroed for both hazards,
identical seed and placement otherwise.

**The control shows the identical disagreement pattern** — same two
founders, same two resources, same region. `mechanism_supported = False`.
Zeroing the hazard-density coupling changed nothing, which falsifies the
hazard-mechanism hypothesis outright rather than confirming it.

## What actually differs between the two founders (candidate, not confirmed)

With the hazard mechanism ruled out, the remaining candidate is the raw
occupancy-density percept itself: `WorldObservation.signals` carries the
literal local-crowding value (§1 of v1, the W1 occupancy signal) to every
organism every tick regardless of whether any hazard math uses it. Two
founders in different cells receive genuinely different numeric percepts
purely from their position (how many neighbors are within
`interaction_radius`), independent of any hazard. This is consistent with
v1/v2's established finding (W02 retry) that cognition is otherwise a
deterministic function of its percept stream: a different percept stream
is sufficient to produce a different trajectory, no hazard or mutation
required.

This is recorded as **OBSERVED, NEEDS_REPLICATION** — not confirmed. It
has not been isolated by its own ablation (e.g. forcing an identical
constant occupancy-density percept across founders and checking whether
disagreement disappears). That is the natural next control, not yet run.

## Status

W03 rejects H0: purely ontogenetic/social differentiation (no genetic
variation, no mutation) did occur between two otherwise law-identical
founders. The mechanism is real but not yet correctly identified — the
first candidate (hazard density-coupling) was tested and ruled out by its
own control, which is the discipline working as intended, not a failure.
The next step before treating this as a confirmed phenomenon is the
occupancy-percept ablation described above, with more seeds.
