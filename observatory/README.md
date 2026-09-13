# Symbiont Observatory

A passive, standalone visual surface for inspecting one Symbiont and its population.
It does not import, mutate, configure or control `symbiont`; it currently runs from a
bounded demo stream and accepts safe snapshots over `window.postMessage`.

## Run locally

```bash
python -m http.server 8787 --directory observatory
```

Open `http://127.0.0.1:8787`.

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

The bounded v1 display contract is documented in `snapshot.schema.json`. The page
rejects other schema versions and caps every collection before rendering it. A
localhost read-only transport can be added later, inside the observatory, once the
operational runtime exposes stable state. Until then, the observatory must not infer
or invent security verdicts from raw host readings.

## Visual language

- cyan: perception and sensor activity;
- violet: revisable beliefs;
- amber: bounded attention;
- coral: preserved contradiction;
- mint: consent boundary and healthy connectivity.

The individual and population views share one timeline. All controls affect only
the local visualization state.

## Replay files

Select **Open replay** or press `O` to load a local JSON recording. A replay follows
`replay.schema.json`, contains between 1 and 10,000 v1 snapshots, and is limited to
5 MB. It is parsed in the browser, kept in memory and never uploaded. Use Space to
pause/resume and the arrow keys to step through the recording.

The privacy audit lists the accepted projection, rejected data classes, transport
and collection bounds. Export creates a local JSON download; it does not publish or
send the recording anywhere.

## Cognitive history

The **History** tab searches and filters four abstract event families: perception,
attention, revision and contradiction. An event may carry a bounded explanation,
the belief it affected, a signed certainty delta and up to eight causal steps. These
are organism-authored display projections; the observatory never derives a threat
label or action from them.

Use the A and B controls beside playback to compare one belief at two replay
positions. The comparison reports certainty, retained evidence and revision count,
and explicitly avoids interpreting the difference as quality, correctness or risk.

## Population maps

The population view exposes four projections over the same bounded members:

- **Ecology** groups compatible normalized environments;
- **Knowledge** shows abstract knowledge relationships and retained volume;
- **Activity** shows relative cognitive activity;
- **Dissent** isolates contested relationships and beliefs.

Relationships are explicit display inputs — up to 1,000 per snapshot — rather than
links invented from screen proximity. Select one organism to explain its ecology,
then another to compare their context, activity, knowledge and contested-belief
counts. The observatory never combines those dimensions into a universal trust or
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

## Passive local connection

In addition to same-origin `window.postMessage`, the page listens on the browser-local
`BroadcastChannel` named `symbiont-observatory-v1`. Publishers send the same
`symbiont-observatory-snapshot` envelope. This is receive-only application logic:
the observatory emits no command, opens no socket, performs no fetch and cannot
control the organism. Until a publisher appears, the UI says it is waiting rather
than pretending to be live.

The renderer caps input at 500 organisms and 1,000 relationships and labels only a
small leading subset, keeping dense populations readable without removing members
from the accessible table or inspector.

## Record the real organism

`adapter.py` projects each public `OrganismRuntime` tick into the bounded v1
display contract. It drops raw values, timestamps, provider identity and host
identity. The run is finite, governed by a hard tick budget and creates no daemon
or network listener:

```bash
python observatory/adapter.py --ticks 20 --output symbiont-replay.json
```

Open the result with **Open replay**. Add `--checkpoint
.symbiont/organism.json` to resume the organism's abstract learned state on the
next run. Add `--stdout` to emit one `symbiont-observatory-snapshot` envelope per
line for a local embedding host that already owns the browser window or
`BroadcastChannel`; the adapter itself still opens no transport.
