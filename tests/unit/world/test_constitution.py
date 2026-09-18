from symbiont_world.constitution import WorldConstitution


def _constitution(**overrides) -> WorldConstitution:
    defaults = dict(
        topology_schema="hex-axial",
        world_dimensions=(64, 64),
        field_laws_hash="f" * 8,
        resource_laws_hash="r" * 8,
        hazard_laws_hash="h" * 8,
        interaction_rules_hash="i" * 8,
        resolution_policy="lottery-deterministic",
        communication_physics="local-attenuated",
        lifecycle_contract_version=1,
        rng_scheme_version=1,
    )
    defaults.update(overrides)
    return WorldConstitution(**defaults)


def test_fingerprint_is_deterministic():
    a = _constitution()
    b = _constitution()
    assert a.fingerprint() == b.fingerprint()


def test_fingerprint_changes_with_any_field():
    base = _constitution()
    changed = _constitution(resolution_policy="proportional")
    assert base.fingerprint() != changed.fingerprint()


def test_canonical_form_is_independent_of_construction_order():
    a = WorldConstitution(
        topology_schema="hex-axial",
        world_dimensions=(64, 64),
        field_laws_hash="f" * 8,
        resource_laws_hash="r" * 8,
        hazard_laws_hash="h" * 8,
        interaction_rules_hash="i" * 8,
        resolution_policy="lottery-deterministic",
        communication_physics="local-attenuated",
        lifecycle_contract_version=1,
        rng_scheme_version=1,
    )
    b = WorldConstitution(
        rng_scheme_version=1,
        lifecycle_contract_version=1,
        communication_physics="local-attenuated",
        resolution_policy="lottery-deterministic",
        interaction_rules_hash="i" * 8,
        hazard_laws_hash="h" * 8,
        resource_laws_hash="r" * 8,
        field_laws_hash="f" * 8,
        world_dimensions=(64, 64),
        topology_schema="hex-axial",
    )
    assert a.canonical() == b.canonical()


def test_schema_version_participates_in_fingerprint():
    base = _constitution()
    bumped = WorldConstitution(
        **{
            **{f: getattr(base, f) for f in base.__slots__ if f != "constitution_schema_version"},
            "constitution_schema_version": base.constitution_schema_version + 1,
        }
    )
    assert base.fingerprint() != bumped.fingerprint()
