from symbiont.host.adaptive import AdaptiveSenseModel
from symbiont.host.readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit


def reading(capability_id: str, value: float, tick: int) -> SensorReading:
    return SensorReading(
        capability_id=capability_id,
        source="fake",
        value=value,
        unit=Unit.COUNT,
        monotonic_timestamp_ns=tick,
        quality=ReadingQuality.NOMINAL,
        privacy_class=ReadingPrivacyClass.AGGREGATE,
    )


def test_unknown_signal_becomes_opaque_learned_sense() -> None:
    model = AdaptiveSenseModel(min_samples=3, active_limit=2)
    for tick, value in enumerate((10.0, 20.0, 5.0), start=1):
        model.observe((reading("candidate.internal", value, tick),))

    mapping = model.percept_names()
    assert set(mapping) == {"candidate.internal"}
    assert mapping["candidate.internal"].startswith("sense_")
    assert "candidate" not in mapping["candidate.internal"]


def test_constant_signal_loses_to_informative_signal_when_capacity_is_bounded() -> None:
    model = AdaptiveSenseModel(min_samples=3, active_limit=1)
    for tick in range(1, 6):
        model.observe(
            (
                reading("constant", 1.0, tick),
                reading("changing", float(tick * tick), tick),
            )
        )
    assert set(model.percept_names()) == {"changing"}


def test_sensory_development_round_trips_without_raw_history() -> None:
    model = AdaptiveSenseModel(min_samples=2, active_limit=3)
    model.observe((reading("x", 1.0, 1),))
    model.observe((reading("x", 3.0, 2),))
    restored = AdaptiveSenseModel.restore(model.export())
    assert restored.percept_names() == model.percept_names()
    assert restored.states[0].samples == 2
    assert not hasattr(restored.states[0], "history")
