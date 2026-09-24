/**
 * Observer-side interpretation of motor-learning evidence.
 *
 * This module never writes to the organism and never invents biological gates.
 */
import { currentMotorOutputEdges } from './derived.js';
import {
  currentEpochStartTick,
  deriveTrend,
  embodimentEpochs,
  historyForCurrentSession,
} from './motor-learning-history.js';

function finite(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function learnedOrigin(origin) {
  const value = String(origin ?? '').toLowerCase();
  return value.includes('cognition') || value.includes('primitive');
}

function evidenceFrom({ tel, snap }) {
  const sm = snap.sensorimotor ?? {};
  const topology = snap.topology ?? { nodes: [], edges: [] };
  const nodes = topology.nodes ?? [];
  const motorEdges = finite(tel.cognitiveMotorOutputEdges ?? currentMotorOutputEdges(topology), 0);
  const repertoire = finite(
    tel.motorRepertoireSize ??
      (Array.isArray(sm.active_motor_repertoire) ? sm.active_motor_repertoire.length : 0),
    0,
  );
  const motorReadouts = finite(
    tel.motorReadoutNodes ??
      nodes.filter(node =>
        node.kind === 'readout' &&
        (
          String(node.id).startsWith('readout_motor:') ||
          String(node.id).startsWith('readout_primitive:')
        )
      ).length,
    0,
  );
  return {
    sm,
    motorEdges,
    repertoire,
    motorReadouts,
    patterns: finite(tel.sensorimotorPatterns ?? sm.known_patterns, 0),
    primitives: finite(tel.motorPrimitives ?? sm.primitives, 0),
    recurrent: finite(tel.recurrentPrimitiveCandidates ?? sm.recurrent_primitive_candidates, 0),
    cognitivePrimitives: finite(tel.cognitiveMotorPrimitives ?? sm.cognitive_primitives, 0),
    samples: finite(tel.maxPrimitiveSamples ?? sm.max_primitive_samples, 0),
    competence: finite(tel.fullCompetenceGateCandidates ?? sm.full_competence_gate_candidates, 0),
    coverage: Number.isFinite(Number(sm.exploration_coverage)) ? Number(sm.exploration_coverage) : null,
    controllability: Number.isFinite(Number(sm.best_controllability)) ? Number(sm.best_controllability) : null,
    directionalConsistency: Number.isFinite(Number(sm.best_directional_consistency))
      ? Number(sm.best_directional_consistency)
      : null,
    replayActive: Boolean(sm.replay_active),
    origin: tel.motorOrigin ?? 'none',
    originDetail: tel.motorOriginDetail ?? null,
  };
}

export function deriveMotorStage({ evidence, observation }) {
  if (!observation.live || !observation.coherent) {
    return { id: null, index: -1, confidence: 'low', evidence: ['observation is not live and coherent'] };
  }
  if (learnedOrigin(evidence.origin)) {
    return {
      id: 'control',
      index: 3,
      confidence: 'high',
      evidence: ['current motor origin uses learned cognitive structure'],
    };
  }
  if (
    evidence.cognitivePrimitives > 0 ||
    (evidence.repertoire > 0 && evidence.motorReadouts > 0 && evidence.motorEdges > 0)
  ) {
    const facts = [];
    if (evidence.repertoire > 0) facts.push('motor repertoire exists');
    if (evidence.motorReadouts > 0) facts.push('motor readouts exist');
    if (evidence.motorEdges > 0) facts.push('structural motor associations exist');
    if (evidence.cognitivePrimitives > 0) facts.push('cognitive motor primitives exist');
    return {
      id: 'consolidation',
      index: 2,
      confidence: facts.length >= 3 ? 'high' : 'medium',
      evidence: facts,
    };
  }
  if (evidence.recurrent > 0 || evidence.primitives > 0) {
    return {
      id: 'discovery',
      index: 1,
      confidence: evidence.recurrent > 0 && evidence.primitives > 0 ? 'high' : 'medium',
      evidence: ['recurrent or primitive action-outcome regularities are visible'],
    };
  }
  return {
    id: 'exploration',
    index: 0,
    confidence: 'high',
    evidence: ['no reusable recurrent motor structure is yet visible'],
  };
}

export function deriveAgencyStatus({ evidence, observation }) {
  if (!observation.live || !observation.coherent) {
    return { status: 'undetermined', origin: evidence.origin };
  }
  if (learnedOrigin(evidence.origin)) {
    return { status: 'active', origin: evidence.origin };
  }
  if (
    evidence.cognitivePrimitives === 0 &&
    evidence.competence === 0 &&
    String(evidence.origin).toLowerCase() === 'exploration'
  ) {
    return { status: 'absent', origin: evidence.origin };
  }
  return { status: 'emerging', origin: evidence.origin };
}

export function deriveMotorBottleneck({ evidence, observation }) {
  if (!observation.live || !observation.coherent) {
    return {
      id: 'insufficient-observation',
      title: 'Insufficient live evidence',
      body: 'Observer interpretation is unavailable until a coherent live cognition + mind frame is present.',
      focus: 'observation coherence',
    };
  }
  if (evidence.coverage != null && evidence.coverage < 1) {
    return {
      id: 'exploration',
      title: 'Motor space exploration is incomplete',
      body: 'The currently observed body has not yet reached complete exploration coverage.',
      focus: 'exploration coverage',
    };
  }
  if (evidence.recurrent === 0) {
    return {
      id: 'recurrence',
      title: 'No recurrent action–outcome regularity yet',
      body: 'Exploration is visible, but no repeatedly observed action–outcome candidate is currently present.',
      focus: 'recurrence',
    };
  }
  if (evidence.repertoire === 0) {
    if (
      evidence.controllability != null &&
      evidence.directionalConsistency != null &&
      evidence.controllability <= evidence.directionalConsistency
    ) {
      return {
        id: 'controllability',
        title: 'Action–outcome controllability remains the weakest observed signal',
        body: 'Recurrent effects exist, but controllability is currently weaker than directional consistency. No biological threshold is inferred.',
        focus: 'controllability trend',
      };
    }
    if (evidence.directionalConsistency != null) {
      return {
        id: 'directional-consistency',
        title: 'Effect direction remains the weakest observed signal',
        body: 'Recurrent effects exist, but directional consistency is currently the weaker observable signal. No biological threshold is inferred.',
        focus: 'directional consistency trend',
      };
    }
  }
  if (evidence.cognitivePrimitives === 0) {
    return {
      id: 'cognitive-integration',
      title: 'Regularities are not yet cognitively reusable',
      body: 'Recurrent sensorimotor structure exists, but none currently appears as a reusable cognitive motor primitive.',
      focus: 'cognitive integration',
    };
  }
  if (evidence.competence === 0) {
    return {
      id: 'competence',
      title: 'Reusable primitives have not formed competence',
      body: 'Reusable cognitive motor primitives are visible, but no full competence candidate is currently present.',
      focus: 'competence formation',
    };
  }
  if (!learnedOrigin(evidence.origin)) {
    return {
      id: 'deployment',
      title: 'Learned capability exists but is not currently deployed',
      body: 'Competence evidence exists, while current motor output is not originating from learned cognitive control.',
      focus: 'cognitive deployment',
    };
  }
  return {
    id: 'none',
    title: 'Learned motor control is currently active',
    body: 'No earlier observable bottleneck is dominant in the current coherent frame.',
    focus: 'stability and transfer',
  };
}

export function deriveEmbodimentTransfer({ tel, snap }) {
  const history = historyForCurrentSession();
  const epochs = embodimentEpochs(history);
  const epoch = Number.isFinite(Number(tel.embodimentEpoch ?? snap.embodiment?.epoch))
    ? Number(tel.embodimentEpoch ?? snap.embodiment?.epoch)
    : null;
  const startTick = currentEpochStartTick();
  const tick = Number.isFinite(Number(tel.tick)) ? Number(tel.tick) : null;
  const currentAgeTicks = startTick != null && tick != null ? Math.max(0, tick - startTick) : null;

  let transfer = 'insufficient-data';
  if (epochs.length >= 2) {
    const completed = epochs.filter(item => item.tickToFirstCognitiveControl != null);
    if (completed.length >= 2) {
      const previous = completed.at(-2);
      const current = completed.at(-1);
      const persistentStructure =
        (current.startingCognitivePrimitives ?? 0) > 0 ||
        (current.endingCognitivePrimitives ?? 0) > 0;
      if (
        persistentStructure &&
        current.tickToFirstCognitiveControl < previous.tickToFirstCognitiveControl
      ) {
        transfer = 'consistent-with-transfer';
      } else if (persistentStructure) {
        transfer = 'possible-transfer';
      } else {
        transfer = 'no-clear-transfer';
      }
    }
  }

  return {
    epoch,
    reacclimating: tel.reacclimating ?? snap.embodiment?.reacclimating ?? null,
    reacclimationRemaining:
      tel.reacclimationRemaining ?? snap.embodiment?.reacclimationRemaining ?? null,
    ageTicks: currentAgeTicks,
    epochs,
    transfer,
  };
}

export function deriveMotorLearningModel({ tel, snap, streamState }) {
  const observation = {
    status: streamState.status,
    live: streamState.status === 'live',
    coherent: Boolean(streamState.coherent),
    stale: Boolean(streamState.stale),
    tick: tel.tick ?? streamState.snapshotTick ?? null,
    source: streamState.source,
    runId: streamState.runId,
    instanceId: streamState.instanceId,
    reason: streamState.reason,
  };
  const evidence = evidenceFrom({ tel, snap });
  const stage = deriveMotorStage({ evidence, observation });
  const agency = deriveAgencyStatus({ evidence, observation });
  const bottleneck = deriveMotorBottleneck({ evidence, observation });
  const trends = {
    controllability: deriveTrend('controllability'),
    directionalConsistency: deriveTrend('directionalConsistency'),
    cognitivePrimitives: deriveTrend('cognitivePrimitives'),
    competenceCandidates: deriveTrend('competenceCandidates'),
  };
  const embodiment = deriveEmbodimentTransfer({ tel, snap });

  return { observation, stage, agency, bottleneck, evidence, trends, embodiment };
}
