# Governed E8 Label-Invariance Campaign

## Execution record

- Candidate commit: `0a901ea273ac8cbcf8c165419e9120033f09c1f0`
- Protocol: [`../label-invariance/experiment.toml`](../label-invariance/experiment.toml), SHA-256 recorded in
  `manifest.json`
- Input provenance: protocol-generated; no external starting state
- Per-run horizon: 300 steps
- Launcher scope: `confirmation`
- Preregistered seeds: 101, 127, 149, 173, 211, 257, 307, 353, 401, 457
- Runs were executed individually and sequentially through `agentctl run start`.
- Each run used a 30-minute wall limit, 1 GiB memory limit, 2 GiB disk
  reservation, and one CPU thread. The launcher's POSIX memory limit and
  identity verification remained enabled.

## Results

All ten receipts report `state=complete`, `returncode=0`, the pinned candidate
commit, the matching seed, and
`scientific_input={"mode":"protocol-generated","external_state":false}`.
Each execution fingerprint names the same commit as its receipt. All ten
one-seed results report 300 steps, `integrity_pass=true`,
`replay_deterministic=true`, and `invariant_rate=1.0`.

The machine-validated aggregation is in [`aggregate.json`](aggregate.json).
The per-seed outputs and execution receipts are preserved as `seed-N.json` and
`receipt-N.json` in this directory. The previous campaign artifact at the
parent directory's `results.json` is unchanged.

## Bounded conclusion

The preregistered E8 acceptance criteria passed for the ten specified seeds on
the pinned candidate. This result is bounded to this protocol, candidate commit,
and seed set; it does not establish generalization beyond them.
