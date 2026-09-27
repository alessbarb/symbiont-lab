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
  ['composite', 'Composite'],
  ['knowledge', 'Knowledge'],
  ['coverage', 'Coverage'],
  ['stability', 'Stability'],
  ['agency', 'Agency'],
];

function observerBody(snapshot) {
  const body = snapshot?.observer_semantics?.body;
  if (!body || typeof body !== 'object') {
    return {
      bodyKind: 'anthropomorphic-v6',
      baseLink: 'pelvis',
      segments: Object.fromEntries(CONTACT_SEGMENTS.map((name) => [name, {}])),
      joints: JOINT_TOPOLOGY.map((joint) => ({
        name: joint.name,
        parent: joint.parent,
        child: joint.child,
        origin: joint.offset ?? [0, 0, 0],
      })),
      contactRegions: CONTACT_SEGMENTS,
    };
  }
  return body;
}

function morphologySegmentNames(snapshot) {
  const names = Object.keys(observerBody(snapshot).segments ?? {});
  return names.length ? names : CONTACT_SEGMENTS;
}

function prettySegment(name) {
  return String(name ?? '').replaceAll('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function jointPhysicalSegment(snapshot, jointIndex) {
  const body = observerBody(snapshot);
  const joints = Array.isArray(body.joints) ? body.joints : [];
  const segments = new Set(Object.keys(body.segments ?? {}));
  const joint = joints[jointIndex];
  if (!joint) return null;
  let child = joint.child;
  if (segments.has(child)) return child;
  const seen = new Set();
  while (child && !seen.has(child)) {
    seen.add(child);
    const next = joints.find((item) => item.parent === child);
    if (!next) break;
    child = next.child;
    if (segments.has(child)) return child;
  }
  return segments.has(joint.parent) ? joint.parent : null;
}


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

function receptorSegment(snapshot, receptorId) {
  const match = /^rec\.(\d+)$/.exec(String(receptorId ?? ''));
  if (!match) return null;
  const ordinal = Number(match[1]);
  const body = observerBody(snapshot);
  const joints = Array.isArray(body.joints) ? body.joints : [];

  if (ordinal < joints.length * 2) {
    return jointPhysicalSegment(snapshot, Math.floor(ordinal / 2));
  }

  const contactRegions = Array.isArray(body.contactRegions) ? body.contactRegions : [];
  const contactPresenceStart = joints.length * 2 + 10;
  const resourceOrdinal = contactPresenceStart + contactRegions.length;
  const contactLoadStart = resourceOrdinal + 1;
  if (ordinal >= contactPresenceStart && ordinal < contactPresenceStart + contactRegions.length) {
    return contactRegions[ordinal - contactPresenceStart] ?? null;
  }
  if (ordinal >= contactLoadStart && ordinal < contactLoadStart + contactRegions.length) {
    return contactRegions[ordinal - contactLoadStart] ?? null;
  }
  return null;
}

function effectorSegment(snapshot, effectorId) {
  const match = /^eff\.(\d+)$/.exec(String(effectorId ?? ''));
  if (!match) return null;
  return jointPhysicalSegment(snapshot, Math.floor(Number(match[1]) / 2));
}

function expectedReceptorsBySegment(snapshot) {
  const names = morphologySegmentNames(snapshot);
  const result = new Map(names.map((segment) => [segment, new Set()]));
  const body = observerBody(snapshot);
  const joints = Array.isArray(body.joints) ? body.joints : [];
  joints.forEach((joint, index) => {
    const segment = jointPhysicalSegment(snapshot, index);
    if (!segment || !result.has(segment)) return;
    result.get(segment).add(`rec.${index * 2}`);
    result.get(segment).add(`rec.${index * 2 + 1}`);
  });

  const contactRegions = Array.isArray(body.contactRegions) ? body.contactRegions : [];
  const contactPresenceStart = joints.length * 2 + 10;
  const resourceOrdinal = contactPresenceStart + contactRegions.length;
  const contactLoadStart = resourceOrdinal + 1;
  contactRegions.forEach((segment, index) => {
    if (!result.has(segment)) return;
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
    label: SEGMENT_LABELS[segment] ?? prettySegment(segment),
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
      if (!receptorSegment(snapshot, sourceId)) continue;
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
  const expected = expectedReceptorsBySegment(snapshot);
  const names = morphologySegmentNames(snapshot);
  const bySegment = new Map(
    names.map((segment) => [segment, emptySegment(segment, expected.get(segment) ?? new Set())])
  );
  bySegment.morphology = observerBody(snapshot);
  const { evidence } = selfEvidenceByReceptor(snapshot);

  for (const item of evidence.values()) {
    const segment = receptorSegment(snapshot, item.sourceId);
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
    const touched = new Set(effectorIds.map((id) => effectorSegment(snapshot, id)).filter(Boolean));
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
  if (mode === 'change') return ratio(Math.abs(entry.changeMagnitude ?? 0));
  if (mode === 'coverage') return entry.coverage;
  if (mode === 'stability') return entry.stability;
  if (mode === 'agency') return entry.agency;
  if (mode === 'composite') {
    return ratio(
      entry.knowledge * .45
      + entry.stability * .30
      + entry.agency * .25
    );
  }
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
    mode === 'composite' ? 'composite' : `focus-${mode}`,
    mode === 'change' && metrics.changeDirection ? `change-${metrics.changeDirection}` : '',
    scoreClass(score),
    selected === segment ? 'selected' : '',
    metrics.agenticDimensions ? 'agentic' : '',
  ].filter(Boolean).join(' ');
  return `class="${cls}" data-self-segment="${segment}" data-self-id="segment|${segment}" style="--segment-score:${score.toFixed(3)};--segment-coverage:${metrics.coverage.toFixed(3)};--segment-quality:${metrics.quality.toFixed(3)};--segment-stability:${metrics.stability.toFixed(3)};--segment-agency:${metrics.agency.toFixed(3)}"`;
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


function aggregateSelfView(segments, snapshot, unmappedEntries = []) {
  const values = [...segments.values()];
  const expected = values.reduce((sum, item) => sum + item.expectedSenseCount, 0);
  const learned = values.reduce((sum, item) => sum + item.senseCount, 0);
  const stable = values.reduce((sum, item) => sum + item.stableSenses, 0);
  const representedRegions = values.filter((item) => item.senseCount > 0).length;
  const agencyRegions = values.filter((item) => item.agency > 0).length;
  const agenticRegions = values.filter((item) => item.agenticDimensions > 0).length;
  const dimensions = Array.isArray(snapshot?.action_dimensions) ? snapshot.action_dimensions : [];
  const mappedDimensionIds = new Set(
    values.flatMap((item) => item.dimensions.map((dimension) => dimension.dimension_id))
  );
  return {
    expected,
    learned,
    stable,
    coverage: expected ? learned / expected : 0,
    stability: expected ? stable / expected : 0,
    knowledge: expected
      ? values.reduce((sum, item) => sum + item.knowledge * item.expectedSenseCount, 0) / expected
      : 0,
    agency: values.length ? mean(values.map((item) => item.agency)) : 0,
    representedRegions,
    agencyRegions,
    agenticRegions,
    unmappedLearned: unmappedEntries.length,
    unmappedDimensions: Math.max(0, dimensions.length - mappedDimensionIds.size),
  };
}

export function captureSelfViewDevelopment(snapshot) {
  const segments = selfViewSegments(snapshot);
  const { unmappedEntries } = selfEvidenceByReceptor(snapshot);
  const aggregate = aggregateSelfView(segments, snapshot, unmappedEntries);
  return {
    tick: finite(snapshot?.tick, 0),
    aggregate,
    morphology: observerBody(snapshot),
    segments: [...segments.values()].map((entry) => ({
      segment: entry.segment,
      coverage: entry.coverage,
      quality: entry.quality,
      knowledge: entry.knowledge,
      stability: entry.stability,
      agency: entry.agency,
      agenticDimensions: entry.agenticDimensions,
      senseCount: entry.senseCount,
      expectedSenseCount: entry.expectedSenseCount,
    })),
  };
}

function snapshotSegments(frame) {
  const morphology = frame?.morphology ?? {};
  const names = Object.keys(morphology.segments ?? {});
  const effectiveNames = names.length ? names : CONTACT_SEGMENTS;
  const map = new Map();
  for (const segment of effectiveNames) {
    const found = frame?.segments?.find((item) => item.segment === segment);
    map.set(segment, {
      ...emptySegment(segment, new Set()),
      ...(found ?? {}),
      label: SEGMENT_LABELS[segment] ?? prettySegment(segment),
    });
  }
  map.morphology = morphology;
  return map;
}

function deltaSegments(frame, baseline) {
  const current = snapshotSegments(frame);
  const previous = snapshotSegments(baseline ?? frame);
  const result = new Map();
  for (const segment of CONTACT_SEGMENTS) {
    const now = current.get(segment);
    const before = previous.get(segment);
    const deltas = {
      coverage: finite(now.coverage, 0) - finite(before.coverage, 0),
      knowledge: finite(now.knowledge, 0) - finite(before.knowledge, 0),
      stability: finite(now.stability, 0) - finite(before.stability, 0),
      agency: finite(now.agency, 0) - finite(before.agency, 0),
    };
    const strongest = Object.entries(deltas)
      .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))[0] ?? ['coverage', 0];
    const magnitude = Math.max(...Object.values(deltas).map((value) => Math.abs(value)));
    result.set(segment, {
      ...now,
      coverage: Math.abs(deltas.coverage),
      knowledge: Math.abs(deltas.knowledge),
      stability: Math.abs(deltas.stability),
      agency: Math.abs(deltas.agency),
      quality: magnitude,
      changeMagnitude: magnitude,
      changeMetric: strongest[0],
      changeValue: strongest[1],
      changeDirection: strongest[1] > .0005 ? 'gained' : strongest[1] < -.0005 ? 'lost' : 'unchanged',
      deltaCoverage: deltas.coverage,
      deltaKnowledge: deltas.knowledge,
      deltaStability: deltas.stability,
      deltaAgency: deltas.agency,
    });
  }
  return result;
}

function developmentScale(frames, mode) {
  if (mode !== 'detail') return { min: 0, max: 1 };
  const values = frames.flatMap((frame) => [
    ratio(frame.aggregate?.coverage),
    ratio(frame.aggregate?.stability),
    ratio(frame.aggregate?.agency),
  ]);
  if (!values.length) return { min: 0, max: 1 };
  const rawMin = Math.min(...values);
  const rawMax = Math.max(...values);
  const span = Math.max(.04, rawMax - rawMin);
  const padding = Math.max(.02, span * .18);
  return {
    min: Math.max(0, rawMin - padding),
    max: Math.min(1, rawMax + padding),
  };
}

function developmentPath(frames, key, width, height, scale) {
  if (frames.length < 2) return '';
  const span = Math.max(.0001, scale.max - scale.min);
  const values = frames.map((frame) => ratio(frame.aggregate?.[key]));
  return values.map((value, index) => {
    const x = 18 + (index / Math.max(1, frames.length - 1)) * (width - 36);
    const normalized = ratio((value - scale.min) / span);
    const y = 10 + (1 - normalized) * (height - 28);
    return `${index ? 'L' : 'M'} ${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(' ');
}

function developmentMilestones(frames) {
  if (!frames.length) return [];
  const points = [{ index: 0, title: 'session start' }];
  for (let index = 1; index < frames.length; index += 1) {
    const prev = frames[index - 1];
    const frame = frames[index];
    if (frame.aggregate.agenticRegions !== prev.aggregate.agenticRegions) {
      points.push({ index, title: `${frame.aggregate.agenticRegions} agentic regions` });
    } else if (frame.aggregate.representedRegions !== prev.aggregate.representedRegions) {
      points.push({ index, title: `${frame.aggregate.representedRegions} represented regions` });
    } else if (Math.abs(frame.aggregate.agency - prev.aggregate.agency) >= .01) {
      points.push({ index, title: 'agency changed' });
    }
  }
  const lastIndex = frames.length - 1;
  if (!points.some((point) => point.index === lastIndex)) {
    points.push({ index: lastIndex, title: 'current' });
  }
  if (points.length <= 8) return points;
  const interior = points.slice(1, -1);
  const stride = Math.ceil(interior.length / 6);
  return [points[0], ...interior.filter((_, index) => index % stride === 0).slice(0, 6), points.at(-1)];
}

function deltaRows(current, baseline) {
  const deltas = [...deltaSegments(current, baseline).values()]
    .filter((item) => item.changeDirection !== 'unchanged')
    .sort((a, b) => Math.abs(b.changeValue) - Math.abs(a.changeValue))
    .slice(0, 6);
  if (!deltas.length) {
    return '<div class="self-development-nochange">No material regional change from the previous recorded frame.</div>';
  }
  const signed = (value) => {
    const n = finite(value, 0);
    return `${n > 0 ? '+' : ''}${Math.round(n * 100)}%`;
  };
  return deltas.map((item) => `<div class="self-development-delta ${item.changeDirection}">
    <strong>${item.label}</strong>
    <span>${item.changeMetric}</span>
    <b>${signed(item.changeValue)}</b>
  </div>`).join('');
}

export function renderSelfViewDevelopment(history, options = {}) {
  const frames = Array.isArray(history) ? history : [];
  if (!frames.length) {
    return '<div class="self-empty-state"><h3>No development history yet</h3><p>Development begins accumulating when this observer session receives Self-Model snapshots.</p></div>';
  }

  const requestedIndex = Number(options.index);
  const selectedIndex = Number.isInteger(requestedIndex)
    ? Math.max(0, Math.min(frames.length - 1, requestedIndex))
    : frames.length - 1;
  const bodyMode = options.bodyMode === 'change' ? 'change' : 'state';
  const scaleMode = options.scaleMode === 'absolute' ? 'absolute' : 'detail';
  const selected = frames[selectedIndex];
  const baseline = frames[Math.max(0, selectedIndex - 1)];
  const first = frames[0];
  const latest = frames[frames.length - 1];
  const scale = developmentScale(frames, scaleMode);
  const selectedSegments = bodyMode === 'change'
    ? deltaSegments(selected, baseline)
    : snapshotSegments(selected);
  const width = 820;
  const height = 190;
  const pct = (value) => `${Math.round(ratio(value) * 100)}%`;
  const signedPct = (value) => {
    const n = finite(value, 0);
    return `${n > 0 ? '+' : ''}${Math.round(n * 100)}%`;
  };
  const markerX = 18 + (selectedIndex / Math.max(1, frames.length - 1)) * (width - 36);
  const milestones = developmentMilestones(frames);

  return `<div class="self-development-head">
    <div><span>Development timeline</span><strong>t${first.tick} → t${latest.tick}</strong></div>
    <small>Browser-session observer history · never fed back</small>
  </div>

  <div class="self-development-controls">
    <div class="self-dev-toggle">
      <span>Body</span>
      <button type="button" class="${bodyMode === 'state' ? 'active' : ''}" data-self-dev-body-mode="state">State</button>
      <button type="button" class="${bodyMode === 'change' ? 'active' : ''}" data-self-dev-body-mode="change">Change</button>
    </div>
    <div class="self-dev-toggle">
      <span>Graph</span>
      <button type="button" class="${scaleMode === 'absolute' ? 'active' : ''}" data-self-dev-scale="absolute">Absolute</button>
      <button type="button" class="${scaleMode === 'detail' ? 'active' : ''}" data-self-dev-scale="detail">Detail</button>
    </div>
    <div class="self-development-selected"><span>Selected</span><strong>t${selected.tick}</strong><small>frame ${selectedIndex + 1}/${frames.length}</small></div>
  </div>

  <div class="self-development-chart">
    <div class="self-dev-scale-labels">
      <span>${pct(scale.max)}</span>
      <span>${pct(scale.min)}</span>
    </div>
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Self body development over time">
      <line x1="18" y1="${height - 18}" x2="${width - 18}" y2="${height - 18}" class="self-dev-axis"/>
      <line x1="18" y1="10" x2="18" y2="${height - 18}" class="self-dev-axis"/>
      <path d="${developmentPath(frames, 'coverage', width, height, scale)}" class="self-dev-line coverage"/>
      <path d="${developmentPath(frames, 'stability', width, height, scale)}" class="self-dev-line stability"/>
      <path d="${developmentPath(frames, 'agency', width, height, scale)}" class="self-dev-line agency"/>
      <line x1="${markerX.toFixed(1)}" y1="10" x2="${markerX.toFixed(1)}" y2="${height - 18}" class="self-dev-selection"/>
    </svg>
    <div class="self-development-legend">
      <span class="coverage">coverage ${pct(selected.aggregate.coverage)}</span>
      <span class="stability">stability ${pct(selected.aggregate.stability)}</span>
      <span class="agency">agency ${pct(selected.aggregate.agency)}</span>
    </div>
  </div>

  <div class="self-development-scrubber">
    <input type="range" min="0" max="${frames.length - 1}" value="${selectedIndex}" step="1" data-self-dev-index aria-label="Development tick"/>
    <div><span>t${first.tick}</span><strong>t${selected.tick}</strong><span>t${latest.tick}</span></div>
  </div>

  <div class="self-development-focus">
    <div class="self-development-main-body ${bodyMode}">
      <div class="self-body-stage-label">
        <strong>${bodyMode === 'change' ? 'What changed' : 'Self body state'}</strong>
        <small>${bodyMode === 'change' ? `t${baseline.tick} → t${selected.tick}` : `observer projection at t${selected.tick}`}</small>
      </div>
      ${skeletonSvg(selectedSegments, bodyMode === 'change' ? 'change' : 'composite', null)}
      <div class="self-development-body-caption">
        <span>${selected.aggregate.representedRegions} represented regions</span>
        <span>${selected.aggregate.agencyRegions} agency regions</span>
        <span>${selected.aggregate.agenticRegions} agentic regions</span>
      </div>
    </div>
    <div class="self-development-evidence">
      <div class="self-section-head"><div><span>${bodyMode === 'change' ? 'Regional delta' : 'Selected state'}</span><small>${bodyMode === 'change' ? 'largest changes since previous recorded frame' : 'developmental evidence at selected tick'}</small></div></div>
      ${bodyMode === 'change'
        ? deltaRows(selected, baseline)
        : `<div class="self-development-state-grid">
            <div><span>Coverage</span><strong>${pct(selected.aggregate.coverage)}</strong><small>${selected.aggregate.learned}/${selected.aggregate.expected} physical channels</small></div>
            <div><span>Stability</span><strong>${pct(selected.aggregate.stability)}</strong><small>${selected.aggregate.stable} stable channels</small></div>
            <div><span>Agency</span><strong>${pct(selected.aggregate.agency)}</strong><small>${selected.aggregate.agencyRegions} regions touched</small></div>
            <div><span>Agentic</span><strong>${selected.aggregate.agenticRegions}</strong><small>regions with agentic dimensions</small></div>
          </div>`}
    </div>
  </div>

  <div class="self-development-milestones">
    <div class="self-section-head"><div><span>Observed milestones</span><small>select a meaningful frame</small></div></div>
    <div class="self-dev-milestone-list">
      ${milestones.map((point) => `<button type="button" class="${point.index === selectedIndex ? 'active' : ''}" data-self-dev-frame="${point.index}">
        <strong>t${frames[point.index].tick}</strong><span>${point.title}</span>
      </button>`).join('')}
    </div>
  </div>

  <div class="self-view-summary">
    <div><span>Coverage since attach</span><strong>${signedPct(selected.aggregate.coverage - first.aggregate.coverage)}</strong></div>
    <div><span>Stability since attach</span><strong>${signedPct(selected.aggregate.stability - first.aggregate.stability)}</strong></div>
    <div><span>Agency regions</span><strong>${selected.aggregate.agencyRegions}</strong></div>
    <div><span>Agentic regions</span><strong>${selected.aggregate.agenticRegions}</strong></div>
    <div><span>Recorded frames</span><strong>${frames.length}</strong></div>
  </div>`;
}

export function renderSelfView(snapshot, mode = 'composite', selected = null) {
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
        <small>${mode === 'composite' ? 'composite: materialization + stability + agency halo' : `focus: ${mode}`} · observer anatomy × organism evidence</small>
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
