from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.studies.learning.structured_causal_experience import _records


def test_structured_causal_protocol_registered():
    assert (
        get_protocol("learning.structured-causal-experience").__name__
        == "run_structured_causal_experience_study"
    )


def test_structured_motor_representation_reuses_action_identity():
    legacy = _records(seed=101, ticks=96, structured=False)
    structured = _records(seed=101, ticks=96, structured=True)

    assert len({record.action_token for record in legacy}) > 1
    assert {record.action_token for record in structured} == {"action.motor.composite"}
    assert any("motor.channel." in token for token in structured[0].context_tokens)
