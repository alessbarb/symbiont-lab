/**
 * Static humanoid topology and observer-panel schema.
 * Kept separate from rendering/lifecycle so the viewer consumes one canonical model.
 */

export const SEGMENTS = {
  pelvis:          { wdh: [0.32, 0.20, 0.22], offset: [0, 0, 0] },
  torso:           { wdh: [0.40, 0.22, 0.50], offset: [0, 0, 0.21] },
  head:            { wdh: [0.21, 0.21, 0.23], offset: [0, 0, 0.12] },
  left_upper_arm:  { wdh: [0.13, 0.13, 0.31], offset: [0, 0, -0.155] },
  left_forearm:    { wdh: [0.11, 0.11, 0.27], offset: [0, 0, -0.135] },
  left_hand:       { wdh: [0.09, 0.15, 0.18], offset: [0, 0, -0.09] },
  right_upper_arm: { wdh: [0.13, 0.13, 0.31], offset: [0, 0, -0.155] },
  right_forearm:   { wdh: [0.11, 0.11, 0.27], offset: [0, 0, -0.135] },
  right_hand:      { wdh: [0.09, 0.15, 0.18], offset: [0, 0, -0.09] },
  left_thigh:      { wdh: [0.15, 0.15, 0.40], offset: [0, 0, -0.20] },
  left_shin:       { wdh: [0.13, 0.13, 0.40], offset: [0, 0, -0.20] },
  left_foot:       { wdh: [0.11, 0.26, 0.07], offset: [0, -0.075, -0.035] },
  right_thigh:     { wdh: [0.15, 0.15, 0.40], offset: [0, 0, -0.20] },
  right_shin:      { wdh: [0.13, 0.13, 0.40], offset: [0, 0, -0.20] },
  right_foot:      { wdh: [0.11, 0.26, 0.07], offset: [0, -0.075, -0.035] },
};

/**
 * Segment colour palette for MeshStandardMaterial.
 * Keys match SEGMENTS.
 */
export const SEGMENT_COLORS = {
  pelvis:          0x2a2a5a,
  torso:           0x1a3a6a,
  head:            0x6a6a7a,
  left_upper_arm:  0x2244aa,
  left_forearm:    0x2244aa,
  left_hand:       0x2244aa,
  right_upper_arm: 0x11aacc,
  right_forearm:   0x11aacc,
  right_hand:      0x11aacc,
  left_thigh:      0x1a5a2a,
  left_shin:       0x1a5a2a,
  left_foot:       0x1a5a2a,
  right_thigh:     0x2a8a3a,
  right_shin:      0x2a8a3a,
  right_foot:      0x2a8a3a,
};

/**
 * Kinematic tree mirrored from the PyBullet humanoid definition.
 *
 * axis:
 *   Y -> yaw
 *   X -> pitch
 *   Z -> roll / deviation
 *
 * All offsets are expressed in PyBullet Z-up coordinates.
 */
export const JOINT_TOPOLOGY = [
  // Trunk
  { name: 'trunk_yaw',            parent: 'pelvis',                    child: 'trunk_yaw_carrier',           offset: [0, 0, 0.10],     axis: 'Y' },
  { name: 'trunk_roll',           parent: 'trunk_yaw_carrier',         child: 'trunk_roll_carrier',          offset: [0, 0, 0],        axis: 'Z' },
  { name: 'trunk_pitch',          parent: 'trunk_roll_carrier',        child: 'torso',                       offset: [0, 0, 0],        axis: 'X' },
  // Neck / Head
  { name: 'neck_yaw',             parent: 'torso',                     child: 'neck_yaw_carrier',            offset: [0, 0, 0.48],     axis: 'Y' },
  { name: 'neck_pitch',           parent: 'neck_yaw_carrier',          child: 'head',                        offset: [0, 0, 0],        axis: 'X' },
  // Left arm
  { name: 'left_shoulder_yaw',    parent: 'torso',                     child: 'left_shoulder_yaw_carrier',   offset: [-0.28, 0, 0.36], axis: 'Y' },
  { name: 'left_shoulder_roll',   parent: 'left_shoulder_yaw_carrier', child: 'left_shoulder_roll_carrier',  offset: [0, 0, 0],        axis: 'Z' },
  { name: 'left_shoulder_pitch',  parent: 'left_shoulder_roll_carrier',child: 'left_upper_arm',              offset: [0, 0, 0],        axis: 'X' },
  { name: 'left_elbow_pitch',     parent: 'left_upper_arm',            child: 'left_elbow_carrier',          offset: [0, 0, -0.31],    axis: 'X' },
  { name: 'left_forearm_roll',    parent: 'left_elbow_carrier',        child: 'left_forearm',                offset: [0, 0, 0],        axis: 'Z' },
  { name: 'left_wrist_pitch',     parent: 'left_forearm',              child: 'left_wrist_carrier',          offset: [0, 0, -0.27],    axis: 'X' },
  { name: 'left_wrist_deviation', parent: 'left_wrist_carrier',        child: 'left_hand',                   offset: [0, 0, 0],        axis: 'Z' },
  // Right arm
  { name: 'right_shoulder_yaw',   parent: 'torso',                     child: 'right_shoulder_yaw_carrier',  offset: [0.28, 0, 0.36],  axis: 'Y' },
  { name: 'right_shoulder_roll',  parent: 'right_shoulder_yaw_carrier',child: 'right_shoulder_roll_carrier', offset: [0, 0, 0],        axis: 'Z' },
  { name: 'right_shoulder_pitch', parent: 'right_shoulder_roll_carrier',child: 'right_upper_arm',            offset: [0, 0, 0],        axis: 'X' },
  { name: 'right_elbow_pitch',    parent: 'right_upper_arm',           child: 'right_elbow_carrier',         offset: [0, 0, -0.31],    axis: 'X' },
  { name: 'right_forearm_roll',   parent: 'right_elbow_carrier',       child: 'right_forearm',               offset: [0, 0, 0],        axis: 'Z' },
  { name: 'right_wrist_pitch',    parent: 'right_forearm',             child: 'right_wrist_carrier',         offset: [0, 0, -0.27],    axis: 'X' },
  { name: 'right_wrist_deviation',parent: 'right_wrist_carrier',       child: 'right_hand',                  offset: [0, 0, 0],        axis: 'Z' },
  // Left leg
  { name: 'left_hip_yaw',         parent: 'pelvis',                    child: 'left_hip_yaw_carrier',        offset: [-0.10, 0, -0.10],axis: 'Y' },
  { name: 'left_hip_roll',        parent: 'left_hip_yaw_carrier',      child: 'left_hip_roll_carrier',       offset: [0, 0, 0],        axis: 'Z' },
  { name: 'left_hip_pitch',       parent: 'left_hip_roll_carrier',     child: 'left_thigh',                  offset: [0, 0, 0],        axis: 'X' },
  { name: 'left_knee_pitch',      parent: 'left_thigh',                child: 'left_shin',                   offset: [0, 0, -0.40],    axis: 'X' },
  { name: 'left_ankle_pitch',     parent: 'left_shin',                 child: 'left_ankle_pitch_carrier',    offset: [0, 0, -0.40],    axis: 'X' },
  { name: 'left_ankle_roll',      parent: 'left_ankle_pitch_carrier',  child: 'left_foot',                   offset: [0, 0, 0],        axis: 'Z' },
  // Right leg
  { name: 'right_hip_yaw',        parent: 'pelvis',                    child: 'right_hip_yaw_carrier',       offset: [0.10, 0, -0.10], axis: 'Y' },
  { name: 'right_hip_roll',       parent: 'right_hip_yaw_carrier',     child: 'right_hip_roll_carrier',      offset: [0, 0, 0],        axis: 'Z' },
  { name: 'right_hip_pitch',      parent: 'right_hip_roll_carrier',    child: 'right_thigh',                 offset: [0, 0, 0],        axis: 'X' },
  { name: 'right_knee_pitch',     parent: 'right_thigh',               child: 'right_shin',                  offset: [0, 0, -0.40],    axis: 'X' },
  { name: 'right_ankle_pitch',    parent: 'right_shin',                child: 'right_ankle_pitch_carrier',   offset: [0, 0, -0.40],    axis: 'X' },
  { name: 'right_ankle_roll',     parent: 'right_ankle_pitch_carrier', child: 'right_foot',                  offset: [0, 0, 0],        axis: 'Z' },
];

export const PANEL_FIELDS = [
  { id: 'tick',                  label: 'Tick' },
  { id: '__state',               label: null, section: 'Body state' },
  { id: 'alive',                 label: 'Life' },
  { id: 'metabolic_reserve',     label: 'Metabolic reserve' },
  { id: 'reserve_trend',         label: 'Reserve trend' },

  { id: '__motion',              label: null, section: 'Motion' },
  { id: 'motor_activity',        label: 'Motor activity' },
  { id: 'active_joints',         label: 'Active joints' },
  { id: 'active_effectors',      label: 'Active effectors' },
  { id: 'contact_count',         label: 'Body contacts' },
  { id: 'ground_contact_count',  label: 'Ground contacts' },
  { id: 'self_contact_count',    label: 'Self contacts' },
  { id: 'resource_contact_count', label: 'Resource contacts' },
  { id: 'distance_travelled',    label: 'Distance travelled' },
  { id: 'displacement',          label: 'Net displacement' },
  { id: 'locomotion_efficiency', label: 'Path efficiency' },

  { id: '__environment',         label: null, section: 'Environment' },
  { id: 'resource_distance',     label: 'Resource distance' },
  { id: 'resource_progress',     label: 'Resource progress' },
  { id: 'motion_effectiveness',  label: 'Approach efficiency' },

  { id: '__control',             label: null, section: 'Control context' },
  { id: 'motor_origin',          label: 'Motor origin' },
  { id: 'cognitive_context',     label: 'Cognitive detail' },
];

export const SEGMENT_ACTIVITY_JOINTS = {
  pelvis: ['trunk_yaw', 'trunk_roll', 'trunk_pitch'],
  torso: ['trunk_yaw', 'trunk_roll', 'trunk_pitch'],
  head: ['neck_yaw', 'neck_pitch'],
  left_upper_arm: ['left_shoulder_yaw', 'left_shoulder_roll', 'left_shoulder_pitch'],
  left_forearm: ['left_elbow_pitch', 'left_forearm_roll'],
  left_hand: ['left_wrist_pitch', 'left_wrist_deviation'],
  right_upper_arm: ['right_shoulder_yaw', 'right_shoulder_roll', 'right_shoulder_pitch'],
  right_forearm: ['right_elbow_pitch', 'right_forearm_roll'],
  right_hand: ['right_wrist_pitch', 'right_wrist_deviation'],
  left_thigh: ['left_hip_yaw', 'left_hip_roll', 'left_hip_pitch'],
  left_shin: ['left_knee_pitch'],
  left_foot: ['left_ankle_pitch', 'left_ankle_roll'],
  right_thigh: ['right_hip_yaw', 'right_hip_roll', 'right_hip_pitch'],
  right_shin: ['right_knee_pitch'],
  right_foot: ['right_ankle_pitch', 'right_ankle_roll'],
};


export function fallbackBodyModel() {
  return {
    bodyKind: 'anthropomorphic-v4',
    baseLink: 'pelvis',
    joints: JOINT_TOPOLOGY,
    segments: SEGMENTS,
    segmentActivityJoints: SEGMENT_ACTIVITY_JOINTS,
  };
}

export function bodyModelFromCatalog(item) {
  const raw = item?.observer_model;
  if (!raw || typeof raw !== 'object') return null;
  if (!raw.base_link || !Array.isArray(raw.joints) || !raw.segments) return null;

  const segments = {};
  for (const [name, segment] of Object.entries(raw.segments)) {
    if (
      !segment ||
      !Array.isArray(segment.size) ||
      segment.size.length !== 3 ||
      !Array.isArray(segment.origin) ||
      segment.origin.length !== 3
    ) continue;
    segments[name] = {
      wdh: segment.size.map(Number),
      offset: segment.origin.map(Number),
    };
  }

  const joints = raw.joints
    .filter((joint) => (
      joint &&
      typeof joint.name === 'string' &&
      typeof joint.parent === 'string' &&
      typeof joint.child === 'string' &&
      Array.isArray(joint.origin) &&
      joint.origin.length === 3
    ))
    .map((joint) => ({
      name: joint.name,
      parent: joint.parent,
      child: joint.child,
      offset: joint.origin.map(Number),
      axisVector: Array.isArray(joint.axis) ? joint.axis.map(Number) : [1, 0, 0],
    }));

  const segmentActivityJoints = {};
  for (const joint of joints) {
    if (segments[joint.child]) {
      (segmentActivityJoints[joint.child] ??= []).push(joint.name);
    }
  }

  return {
    bodyKind: String(item.body_kind || item.id || ''),
    baseLink: String(raw.base_link),
    joints,
    segments,
    segmentActivityJoints,
  };
}

export function dominantAxis(axisVector) {
  if (typeof axisVector === 'string' && ['X', 'Y', 'Z'].includes(axisVector)) {
    return axisVector;
  }
  const [x = 0, y = 0, z = 0] = axisVector ?? [];
  const abs = [Math.abs(x), Math.abs(y), Math.abs(z)];
  const index = abs.indexOf(Math.max(...abs));
  return index === 0 ? 'X' : index === 1 ? 'Y' : 'Z';
}
