from __future__ import annotations

from types import SimpleNamespace

import symbiont_lab.modeling.gateway as gateway_module
from symbiont_lab.modeling.gateway import ArtifactInferenceGateway


class _FakeStore:
    def __init__(self, artifact) -> None:
        self.artifact = artifact
        self.get_calls = 0

    def get(self, model_id: str):
        self.get_calls += 1
        return self.artifact


class _FakeTensor:
    def __init__(self, values=None) -> None:
        self._values = values or [0.6, 0.4]

    def __getitem__(self, _key):
        return self

    def detach(self):
        return self

    def cpu(self):
        return self

    def tolist(self):
        return self._values


class _FakeTorch:
    long = object()
    bool = object()

    @staticmethod
    def device(value):
        return value

    @staticmethod
    def tensor(_value, **_kwargs):
        return _FakeTensor()

    @staticmethod
    def ones_like(_value, **_kwargs):
        return _FakeTensor()

    @staticmethod
    def no_grad():
        class _Ctx:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

        return _Ctx()

    @staticmethod
    def softmax(_value, dim=-1):
        return _FakeTensor()

    @staticmethod
    def topk(_value, k=4):
        return _FakeTensor([0.6, 0.4][:k]), _FakeTensor([1, 0][:k])


class _FakeParameter:
    device = "cpu"


class _FakeModel:
    def parameters(self):
        return iter((_FakeParameter(),))

    def __call__(self, *_args, **_kwargs):
        return _FakeTensor()


def test_gateway_reads_artifact_once_across_repeated_inference(monkeypatch) -> None:
    artifact = SimpleNamespace(
        manifest=SimpleNamespace(
            model_id="a" * 64,
            context_window=8,
            architecture_id="fake",
        ),
        weights=b"weights",
    )
    store = _FakeStore(artifact)
    gateway = ArtifactInferenceGateway(store, vocab_size=8)

    monkeypatch.setattr(gateway_module, "_torch", lambda: _FakeTorch())
    monkeypatch.setattr(
        gateway_module,
        "load_artifact_model",
        lambda *_args, **_kwargs: _FakeModel(),
    )

    gateway.infer(model_id="a" * 64, token_ids=(1, 2), top_k=2)
    gateway.infer(model_id="a" * 64, token_ids=(2, 3), top_k=2)

    assert store.get_calls == 1
