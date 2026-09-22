# Symbiont kernel characterization — interim decision report

## Scope

K1–K12 were implemented as experiment-local variants and executed from the
same runner. The canonical kernel was not modified. K1-B reused the real
Physics3D apparatus; K4–K11 exercised the corresponding real kernel
components; K1-A, K2, K3 and K12 remain synthetic screens by design.

Every new sweep used ten paired seeds and recorded a manifest with commit,
kernel, protocol, seeds, Python and platform. The relevant targeted test suite
passed (`8 passed`). The full repository suite is not a valid green gate in
this checkout: an earlier full run had unrelated baseline failures, so this
report does not claim repository-wide correctness.

## Evidence and recommendation

| protocol | result | recommendation |
| --- | --- | --- |
| K1-A nodes | error improved through 512, with diminishing cost/benefit | keep 192 pending a task-coupled developmental task |
| K1-B Physics3D | 192 had the best embodied control among 192–512 | keep 192 |
| K2 connectivity | filler-edge cost screen; error was invariant | keep 1536; rerun with useful sparse connectivity |
| K3 concepts | synthetic demand still improved at 128 | do not raise 32 from this probe |
| K4 mutation rate | evidence stream saturated at 20 accepted mutations | keep 8; require developmental protocol |
| K5 tentative pool | stream produced at most 20 candidates | keep 128; require developmental protocol |
| K6 cadence | first commit 24–256 ticks as cadence widened | keep 32 control |
| K7 support | first commit scales linearly with support epochs | keep 4 control |
| K8 fast gate | 0.95 rejected the 0.90 event; no false positives in separated stimuli | keep 0.80 / 0.60 |
| K9 memory capacity | salient retention followed configured cap; unique statistical keys did not mature | keep 256 / 64 |
| K10 weight norm | real clamp respected every tested norm | keep 8.0 |
| K11 reacclimation | contract screen exactly matched configured window | keep 32; run live restore task before changing |
| K12 interaction | 540 runs passed; surface was flat because probe lacks development | no joint promotion |

## Current recommended canonical values

```text
max_nodes = 192
max_edges = 1536
max_concepts = 32
max_tentative_edges = 128
max_structural_mutations_per_consolidation = 8
consolidation_interval_ticks = 32
consolidation_epoch_ticks = 8
slow_support_epochs = 4
fast_consolidation_threshold = 0.80
fast_min_reliability = 0.60
max_consolidation_candidates = 256
max_salient_event_traces = 64
max_incoming_consolidated_weight_norm = 8.0
reacclimation_ticks = 32
```

These are **control values**, not values proven optimal. The campaign shows no
safe basis for changing production without changing the protocols first.

## Required next scientific tranche

1. Replace K2 filler edges with task-useful sparse structural alternatives.
2. Use real developmental organisms for K3, K4, K5 and K12.
3. Add spaced positive/negative/contradictory evidence to K6–K9.
4. Run K11 through actual checkpoint/restore and measure prediction error,
   mutation suppression and recovery, rather than only the configured gate.
5. Only then run a confirmatory 30/100-seed campaign and consider a canonical
   change or a resource-budget model.

## Artifacts

The raw artifacts remain under `/tmp/symbiont-kernel-characterization/1c70371e/`
and the protocol-specific reports are in this directory. The final report is
an evidence ledger, not a claim that the synthetic screens establish cognitive
capacity in the production organism.

