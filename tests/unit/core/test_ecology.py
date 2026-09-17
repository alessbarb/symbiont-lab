import pytest

from symbiont.core.ecology import SharedHabitat

def test_capacity_and_resource_release():
 h=SharedHabitat(habitat_id='h',capacity=1,resources=1); assert h.admit('a',.8); assert not h.admit('b',.1); assert h.release('a')==.8; assert h.snapshot().available_resources==1

def test_checkpoint_round_trip():
 h=SharedHabitat(habitat_id='h',capacity=2,resources=2); h.admit('a',1); assert SharedHabitat.from_checkpoint(h.checkpoint()).snapshot()==h.snapshot()

def test_habitat_dynamics_change_intake_without_semantic_preferences():
 h=SharedHabitat(habitat_id='h',capacity=1,resources=2,
                 renewal_rate=.25,acquisition_cost=2,
                 physiological_usefulness=1.5,information_content=.75)
 assert h.admit('a', 1)
 assert h.consume('a', .2) == pytest.approx(.3)
 assert h.snapshot().available_resources == pytest.approx(.6)
 assert h.renew() == pytest.approx(.25)
 assert h.snapshot().available_resources == pytest.approx(.85)
 restored=SharedHabitat.from_checkpoint(h.checkpoint())
 assert restored.acquisition_cost == 2
 assert restored.physiological_usefulness == 1.5
 assert restored.information_content == .75
