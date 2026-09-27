from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from symbiont.core.cognition.agent import Agent
from symbiont.core.cognition.curiosity import CuriosityPlanner, CuriosityProbe
from symbiont.core.cognition.metacognition import MetacognitionEngine, MetacognitiveState
from symbiont.core.cognition.reasoning import Hypothesis, ReasoningEngine
from symbiont.core.foundation.model import Assessment
from symbiont.core.social.ledger import SocialEvidenceLedger
from symbiont.environment.regimes import apply_regime_shift
from symbiont.environment.rng import make_rng_streams
from symbiont.environment.world import benign_event, make_profiles, pathogen_event

from .evaluation import Evaluator
from .events import EventContext
from .result import SimulationResult
from .snapshots import SimulationSnapshot


@dataclass(slots=True, frozen=True)
class SimulationConfig:
    hosts: int = 100
    steps: int = 300
    seed: int = 7
    threat_rate: float = 0.018
    poison_fraction: float = 0.08
    heterogeneity: float = 0.12
    drift_step: int | None = None
    drift_fraction: float = 0.35
    drift_magnitude: float = 0.22


def _make_agents(
    hosts: int, rng, poison_fraction: float, heterogeneity: float
) -> tuple[list[Agent], set[str]]:
    poison_count = min(hosts, max(0, round(hosts * poison_fraction)))
    poisoned_indexes = set(rng.sample(range(hosts), poison_count)) if poison_count else set()
    agents: list[Agent] = []
    poisoned_ids: set[str] = set()
    spread = max(0.0, heterogeneity)
    for i in range(hosts):
        agent_id = f"agent-{i:03d}"
        poisoned = i in poisoned_indexes
        if poisoned:
            poisoned_ids.add(agent_id)
        agents.append(
            Agent(
                agent_id=agent_id,
                risk_scale=min(1.30, max(0.70, rng.gauss(1.0, spread))),
                curiosity_scale=min(1.35, max(0.65, rng.gauss(1.0, spread))),
                investigation_bias=rng.uniform(-0.04, 0.04) * min(spread / 0.12, 1.5),
                report_inversion=poisoned,
            )
        )
    return agents, poisoned_ids


def _mean_reliability(ledger: SocialEvidenceLedger) -> float:
    states = ledger.source_states.values()
    return sum(s.source_reliability for s in states) / len(states) if states else 0.0


def _low_rel_sources(ledger: SocialEvidenceLedger) -> int:
    return sum(1 for s in ledger.source_states.values() if s.source_reliability < 0.4)


def _trust_gap(ledger: SocialEvidenceLedger, poisoned_ids: set[str]) -> float:
    honest = [
        state.source_reliability
        for source, state in ledger.source_states.items()
        if source not in poisoned_ids
    ]
    poisoned = [
        state.source_reliability
        for source, state in ledger.source_states.items()
        if source in poisoned_ids
    ]
    if not honest or not poisoned:
        return 0.0
    return sum(honest) / len(honest) - sum(poisoned) / len(poisoned)


def _cognitive_outputs(
    ledger: SocialEvidenceLedger,
    reasoner: ReasoningEngine,
    curiosity: CuriosityPlanner,
) -> tuple[tuple[Hypothesis, ...], tuple[CuriosityProbe, ...]]:
    hypotheses = reasoner.analyze(ledger)
    return hypotheses, curiosity.plan(hypotheses, ledger)


def _rate_or_zero(value: float | None) -> float:
    return value if value is not None else 0.0


def _snapshot(
    *,
    step: int,
    total_steps: int,
    evaluator: Evaluator,
    agents: list[Agent],
    ledger: SocialEvidenceLedger,
    poisoned_ids: set[str],
    reasoner: ReasoningEngine,
    curiosity: CuriosityPlanner,
    meta: MetacognitiveState,
    drift_step: int,
    drifted_hosts: set[int],
) -> SimulationSnapshot:
    investigated = sum(agent.investigated for agent in agents)
    hypotheses, probes = _cognitive_outputs(ledger, reasoner, curiosity)
    attention_recall = _rate_or_zero(evaluator.counts.attention_recall)
    attention_precision = _rate_or_zero(evaluator.counts.attention_precision)
    attention_fpr = _rate_or_zero(evaluator.counts.attention_false_positive_rate)
    classification_recall = _rate_or_zero(evaluator.counts.classification_recall)
    classification_precision = _rate_or_zero(evaluator.counts.classification_precision)
    classification_fpr = _rate_or_zero(evaluator.counts.classification_false_positive_rate)
    return SimulationSnapshot(
        step=step,
        total_steps=total_steps,
        pathogen_events=evaluator.pathogen_events,
        benign_events=evaluator.benign_events,
        investigated=investigated,
        true_positives=evaluator.true_positives,
        false_positives=evaluator.false_positives,
        false_negatives=evaluator.false_negatives,
        detection_rate=attention_recall,
        precision=attention_precision,
        false_positive_rate=attention_fpr,
        attention_recall=attention_recall,
        attention_precision=attention_precision,
        attention_false_positive_rate=attention_fpr,
        classification_recall=classification_recall,
        classification_precision=classification_precision,
        classification_false_positive_rate=classification_fpr,
        classification_miss_rate=evaluator.classification_miss_rate,
        high_confidence_miss_rate=evaluator.high_confidence_miss_rate,
        social_claims=len(ledger.claims),
        open_questions=len(ledger.open_questions()),
        forgotten_episodes=sum(agent.memory.forgotten for agent in agents),
        consolidated_episodes=sum(agent.memory.consolidated for agent in agents),
        mean_source_reliability=_mean_reliability(ledger),
        low_reliability_sources=_low_rel_sources(ledger),
        poisoned_agents=len(poisoned_ids),
        trust_gap=_trust_gap(ledger, poisoned_ids),
        reasoning_hypotheses=hypotheses,
        reasoning_priority=hypotheses[0].priority if hypotheses else 0.0,
        curiosity_probes=probes,
        curiosity_focus=probes[0].utility if probes else 0.0,
        self_confidence=meta.self_confidence,
        epistemic_pressure=meta.epistemic_pressure,
        mean_uncertainty=meta.mean_uncertainty,
        mean_novelty=meta.mean_novelty,
        social_contradiction_pressure=meta.social_contradiction_pressure,
        metacognitive_status=meta.status,
        calibration_error=evaluator.calibration_error,
        brier_score=evaluator.brier_score,
        overconfidence_rate=evaluator.overconfidence_rate,
        blind_spot_rate=evaluator.blind_spot_rate,
        drift_active=step > drift_step,
        drift_step=drift_step,
        drifted_hosts=len(drifted_hosts),
        drift_adaptations=sum(agent.drift_adaptations for agent in agents),
        drift_false_positive_rate=evaluator.drift_false_positive_rate,
        recent_drift_false_positive_rate=evaluator.recent_drift_false_positive_rate,
    )


def _run_population(
    hosts: int = 100,
    steps: int = 300,
    seed: int = 7,
    threat_rate: float = 0.018,
    poison_fraction: float = 0.08,
    heterogeneity: float = 0.12,
    drift_step: int | None = None,
    drift_fraction: float = 0.35,
    drift_magnitude: float = 0.22,
    on_snapshot: Callable[[SimulationSnapshot], None] | None = None,
    on_event: Callable[[EventContext], None] | None = None,
    ledger: SocialEvidenceLedger | None = None,
) -> tuple[SimulationResult, SocialEvidenceLedger]:
    streams = make_rng_streams(seed)
    profiles = make_profiles(hosts, streams.profiles)
    agents, poisoned_ids = _make_agents(
        hosts,
        streams.agents,
        poison_fraction,
        heterogeneity,
    )
    ledger = ledger or SocialEvidenceLedger()
    evaluator = Evaluator()
    reasoner = ReasoningEngine()
    curiosity = CuriosityPlanner()
    metacognition = MetacognitionEngine()
    meta = metacognition.assess([], ledger)
    resolved_drift_step = max(50, int(steps * 0.55)) if drift_step is None else max(0, drift_step)
    drifted_hosts: set[int] = set()

    for step in range(steps):
        if step == resolved_drift_step:
            drifted_hosts = apply_regime_shift(
                profiles,
                streams.drift,
                fraction=drift_fraction,
                magnitude=drift_magnitude,
            )

        step_assessments: list[Assessment] = []
        for index, (profile, agent) in enumerate(zip(profiles, agents)):
            inject = step >= 50 and streams.schedule.random() < threat_rate
            if inject:
                roll = streams.schedule.random()
                kind = "ransom_sim" if roll < 0.40 else "bot_sim" if roll < 0.72 else "stealth_sim"
                event = pathogen_event(kind, profile, streams.observations)
            else:
                event = benign_event(profile, streams.observations)

            if step < 50:
                phase = "warmup"
            elif step < resolved_drift_step:
                phase = "pre_drift"
            else:
                phase = "post_drift"
            drift_state = (
                "pre_drift"
                if step < resolved_drift_step
                else "affected"
                if index in drifted_hosts
                else "unaffected"
            )

            if on_event is not None:
                on_event(
                    EventContext(
                        step=step,
                        host_index=index,
                        truth_label=event.truth_label,
                        is_threat=event.is_threat,
                        phase=phase,
                        drift_state=drift_state,
                        observation=event.observation,
                    )
                )

            assessment = agent.observe(step, event.observation, ledger)
            step_assessments.append(assessment)
            evaluator.record(
                is_threat=event.is_threat,
                investigated=assessment.should_investigate,
                assessment=assessment,
                truth_label=event.truth_label,
                phase=phase,
                drift_state=drift_state,
            )

        meta = metacognition.assess(step_assessments, ledger)
        if on_snapshot is not None:
            on_snapshot(
                _snapshot(
                    step=step + 1,
                    total_steps=steps,
                    evaluator=evaluator,
                    agents=agents,
                    ledger=ledger,
                    poisoned_ids=poisoned_ids,
                    reasoner=reasoner,
                    curiosity=curiosity,
                    meta=meta,
                    drift_step=resolved_drift_step,
                    drifted_hosts=drifted_hosts,
                )
            )

    investigated = sum(agent.investigated for agent in agents)
    hypotheses, probes = _cognitive_outputs(ledger, reasoner, curiosity)
    result = SimulationResult(
        hosts=hosts,
        steps=steps,
        pathogen_events=evaluator.pathogen_events,
        benign_events=evaluator.benign_events,
        investigated=investigated,
        true_positive_investigations=evaluator.true_positives,
        false_positive_investigations=evaluator.false_positives,
        false_negatives=evaluator.false_negatives,
        classification_true_positives=evaluator.classification_true_positives,
        classification_false_positives=evaluator.classification_false_positives,
        classification_true_negatives=evaluator.classification_true_negatives,
        classification_false_negatives=evaluator.classification_false_negatives,
        social_claims=len(ledger.claims),
        open_questions=len(ledger.open_questions()),
        forgotten_episodes=sum(agent.memory.forgotten for agent in agents),
        consolidated_episodes=sum(agent.memory.consolidated for agent in agents),
        mean_source_reliability=_mean_reliability(ledger),
        low_reliability_sources=_low_rel_sources(ledger),
        poisoned_agents=len(poisoned_ids),
        trust_gap=_trust_gap(ledger, poisoned_ids),
        reasoning_hypotheses=len(hypotheses),
        top_reasoning_priority=hypotheses[0].priority if hypotheses else 0.0,
        curiosity_probes=len(probes),
        top_probe_utility=probes[0].utility if probes else 0.0,
        self_confidence=meta.self_confidence,
        epistemic_pressure=meta.epistemic_pressure,
        metacognitive_status=meta.status,
        calibration_error=evaluator.calibration_error,
        brier_score=evaluator.brier_score,
        overconfidence_rate=evaluator.overconfidence_rate,
        blind_spot_rate=evaluator.blind_spot_rate,
        high_confidence_miss_rate=evaluator.high_confidence_miss_rate,
        drift_step=resolved_drift_step,
        drifted_hosts=len(drifted_hosts),
        drift_adaptations=sum(agent.drift_adaptations for agent in agents),
        drift_false_positive_rate=evaluator.drift_false_positive_rate,
        recent_drift_false_positive_rate=evaluator.recent_drift_false_positive_rate,
        evaluation_breakdown=evaluator.breakdown(),
    )
    return result, ledger


def run_simulation(
    hosts: int = 100,
    steps: int = 300,
    seed: int = 7,
    threat_rate: float = 0.018,
    poison_fraction: float = 0.08,
    heterogeneity: float = 0.12,
    drift_step: int | None = None,
    drift_fraction: float = 0.35,
    drift_magnitude: float = 0.22,
    on_snapshot: Callable[[SimulationSnapshot], None] | None = None,
    on_event: Callable[[EventContext], None] | None = None,
) -> tuple[SimulationResult, SocialEvidenceLedger]:
    return _run_population(
        hosts=hosts,
        steps=steps,
        seed=seed,
        threat_rate=threat_rate,
        poison_fraction=poison_fraction,
        heterogeneity=heterogeneity,
        drift_step=drift_step,
        drift_fraction=drift_fraction,
        drift_magnitude=drift_magnitude,
        on_snapshot=on_snapshot,
        on_event=on_event,
    )
