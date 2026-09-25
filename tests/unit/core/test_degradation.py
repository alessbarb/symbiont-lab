from symbiont.core.degradation import DegradationQueue, RetentionState


def test_state_ages_and_is_excreted():
    q = DegradationQueue(aging_ticks=2, waste_ticks=1)
    q.retain("x", 0.5)
    assert q.age_tick() == 0 and q.items[0].state is RetentionState.ACTIVE
    assert q.age_tick() == 0 and q.items[0].state is RetentionState.AGING
    assert q.age_tick() == 1 and not q.items
    assert q.excreted_units == 1


def test_capacity_and_checkpoint():
    q = DegradationQueue(max_items=1)
    assert q.retain("a", 0.2)
    assert not q.retain("b", 0.3)
    assert DegradationQueue.from_checkpoint(q.checkpoint()).items[0].item_id == "a"
