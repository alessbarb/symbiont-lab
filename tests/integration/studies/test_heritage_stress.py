from symbiont.core.heritage import HeritagePattern, SpeciesHeritage
from symbiont_lab.studies.heritage.stress import (
    invert_heritage,
    misalign_heritage,
    run_heritage_stress_study,
)


def _heritage() -> SpeciesHeritage:
    return SpeciesHeritage(
        generation=2,
        patterns=(
            HeritagePattern("A", 0.80, 0.45, 10, 1),
            HeritagePattern("B", 0.20, 0.40, 8, 1),
            HeritagePattern("C", 0.65, 0.35, 7, 1),
        ),
    )


def test_inverted_heritage_preserves_structure_but_flips_probabilities():
    original = _heritage()
    inverted = invert_heritage(original)

    assert inverted.generation == original.generation
    assert [pattern.fingerprint for pattern in inverted.patterns] == [
        pattern.fingerprint for pattern in original.patterns
    ]
    for before, after in zip(original.patterns, inverted.patterns):
        assert after.threat_probability == 1.0 - before.threat_probability
        assert after.certainty == before.certainty
        assert after.support == before.support


def test_misaligned_heritage_rotates_beliefs_across_same_fingerprints():
    original = _heritage()
    shifted = misalign_heritage(original)

    assert {pattern.fingerprint for pattern in shifted.patterns} == {
        pattern.fingerprint for pattern in original.patterns
    }
    assert sorted(pattern.threat_probability for pattern in shifted.patterns) == sorted(
        pattern.threat_probability for pattern in original.patterns
    )
    assert shifted.patterns[0].threat_probability == original.patterns[-1].threat_probability


def test_stress_conditions_share_exact_same_target_world_and_are_deterministic():
    first = run_heritage_stress_study(
        source_seed=5,
        target_seed=1014,
        hosts=24,
        steps=150,
        threat_rate=0.06,
        heritage_limit=10,
    )
    second = run_heritage_stress_study(
        source_seed=5,
        target_seed=1014,
        hosts=24,
        steps=150,
        threat_rate=0.06,
        heritage_limit=10,
    )

    assert first == second
    assert [condition.name for condition in first.conditions] == [
        "naive",
        "learned",
        "inverted",
        "misaligned",
    ]
    assert len({condition.world_digest for condition in first.conditions}) == 1
    assert first.conditions[0].inherited_patterns == 0
    assert all(0 <= condition.brier_score <= 1 for condition in first.conditions)


def test_naive_condition_has_no_fabricated_prior_alignment_metrics():
    study = run_heritage_stress_study(
        source_seed=3,
        target_seed=1012,
        hosts=16,
        steps=110,
        threat_rate=0.06,
        heritage_limit=8,
    )
    naive = study.conditions[0]

    assert naive.name == "naive"
    assert naive.prior_mae is None
    assert naive.live_mae is None
    assert naive.combined_mae is None
    assert naive.correction_gain is None
    assert naive.live_override_rate is None
    assert naive.reexport_rate is None
