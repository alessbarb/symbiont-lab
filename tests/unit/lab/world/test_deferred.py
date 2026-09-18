import pytest

from symbiont_lab.world.deferred import DeferredEffect, DeferredEffectQueue, MAX_QUEUE_SIZE


def test_deferred_effect_rejects_out_of_bound_amount():
    with pytest.raises(ValueError):
        DeferredEffect(organism_id="org-a", due_tick=5, amount=0.3)
    with pytest.raises(ValueError):
        DeferredEffect(organism_id="org-a", due_tick=5, amount=0.0)


def test_deferred_effect_rejects_negative_due_tick():
    with pytest.raises(ValueError):
        DeferredEffect(organism_id="org-a", due_tick=-1, amount=0.1)


def test_queue_pop_due_returns_only_matured_effects_for_that_organism():
    queue = DeferredEffectQueue()
    queue.schedule(DeferredEffect(organism_id="org-a", due_tick=5, amount=0.1))
    queue.schedule(DeferredEffect(organism_id="org-a", due_tick=10, amount=0.1))
    queue.schedule(DeferredEffect(organism_id="org-b", due_tick=5, amount=0.1))

    due = queue.pop_due("org-a", current_tick=7)
    assert len(due) == 1
    assert due[0].due_tick == 5


def test_queue_pop_due_removes_matured_effects_only_once():
    queue = DeferredEffectQueue()
    queue.schedule(DeferredEffect(organism_id="org-a", due_tick=5, amount=0.1))
    first = queue.pop_due("org-a", current_tick=10)
    second = queue.pop_due("org-a", current_tick=10)
    assert len(first) == 1
    assert len(second) == 0


def test_queue_is_bounded():
    queue = DeferredEffectQueue(max_size=2)
    assert queue.schedule(DeferredEffect(organism_id="org-a", due_tick=1, amount=0.1)) is True
    assert queue.schedule(DeferredEffect(organism_id="org-a", due_tick=2, amount=0.1)) is True
    assert queue.schedule(DeferredEffect(organism_id="org-a", due_tick=3, amount=0.1)) is False
    assert len(queue) == 2


def test_default_max_queue_size_is_32():
    assert MAX_QUEUE_SIZE == 32
