/**
 * Observer-only Body presentation tuning.
 *
 * None of these values feed back into Physics3D or Symbiont. They only
 * control browser rendering, interpolation and camera behaviour.
 */
export const BODY_PRESENTATION = Object.freeze({
  uiUpdateIntervalMs: 66,
  maxPixelRatio: 1.5,

  interpolation: Object.freeze({
    initialDelayMs: 120,
    maxPoseFrames: 32,
    nominalDenseHz: 24,
    minBufferMs: 45,
    maxBufferMs: 220,
    producerRateMin: 0.05,
    producerRateMax: 4,
    producerSampleWindow: 12,
    producerSmoothing: 0.22,
  }),

  camera: Object.freeze({
    initialDistance: 3.2,
    boundsRefreshMs: 120,
    targetResponsiveness: 8,
    cameraResponsiveness: 6,
    minFollowDistance: 2.25,
    maxFollowDistance: 5.2,
    framingMargin: 1.28,
    minOrbitDistance: 0.7,
    maxOrbitDistance: 10,
  }),

  trajectory: Object.freeze({
    maxPoints: 220,
    minPointDistance: 0.012,
  }),
});
