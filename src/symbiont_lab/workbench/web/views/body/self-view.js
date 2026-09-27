import { JOINT_TOPOLOGY } from './model.js';

const CONTACT_SEGMENTS = [
  'pelvis',
  'torso',
  'head',
  'left_upper_arm',
  'left_forearm',
  'left_hand',
  'right_upper_arm',
  'right_forearm',
  'right_hand',
  'left_thigh',
  'left_shin',
  'left_foot',
  'right_thigh',
  'right_shin',
  'right_foot',
];

const SEGMENT_LABELS = {
  pelvis: 'Pelvis',
  torso: 'Torso',
  head: 'Head',
  left_upper_arm: 'Left upper arm',
  left_forearm: 'Left forearm',
  left_hand: 'Left hand',
  right_upper_arm: 'Right upper arm',
  right_forearm: 'Right forearm',
  right_hand: 'Right hand',
  left_thigh: 'Left thigh',
  left_shin: 'Left shin',
  left_foot: 'Left foot',
  right_thigh: 'Right thigh',
  right_shin: 'Right shin',
  right_foot: 'Right foot',
};

export const SELF_VIEW_MODES = [
  ['knowledge', 'Knowledge'],
  ['stability', 'Stability'],
  ['agency', 'Agency'],
];

function finite(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function ratio(value) {
  return Math.max(0, Math.min(1, finite(value, 0)));
}

function classRatio(value, classes = 16) {
  return ratio(finite(value, 0) / Math.max(1, classes - 1));
}

function mean(values) {
  if (!values.length) return 0;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function jointSegment(jointName) {
  if (jointName.startsWith('trunk_')) return 'torso';
  if (jointName.startsWith('neck_')) return 'head';
  if (jointName.startsWith('left_shoulder_')) return 'left_upper_arm';
  if (jointName.startsWith('left_elbow_') || jointName.startsWith('left_forearm_')) return 'left_forearm';
  if (jointName.startsWith('left_wrist_')) return 'left_hand';
  if (jointName.startsWith('right_shoulder_')) return 'right_upper_arm';
  if (jointName.startsWith('right_elbow_') || jointName.startsWith('right_forearm_')) return 'right_forearm';
  if (jointName.startsWith('right_wrist_')) return 'right_hand';
  if (jointName.startsWith('left_hip_')) return 'left_thigh';
  if (jointName.startsWith('left_knee_')) return 'left_shin';
  if (jointName.startsWith('left_ankle_')) return 'left_foot';
  if (jointName.startsWith('right_hip_')) return 'right_thigh';
  if (jointName.startsWith('right_knee_')) return 'right_shin';
  if (jointName.startsWith('right_ankle_')) return 'right_foot';
  return null;
}

function receptorSegment(receptorId) {
  const match = /^rec\.(\d+)$/.exec(String(receptorId ?? ''));
  if (!match) return null;
  const ordinal = Number(match[1]);

  // rec.0..61: position/velocity pair for the 31 canonical motor DoFs.
  if (ordinal < 62) {
    const jointOrdinal = Math.floor(ordinal / 2);
    const joint = JOINT_TOPOLOGY[jointOrdinal];
    return joint ? jointSegment(joint.name) : null;
  }

  // rec.62..71 are whole-body orientation/velocity channels and are not
  // projected onto a single observer anatomical segment.
  // rec.72..86 are somatic contact-presence channels.
  if (ordinal >= 72 && ordinal <= 86) {
    return CONTACT_SEGMENTS[ordinal - 72] ?? null;
  }
  // rec.87 is ecological/external-field state.
  // rec.88..102 are somatic contact-load channels.
  if (ordinal >= 88 && ordinal <= 102) {
    return CONTACT_SEGMENTS[ordinal - 88] ?? null;
  }
  // rec.103..106 are interoceptive and deliberately whole-body.
  return null;
}

function effectorSegment(effectorId) {
  const match = /^eff\.(\d+)$/.exec(String(effectorId ?? ''));
  if (!match) return null;
  const jointOrdinal = Math.floor(Number(match[1]) / 2);
  const joint = JOINT_TOPOLOGY[jointOrdinal];
  return joint ? jointSegment(joint.name) : null;
}

function emptySegment(segment) {
  return {
    segment,
    label: SEGMENT_LABELS[segment] ?? segment,
    receptorIds: [],
    senseCount: 0,
    confidence: 0,
    health: 0,
    maturity: 0,
    stableSenses: 0,
    dimensions: [],
    agenticDimensions: 0,
    agency: 0,
    knowledge: 0,
    stability: 0,
  };
}

export function selfViewSegments(snapshot) {
  const bySegment = new Map(CONTACT_SEGMENTS.map((segment) => [segment, emptySegment(segment)]));
  const selfModel = snapshot?.self_model && typeof snapshot.self_model === 'object'
    ? snapshot.self_model : {};

  for (const [receptorId, state] of Object.entries(selfModel)) {
    const segment = receptorSegment(receptorId);
    if (!segment || !bySegment.has(segment)) continue;
    const entry = bySegment.get(segment);
    entry.receptorIds.push(receptorId);
    entry.senseCount += 1;
    entry.confidence += classRatio(state?.confidence_class);
    entry.health += classRatio(state?.health_class);
    entry.maturity += classRatio(state?.maturity_class, 8);
    if (finite(state?.maturity_class, 0) >= 4 && finite(state?.confidence_class, 0) >= 3) {
      entry.stableSenses += 1;
    }
  }

  const dimensions = Array.isArray(snapshot?.action_dimensions) ? snapshot.action_dimensions : [];
  for (const dimension of dimensions) {
    const segment = effectorSegment(dimension?.actuator_slot_id);
    if (!segment || !bySegment.has(segment)) continue;
    const entry = bySegment.get(segment);
    entry.dimensions.push(dimension);
    if (dimension?.agentic === true) entry.agenticDimensions += 1;
  }

  for (const entry of bySegment.values()) {
    const n = entry.senseCount;
    if (n) {
      entry.confidence /= n;
      entry.health /= n;
      entry.maturity /= n;
      entry.knowledge = mean([entry.confidence, entry.health, entry.maturity]);
      entry.stability = entry.stableSenses / n;
    }
    if (entry.dimensions.length) {
      entry.agency = mean(entry.dimensions.map((dimension) => ratio(
        dimension?.agentic === true
          ? Math.max(finite(dimension?.controllability, 0), finite(dimension?.confidence, 0))
          : finite(dimension?.controllability, 0) * .6
      )));
    }
  }
  return bySegment;
}

function scoreFor(entry, mode) {
  if (mode === 'stability') return entry.stability;
  if (mode === 'agency') return entry.agency;
  return entry.knowledge;
}

function scoreClass(score) {
  if (score >= .75) return 'strong';
  if (score >= .45) return 'medium';
  if (score > .08) return 'weak';
  return 'unknown';
}

function segmentAttrs(segment, metrics, mode, selected) {
  const score = scoreFor(metrics, mode);
  const cls = [
    'self-body-segment',
    scoreClass(score),
    selected === segment ? 'selected' : '',
    metrics.agenticDimensions ? 'agentic' : '',
  ].filter(Boolean).join(' ');
  return `class="${cls}" data-self-segment="${segment}" data-self-id="segment|${segment}" style="--segment-score:${score.toFixed(3)}"`;
}

function skeletonSvg(segments, mode, selected) {
  const a = (segment) => segmentAttrs(segment, segments.get(segment), mode, selected);
  return `<svg class="self-body-svg" viewBox="0 0 500 720" role="img" aria-label="Observer anatomical projection of learned self knowledge">
    <g ${a('head')}><circle cx="250" cy="76" r="48"/></g>

    <g ${a('torso')}>
      <path d="M195 142 Q250 122 305 142 L322 318 Q250 345 178 318 Z"/>
      <line x1="250" y1="145" x2="250" y2="318" class="self-body-bone"/>
    </g>
    <g ${a('pelvis')}><path d="M181 316 Q250 340 319 316 L303 386 Q250 408 197 386 Z"/></g>

    <g ${a('left_upper_arm')}>
      <line x1="190" y1="164" x2="128" y2="278" class="self-body-limb"/>
      <circle cx="187" cy="166" r="12"/><circle cx="128" cy="278" r="10"/>
    </g>
    <g ${a('left_forearm')}>
      <line x1="128" y1="278" x2="100" y2="410" class="self-body-limb"/>
      <circle cx="100" cy="410" r="9"/>
    </g>
    <g ${a('left_hand')}><path d="M83 405 Q100 394 117 405 L113 453 Q100 468 87 453 Z"/></g>

    <g ${a('right_upper_arm')}>
      <line x1="310" y1="164" x2="372" y2="278" class="self-body-limb"/>
      <circle cx="313" cy="166" r="12"/><circle cx="372" cy="278" r="10"/>
    </g>
    <g ${a('right_forearm')}>
      <line x1="372" y1="278" x2="400" y2="410" class="self-body-limb"/>
      <circle cx="400" cy="410" r="9"/>
    </g>
    <g ${a('right_hand')}><path d="M383 405 Q400 394 417 405 L413 453 Q400 468 387 453 Z"/></g>

    <g ${a('left_thigh')}>
      <line x1="220" y1="378" x2="196" y2="520" class="self-body-limb"/>
      <circle cx="218" cy="382" r="12"/><circle cx="196" cy="520" r="10"/>
    </g>
    <g ${a('left_shin')}>
      <line x1="196" y1="520" x2="188" y2="648" class="self-body-limb"/>
      <circle cx="188" cy="648" r="9"/>
    </g>
    <g ${a('left_foot')}><path d="M163 646 L198 646 L220 682 L165 682 Z"/></g>

    <g ${a('right_thigh')}>
      <line x1="280" y1="378" x2="304" y2="520" class="self-body-limb"/>
      <circle cx="282" cy="382" r="12"/><circle cx="304" cy="520" r="10"/>
    </g>
    <g ${a('right_shin')}>
      <line x1="304" y1="520" x2="312" y2="648" class="self-body-limb"/>
      <circle cx="312" cy="648" r="9"/>
    </g>
    <g ${a('right_foot')}><path d="M302 646 L337 646 L335 682 L280 682 Z"/></g>
  </svg>`;
}

function segmentList(segments, mode, selected) {
  return [...segments.values()]
    .sort((a, b) => scoreFor(b, mode) - scoreFor(a, mode))
    .map((entry) => {
      const score = scoreFor(entry, mode);
      return `<button type="button" class="self-body-region-row ${selected === entry.segment ? 'selected' : ''}" data-self-id="segment|${entry.segment}" data-self-segment="${entry.segment}">
        <span>${entry.label}</span>
        <i><b style="width:${Math.round(score * 100)}%"></b></i>
        <strong>${Math.round(score * 100)}%</strong>
      </button>`;
    }).join('');
}

export function renderSelfView(snapshot, mode = 'knowledge', selected = null) {
  const segments = selfViewSegments(snapshot);
  const mappedSenses = [...segments.values()].reduce((sum, item) => sum + item.senseCount, 0);
  const agentic = [...segments.values()].reduce((sum, item) => sum + item.agenticDimensions, 0);
  const stable = [...segments.values()].reduce((sum, item) => sum + item.stableSenses, 0);

  return `<div class="self-view-toolbar">
    <div class="self-view-modes">
      ${SELF_VIEW_MODES.map(([id, label]) =>
        `<button type="button" class="${mode === id ? 'active' : ''}" data-self-view-mode="${id}">${label}</button>`
      ).join('')}
    </div>
    <div class="self-view-legend">
      <span><i class="unknown"></i>unknown</span>
      <span><i class="weak"></i>weak</span>
      <span><i class="medium"></i>developing</span>
      <span><i class="strong"></i>strong</span>
    </div>
  </div>
  <div class="self-view-layout">
    <div class="self-body-stage">
      <div class="self-body-stage-label">
        <strong>Known body</strong>
        <small>Observer anatomy × organism-owned evidence</small>
      </div>
      ${skeletonSvg(segments, mode, selected)}
      <div class="self-body-epistemic">Anatomical names and positions are observer metadata. Symbiont still sees only opaque rec.N / eff.N channels.</div>
    </div>
    <div class="self-body-regions">
      <div class="self-section-head"><div><span>Body regions</span><small>Click a region to inspect what is actually known there</small></div></div>
      ${segmentList(segments, mode, selected)}
    </div>
  </div>
  <div class="self-view-summary">
    <div><span>Mapped senses</span><strong>${mappedSenses}</strong></div>
    <div><span>Stable senses</span><strong>${stable}</strong></div>
    <div><span>Agentic dimensions</span><strong>${agentic}</strong></div>
    <div><span>Projection mode</span><strong>${mode}</strong></div>
  </div>`;
}

export function selfViewSegmentRecord(snapshot, segment) {
  const entry = selfViewSegments(snapshot).get(segment);
  if (!entry) return null;
  return {
    kind: 'Observer anatomical projection',
    displayId: entry.label,
    item: {
      observer_region: entry.label,
      mapped_senses: entry.senseCount,
      knowledge: Number(entry.knowledge.toFixed(4)),
      confidence: Number(entry.confidence.toFixed(4)),
      health: Number(entry.health.toFixed(4)),
      maturity: Number(entry.maturity.toFixed(4)),
      stable_senses: entry.stableSenses,
      action_dimensions: entry.dimensions.length,
      agentic_dimensions: entry.agenticDimensions,
      agency: Number(entry.agency.toFixed(4)),
      epistemic_status: 'observer projection only',
      receptor_ids: entry.receptorIds,
      dimension_ids: entry.dimensions.map((item) => item.dimension_id),
    },
  };
}
