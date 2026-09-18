# Private model adaptation v1

**Protocol:** `learning.private-model-adaptation`  
**Status:** positive in preregistered scope; does not reclassify D-v1 or D-v2  
**Seeds:** 101, 127, 149  
**Regime:** the fixed bijective outcome permutation from D-v2

## Causal implementation finding

Before this study, `parent_model_id` existed in requests and manifests but
`train_private_model()` always constructed a fresh model. The previous lineage
was therefore metadata-only. The new `adapt_private_model()` loads the verified
parent artifact state dict, validates same-organism ownership and structural
compatibility, and trains a bounded successor on the new evidence corpus.

## Preregistered comparison and gate

Each seed compares:

1. stale pre-shift model;
2. fresh post-shift cold-start model;
3. adapted post-shift successor initialized from the pre-shift parent.

The gate was declared before execution:

- `mean_adapted_vs_stale > 0` nats;
- `mean_adapted_vs_fresh >= -0.15` nats;
- valid parent/ancestor lineage for every seed;
- adaptation inside authorized ceilings.

## Result

| metric | value |
|---|---:|
| mean stale degradation | +0.0276356 |
| mean fresh recovery | -0.00118335 |
| mean adapted recovery | +0.0868168 |
| mean adapted vs stale | +0.0868168 |
| mean adapted vs fresh | +0.0880002 |
| lineage valid | 3/3 |
| mean adaptation cost | 44 steps |

Per-seed `adapted_vs_stale` values were `+0.0654389`, `+0.0687194` and
`+0.1262921` nats for 101, 127 and 149 respectively. All adaptation requests
were authorized with a 512-step ceiling; the observed costs were 48, 36 and 48.

## Interpretation and limits

The adapted successor improved over stale in every preregistered seed and was
better than the fresh control in this bounded protocol. This closes the causal
substrate gap identified after D-v2 for this scope: successor training now has
real weight continuity rather than only a parent identifier.

This is not a retroactive D-v2 pass. D-v2 remains a negative/ambiguous result
for cold-start retraining. The result does not establish adaptation under every
architecture, tokenizer migration, corpus size, shift family or budget.
