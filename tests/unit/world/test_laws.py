import math

import pytest

from symbiont_world.laws import HazardLaw, PeriodicFieldLaw, ResourceLaw


def test_periodic_field_law_is_deterministic_for_the_same_tick():
    law = PeriodicFieldLaw(amplitude=1.0, bias=0.0, angular_frequency=0.1, phase=0.5)
    assert law.value_at(42) == law.value_at(42)


def test_periodic_field_law_matches_closed_form():
    law = PeriodicFieldLaw(amplitude=2.0, bias=1.0, angular_frequency=0.5, phase=0.25)
    tick = 7
    expected = 1.0 + 2.0 * math.sin(0.5 * tick + 0.25)
    assert law.value_at(tick) == pytest.approx(expected)


def test_resource_law_rejects_negative_parameters():
    with pytest.raises(ValueError):
        ResourceLaw(capacity=10.0, renewal_rate=-0.1, decay_rate=0.0, initial_quantity=1.0)


def test_resource_law_rejects_initial_quantity_out_of_bounds():
    with pytest.raises(ValueError):
        ResourceLaw(capacity=10.0, renewal_rate=0.1, decay_rate=0.0, initial_quantity=11.0)


def test_resource_law_step_never_exceeds_capacity():
    law = ResourceLaw(capacity=10.0, renewal_rate=0.9, decay_rate=0.0, initial_quantity=9.9)
    value = law.initial_quantity
    for _ in range(50):
        value = law.step(value)
        assert value <= 10.0


def test_resource_law_step_never_goes_negative():
    law = ResourceLaw(capacity=10.0, renewal_rate=0.0, decay_rate=5.0, initial_quantity=3.0)
    value = law.initial_quantity
    for _ in range(10):
        value = law.step(value)
        assert value >= 0.0


def test_hazard_law_rejects_out_of_range_base_probability():
    with pytest.raises(ValueError):
        HazardLaw(base_probability=1.5, density_coupling=0.0)


def test_hazard_law_rejects_negative_coupling():
    with pytest.raises(ValueError):
        HazardLaw(base_probability=0.1, density_coupling=-0.5)


def test_hazard_exposure_at_zero_density_equals_base_probability():
    law = HazardLaw(base_probability=0.2, density_coupling=3.0)
    assert law.exposure(0.0) == pytest.approx(0.2)


def test_hazard_exposure_increases_monotonically_with_density():
    law = HazardLaw(base_probability=0.1, density_coupling=2.0)
    densities = [0.0, 0.2, 0.5, 0.8, 1.0]
    exposures = [law.exposure(d) for d in densities]
    assert exposures == sorted(exposures)


def test_hazard_exposure_is_bounded_in_unit_interval():
    law = HazardLaw(base_probability=0.9, density_coupling=10.0)
    for density in (0.0, 0.3, 0.7, 1.0):
        exposure = law.exposure(density)
        assert 0.0 <= exposure <= 1.0


def test_hazard_law_is_stateless_across_repeated_calls():
    law = HazardLaw(base_probability=0.3, density_coupling=1.0)
    assert law.exposure(0.5) == law.exposure(0.5)
