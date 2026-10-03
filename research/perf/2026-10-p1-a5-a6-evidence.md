# Phase A P1 A5/A6 bounded validation and A7 audit status

Date: 2026-10-03  
Base under test: `6da1866e`  
Environment: repository locked environment (`uv run pytest`), Linux/Python 3.12;
PyBullet is optional and one test was skipped by the suite.

## A5 — Observation independence

**Outcome: confirmed within the tested contract and configurations.** The
matched-run test
`tests/experimental_integrity/test_physics3d_observation_independence.py`
passed all six cases: seeds 127 and 149, each across anthropomorphic-v6 in the
flat environment, anthropomorphic-v6-vision in vision-nursery-d1-v1, and
anthropomorphic-v6-vision in vision-nursery-d1-v2. Each pair started from one
captured organism and physical checkpoint and ran 16 ticks with observer OFF
versus ON. Organism state hash, motor intents, actuations, physical checkpoint
and tick matched at every comparison.

The test's state-hash equality supports equality of the full checkpointed
organism state; the explicit output comparisons additionally check intent and
actuation. This is a software-mechanics validation, not evidence about
scientific cognition or all seeds/configurations.

### Cost decomposition

The separate exploratory profile was run on Linux 7.0.0 / glibc 2.39,
Python 3.12.13, PyBullet 3.2.7 (API 202010061; build Sep 29 2026), seed 127,
using a ~600 KB organism+physics checkpoint payload. It measured:

| Component | Median |
| --- | ---: |
| Causal organism tick, observer OFF | 4.041 ms/tick |
| Tick with observer projections ON | 4.468 ms/tick |
| Paired ON-minus-OFF median (3 × 100-tick runs) | +0.427 ms/tick (+10.57%) |
| Deep-copy checkpoint + physical state | 18.831 ms |
| JSON serialization of checkpoint + physical state | 8.180 ms |
| In-process queue put/get | 0.017 ms |
| Multiprocessing queue put/get, ~600 KB | 8.848 ms |
| Local file write + fsync, ~600 KB | 1.636 ms |
| Sync V4.1 writer append producer | 3.577 ms |
| Async V4.1 writer append producer (bounded queue) | 0.002 ms |
| 30-tick passive viewer pipeline delta under Xvfb | +1.063 s/run median |

The viewer delta is an end-to-end UI/process/IPC/render-path comparison, not a
pure pixel-render timer. The V4.1 append timings include schema/record work and
buffered file writes; fsync is reported separately. The asynchronous writer's
close drains the queue and closes the writer. Three viewer repetitions per arm
varied substantially; none of these measurements is a stable hardware budget.
The paired observer-tax differences were +0.427, +0.127 and +1.365 ms/tick.
All observer ON/OFF start and end state hashes matched in that profile.

The first Xvfb viewer profile exposed a real presentation bug: the ecology
panel constructed `primitives`/`origins` variables but attempted to write
`competences`/`sources`, raising `KeyError` on frame update. The panel keys were
aligned with the displayed fields and a unit regression test was added. The
subsequent three-run viewer profile completed with no Tk callback exception.

**Boundary:** this closes the required *bounded decomposition* and the tested
observation-independence contract. It does not justify a technology migration,
performance threshold, or general claim across hosts, body kinds, or workloads.

## A6 — Shared equivalence harness

**Outcome: confirmed within the expanded shared harness contract.** The
focused `tests/integration/test_physics3d_equivalence_harness.py` test passed.
The harness now also captures a canonical per-tick trace digest covering the
`Tick3D` record, full physical checkpoint and physical tick, motor intents,
delivered actuations, and passive observer projection. Existing per-tick
organism checkpoints capture causal state, provenance, learning transitions
and model lifecycle; existing run digests additionally compare model files,
promotion/training outcomes and provenance/body final digests. Deterministic
replay and detection of a causal perturbation both pass.

Focused run after adding the per-tick trace regression:

```text
uv run pytest -q \
  tests/experimental_integrity/test_physics3d_observation_independence.py \
  tests/integration/test_physics3d_equivalence_harness.py \
  tests/unit/lab/physics3d/test_dynamics.py
23 passed, 1 skipped, 1 deselected in 44.43s
```

The deterministic replay/causal perturbation test (marked `slow`) was run
separately:

```text
uv run pytest -q -m slow tests/integration/test_physics3d_equivalence_harness.py
1 passed, 1 deselected in 7.33s
```

The wider Physics3D mechanics suite passed earlier on this change set:
`uv run pytest -q tests/unit/lab/physics3d` — 284 passed, 1 skipped. The full
suite was not rerun after the final trace normalization; focused A5/A6 tests
were rerun and passed.

These results do not establish that every listed per-tick A6 dimension is
captured for every future refactor. The shared harness remains a mandatory
regression gate; extend its trace when a changed boundary requires additional
dimensions.

## A7 — Current audit; no complete closure

The existing deterministic humanoid actuation test
`tests/unit/lab/physics3d/test_dynamics.py::test_humanoid_v4_hard_limits_hold_under_deterministic_actuation`
exercises 360 ticks and 720 physics substeps. Its declared assertions are:

- joint angular limit violation below `JOINT_LIMIT_SOLVER_TOLERANCE`
  (`0.5 degrees`);
- each motor velocity at or below its declared joint maximum plus `1e-6`;
- aggregate absolute joint speed below `150`;
- base displacement below `8 m`;
- measured maxima/displacement finite.

Those thresholds are specific to this humanoid actuation scenario. The wider
suite result (283 passed, 1 skipped) is not a substitute for the A7 canonical
stress matrix. Audit found no repo-defined global numeric thresholds for
contact/velocity explosions, energy bounds, or permitted divergence under
friction/mass perturbation. We introduce no post-hoc thresholds.

Accordingly, A7 remains open. This audit has not confirmed or refuted
whole-project numerical/mechanical stability. The next valid scope is to
exercise already-declared invariants, where they exist, and keep each body ×
stress mode without an applicable declared acceptance bound explicitly
`not_assessable` until the scientific owner freezes one. Required unresolved
matrix cells include idle, collision, checkpoint/restore, re-embodiment, and
friction/mass perturbation across the four registered body kinds.

No A7 source change or new numerical threshold was made in this audit.
