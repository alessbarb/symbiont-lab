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
  ['coverage', 'Coverage'],
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
  const valid = values.map((value) => finite(value, null)).filter((value) => value !== null);
  if (!valid.length) return 0;
  return valid.reduce((sum, value) => sum + value, 0) / valid.length;
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

  if (ordinal < JOINT_TOPOLOGY.length * 2) {
    const jointOrdinal = Math.floor(ordinal / 2);
    const joint = JOINT_TOPOLOGY[jointOrdinal];
    return joint ? jointSegment(joint.name) : null;
  }

  const proprioCount = JOINT_TOPOLOGY.length * 2;
  const contactPresenceStart = proprioCount + 10;
  const resourceOrdinal = contactPresenceStart + CONTACT_SEGMENTS.length;
  const contactLoadStart = resourceOrdinal + 1;

  if (ordinal >= contactPresenceStart && ordinal < contactPresenceStart + CONTACT_SEGMENTS.length) {
    return CONTACT_SEGMENTS[ordinal - contactPresenceStart] ?? null;
  }
  if (ordinal >= contactLoadStart && ordinal < contactLoadStart + CONTACT_SEGMENTS.length) {
    return CONTACT_SEGMENTS[ordinal - contactLoadStart] ?? null;
  }
  return null;
}

function effectorSegment(effectorId) {
  const match = /^eff\.(\d+)$/.exec(String(effectorId ?? ''));
  if (!match) return null;
  const jointOrdinal = Math.floor(Number(match[1]) / 2);
  const joint = JOINT_TOPOLOGY[jointOrdinal];
  return joint ? jointSegment(joint.name) : null;
}

function expectedReceptorsBySegment() {
  const result = new Map(CONTACT_SEGMENTS.map((segment) => [segment, new Set()]));
  JOINT_TOPOLOGY.forEach((joint, index) => {
    const segment = jointSegment(joint.name);
    if (!segment || !result.has(segment)) return;
    result.get(segment).add(`rec.${index * 2}`);
    result.get(segment).add(`rec.${index * 2 + 1}`);
  });

  const contactPresenceStart = JOINT_TOPOLOGY.length * 2 + 10;
  const resourceOrdinal = contactPresenceStart + CONTACT_SEGMENTS.length;
  const contactLoadStart = resourceOrdinal + 1;
  CONTACT_SEGMENTS.forEach((segment, index) => {
    result.get(segment).add(`rec.${contactPresenceStart + index}`);
    result.get(segment).add(`rec.${contactLoadStart + index}`);
  });
  return result;
}

function sourceIdsForSelfEntry(snapshot, selfId) {
  if (/^rec\.\d+$/.test(String(selfId))) return [String(selfId)];
  const semantics = snapshot?.observer_semantics?.sensory?.[selfId];
  const sourceIds = semantics?.sourceIds;
  return Array.isArray(sourceIds) ? sourceIds.map(String) : [];
}

function emptySegment(segment, expectedIds) {
  return {
    segment,
    label: SEGMENT_LABELS[segment] ?? segment,
    expectedReceptorIds: [...expectedIds],
    expectedSenseCount: expectedIds.size,
    receptorIds: [],
    senseCount: 0,
    confidence: 0,
    health: 0,
    maturity: 0,
    quality: 0,
    coverage: 0,
    stableSenses: 0,
    dimensions: [],
    agenticDimensions: 0,
    agency: 0,
    knowledge: 0,
    stability: 0,
  };
}

function selfEvidenceByReceptor(snapshot) {
  const selfModel = snapshot?.self_model && typeof snapshot.self_model === 'object'
    ? snapshot.self_model : {};
  const evidence = new Map();
  const unmappedEntries = [];

  for (const [selfId, state] of Object.entries(selfModel)) {
    const sourceIds = sourceIdsForSelfEntry(snapshot, selfId);
    let localized = false;
    for (const sourceId of sourceIds) {
      if (!receptorSegment(sourceId)) continue;
      localized = true;
      const previous = evidence.get(sourceId);
      const current = {
        selfId,
        sourceId,
        confidence: classRatio(state?.confidence_class),
        health: classRatio(state?.health_class),
        maturity: classRatio(state?.maturity_class, 8),
        stable: finite(state?.maturity_class, 0) >= 4 && finite(state?.confidence_class, 0) >= 3,
      };
      if (!previous || mean([current.confidence, current.health, current.maturity]) >
        mean([previous.confidence, previous.health, previous.maturity])) {
        evidence.set(sourceId, current);
      }
    }
    if (!localized) unmappedEntries.push(selfId);
  }
  return { evidence, unmappedEntries };
}

export function selfViewSegments(snapshot) {
  const expected = expectedReceptorsBySegment();
  const bySegment = new Map(
    CONTACT_SEGMENTS.map((segment) => [segment, emptySegment(segment, expected.get(segment))])
  );
  const { evidence } = selfEvidenceByReceptor(snapshot);

  for (const item of evidence.values()) {
    const segment = receptorSegment(item.sourceId);
    if (!segment || !bySegment.has(segment)) continue;
    const entry = bySegment.get(segment);
    entry.receptorIds.push(item.sourceId);
    entry.senseCount += 1;
    entry.confidence += item.confidence;
    entry.health += item.health;
    entry.maturity += item.maturity;
    if (item.stable) entry.stableSenses += 1;
  }

  const dimensions = Array.isArray(snapshot?.action_dimensions) ? snapshot.action_dimensions : [];
  const dimensionSemantics = snapshot?.observer_semantics?.actionDimensions ?? {};
  for (const dimension of dimensions) {
    const semantics = dimensionSemantics?.[dimension?.dimension_id];
    const effectorIds = Array.isArray(semantics?.effectorIds) ? semantics.effectorIds : [];
    const touched = new Set(effectorIds.map(effectorSegment).filter(Boolean));
    for (const segment of touched) {
      if (!bySegment.has(segment)) continue;
      const entry = bySegment.get(segment);
      entry.dimensions.push({
        ...dimension,
        observer_mapping: semantics?.mapping ?? 'unresolved',
        mapped_channel_count: finite(semantics?.mappedChannelCount, 0),
        channel_count: finite(semantics?.channelCount, dimension?.channel_count ?? 0),
      });
      if (dimension?.agentic === true) entry.agenticDimensions += 1;
    }
  }

  for (const entry of bySegment.values()) {
    const n = entry.senseCount;
    if (n) {
      entry.confidence /= n;
      entry.health /= n;
      entry.maturity /= n;
      entry.quality = mean([entry.confidence, entry.health, entry.maturity]);
    }
    entry.coverage = entry.expectedSenseCount
      ? ratio(entry.senseCount / entry.expectedSenseCount)
      : 0;
    entry.knowledge = entry.coverage * entry.quality;
    entry.stability = entry.expectedSenseCount
      ? ratio(entry.stableSenses / entry.expectedSenseCount)
      : 0;

    if (entry.dimensions.length) {
      entry.agency = mean(entry.dimensions.map((dimension) => {
        const evidenceStrength = Math.max(
          finite(dimension?.controllability, 0),
          finite(dimension?.confidence, 0)
        );
        return ratio(dimension?.agentic === true ? evidenceStrength : evidenceStrength * .55);
      }));
    }
  }
  return bySegment;
}

function scoreFor(entry, mode) {
  if (mode === 'coverage') return entry.coverage;
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
  return `class="${cls}" data-self-segment="${segment}" data-self-id="segment|${segment}" style="--segment-score:${score.toFixed(3)};--segment-coverage:${metrics.coverage.toFixed(3)}"`;
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

function regionStatus(entry) {
  if (!entry.senseCount) return 'unknown';
  if (entry.coverage >= .75 && entry.quality >= .75) return 'well represented';
  if (entry.coverage >= .35) return 'partial';
  return 'sparse';
}

function segmentList(segments, mode, selected) {
  return [...segments.values()]
    .sort((a, b) => scoreFor(b, mode) - scoreFor(a, mode))
    .map((entry) => {
      const score = scoreFor(entry, mode);
      return `<button type="button" class="self-body-region-row ${selected === entry.segment ? 'selected' : ''}" data-self-id="segment|${entry.segment}" data-self-segment="${entry.segment}">
        <span><b>${entry.label}</b><small>${regionStatus(entry)} · ${entry.senseCount}/${entry.expectedSenseCount}</small></span>
        <i><b style="width:${Math.round(score * 100)}%"></b></i>
        <strong>${Math.round(score * 100)}%</strong>
      </button>`;
    }).join('');
}

export function renderSelfView(snapshot, mode = 'knowledge', selected = null) {
  const segments = selfViewSegments(snapshot);
  const { evidence, unmappedEntries } = selfEvidenceByReceptor(snapshot);
  const expectedTotal = [...segments.values()].reduce((sum, item) => sum + item.expectedSenseCount, 0);
  const mappedSenses = evidence.size;
  const agenticDimensions = new Set();
  const mappedDimensions = new Set();
  for (const entry of segments.values()) {
    for (const dimension of entry.dimensions) {
      mappedDimensions.add(dimension.dimension_id);
      if (dimension.agentic === true) agenticDimensions.add(dimension.dimension_id);
    }
  }
  const totalDimensions = Array.isArray(snapshot?.action_dimensions) ? snapshot.action_dimensions.length : 0;
  const unmappedDimensions = Math.max(0, totalDimensions - mappedDimensions.size);
  const stable = [...segments.values()].reduce((sum, item) => sum + item.stableSenses, 0);

  return `<div class="self-view-toolbar">
    <div class="self-view-modes">
      ${SELF_VIEW_MODES.map(([id, label]) =>
        `<button type="button" class="${mode === id ? 'active' : ''}" data-self-view-mode="${id}">${label}</button>`
      ).join('')}
    </div>
    <div class="self-view-legend">
      <span><i class="unknown"></i>unknown</span>
      <span><i class="weak"></i>sparse</span>
      <span><i class="medium"></i>developing</span>
      <span><i class="strong"></i>strong</span>
    </div>
  </div>
  <div class="self-view-layout">
    <div class="self-body-stage">
      <div class="self-body-stage-label">
        <strong>Known body</strong>
        <small>ghost body: physical observer surface × organism-owned evidence</small>
      </div>
      ${skeletonSvg(segments, mode, selected)}
      <div class="self-body-epistemic">Fill is learned evidence projected onto observer anatomy. Anatomical labels never feed back; Symbiont still sees opaque channels.</div>
    </div>
    <div class="self-body-regions">
      <div class="self-section-head"><div><span>Body regions</span><small>score · learned/expected physical channels</small></div></div>
      ${segmentList(segments, mode, selected)}
    </div>
  </div>
  <div class="self-view-summary">
    <div><span>Physical surface represented</span><strong>${mappedSenses} / ${expectedTotal}</strong></div>
    <div><span>Stable channels</span><strong>${stable}</strong></div>
    <div><span>Agentic dimensions localized</span><strong>${agenticDimensions.size}</strong></div>
    <div><span>Unmapped learned evidence</span><strong>${unmappedEntries.length}</strong></div>
    <div><span>Unmapped dimensions</span><strong>${unmappedDimensions}</strong></div>
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
      physical_channels_expected: entry.expectedSenseCount,
      learned_channels_mapped: entry.senseCount,
      coverage: Number(entry.coverage.toFixed(4)),
      quality: Number(entry.quality.toFixed(4)),
      knowledge: Number(entry.knowledge.toFixed(4)),
      confidence: Number(entry.confidence.toFixed(4)),
      health: Number(entry.health.toFixed(4)),
      maturity: Number(entry.maturity.toFixed(4)),
      stable_channels: entry.stableSenses,
      stability: Number(entry.stability.toFixed(4)),
      action_dimensions: entry.dimensions.length,
      agentic_dimensions: entry.agenticDimensions,
      agency: Number(entry.agency.toFixed(4)),
      epistemic_status: 'observer projection only',
      receptor_ids: entry.receptorIds,
      expected_receptor_ids: entry.expectedReceptorIds,
      dimension_ids: entry.dimensions.map((item) => item.dimension_id),
    },
  };
}
