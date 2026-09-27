"""Factorized Effect Representation v1 §5: atoms in the causal evidence ledger."""

from __future__ import annotations

from collections import Counter

import pytest

from symbiont.actuation.effects import atoms_from_changes
from symbiont.actuation.evidence import CausalEvidence, CausalEvidenceLedger
from tests.unit.actuation.acquisition_support import A, B, act, fresh_acquisition, rest


def _atom(changes):
    (atom,) = atoms_from_changes(changes)
    return atom.effect_id


def test_attempts_and_passive_windows_carry_their_atoms():
    acquisition = fresh_acquisition()
    update = act(acquisition, 0, {A: 0.5}, {"signal.a": 0.4, "signal.b": -0.3})
    assert update.evidence.effect_atoms == tuple(
        sorted(atom.effect_id for atom in atoms_from_changes({"signal.a": 0.4, "signal.b": -0.3}))
    )
    rest(acquisition, 2, {"signal.c": 0.5})
    (passive,) = acquisition.causal_evidence.passive_evidence
    assert passive.effect_atoms == (_atom({"signal.c": 0.5}),)


def test_atom_opportunities_match_a_brute_force_count_under_eviction():
    acquisition = fresh_acquisition()
    ledger = CausalEvidenceLedger(capacity=5, passive_capacity=3)
    acquisition.causal_evidence = ledger
    changes = [{"signal.a": 0.4}, {"signal.a": 0.4, "signal.b": 0.3}, {"signal.b": 0.3}]
    for tick in range(12):
        act(acquisition, tick * 2, {A if tick % 2 else B: 0.5}, changes[tick % 3])
        rest(acquisition, tick * 2 + 1, changes[(tick + 1) % 3])
    atom = _atom({"signal.a": 0.4})
    for item in ledger.intervention_evidence:
        signature = item.intervention_signature_id
        action = [
            e for e in ledger.intervention_evidence if e.intervention_signature_id == signature
        ]
        every = [*ledger.intervention_evidence, *ledger.passive_evidence]
        expected = (
            len(action),
            sum(atom in e.effect_atoms for e in action),
            len(every) - len(action),
            sum(atom in e.effect_atoms for e in every)
            - sum(atom in e.effect_atoms for e in action),
        )
        assert (
            ledger.atom_opportunities(atom, field="intervention_signature_id", values=(signature,))
            == expected
        )
    hits = Counter(
        a
        for e in ledger.intervention_evidence
        for a in e.effect_atoms
        if e.intervention_signature_id == signature
    )
    assert ledger.source_atoms(field="intervention_signature_id", value=signature) == dict(hits)


def test_atoms_round_trip_and_schema_3_restores_without_atoms():
    acquisition = fresh_acquisition()
    act(acquisition, 0, {A: 0.5}, {"signal.a": 0.4})
    rest(acquisition, 2, {"signal.c": 0.5})
    payload = acquisition.causal_evidence.checkpoint()
    restored = CausalEvidenceLedger.restore(payload)
    assert restored.checkpoint() == payload
    legacy = {**payload, "schema_version": 3}
    legacy["evidence"] = [
        {key: value for key, value in item.items() if key != "effect_atoms"}
        for item in payload["evidence"]
    ]
    legacy["passive_evidence"] = [
        {key: value for key, value in item.items() if key != "effect_atoms"}
        for item in payload["passive_evidence"]
    ]
    old = CausalEvidenceLedger.restore(legacy)
    assert all(item.effect_atoms == () for item in old.intervention_evidence)
    assert (
        old.atom_opportunities(
            _atom({"signal.a": 0.4}),
            field="intervention_signature_id",
            values=(old.intervention_evidence[0].intervention_signature_id,),
        )[1]
        == 0
    )


def test_evidence_rejects_unsorted_or_foreign_atoms():
    base = dict(
        evidence_id="causal.x",
        attempt_id=None,
        intervention_signature_id=None,
        commitment_id=None,
        competence_id=None,
        effect_id=None,
        context_ref=None,
        observation_tick=1,
    )
    with pytest.raises(ValueError):
        CausalEvidence(**base, effect_atoms=("effect.atom.b", "effect.atom.a"))
    with pytest.raises(ValueError):
        CausalEvidence(**base, effect_atoms=("effect.123",))
