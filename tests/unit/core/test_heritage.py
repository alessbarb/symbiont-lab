import pytest

from symbiont.core.collective import CollectiveMemory
from symbiont.core.heritage import SpeciesHeritage, apply_heritage, distill_heritage
from symbiont_lab.studies.heritage.longitudinal import run_longitudinal_species


def test_inherited_prior_creates_no_live_reporters_and_can_be_overruled():
    collective = CollectiveMemory()
    collective.inherit(
        "H-H-H-H-H",
        0.90,
        0.55,
        generation=2,
        support=20,
    )

    assert collective.patterns == {}
    assert collective.source_trust == {}
    probability, certainty = collective.belief("H-H-H-H-H")
    assert probability == pytest.approx(0.90)
    assert certainty == pytest.approx(0.55)

    for index in range(8):
        collective.report("H-H-H-H-H", False, 0.95, f"live-{index}")

    probability, _ = collective.belief("H-H-H-H-H")
    assert probability < 0.5


def test_heritage_requires_fresh_live_evidence_to_survive():
    collective = CollectiveMemory()
    collective.inherit("old", 0.95, 0.55, generation=1, support=30)
    for index in range(8):
        collective.report("fresh", True, 0.95, f"agent-{index}")

    heritage = distill_heritage(
        collective,
        generation=2,
        max_patterns=8,
        min_reports=6,
        min_sources=4,
        min_certainty=0.60,
    )
    fingerprints = {pattern.fingerprint for pattern in heritage.patterns}

    assert "fresh" in fingerprints
    assert "old" not in fingerprints


def test_apply_heritage_keeps_source_trust_empty():
    original = CollectiveMemory()
    for index in range(8):
        original.report("H-M-H-M-H", True, 0.95, f"agent-{index}")
    heritage = distill_heritage(original, generation=1, min_certainty=0.60)

    newborn = CollectiveMemory()
    apply_heritage(newborn, heritage)

    assert newborn.inherited_count == len(heritage.patterns)
    assert newborn.source_trust == {}
    assert newborn.patterns == {}


def test_longitudinal_first_generation_matches_naive_control_and_is_deterministic():
    first = run_longitudinal_species(
        generations=2,
        hosts=18,
        steps=90,
        seed=5,
        heritage_limit=8,
    )
    second = run_longitudinal_species(
        generations=2,
        hosts=18,
        steps=90,
        seed=5,
        heritage_limit=8,
    )

    assert first == second
    generation_one = first.generations[0]
    assert generation_one.inherited_patterns == 0
    assert generation_one.detection_delta == pytest.approx(0.0)
    assert generation_one.precision_delta == pytest.approx(0.0)
    assert generation_one.false_positive_delta == pytest.approx(0.0)
    assert generation_one.calibration_delta == pytest.approx(0.0)
    assert generation_one.blind_spot_delta == pytest.approx(0.0)
    assert first.generations[1].inherited_patterns == generation_one.exported_patterns


def test_longitudinal_generation_limit_is_bounded():
    with pytest.raises(ValueError):
        run_longitudinal_species(generations=0)
    with pytest.raises(ValueError):
        run_longitudinal_species(generations=51)
