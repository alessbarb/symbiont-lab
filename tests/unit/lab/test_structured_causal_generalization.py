from symbiont.modeling import NativeTokenizer, build_training_corpus
from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.studies.learning.structured_causal_generalization import (
    _motor_trace,
    _records,
)


def test_structured_causal_generalization_protocol_registered():
    assert (
        get_protocol("learning.structured-causal-generalization").__name__
        == "run_structured_causal_generalization_study"
    )


def test_v2_creates_novel_legacy_actions_but_reusable_structured_motor_tokens():
    trace = _motor_trace(seed=101, ticks=384, channels=8)
    legacy = build_training_corpus(_records(trace, seed=101, structured=False))
    structured = build_training_corpus(_records(trace, seed=101, structured=True))

    legacy_tokenizer = NativeTokenizer.from_records(legacy.train)
    structured_tokenizer = NativeTokenizer.from_records(structured.train)
    legacy_vocab = set(legacy_tokenizer.vocabulary)
    structured_vocab = set(structured_tokenizer.vocabulary)

    legacy_unseen = [
        record.action_token not in legacy_vocab
        for record in legacy.test
        if record.action_token is not None
    ]
    structured_motor_tokens = [
        token
        for record in structured.test
        for token in record.context_tokens
        if "motor.channel." in token
    ]

    assert sum(legacy_unseen) / len(legacy_unseen) > 0.80
    assert all(token in structured_vocab for token in structured_motor_tokens)
    assert len(structured_tokenizer.vocabulary) < len(legacy_tokenizer.vocabulary)
