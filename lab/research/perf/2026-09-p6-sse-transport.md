# P6 — SSE Transport Cleanup

Status: implementation candidate  
Base: P5 live anchors + deltas on `main`

## Goal

P5 reduces live observer payload size. P6 ensures the SSE transport does not
reintroduce avoidable CPU and syscall overhead.

The critical path is:

```text
ObservationBus
  -> serialized observer message
  -> SSE framing
  -> socket write
```

## Transport identity is out-of-band

Before P6, `ObservationBus` embedded `_stream_id` into every JSON payload.
`stream_organism()` then parsed the already-serialized JSON with
`json.loads()` solely to recover that value and emit the SSE `id:` line.

P6 introduces:

```python
ObservationMessage(
    stream_id: int,
    data: bytes,
)
```

The JSON document is serialized once in `ObservationBus.push()`. Transport
identity travels beside it and never needs to be recovered from the payload.

The browser still receives the standard SSE frame:

```text
id: 42
data: {"type":"observation_delta",...}

```

EventSource therefore keeps native `Last-Event-ID` resume semantics without
requiring a duplicate JSON field.

## Pre-serialized bytes

Observer JSON is encoded to UTF-8 bytes once at the bus boundary.

The SSE organism stream now concatenates:

```text
b"id: " + stream_id + b"\n"
b"data: " + payload + b"\n\n"
```

It does not:

- decode UTF-8 back to Python text;
- call `json.loads()`;
- call `json.dumps()` again;
- re-encode the payload.

Other SSE endpoints keep their existing JSON encoder because their source data
is still structured Python state rather than pre-serialized ObservationBus
messages.

## Opportunistic batching

`stream_organism()` blocks only for the first available message.

Once one message is ready, it drains only messages already present in the queue,
up to:

- 64 messages; or
- approximately 256 KiB of framed data.

The batch is written and flushed once.

There is no timer waiting to fill the batch, so an isolated event preserves the
same latency behavior as before.

Heartbeat frames remain flushed immediately.

## Backpressure and P5 recovery

P6 does not change the P5 overflow semantics.

A slow ObservationBus consumer may still lose queued deltas. When that happens,
the bus replaces the current compressed event with the latest materialized
channel anchor so the decoder can recover immediately.

The typed `ObservationMessage` carries the correct stream id for both ordinary
events and recovery anchors.

## Compatibility

The browser never consumed `_stream_id`; searches before P6 found it only in
the bus, SSE adapter and tests. Removing it from the JSON therefore does not
change Body or Mind contracts.

`body_pose`, `world_scene`, anchors and deltas are otherwise byte-for-byte
normal JSON documents within SSE `data:` fields.

## Verification

P6 tests require:

1. serialized SSE framing preserves payload bytes exactly;
2. batched messages retain stream order and SSE ids;
3. `stream_organism()` succeeds even when `json.loads` is replaced by a
   function that raises;
4. an isolated event is emitted immediately without waiting for a future batch;
5. ObservationBus consumers use typed messages rather than parsing transport
   identity from JSON;
6. `_stream_id` is absent from observer JSON payloads.

`scripts/bench_sse_transport.py` compares the legacy
parse/decode/re-encode framing path against P6 framing on equivalent payloads.

P7 can now focus entirely on browser-side rendering cost.
