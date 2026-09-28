from __future__ import annotations

import queue
from io import BytesIO


from symbiont_lab.observation.bus import ObservationBus, ObservationMessage
from symbiont_lab.server import sse


def test_serialized_sse_framing_keeps_payload_bytes_opaque():
    payload = b'{"type":"vitals","tick":7}'
    framed = sse._encode_serialized_sse(payload, event_id=41)

    assert framed == b'id: 41\ndata: {"type":"vitals","tick":7}\n\n'


def test_observation_batch_preserves_order_and_ids():
    consumer: queue.Queue[ObservationMessage] = queue.Queue()
    first = ObservationMessage(10, b'{"type":"body","tick":1}')
    consumer.put_nowait(ObservationMessage(11, b'{"type":"cognition","tick":1}'))
    consumer.put_nowait(ObservationMessage(12, b'{"type":"vitals","tick":1}'))

    batch = sse._drain_observation_batch(consumer, first)

    assert batch == (
        b'id: 10\ndata: {"type":"body","tick":1}\n\n'
        b'id: 11\ndata: {"type":"cognition","tick":1}\n\n'
        b'id: 12\ndata: {"type":"vitals","tick":1}\n\n'
    )
    assert consumer.empty()


def test_stream_organism_never_parses_serialized_payload(monkeypatch):
    class Consumer:
        def __init__(self):
            self.calls = 0

        def get(self, timeout=None):
            self.calls += 1
            if self.calls == 1:
                return ObservationMessage(7, b'{"type":"vitals","tick":2}')
            raise BrokenPipeError()

        def get_nowait(self):
            raise queue.Empty

    class Stream:
        def __init__(self):
            self.consumer = Consumer()
            self.unsubscribed = False

        def subscribe(self, after_sequence=None):
            assert after_sequence is None
            return self.consumer

        def unsubscribe(self, consumer):
            assert consumer is self.consumer
            self.unsubscribed = True

    class Writer:
        def __init__(self):
            self.data = bytearray()
            self.flushes = 0

        def write(self, data):
            self.data.extend(data)

        def flush(self):
            self.flushes += 1

    class Handler:
        def __init__(self):
            self.headers = {}
            self.wfile = Writer()
            self.responses = []

        def send_response(self, status):
            self.responses.append(status)

        def send_header(self, *_args):
            pass

        def end_headers(self):
            pass

    def forbidden_loads(*_args, **_kwargs):
        raise AssertionError("SSE must not parse serialized observer payloads")

    monkeypatch.setattr(sse.json, "loads", forbidden_loads)

    handler = Handler()
    stream = Stream()
    sse.stream_organism(handler, stream)

    assert handler.responses == [200]
    assert bytes(handler.wfile.data) == b'id: 7\ndata: {"type":"vitals","tick":2}\n\n'
    assert handler.wfile.flushes == 1
    assert stream.unsubscribed is True


def test_batch_does_not_wait_for_future_messages():
    consumer: queue.Queue[ObservationMessage] = queue.Queue()
    first = ObservationMessage(1, b'{"type":"body_pose","tick":1}')

    batch = sse._drain_observation_batch(consumer, first)

    assert batch == b'id: 1\ndata: {"type":"body_pose","tick":1}\n\n'



def test_observation_bus_keeps_stream_id_out_of_json_payload():
    bus = ObservationBus()
    stream_id = bus.push({"type": "body_pose", "tick": 3})
    consumer = bus.subscribe(after_sequence=0)
    message = consumer.get_nowait()

    assert message.stream_id == stream_id
    assert b'"_stream_id"' not in message.data
    assert message.data == b'{"type":"body_pose","tick":3}'
