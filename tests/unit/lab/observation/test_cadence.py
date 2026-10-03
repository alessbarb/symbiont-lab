from lab.observation.cadence import ExecutionRates


def test_default_rates_resolve_to_independent_exact_clocks():
    rates = ExecutionRates.resolve(physics_hz=240, cognition_hz=24)

    assert rates.physics_hz == 240
    assert rates.cognition_hz == 24
    assert rates.observation_hz == 12
    assert rates.render_hz == 60
    assert rates.physics_substeps_per_cognition == 10
    assert [tick for tick in range(1, 7) if rates.observation_due(tick)] == [2, 4, 6]


def test_auto_rates_remain_valid_when_non_default_frequencies_are_used():
    rates = ExecutionRates.resolve(physics_hz=100, cognition_hz=20)

    assert rates.observation_hz == 12
    assert rates.render_hz == 60


def test_explicit_rates_can_be_rational_relative_to_source_clock():
    rates = ExecutionRates.resolve(
        physics_hz=240,
        cognition_hz=24,
        observation_hz=10,
        render_hz=50,
    )

    assert rates.observation_hz == 10
    assert rates.render_hz == 50
    sampled = [tick for tick in range(1, 25) if rates.observation_due(tick)]
    assert len(sampled) == 10


def test_manual_step_can_force_observation_without_changing_clock():
    rates = ExecutionRates.resolve(
        physics_hz=240,
        cognition_hz=24,
        observation_hz=12,
        render_hz=60,
    )

    assert not rates.observation_due(3)
    assert rates.observation_due(3, force=True)
    assert rates.observation_due(4)
