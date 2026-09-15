from symbiont.core.interactions import EcologicalResourcePool


def test_competing_requests_are_allocated_proportionally() -> None:
    pool = EcologicalResourcePool({"food": 1.0})

    allocations = pool.allocate([("a", "food", 1.0), ("b", "food", 1.0)])

    assert [item.granted for item in allocations] == [0.5, 0.5]
    assert pool.snapshot()["food"] == 0.0


def test_specialized_resources_and_explicit_replenishment() -> None:
    pool = EcologicalResourcePool({"food": 1.0, "signal": 1.0})

    allocations = pool.allocate([("organism", "food", 0.5), ("organism", "signal", 0.5)])

    assert [item.granted for item in allocations] == [0.5, 0.5]
    pool.replenish("food", 0.2)
    assert pool.snapshot()["food"] == 0.7
