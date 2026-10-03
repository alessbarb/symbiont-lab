from __future__ import annotations

from dataclasses import dataclass

from symbiont.cognition.generative import (
    CompetenceEffectGenerativeAdapter,
    EpisodicReplayAdapter,
    EpistemicOrigin,
    GeneratedFeature,
    GenerativeContext,
    GenerativeOperation,
    GenerativeState,
    PrivateSLMGenerativeAdapter,
    SensorimotorDynamicsGenerativeAdapter,
)


@dataclass
class PrivateResult:
    predicted_token: str = "outcome-a"
    confidence_class: int = 6


@dataclass
class EffectResult:
    effect_id: str = "effect-a"
    confidence: float = 0.75


def state() -> GenerativeState:
    return GenerativeState(
        "s0", "e0", EpistemicOrigin.INFERRED, None, 0, (), (), (), (), (), (), 0.5, 0.5, 0
    )


def test_private_adapter_preserves_direct_callback_result_without_recording_it():
    calls = []

    def direct(competence, context):
        calls.append((competence, context))
        return PrivateResult()

    adapter = PrivateSLMGenerativeAdapter("private-a", direct)
    result = adapter.generate(
        state=state(),
        operation=GenerativeOperation.PREDICT,
        context=GenerativeContext(("competence-a", "ctx-a"), ("ref-a",)),
    )
    assert calls == [("competence-a", ("ctx-a",))]
    assert result[0].predicted_outcomes == ("outcome-a",)
    assert result[0].support_refs == ("ref-a",)


def test_sensorimotor_and_competence_adapters_are_thin_translators():
    sensor = SensorimotorDynamicsGenerativeAdapter(
        "dynamics-a", lambda context: {"p2": 2.0, "p1": 1.0}
    )
    result = sensor.generate(
        state=state(), operation=GenerativeOperation.PREDICT, context=GenerativeContext()
    )
    assert [feature.token for feature in result[0].features] == ["p1", "p2"]

    effect = CompetenceEffectGenerativeAdapter(
        "effect-a", lambda competence, context: EffectResult()
    )
    result = effect.generate(
        state=state(),
        operation=GenerativeOperation.PREDICT,
        context=GenerativeContext(("competence-a", "context-a")),
    )
    assert result[0].predicted_outcomes == ("effect-a",)

    replay = EpisodicReplayAdapter(
        "replay-a", lambda context: (GeneratedFeature("recalled", None, 0.8),)
    )
    result = replay.generate(
        state=state(), operation=GenerativeOperation.REPLAY, context=GenerativeContext()
    )
    assert result[0].features[0].token == "recalled"
