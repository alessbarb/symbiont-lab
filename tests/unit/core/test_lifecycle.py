import pytest
from symbiont.core.lifecycle import LifeState, ViabilityController
from symbiont.core.metabolism import ResourcePressure

def test_viability_states_and_irreversible_death():
 v=ViabilityController(organism_id='o'); assert v.transition(ResourcePressure.SEVERE, integrity=.8) is LifeState.DORMANT
 v.transition(ResourcePressure.UNRECOVERABLE, integrity=0); v.finalize_death()
 assert v.state is LifeState.DEAD and v.transition(ResourcePressure.NORMAL, integrity=1) is LifeState.DEAD
 with pytest.raises(ValueError): v.finalize_death()

def test_dead_checkpoint_is_terminal():
 v=ViabilityController(state=LifeState.DEAD, organism_id='o'); assert ViabilityController.from_checkpoint(v.checkpoint()).state is LifeState.DEAD
