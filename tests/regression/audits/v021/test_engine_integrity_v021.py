import pytest

from symbiont.core.collective import CollectiveMemory
from symbiont.environment.rng import make_rng_streams
from symbiont.simulation import _make_agents
from symbiont_lab.studies.evidence.replicated import run_replicated_evidence_study
from symbiont_lab.studies.heritage.longitudinal import run_longitudinal_species
from symbiont_lab.studies.heritage.replicated import (
    run_replicated_heritage_stress_study,
)
from symbiont_lab.studies.heritage.stress import run_heritage_stress_study


def _traits(agents):
    return [
        (agent.risk_scale, agent.curiosity_scale, agent.investigation_bias)
        for agent in agents
    ]


def test_poison_fraction_does_not_shift_agent_trait_draws():
    clean_streams = make_rng_streams(37)
    poisoned_streams = make_rng_streams(37)

    clean_agents, clean_ids = _make_agents(
        20,
        clean_streams.agents,
        poison_fraction=0.0,
        heterogeneity=0.12,
    )
    poisoned_agents, poisoned_ids = _make_agents(
        20,
        poisoned_streams.agents,
        poison_fraction=0.30,
        heterogeneity=0.12,
    )

    assert clean_ids == set()
    assert len(poisoned_ids) == 6
    assert _traits(clean_agents) == _traits(poisoned_agents)
    assert [agent.report_inversion for agent in clean_agents] != [
        agent.report_inversion for agent in poisoned_agents
    ]


def test_recalibration_is_idempotent_without_fresh_reports():
    collective = CollectiveMemory()
    fingerprint = "M-H-M-H-M"
    for index in range(5):
        collective.report(
            fingerprint,
            threat=index < 4,
            confidence=0.9,
            source=f"source-{index}",
        )

    collective.recalibrate_sources(min_peers=4)
    first = {
        source: (state.score, state.evaluations)
        for source, state in collective.source_trust.items()
    }

    for _ in range(50):
        collective.recalibrate_sources(min_peers=4)

    repeated = {
        source: (state.score, state.evaluations)
        for source, state in collective.source_trust.items()
    }
    assert repeated == first

    # An identical compatibility-mode report is a replay, not fresh evidence.
    assert not collective.report(fingerprint, True, 0.9, "source-0")
    collective.recalibrate_sources(min_peers=4)
    assert {
        source: (state.score, state.evaluations)
        for source, state in collective.source_trust.items()
    } == first

    # A separately identified observation is fresh, but it evaluates only the
    # source that supplied the revision rather than replaying every old peer.
    assert collective.report(
        fingerprint,
        True,
        0.9,
        "source-0",
        evidence_id="fresh-observation",
    )
    collective.recalibrate_sources(min_peers=4)
    assert collective.source_trust["source-0"].evaluations == first["source-0"][1] + 1
    for source in ("source-1", "source-2", "source-3", "source-4"):
        assert collective.source_trust[source].evaluations == first[source][1]


def test_longitudinal_preserves_undefined_recall_without_threats():
    result = run_longitudinal_species(
        generations=2,
        hosts=12,
        steps=80,
        seed=13,
        threat_rate=0.0,
        heritage_limit=8,
    )

    for generation in result.generations:
        assert generation.inherited_detection_rate is None
        assert generation.control_detection_rate is None
        assert generation.detection_delta is None
        assert generation.inherited_classification_recall is None
        assert generation.control_classification_recall is None
        assert generation.classification_recall_delta is None

    assert result.mean_detection_delta is None
    assert result.mean_classification_recall_delta is None


def test_longitudinal_mean_excludes_generation_without_heritage():
    result = run_longitudinal_species(
        generations=3,
        hosts=22,
        steps=130,
        seed=17,
        threat_rate=0.06,
        heritage_limit=8,
    )
    intervention = [row for row in result.generations if row.inherited_patterns > 0]

    assert result.heritage_effect_generations == len(intervention)
    defined = [row.detection_delta for row in intervention if row.detection_delta is not None]
    if defined:
        assert result.mean_detection_delta == pytest.approx(sum(defined) / len(defined))


def test_reexport_diagnostics_distinguish_direction_from_true_improvement():
    study = run_heritage_stress_study(
        source_seed=3,
        target_seed=1012,
        hosts=28,
        steps=170,
        threat_rate=0.06,
        heritage_limit=10,
    )

    for row in study.conditions:
        assert row.corrected_reexports == row.direction_flips
        assert row.evaluable_reexports >= row.improved_reexports + row.worsened_reexports
        payload = row.as_dict()
        assert payload["direction_flips"] == row.direction_flips
        assert payload["corrected_reexports"] == row.direction_flips
        if row.evaluable_reexports == 0:
            assert row.mean_reexport_mae_gain is None


def test_replicated_studies_reject_duplicate_seed_claims():
    with pytest.raises(ValueError, match="unique"):
        run_replicated_evidence_study(seeds=(7, 7), hosts=2, steps=5)
    with pytest.raises(ValueError, match="unique"):
        run_replicated_heritage_stress_study(
            source_seeds=(7, 7),
            hosts=2,
            steps=5,
        )
