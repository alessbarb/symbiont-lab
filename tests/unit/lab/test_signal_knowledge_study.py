from symbiont_lab.studies.learning.signal_knowledge import run_signal_knowledge


def test_signal_knowledge_study_is_reproducible_and_keeps_truth_outside_engine():
    first = run_signal_knowledge(101)
    second = run_signal_knowledge(101)
    assert first == second
    assert first.ticks == 192
    assert first.profiles == 2
    assert first.claims >= 2
