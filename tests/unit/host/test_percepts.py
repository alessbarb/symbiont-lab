from __future__ import annotations

import pytest

from symbiont.host import (
    Percept,
    ReadingPrivacyClass,
    ReadingQuality,
    SensorReading,
    Unit,
    perceive_local_host,
    synthesize_percepts,
)


def _reading(
    capability_id: str,
    *,
    source: str = "stdlib",
    value: float | None = 0.5,
    unit: Unit = Unit.RATIO,
    quality: ReadingQuality = ReadingQuality.NOMINAL,
) -> SensorReading:
    return SensorReading(
        capability_id=capability_id,
        source=source,
        value=value,
        unit=unit,
        monotonic_timestamp_ns=1,
        quality=quality,
        privacy_class=ReadingPrivacyClass.AGGREGATE,
    )


def test_known_capability_is_synthesized_into_its_percept_name():
    percepts = synthesize_percepts([_reading("compute.logical_cpu", value=0.4)])

    assert len(percepts) == 1
    assert percepts[0].name == "system_load"
    assert percepts[0].value == 0.4


def test_unrecognized_capability_is_skipped_not_guessed_at():
    percepts = synthesize_percepts([_reading("some.unmapped.capability")])
    assert percepts == ()


def test_percept_carries_no_capability_id_or_source():
    percept = synthesize_percepts([_reading("storage.disk_usage", value=12.0)])[0]
    public_attrs = {name for name in dir(percept) if not name.startswith("_")}
    assert "capability_id" not in public_attrs
    assert "source" not in public_attrs
    assert percept.as_dict().keys() == {"name", "value", "unit", "quality", "privacy_class"}


def test_custom_percept_name_mapping_overrides_default():
    percepts = synthesize_percepts(
        [_reading("compute.logical_cpu")],
        percept_names={"compute.logical_cpu": "custom_name"},
    )
    assert percepts[0].name == "custom_name"


def test_unavailable_reading_still_synthesizes_with_null_value():
    percepts = synthesize_percepts(
        [_reading("compute.logical_cpu", value=None, quality=ReadingQuality.UNAVAILABLE)]
    )
    assert percepts[0].value is None
    assert percepts[0].quality is ReadingQuality.UNAVAILABLE


@pytest.mark.parametrize("bad_name", ["", "has space"])
def test_percept_rejects_malformed_name(bad_name):
    with pytest.raises(ValueError):
        Percept(
            name=bad_name,
            value=1.0,
            unit=Unit.RATIO,
            quality=ReadingQuality.NOMINAL,
            privacy_class=ReadingPrivacyClass.AGGREGATE,
        )


def test_perceive_local_host_returns_known_built_in_percepts():
    percepts = perceive_local_host()
    names = {percept.name for percept in percepts}
    assert "system_load" in names
    assert "storage_pressure" in names
