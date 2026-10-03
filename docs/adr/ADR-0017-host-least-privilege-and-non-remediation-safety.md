# ADR-0017: Host Least-Privilege and Non-Remediation Safety Boundary

## Status

Accepted

## Context

When Symbiont executes in real-host environments (such as developer machines or server infrastructure), its cognitive threat models, anomaly detection, and adaptive mechanisms interact with real system signals. Without strict, unyielding architectural safety boundaries, an autonomous defensive research organism risks mutating into an unauthorized intrusion response agent, scanner, or invasive process.

## Decision

1. **Read-only aggregate observation.** Real-host interaction is strictly limited to vetted, local, coarse-grained, aggregate signals (e.g. system load, thermal states, memory pressure, block I/O rates).
2. **Zero personally identifiable information (PII) or user content.** The sensing layer must never inspect, ingest, or persist:
   - Usernames, hostnames, machine IDs, or MAC/IP addresses;
   - File system paths, filenames, or directory trees;
   - File contents, database records, network payloads, or keystrokes;
   - Process arguments, environment variables, or credentials.
3. **Absolute prohibition of remediation.** Symbiont is purely contemplative and defensive. The reasoning layer and runtime are strictly forbidden from executing administrative or corrective actions:
   - No process termination (`kill`), suspension, or priority alteration;
   - No file modification, deletion, permission change, or quarantine;
   - No firewall manipulation, network interface changes, or routing edits;
   - No execution of external binaries or arbitrary shell commands.
4. **Prohibition of lateral movement and network activity.** Symbiont shall open no network listening sockets, execute no port scans, conduct no ARP/DNS/SNMP discovery, inject no network packets, and attempt no remote communication.
5. **Fail-closed contract.** If any host provider or sensory probe requires write permissions, elevated capabilities (`sudo`/`root`), or remote scopes, it must fail closed and deactivate the sensor channel immediately.

## Consequences

- Symbiont cannot inflict damage, cause downtime, or interfere with legitimate host processes.
- Guarantees full compliance with institutional research ethics and privacy standards.
- Threats and perturbations remain synthetic and sandboxed within scientific experiments.

## Introduced in

v0.20.0.

## Evidence

`docs/safety/README.md`, `symbiont/tests/unit/host/test_linux_surfaces.py`, `symbiont/tests/unit/host/test_discovery.py`.
