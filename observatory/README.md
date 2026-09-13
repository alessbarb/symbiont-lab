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
