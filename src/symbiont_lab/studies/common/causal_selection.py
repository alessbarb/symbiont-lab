from __future__ import annotations

from dataclasses import dataclass
from math import floor
from typing import Callable, Sequence, TypeVar

T = TypeVar("T")
_MASK64 = (1 << 64) - 1


@dataclass(slots=True)
class OrderNode:
    key: tuple[float, int]
    priority: int
    left: OrderNode | None = None
    right: OrderNode | None = None
    size: int = 1


def _node_size(node: OrderNode | None) -> int:
    return 0 if node is None else node.size


def _refresh(node: OrderNode) -> None:
    node.size = 1 + _node_size(node.left) + _node_size(node.right)


def _priority(serial: int) -> int:
    """Deterministic splitmix64 priority; affects tree shape, never score order."""
    value = (serial + 0x9E3779B97F4A7C15) & _MASK64
    value = (value ^ (value >> 30)) * 0xBF58476D1CE4E5B9 & _MASK64
    value = (value ^ (value >> 27)) * 0x94D049BB133111EB & _MASK64
    return (value ^ (value >> 31)) & _MASK64


def _rotate_right(root: OrderNode) -> OrderNode:
    child = root.left
    assert child is not None
    root.left = child.right
    child.right = root
    _refresh(root)
    _refresh(child)
    return child


def _rotate_left(root: OrderNode) -> OrderNode:
    child = root.right
    assert child is not None
    root.right = child.left
    child.left = root
    _refresh(root)
    _refresh(child)
    return child


def _insert(root: OrderNode | None, node: OrderNode) -> OrderNode:
    if root is None:
        return node
    if node.key < root.key:
        root.left = _insert(root.left, node)
        if root.left.priority < root.priority:
            root = _rotate_right(root)
    else:
        root.right = _insert(root.right, node)
        if root.right.priority < root.priority:
            root = _rotate_left(root)
    _refresh(root)
    return root


def _kth(root: OrderNode, index: int) -> tuple[float, int]:
    left_size = _node_size(root.left)
    if index < left_size:
        assert root.left is not None
        return _kth(root.left, index)
    if index == left_size:
        return root.key
    assert root.right is not None
    return _kth(root.right, index - left_size - 1)


@dataclass(slots=True)
class OrderStatisticHistory:
    root: OrderNode | None = None
    length: int = 0

    def add(self, value: float) -> None:
        node = OrderNode(
            key=(float(value), self.length),
            priority=_priority(self.length),
        )
        self.root = _insert(self.root, node)
        self.length += 1

    def threshold(self, target_rate: float, fallback: float) -> float:
        if self.length < 32:
            return fallback
        quantile = min(max(1.0 - target_rate, 0.0), 1.0)
        index = min(
            self.length - 1,
            max(0, floor(quantile * (self.length - 1))),
        )
        assert self.root is not None
        return _kth(self.root, index)[0]


def historical_threshold(history: list[float], target_rate: float, fallback: float) -> float:
    """Reference implementation retained for exact-equivalence regression tests."""
    if len(history) < 32:
        return fallback
    ordered = sorted(history)
    quantile = min(max(1.0 - target_rate, 0.0), 1.0)
    index = min(len(ordered) - 1, max(0, floor(quantile * (len(ordered) - 1))))
    return ordered[index]


def online_indices(
    items: Sequence[T],
    *,
    budget: int,
    score: Callable[[T], float],
    eligible: Callable[[T], bool],
    tie_break: Callable[[T], float],
    fallback: float,
    random_mode: bool = False,
) -> tuple[list[int], int]:
    """Irrevocably select indices using only the observed prefix.

    ``eligible`` defines the common ex-ante population. Directed policies compare
    each score with an exact online quantile of prior eligible scores. ``random``
    policies instead sample without replacement using the remaining capacity.
    The returned forced count records selections needed only to honor the fixed
    ex-ante budget at the end of the stream.
    """
    eligible_items = [(index, item) for index, item in enumerate(items) if eligible(item)]
    total = len(eligible_items)
    budget = min(max(int(budget), 0), total)
    if budget == 0:
        return [], 0

    history = OrderStatisticHistory()
    selected: list[int] = []
    forced = 0

    for eligible_position, (index, item) in enumerate(eligible_items):
        remaining_budget = budget - len(selected)
        if remaining_budget <= 0:
            break
        remaining_events = total - eligible_position
        must_take = remaining_budget >= remaining_events
        current_score = float(score(item))

        if must_take:
            take = True
            forced += 1
        elif random_mode:
            take = float(tie_break(item)) < remaining_budget / remaining_events
        else:
            target_rate = remaining_budget / remaining_events
            threshold = history.threshold(target_rate, fallback)
            if current_score > threshold:
                take = True
            elif abs(current_score - threshold) <= 1e-12:
                take = float(tie_break(item)) < target_rate
            else:
                take = False

        if take:
            selected.append(index)
        history.add(current_score)

    if len(selected) != budget:
        raise RuntimeError("causal selector failed to honor its ex-ante budget")
    return selected, forced
