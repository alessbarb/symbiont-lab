"""Factorized Effect Representation v1 §4.1: atomic effects."""

from __future__ import annotations

import pytest

from symbiont.actuation.effects import (
    MAX_ATOMS_PER_TRANSITION,
    EffectAtom,
    EffectSpace,
    atoms_from_changes,
    atoms_from_signature,
    magnitude_class,
)


@pytest.mark.parametrize(
    ("bucket", "expected"), [(1, 1), (-2, 1), (3, 2), (-4, 2), (5, 3), (7, 3), (-7, 3)]
)
def test_magnitude_class_is_a_fixed_function_of_the_bucket(bucket, expected):
    assert magnitude_class(bucket) == expected


def test_zero_or_out_of_range_bucket_has_no_class():
    for bucket in (0, 8, -8):
        with pytest.raises(ValueError):
            magnitude_class(bucket)


def test_v4_signature_decomposes_exactly_one_atom_per_entry():
    changes = {"signal.b": -0.5, "signal.a": 0.2, "signal.c": 0.9}
    signature = EffectSpace.signature(changes)
    atoms = atoms_from_signature(signature)
    assert len(atoms) == len(signature)
    assert [(atom.feature_ref, atom.direction) for atom in atoms] == [
        ("signal.a", 1),
        ("signal.b", -1),
        ("signal.c", 1),
    ]
    assert [atom.magnitude_class for atom in atoms] == [1, 2, 3]


def test_atom_identity_is_pure_and_distinguishes_direction_and_magnitude():
    atom = EffectAtom("signal.a", 1, 2)
    assert atom.effect_id == EffectAtom("signal.a", 1, 2).effect_id
    assert atom.effect_id.startswith("effect.atom.")
    assert atom.effect_id != EffectAtom("signal.a", -1, 2).effect_id
    assert atom.effect_id != EffectAtom("signal.a", 1, 3).effect_id


def test_the_same_consequence_gives_the_same_atoms_despite_small_differences():
    # Whole-state identity differs (bucket 3 vs 4), the atom does not.
    first = atoms_from_changes({"signal.a": 3 / 7})
    second = atoms_from_changes({"signal.a": 4 / 7})
    assert EffectSpace.signature({"signal.a": 3 / 7}) != EffectSpace.signature({"signal.a": 4 / 7})
    assert first == second


def test_transition_atoms_are_bounded_keeping_the_largest_changes():
    changes = {f"signal.{index:02d}": 0.2 for index in range(30)}
    changes["signal.big"] = 1.0
    atoms = atoms_from_changes(changes)
    assert len(atoms) == MAX_ATOMS_PER_TRANSITION
    assert "signal.big" in {atom.feature_ref for atom in atoms}
    assert atoms == atoms_from_changes(dict(reversed(list(changes.items()))))


def test_non_organism_features_and_negligible_changes_make_no_atom():
    assert atoms_from_changes({"joint.knee": 0.9, "signal.a": 0.01}) == ()
    with pytest.raises(ValueError):
        EffectAtom("joint.knee", 1, 1)
