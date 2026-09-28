# ADR-0018: Transparent Resident Lifecycle Supervision

## Status

Accepted

## Context

Long-running autonomous organisms operating outside batch simulations (such as the `resident` background observer) require persistent execution. In artificial life, persistent agents frequently raise security concerns if their lifecycle mimics malware evasion, background stealth, hidden processes, or unkillable daemons.

## Decision

1. **Explicit owner consent.** The resident lifecycle exists only when explicitly installed and launched by the host owner. It must run either as a foreground terminal process or as a supervised user-level service (e.g. `systemd --user`).
2. **Deterministic, clean termination.** The resident runtime must trap `SIGINT` and `SIGTERM`. Upon receipt of either signal:
   - Causal processing stops immediately;
   - In-flight checkpoint write completes cleanly;
   - Observation files and lockfiles are released;
   - The process terminates with exit status 0 within a bounded timeout (< 5s).
3. **Bounded atomic state persistence.** Periodic checkpoints and telemetry logs use atomic rename operations (`write -> fsync -> rename`) to eliminate corrupted files on unexpected shutdown. State storage is bounded in size through rolling windows and fixed-size buffers, preventing disk space depletion.
4. **Zero stealth or evasion.** The resident process:
   - Does not hide its process ID (PID);
   - Does not manipulate `argv` or disguise process name;
   - Does not hook system calls, inject threads into other processes, or spawn disowned watchdog forks;
   - Never attempts privilege escalation.
5. **Clean uninstallation.** Removing the user service or deleting the working directory completely purges the resident with zero orphaned artifacts.

## Consequences

- The resident observer is transparent, predictable, and cooperative with system resource managers.
- Administrators can audit, monitor, inspect, and kill the process using standard POSIX utilities.

## Introduced in

Milestone R (Resident Observatory).

## Evidence

`observatory/resident.py`, `tests/unit/test_resident.py`, `tests/unit/host/test_lifecycle.py`.
