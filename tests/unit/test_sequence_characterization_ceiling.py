from symbiont.modeling import ModeledOrganismRuntime


def test_sequence_max_length_is_a_bounded_runtime_ceiling_and_restores():
    runtime = ModeledOrganismRuntime(organism_id="org.a", bootstrap_semantic_senses=False, sequence_max_length=1)
    receiver = ModeledOrganismRuntime(organism_id="org.b", bootstrap_semantic_senses=False)
    decision = runtime.autonomous_sequence_decision((receiver,), local_context_tokens=("context.x",), tick=1)
    assert decision.selected_symbols is None or len(decision.selected_symbols) == 1
    restored = ModeledOrganismRuntime.from_checkpoint(runtime.checkpoint())
    assert restored._sequence_max_length == 1
