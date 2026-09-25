from __future__ import annotations

from symbiont_lab.studies.embodiment.reembodiment_reacclimation import (
    ReacclimationVerdict,
    analyze_reembodiment_reacclimation,
)


def _checkpoint(
    *,
    embodiment_id: str,
    body_id: str,
    tick: int,
    contract: str,
    prior_relation: str,
    historical: tuple[str, ...] = (),
    bindings: tuple[str, ...] = (),
    causal: float = 0.0,
    controllability: float = 0.0,
    uncertainty: float = 1.0,
    shock: float = 1.0,
    recovery_tick: int | None = None,
) -> dict[str, object]:
    return {
        "embodiment_episode": {
            "embodiment_id": embodiment_id,
            "body_id": body_id,
            "embodiment_tick": tick,
            "contract": {
                "contract_fingerprint": contract,
            },
            "prior": {
                "relation": prior_relation,
                "authority": "hypothesis_only",
            },
            "adaptation": {
                "prediction_shock": shock,
                "schema_uncertainty": uncertainty,
                "causal_confidence": causal,
                "controllability_confidence": controllability,
                "recovery_tick": recovery_tick,
            },
            "execution_bindings": {
                "items": [
                    {
                        "competence_id": value,
                        "evidence_refs": [f"evidence.{tick}"],
                    }
                    for value in bindings
                ],
            },
            "causal_evidence": {
                "evidence": [
                    {"evidence_id": f"e.{index}"}
                    for index in range(tick)
                ],
            },
        },
        "actuation": {
            "action_domain": {
                "competence_development": {
                    "historical_candidates": [
                        {
                            "primitive_id": value,
                            "embodiment_fingerprint": contract,
                            "sequence": [],
                        }
                        for value in historical
                    ],
                },
            },
        },
    }


def test_a_b_a_reports_revalidated_transfer_without_blind_authority() -> None:
    a1 = [
        _checkpoint(
            embodiment_id="a1",
            body_id="body.a1",
            tick=0,
            contract="contract.a",
            prior_relation="novel",
        ),
        _checkpoint(
            embodiment_id="a1",
            body_id="body.a1",
            tick=18,
            contract="contract.a",
            prior_relation="novel",
            bindings=("primitive.a",),
            causal=0.5,
            controllability=0.4,
            uncertainty=0.3,
            shock=0.1,
            recovery_tick=24,
        ),
    ]
    b = [
        _checkpoint(
            embodiment_id="b",
            body_id="body.b",
            tick=0,
            contract="contract.b",
            prior_relation="novel",
        ),
    ]
    a2 = [
        _checkpoint(
            embodiment_id="a2",
            body_id="body.a2",
            tick=0,
            contract="contract.a",
            prior_relation="same-contract",
            historical=("primitive.a",),
        ),
        _checkpoint(
            embodiment_id="a2",
            body_id="body.a2",
            tick=7,
            contract="contract.a",
            prior_relation="same-contract",
            historical=("primitive.a",),
            bindings=("primitive.a",),
            causal=0.5,
            controllability=0.4,
            uncertainty=0.3,
            shock=0.1,
            recovery_tick=12,
        ),
    ]

    result = analyze_reembodiment_reacclimation(
        a1_trace=a1,
        b_trace=b,
        a2_trace=a2,
    )

    assert result.clean_a2_start
    assert result.historical_hypotheses_present
    assert result.a2.first_prior_revalidation_tick == 7
    assert result.a2.start_executable_count == 0
    assert result.verdict is ReacclimationVerdict.REVALIDATED_TRANSFER
    assert result.passed


def test_instant_a2_binding_is_contaminated_restore() -> None:
    a1 = [
        _checkpoint(
            embodiment_id="a1",
            body_id="body.a1",
            tick=0,
            contract="contract.a",
            prior_relation="novel",
        ),
        _checkpoint(
            embodiment_id="a1",
            body_id="body.a1",
            tick=10,
            contract="contract.a",
            prior_relation="novel",
            bindings=("primitive.a",),
            causal=0.6,
            controllability=0.5,
            recovery_tick=16,
        ),
    ]
    b = [
        _checkpoint(
            embodiment_id="b",
            body_id="body.b",
            tick=0,
            contract="contract.b",
            prior_relation="novel",
        ),
    ]
    a2 = [
        _checkpoint(
            embodiment_id="a2",
            body_id="body.a2",
            tick=0,
            contract="contract.a",
            prior_relation="same-contract",
            historical=("primitive.a",),
            bindings=("primitive.a",),
        ),
    ]
    result = analyze_reembodiment_reacclimation(
        a1_trace=a1,
        b_trace=b,
        a2_trace=a2,
    )
    assert result.verdict is ReacclimationVerdict.CONTAMINATED_RESTORE
    assert not result.passed


def test_same_contract_without_measurable_gain_is_no_transfer() -> None:
    a1 = [
        _checkpoint(
            embodiment_id="a1",
            body_id="body.a1",
            tick=0,
            contract="contract.a",
            prior_relation="novel",
        ),
        _checkpoint(
            embodiment_id="a1",
            body_id="body.a1",
            tick=8,
            contract="contract.a",
            prior_relation="novel",
            bindings=("primitive.a",),
            causal=0.5,
            controllability=0.4,
        ),
    ]
    b = [
        _checkpoint(
            embodiment_id="b",
            body_id="body.b",
            tick=0,
            contract="contract.b",
            prior_relation="novel",
        ),
    ]
    a2 = [
        _checkpoint(
            embodiment_id="a2",
            body_id="body.a2",
            tick=0,
            contract="contract.a",
            prior_relation="same-contract",
            historical=("primitive.a",),
        ),
        _checkpoint(
            embodiment_id="a2",
            body_id="body.a2",
            tick=8,
            contract="contract.a",
            prior_relation="same-contract",
            historical=("primitive.a",),
            bindings=("primitive.a",),
            causal=0.5,
            controllability=0.4,
        ),
    ]
    result = analyze_reembodiment_reacclimation(
        a1_trace=a1,
        b_trace=b,
        a2_trace=a2,
    )
    assert result.verdict is ReacclimationVerdict.NO_TRANSFER
