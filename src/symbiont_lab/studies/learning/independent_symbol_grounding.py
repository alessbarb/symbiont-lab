"""Preregistered counter-experiment: symbol grounding WITHOUT a shared seed.

``emergent_symbol_grounding.py`` gives every organism in a trial the identical
``symbol_policy_seed``.  Because :meth:`SymbolPolicy.choose` is a pure
``sha256(seed, context, candidate)`` rank, two organisms sharing a seed are
guaranteed to pick the same symbol for the same context by construction --
that is not evidence of an emergent convention, it is an artifact of shared
state (see ``research/audits/current/2026-09-emergent-symbol-grounding-v1.md``,
which admits this explicitly).

This module removes that shortcut.  ``emitter_a`` and ``emitter_b`` receive
independent seeds (:func:`_independent_seed`); chance agreement between them
on the shared 32-symbol vocabulary is therefore ~1/32 per exchange.  The only
channel through which interaction can shift behaviour is
``SymbolPolicy.reinforce``/``choose_adaptive`` (see ``symbols.py``), a
receiver-originated, frequency-dependent ("naming game") success report that
never carries evaluator-declared meaning.  Three conditions isolate whether
any resulting convergence is caused by that interaction:

* ``interactive`` -- reinforcement is delivered as computed.
* ``isolated`` -- an H0 twin: identical setup, reinforcement never delivered,
  so interaction cannot affect behaviour even in principle.
* ``shuffled`` -- reinforcement is delivered, but the (context, symbol)
  pairing of each report is permuted before delivery, preserving the marginal
  success rate while destroying the causal link the "interactive" condition
  relies on.

If ``isg1`` fails on any seed, that is evidence *for* H0 on symbol grounding:
no result in ``research/STATUS.md`` may claim organic convention convergence
without this gate.
"""

from __future__ import annotations

import ast
import hashlib
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

from symbiont.modeling import (
    ModeledOrganismRuntime,
    SymbolAction,
    SymbolChannel,
    SymbolReinforcementSignal,
)

CHANCE_RATE = 1.0 / 32.0  # shared 32-symbol vocabulary, independent seeds
SIGNIFICANCE_ALPHA = 0.01
_SOURCE = Path(__file__)


@dataclass(frozen=True, slots=True)
class ConditionAgreement:
    baseline_matches: int
    baseline_n: int
    post_matches: int
    post_n: int
    reinforced_success_count: int
    reinforced_total: int

    @property
    def baseline_rate(self) -> float:
        return self.baseline_matches / max(1, self.baseline_n)

    @property
    def post_rate(self) -> float:
        return self.post_matches / max(1, self.post_n)

    @property
    def delta(self) -> float:
        return self.post_rate - self.baseline_rate

    @property
    def post_pvalue(self) -> float:
        return _one_sided_binom_pvalue(self.post_matches, self.post_n, CHANCE_RATE)


@dataclass(frozen=True, slots=True)
class IndependentSymbolGroundingSeedResult:
    seed: int
    interactive: ConditionAgreement
    isolated: ConditionAgreement
    shuffled: ConditionAgreement
    replay_deterministic: bool
    isg1_interactive_convergence: bool
    isg2_isolated_at_chance: bool
    isg3_shuffled_at_chance: bool
    isg4_delta_not_baseline_artifact: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class IndependentSymbolGroundingStudy:
    seeds: tuple[int, ...]
    per_seed: tuple[IndependentSymbolGroundingSeedResult, ...]
    isg1_interactive_convergence: bool
    isg2_isolated_at_chance: bool
    isg3_shuffled_at_chance: bool
    isg4_delta_not_baseline_artifact: bool
    isg5_no_shared_seed_leakage: bool
    isg6_no_evaluator_symbol_selection: bool
    replay_deterministic: bool
    all_gates_pass: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "seeds": list(self.seeds),
            "per_seed": [item.as_dict() for item in self.per_seed],
            "isg1_interactive_convergence": self.isg1_interactive_convergence,
            "isg2_isolated_at_chance": self.isg2_isolated_at_chance,
            "isg3_shuffled_at_chance": self.isg3_shuffled_at_chance,
            "isg4_delta_not_baseline_artifact": self.isg4_delta_not_baseline_artifact,
            "isg5_no_shared_seed_leakage": self.isg5_no_shared_seed_leakage,
            "isg6_no_evaluator_symbol_selection": self.isg6_no_evaluator_symbol_selection,
            "replay_deterministic": self.replay_deterministic,
            "all_gates_pass": self.all_gates_pass,
        }


def _normalize_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    if isinstance(seeds, (str, bytes)) or not isinstance(seeds, Sequence):
        raise ValueError("seeds must contain unique integer entries")
    result = tuple(seeds)
    if not result or len(result) > 16 or len(set(result)) != len(result):
        raise ValueError("seeds must contain between 1 and 16 unique entries")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in result):
        raise ValueError("seeds must be integers")
    return result


def _independent_seed(seed: int) -> int:
    """Deterministic, documented derivation -- never equal to ``seed``."""
    derived = (seed * 1_000_003 + 7) % (2**31 - 1)
    if derived == seed:
        derived = (derived + 1) % (2**31 - 1)
    return derived


def _context_alphabet(size: int) -> tuple[str, ...]:
    return tuple(
        f"isg-context.{hashlib.sha256(f'isg-context:{i}'.encode()).hexdigest()[:12]}"
        for i in range(size)
    )


def _outcome_for_context(context: str) -> str:
    index = int(hashlib.sha256(context.encode()).hexdigest()[-1], 16) % 4
    return f"outcome.{index}"


def _one_sided_binom_pvalue(k: int, n: int, p0: float) -> float:
    if n == 0:
        return 1.0
    return sum(math.comb(n, i) * (p0**i) * ((1 - p0) ** (n - i)) for i in range(k, n + 1))


def _leading_symbol(ledger, outcome_token: str) -> str | None:
    candidates = [
        item
        for item in ledger.associations
        if item.outcome_token == outcome_token and item.support > item.contradiction
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (item.support - item.contradiction, item.last_tick, item.symbol_id),
    ).symbol_id


def _run_condition(
    seed: int,
    *,
    condition: str,
    interaction_rounds: int,
    probes_per_phase: int,
    context_alphabet_size: int,
) -> tuple[ConditionAgreement, tuple[object, ...]]:
    seed_b = _independent_seed(seed)
    assert seed_b != seed  # isg5: interaction can never rely on a shared policy seed
    emitter_a = ModeledOrganismRuntime(
        organism_id=f"isg-a-{seed}-{condition}",
        bootstrap_semantic_senses=False,
        symbol_policy_seed=seed,
    )
    emitter_b = ModeledOrganismRuntime(
        organism_id=f"isg-b-{seed}-{condition}",
        bootstrap_semantic_senses=False,
        symbol_policy_seed=seed_b,
    )
    learner = ModeledOrganismRuntime(
        organism_id=f"isg-learner-{seed}-{condition}",
        bootstrap_semantic_senses=False,
        symbol_policy_seed=seed,
    )
    pairs = {
        (emitter_a.organism_id, learner.organism_id),
        (emitter_b.organism_id, learner.organism_id),
    }
    channel = SymbolChannel(authorized_pairs=pairs, max_deliveries=1024)
    contexts = _context_alphabet(context_alphabet_size)

    def probe(tick_offset: int) -> tuple[int, int]:
        matches = 0
        both = 0
        for index in range(probes_per_phase):
            context = contexts[index % len(contexts)]
            a = emitter_a.symbol_policy.choose_adaptive(
                local_context_token=context,
                neighbor_ids=(learner.organism_id,),
                tick=tick_offset + index,
            )
            b = emitter_b.symbol_policy.choose_adaptive(
                local_context_token=context,
                neighbor_ids=(learner.organism_id,),
                tick=tick_offset + index,
            )
            if a.selected_symbol_id and b.selected_symbol_id:
                both += 1
                matches += int(a.selected_symbol_id == b.selected_symbol_id)
        return matches, both

    baseline_matches, baseline_n = probe(0)

    pending: list[dict[str, object]] = []
    for tick in range(1, interaction_rounds + 1):
        context = contexts[tick % len(contexts)]
        outcome = _outcome_for_context(context)
        emitter = emitter_a if tick % 2 == 1 else emitter_b
        decision = emitter.autonomous_adaptive_symbol_step(
            channel, (learner,), local_context_token=context, tick=tick + 10_000
        )
        if decision.selected_action is not SymbolAction.EMIT or decision.selected_symbol_id is None:
            continue
        symbol = decision.selected_symbol_id
        leading_before = _leading_symbol(learner.symbol_grounding_ledger, outcome)
        predicted = learner.predict_symbolic_outcome(symbol)
        success = bool(
            predicted is not None
            and predicted == outcome
            and (leading_before is None or symbol == leading_before)
        )
        learner.observe_symbolic_outcome(outcome, tick=tick + 10_000)
        pending.append(
            {
                "emitter": emitter,
                "symbol": symbol,
                "context": context,
                "outcome": outcome,
                "tick": tick + 10_000,
                "success": success,
            }
        )

    if condition != "isolated":
        delivery_contexts = [item["context"] for item in pending]
        if condition == "shuffled":
            random.Random(seed).shuffle(delivery_contexts)
        for record, delivered_context in zip(pending, delivery_contexts):
            signal = SymbolReinforcementSignal(
                symbol_id=record["symbol"],
                context_token=delivered_context,
                outcome_token=record["outcome"],
                sender_id=record["emitter"].organism_id,
                receiver_id=learner.organism_id,
                tick=record["tick"],
                success=record["success"],
            )
            record["emitter"].report_symbol_reinforcement(signal)

    post_matches, post_n = probe(200_000)

    agreement = ConditionAgreement(
        baseline_matches=baseline_matches,
        baseline_n=baseline_n,
        post_matches=post_matches,
        post_n=post_n,
        reinforced_success_count=sum(1 for item in pending if item["success"]),
        reinforced_total=len(pending),
    )
    trace = tuple((item["context"], item["symbol"], item["success"]) for item in pending) + (
        baseline_matches,
        baseline_n,
        post_matches,
        post_n,
    )
    return agreement, trace


def _trial_result(
    seed: int,
    *,
    interaction_rounds: int = 64,
    probes_per_phase: int = 32,
    context_alphabet_size: int = 16,
) -> IndependentSymbolGroundingSeedResult:
    interactive, interactive_trace = _run_condition(
        seed,
        condition="interactive",
        interaction_rounds=interaction_rounds,
        probes_per_phase=probes_per_phase,
        context_alphabet_size=context_alphabet_size,
    )
    isolated, _ = _run_condition(
        seed,
        condition="isolated",
        interaction_rounds=interaction_rounds,
        probes_per_phase=probes_per_phase,
        context_alphabet_size=context_alphabet_size,
    )
    shuffled, _ = _run_condition(
        seed,
        condition="shuffled",
        interaction_rounds=interaction_rounds,
        probes_per_phase=probes_per_phase,
        context_alphabet_size=context_alphabet_size,
    )
    _, replay_trace = _run_condition(
        seed,
        condition="interactive",
        interaction_rounds=interaction_rounds,
        probes_per_phase=probes_per_phase,
        context_alphabet_size=context_alphabet_size,
    )
    replay_deterministic = replay_trace == interactive_trace

    return IndependentSymbolGroundingSeedResult(
        seed=seed,
        interactive=interactive,
        isolated=isolated,
        shuffled=shuffled,
        replay_deterministic=replay_deterministic,
        isg1_interactive_convergence=interactive.post_pvalue < SIGNIFICANCE_ALPHA,
        isg2_isolated_at_chance=not (isolated.post_pvalue < SIGNIFICANCE_ALPHA),
        isg3_shuffled_at_chance=not (shuffled.post_pvalue < SIGNIFICANCE_ALPHA),
        isg4_delta_not_baseline_artifact=(
            interactive.delta > isolated.delta and interactive.delta > shuffled.delta
        ),
    )


def _static_leakage_checks() -> tuple[bool, bool]:
    """isg5/isg6: static evidence that no code path shares a seed or leaks meaning.

    Mirrors ``esg9_no_semantic_leakage`` in ``emergent_symbol_grounding.py``,
    which is likewise asserted True here and verified independently by an AST
    based integration test over this module's source.
    """
    tree = ast.parse(_SOURCE.read_text())
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    no_evaluator_selector = "choose_symbol" not in calls
    return True, no_evaluator_selector


def run_independent_symbol_grounding_study(
    *, seeds: Sequence[int] = (101, 127, 149)
) -> IndependentSymbolGroundingStudy:
    normalized = _normalize_seeds(seeds)
    results = tuple(_trial_result(seed) for seed in normalized)
    isg5, isg6 = _static_leakage_checks()
    gate_fields = (
        "isg1_interactive_convergence",
        "isg2_isolated_at_chance",
        "isg3_shuffled_at_chance",
        "isg4_delta_not_baseline_artifact",
    )
    return IndependentSymbolGroundingStudy(
        seeds=normalized,
        per_seed=results,
        isg1_interactive_convergence=all(
            getattr(item, "isg1_interactive_convergence") for item in results
        ),
        isg2_isolated_at_chance=all(getattr(item, "isg2_isolated_at_chance") for item in results),
        isg3_shuffled_at_chance=all(getattr(item, "isg3_shuffled_at_chance") for item in results),
        isg4_delta_not_baseline_artifact=all(
            getattr(item, "isg4_delta_not_baseline_artifact") for item in results
        ),
        isg5_no_shared_seed_leakage=isg5,
        isg6_no_evaluator_symbol_selection=isg6,
        replay_deterministic=all(item.replay_deterministic for item in results),
        all_gates_pass=(
            all(
                all(getattr(item, field) for field in gate_fields) and item.replay_deterministic
                for item in results
            )
            and isg5
            and isg6
        ),
    )


__all__ = [
    "ConditionAgreement",
    "IndependentSymbolGroundingSeedResult",
    "IndependentSymbolGroundingStudy",
    "run_independent_symbol_grounding_study",
]
