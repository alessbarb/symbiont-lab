from lab.experiments.spec import spec_from_payload


def test_experiment_spec_parses_research_metadata_and_bounds_parameters():
    spec = spec_from_payload(
        {
            "title": "  Drift recovery  ",
            "hypothesis": "Novelty rises after drift.",
            "success_criteria": "Recent drift FP falls.",
            "notes": "comparison A",
            "hosts": 0,
            "steps": 9999999,
            "poison_fraction": 2,
            "drift_step": -1,
        }
    )
    assert spec.title == "Drift recovery"
    assert spec.hypothesis == "Novelty rises after drift."
    assert spec.success_criteria == "Recent drift FP falls."
    assert spec.hosts == 1
    assert spec.steps == 100000
    assert spec.poison_fraction == 1.0
    assert spec.drift_step is None
