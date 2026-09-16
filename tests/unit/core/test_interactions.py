from symbiont.core.interactions import EcologicalResourcePool
import pytest


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


@pytest.mark.parametrize("resources", [
    {"food": float("nan")}, {"food": float("inf")}, {"": 1.0}, {1: 1.0},
])
def test_resource_pool_rejects_unbounded_resource_definitions(resources) -> None:
    with pytest.raises(ValueError, match="invalid ecological resources"):
        EcologicalResourcePool(resources)


@pytest.mark.parametrize("request_rows", [
    [("a", "food", float("nan"))],
    [("a", "food", float("inf"))],
    [("a", "food", True)],
])
def test_resource_pool_rejects_unbounded_requests(request_rows) -> None:
    with pytest.raises(ValueError, match="invalid resource request"):
        EcologicalResourcePool({"food": 1.0}).allocate(request_rows)


def test_resource_pool_rejects_unbounded_replenishment() -> None:
    pool = EcologicalResourcePool({"food": 1.0})
    with pytest.raises(ValueError, match="invalid replenishment"):
        pool.replenish("food", float("nan"))
