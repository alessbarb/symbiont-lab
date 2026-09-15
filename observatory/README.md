# Symbiont Observatory

A passive, standalone visual surface for inspecting one Symbiont or a local fleet.
It never mutates, configures or controls `symbiont`. It can consume bounded demo/replay
snapshots, same-origin browser messages, or the local read-only Fleet/SSE transport.

## Run locally

For the current live Observatory, use the local-only server so the UI and SSE routes
share one origin:

```bash
python observatory/server.py --observatory-dir ~/.local/state/symbiont/observatory
```

Open `http://127.0.0.1:8899/`. The server refuses non-loopback binds and serves only
the Observatory HTML, JavaScript and CSS assets plus its read-only SSE endpoints.

For static demo/replay-only use, `python -m http.server 8787 --directory observatory`
remains sufficient, but it does not provide Fleet/SSE routes.

## Snapshot adapter

An embedding host can publish a snapshot without coupling the visual layer to the
organism runtime:

```js
observatoryWindow.postMessage({
  type: "symbiont-observatory-snapshot",
  snapshot: {
    schema_version: 1,
    tick: 12,
    organism: {
      display_id: "A-17",
      state: "exploring",
      percepts: [],
      beliefs: []
    },
    population: { members: [] }
  }
}, location.origin);
```

The display contracts are closed and bounded. A v1 snapshot carries neither
`organism.cognition` nor `organism.body_schema`; v2 requires cognition and forbids
BodySchema; v3 requires BodySchema while cognition remains optional. The Observatory
never infers security verdicts from raw host readings and never reconstructs Self
from privileged phenotype state.

## Visual language

- cyan: perception and sensor activity;
- violet: revisable beliefs;
- amber: bounded attention;
- coral: preserved contradiction;
- mint: consent boundary and healthy connectivity.

The individual and population views share one timeline. All controls affect only
the local visualization state.

## Phenotype and Self

The Individual view has two epistemically distinct perspectives:

- **Phenotype** is the scientific apparatus view. It may show bounded topology,
  current percepts and other external observations that the organism itself does not
  necessarily know.
- **Self** shows only `BodySchemaEngine.export_representation()` state produced by
  the organism. It never fills missing parts from topology, cognition, percepts or
  beliefs.

PR5 exposed the first sensory Self: opaque self-known sensory part ids plus bounded
existence, health, confidence, maturity, cost and recency classes. PR6 extends that
organism-owned representation with coarse **cognitive regions** learned from repeated
internal activity and weak functional dependencies learned from repeated coactivity
or temporal precedence. These are not copies of CognitiveGraph nodes or edges:
BodySchema never receives graph topology, and Observatory never reconstructs missing
Self structure from it.

Cognitive regions expose only opaque `part.region.*` identities plus bounded
existence, confidence, activity, maturity and recency. They deliberately do not
invent health or cost. Functional dependencies are currently limited to
`co_acts_with` and `precedes`; both remain revisable as new opportunities change
confidence. Human labels such as “Cognitive region 2” are Observatory presentation
only and are never written back to the organism.

Host capability names, private cognitive channel memberships and the BodySchema
checkpoint salt are never part of this projection. An organism with no learned
BodySchema is shown explicitly as **not yet developed**; the UI does not substitute
Phenotype truth.

## Replay files

Select **Open replay** or press `O` to load a local JSON recording. A replay follows
`replay.schema.json`, contains between 1 and 10,000 snapshots and is limited to
5 MB. It is parsed in the browser, kept in memory and never uploaded. Use Space to
pause/resume and the arrow keys to step through the recording.

The privacy audit lists the accepted projection, rejected data classes, transport
and collection bounds. Export creates a local JSON download; it does not publish or
send the recording anywhere. If a bounded BodySchema is present, browser export
uses snapshot v3 so Self survives the replay without synthesizing cognition.

## Cognitive history

The **History** tab searches and filters four abstract event families: perception,
attention, revision and contradiction. An event may carry a bounded explanation,
the belief it affected, a signed certainty delta and up to eight causal steps. These
are organism-authored display projections; the Observatory never derives a threat
label or action from them.

Use the A and B controls beside playback to compare one belief at two replay
positions. The comparison reports certainty, retained evidence and revision count,
and explicitly avoids interpreting the difference as quality, correctness or risk.

## Signal knowledge

The Individual inspector can show the organism's bounded knowledge about the
currently selected opaque signal. Each profile contains only aggregate opportunity
and valid-observation counts, an age class and up to four revisable claims
(stability, change, synchronous association, lead prediction or self-relevance).
Claims expose status, bounded evidence/validation counts, revision and a reason
class; they do not expose raw readings, host capability names or provider identity.

Signal knowledge is an organism-authored projection, not an Observatory inference.
Insufficient evidence is rendered explicitly, and stale or contested claims remain
visible rather than being collapsed into a score. Bounded knowledge events may also
be carried in a snapshot for the History view; the Observatory does not turn them
into threat labels, trust scores or actions.

## Population maps

The population view exposes four projections over the same bounded members:

- **Ecology** groups compatible normalized environments;
- **Knowledge** shows abstract knowledge relationships and retained volume;
- **Activity** shows relative cognitive activity;
- **Dissent** isolates contested relationships and beliefs.

Relationships are explicit display inputs — up to 1,000 per snapshot — rather than
links invented from screen proximity. Select one organism to explain its ecology,
then another to compare their context, activity, knowledge and contested-belief
counts. The Observatory never combines those dimensions into a universal trust or
risk score.

## Reading levels and individual state

- **Summary** explains lifecycle, acclimation, bounded resource use and narrative in
  everyday language.
- **Organism** exposes bounded memory, open questions, investigations and regime
  changes.
- **Research** reports exact projection counts and opens a keyboard- and
  screen-reader-friendly table equivalent to the visual graph.

The help drawer documents colors and shortcuts. Preferences remain in browser local
storage; replay and organism data do not.

## Passive browser-local connection

In addition to same-origin `window.postMessage`, the page listens on the browser-local
`BroadcastChannel` named `symbiont-observatory-v1`. Publishers send the same
`symbiont-observatory-snapshot` envelope. This is receive-only application logic:
the Observatory emits no command and cannot control the organism.

The renderer caps input at 500 organisms and 1,000 relationships and labels only a
small leading subset, keeping dense populations readable without removing members
from the accessible table or inspector.

## Record the real organism

`adapter.py` projects each public `OrganismRuntime` tick into the bounded display
contract. It drops raw values, timestamps, provider identity and host identity. The
run is finite, governed by a hard tick budget and creates no daemon or network
listener:

```bash
python observatory/adapter.py --ticks 20 --output symbiont-replay.json
```

Open the result with **Open replay**. Add `--checkpoint .symbiont/organism.json` to
resume the organism's abstract learned state. Add `--stdout` to emit one
`symbiont-observatory-snapshot` envelope per line for a local embedding host.

The adapter receives only the observer-safe BodySchema representation. It never
reads or serializes the private BodySchema checkpoint export, including private
cognitive channel membership/evidence.

## Resident, Fleet and cognition

`observatory/resident.py` runs the same `OrganismRuntime` lifecycle and publishes
passive Observatory artifacts. On a first cognitive launch it accepts the same
owner-authored inputs as the main organism CLI:

```bash
python observatory/resident.py \
  --genome-file examples/cognition/genome.json \
  --graph-file examples/cognition/graph.json \
  --semantic-bootstrap
```

`--graph-file` requires `--genome-file`. Once a checkpoint exists, cognition is
restored from that checkpoint rather than re-read from the launch files.

Artifacts live under `--observatory-dir` — by default
`~/.local/state/symbiont/observatory` — with one organism writer and Observatory as
reader:

```text
instances/
├── <instance_id>.json              registry: identity + heartbeat
└── <instance_id>.topology.json     structure: nodes/edges, revision-gated

journal/
├── <run_id>-000001.ndjson          per-tick transport state
├── <run_id>-000002.ndjson
└── ...
```

`instance_id` is a stable hash of the resolved `--state-file` path — never the path
itself — so restarting the same resident is recognized as the same instance while
`run_id` is fresh every launch. A cognitive resident writes its topology on the
first tick even when `topology_revision == 0`, then rewrites it only after a real
structural revision. A non-cognitive resident removes any stale topology artifact.

Journal segments are append-only and rotated by deleting whole closed files. The SSE
server replays at most the most recent 200 entries on connection, then tails segments
by file position rather than reparsing the retained journal every second. When a
resident restarts, the stream detects the new `run_id`, clears its sequence cursor
and accepts the new run's `sequence == 0` immediately.

The organism's durable checkpoint is separate and is never read by Observatory.

`resident.py` stays label-free by default — opaque, self-developed senses only. An
owner-authored graph that declares semantic `SENSE` node ids such as `system_load`
or `storage_pressure` needs `--semantic-bootstrap` to opt in to the legacy aliases
those ids expect. Without it, such a graph is legitimately not fed by those aliases.

## Fleet server

`server.py` watches only registry, topology and journal artifacts and never imports
`symbiont.core`:

```bash
python observatory/server.py --observatory-dir ~/.local/state/symbiont/observatory
```

The **Fleet** panel lists discovered instances by heartbeat liveness — never by PID,
because PIDs are reusable. Selecting one connects its stream. Overview/Senses/
Beliefs remain read-only, and **Cognition** shows the graph topology summary, live
readouts, prediction-error classes, structural mutations and safety state. Fleet
shows independent organisms side by side; it never merges them into a collective
cognition.

Malformed registry, journal or topology artifacts are ignored rather than allowed to
terminate an SSE thread.

## Schema versions

`snapshot.schema.json` accepts `schema_version` 1, 2 or 3:

- **v1** forbids both `organism.cognition` and `organism.body_schema`;
- **v2** requires `organism.cognition` and forbids `organism.body_schema`;
- **v3** requires `organism.body_schema` and makes cognition optional.

Inside snapshot v3, BodySchema has its own independent version:

- **BodySchema v1** is the historical sensory-only PR4/PR5 contract, with at most
  256 sensory parts and no dependencies;
- **BodySchema v2** adds at most 32 cognitive regions and up to 256 learned
  `co_acts_with` / `precedes` dependencies while keeping `global_state` empty.

Old snapshot v1/v2 files and snapshot-v3 replays carrying BodySchema v1 remain valid.
`body_schema.schema.json`, `topology.schema.json`, `cognition_state.schema.json` and
`instance.schema.json` document the additional contracts.

The repository's contract-test validator resolves local `$ref` schemas and enforces
the schema keywords used by these contracts, including `not`, `if/then/else`,
`allOf`, `anyOf`, bounded collections, patterns and closed additional properties.
