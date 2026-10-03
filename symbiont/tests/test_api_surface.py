"""Public API exports organism contracts, not embodiment composition types."""

from symbiont import api


def test_public_api_does_not_export_embodiment_transition_contracts() -> None:
    assert not hasattr(api, "begin_reembodiment")
    assert not hasattr(api, "replace_body")
    assert not hasattr(api, "EmbodimentDescriptor")
    assert not hasattr(api, "prepare_fresh_embodiment_checkpoint")


def test_public_api_retains_organism_lifecycle_and_persistence() -> None:
    assert hasattr(api, "OrganismRuntime")
    assert hasattr(api, "load_checkpoint_file")
    assert hasattr(api, "save_checkpoint_atomic")
    assert hasattr(api, "checkpoint_state_hash")
