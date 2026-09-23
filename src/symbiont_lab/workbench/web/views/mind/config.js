export const PAL = {
  cyan:   '#50d9ff',
  violet: '#a777ff',
  amber:  '#ffbd54',
  coral:  '#ff7f83',
  mint:   '#71e9ba',
  muted:  '#627888',
  text:   '#c8d8e4',
  bg:     '#060e18',
  surface:'#0b1929',
  line:   '#1a2d40',
};

// Observer-defined reference zones. Analytical overlays only.
export const REGIMES = [
  { id: 'low_activity',        name: 'Baja actividad',        x: -160, y:  130, color: PAL.cyan,  radius: 95,  description: 'Observer projection: low measured activity and low predictive tension.' },
  { id: 'sustained_activity',  name: 'Actividad sostenida',   x:  170, y:  110, color: PAL.mint,  radius: 100, description: 'Observer projection: sustained activity with comparatively low predictive tension.' },
  { id: 'transient_activity',  name: 'Actividad transitoria', x:  -40, y:  -50, color: PAL.amber, radius: 90,  description: 'Observer projection: intermediate activity with elevated short-term predictive tension.' },
  { id: 'high_tension',        name: 'Tensión elevada',       x:  180, y: -170, color: PAL.coral, radius: 95,  description: 'Observer projection: high activity and/or predictive tension.' },
];

export const GRAPH_PHYSICS = Object.freeze({
  repulsion: 7500,
  springK: 0.045,
  springLength: 80,
  centerGravity: 0.015,
  damping: 0.86,
  alphaDecay: 0.985,
  alphaMin: 0.001,
});
