import inspect

import pytest

from symbiont_lab.physics3d.humanoid import (
    effector_contract_ids,
    receptor_contract_ids,
)
from symbiont_lab.physics3d.apparatus import (
    physics3d_cognition,
    physics3d_sensory_system,
)


def test_physics3d_contract_uses_only_opaque_port_ids():
    receptors = receptor_contract_ids()
    effectors = effector_contract_ids()

    assert len(receptors) == 31
    assert len(effectors) == 16
    assert receptors == tuple(f"rec.{i}" for i in range(31))
    assert effectors == tuple(f"eff.{i}" for i in range(16))


def test_effector_contract_rejects_non_positive_motor_count():
    with pytest.raises(ValueError):
        effector_contract_ids(0)


def test_physics3d_optional_dependency_is_lazy():
    import symbiont_lab.physics3d.runtime as runtime

    source = inspect.getsource(runtime)
    assert "import pybullet as p" in source
    assert "PyBullet is optional" in source


def test_anatomical_labels_do_not_live_in_core_symbiont_surface():
    import symbiont.core.symbiont as symbiont

    source = inspect.getsource(symbiont).lower()
    for anatomical_term in ("knee", "elbow", "shoulder", "hip", "thigh", "shin"):
        assert anatomical_term not in source



def test_physics3d_uses_canonical_runtime_motor_constitution():
    genome, _graph, _limits = physics3d_cognition(motor_slots=16)

    assert genome.motor.slot_count == 16
    assert genome.genome_id == "genome_symbiont_physics3d_v1"


def test_physics3d_runtime_does_not_call_parallel_symbiont_step():
    import symbiont_lab.physics3d.runtime as runtime

    source = inspect.getsource(runtime)
    assert "PrivateModelOrganismRuntime" in source
    assert "Symbiont(" not in source
    assert ".symbiont.step(" not in source



def test_physics3d_grants_body_sized_bounded_sensory_checkpoint_budget():
    sensory = physics3d_sensory_system()

    assert sensory.plasticity_enabled is True
    assert sensory.limits.max_active_sensors == 64
    assert sensory.limits.max_sensor_checkpoint_bytes == 512 * 1024
