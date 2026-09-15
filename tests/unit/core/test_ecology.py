from symbiont.core.ecology import SharedHabitat

def test_capacity_and_resource_release():
 h=SharedHabitat(habitat_id='h',capacity=1,resources=1); assert h.admit('a',.8); assert not h.admit('b',.1); assert h.release('a')==.8; assert h.snapshot().available_resources==1

def test_checkpoint_round_trip():
 h=SharedHabitat(habitat_id='h',capacity=2,resources=2); h.admit('a',1); assert SharedHabitat.from_checkpoint(h.checkpoint()).snapshot()==h.snapshot()
