# Adversarial audit — Autonomous Cultural Agency v1

## Audit boundary

Audit performed against the `learning.autonomous-cultural-agency` treatment
before recording the final result. The historical directed Cumulative Culture
study remains a separate benchmark and was not changed.

## Findings

- **No hidden planner:** the treatment calls
  `ModeledOrganismRuntime.autonomous_cultural_step(channel, neighbors, tick)`;
  it does not pass claim IDs, composite IDs, utility labels or truth.
- **Transport/action separation:** the harness constructs authorized in-memory
  pairs only. The policy chooses both payload and receiver from local options;
  the channel only enforces authorization and delivery bounds.
- **No evaluator ordering:** composition candidates are generated in
  `symbiont.modeling` from the receiver's own ledger. The study does not call
  `compose_cultural_claims` with content.
- **No truth oracle:** no policy signature or treatment path accepts
  `ground_truth`, task success, population state or future outcomes.
- **No free action:** policy decisions and transport/composition costs are
  bounded, checkpointed and exposed passively.
- **No acquired-state heredity:** clonal modeled runtime creation supplies a
  fresh social ledger and fresh policy decision history; no claims/composites
  or decisions cross the birth boundary.
- **No SLM contamination:** the new policy has no model/corpus dependency and
  does not amend private training admissibility.
- **Replay:** policy state, decision history and cost are checkpointed; the
  preregistered run reproduces per-seed results.

## Preregistered result

The official run used seeds `101, 127, 149`, 24 ticks and eight contact
rounds after the preregistration was committed. ACA1--ACA10 and replay passed
for all three seeds. Per seed, the autonomous condition produced respectively
`2`, `4` and `5` useful multi-contributor composites; transmission attempts
were `67`, `71` and `62` out of `96` opportunities, and cultural costs were
`178`, `180` and `185`. The directed benchmark remained positive in all three
seeds and was not modified. These results are evidence for this bounded policy
and protocol, not for general cooperation.

## Residual limitation

The policy is an explicit deterministic baseline, not an emergent learned
cooperation mechanism. The apparatus still controls topology, timing and
experience surfaces. Closure therefore applies only to bounded organism-side
cultural agency under this protocol.
