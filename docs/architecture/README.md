# Architecture: Two-Package Epistemological Boundary

Symbiont Lab is structured as a research monorepo containing two decoupled Python packages:

1. **`symbiont`** — The experimental subject: organism, cognition, synthetic environment, and simulation engine.
2. **`symbiont_lab`** — The scientific apparatus: experimental specifications, declarative runners, replication studies, statistical protocols, archives, CLI, and dashboard.

## Epistemological Hierarchy & Direction of Information

```text
GROUND TRUTH (Simulator/World)
       │
       ▼
EVALUATION EVENTS (Simulator-Side Truth)
       │
       ├────────────────────────────────┐
       ▼                                ▼
OBSERVATIONS (Sensory Surface)     EVALUATOR (Lab/Simulator Metrics)
       │                                │
       ▼                                ▼
ORGANISM (Agent / Cognition)      SCIENTIFIC APPARATUS (Studies / Lab)
```

### Invariant Rules
1. **Zero Downward Knowledge:** Synthetic ground truth belongs exclusively to the simulator and evaluator. Cognition components (`symbiont.core`) only observe synthetic sensory signals, local memory, collective reports, coarse fingerprints, and derived trust.
2. **No Upward Coupling (`symbiont` NEVER imports `symbiont_lab`):**
   The experimental subject must be able to exist conceptually and structurally in total isolation from the laboratory apparatus.
   ```text
   symbiont_lab ───► symbiont        [ALLOWED]
   symbiont     ───► symbiont_lab    [FORBIDDEN - AST Enforced]
   ```
3. **Passive Visualization:** Visualization (Dashboard) receives calculated metrics from the lab apparatus; it never defines or computes metrics itself.
