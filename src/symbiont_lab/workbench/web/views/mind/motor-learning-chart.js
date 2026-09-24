import { el } from '../shared/dom.js';
import { PAL } from './config.js';

function finite(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function svgNode(name, attrs = {}) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', name);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, String(value));
  return node;
}

export function motorSparkline({ label, history, key, epochEvents = [] }) {
  const wrap = el('div', '');
  wrap.style.cssText = 'padding:10px 0 4px;';

  const title = el('div', '');
  title.style.cssText = 'font-size:9px;letter-spacing:.045em;color:var(--muted);margin-bottom:6px;text-transform:uppercase;';
  title.textContent = label;
  wrap.appendChild(title);

  const points = history
    .map(item => ({ tick: finite(item.tick), value: finite(item[key]) }))
    .filter(item => item.tick != null && item.value != null);

  if (points.length < 2) {
    const empty = el('div', '');
    empty.style.cssText = 'height:54px;display:flex;align-items:center;color:var(--muted);font-size:9px;border-top:1px solid rgba(98,120,136,.12);';
    empty.textContent = 'Insufficient temporal evidence';
    wrap.appendChild(empty);
    return wrap;
  }

  const width = 800;
  const height = 72;
  const pad = 8;
  const minTick = points[0].tick;
  const maxTick = Math.max(minTick + 1, points.at(-1).tick);
  const values = points.map(item => item.value);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const span = Math.max(1e-9, maxValue - minValue);

  const x = tick => pad + ((tick - minTick) / (maxTick - minTick)) * (width - pad * 2);
  const y = value => height - pad - ((value - minValue) / span) * (height - pad * 2);

  const svg = svgNode('svg', {
    viewBox: `0 0 ${width} ${height}`,
    preserveAspectRatio: 'none',
    role: 'img',
    'aria-label': `${label} over organism ticks`,
  });
  svg.style.cssText = 'display:block;width:100%;height:72px;overflow:visible;';

  svg.appendChild(svgNode('line', {
    x1: pad, y1: height - pad, x2: width - pad, y2: height - pad,
    stroke: 'rgba(98,120,136,.18)', 'stroke-width': 1,
  }));

  for (const event of epochEvents) {
    const tick = finite(event.tick);
    if (tick == null || tick < minTick || tick > maxTick) continue;
    const px = x(tick);
    svg.appendChild(svgNode('line', {
      x1: px, y1: 2, x2: px, y2: height - 2,
      stroke: 'rgba(113,233,186,.28)', 'stroke-width': 1, 'stroke-dasharray': '3 3',
    }));
    const labelNode = svgNode('text', {
      x: Math.min(width - 24, px + 3), y: 10, fill: 'rgba(143,164,179,.9)', 'font-size': 8,
    });
    labelNode.textContent = `E${event.toEpoch}`;
    svg.appendChild(labelNode);
  }

  const path = points.map((item, index) =>
    `${index === 0 ? 'M' : 'L'} ${x(item.tick).toFixed(2)} ${y(item.value).toFixed(2)}`
  ).join(' ');
  svg.appendChild(svgNode('path', {
    d: path,
    fill: 'none',
    stroke: PAL.mint,
    'stroke-width': 1.6,
    'vector-effect': 'non-scaling-stroke',
  }));

  wrap.appendChild(svg);
  return wrap;
}

export function embodimentTimeline({ epochs, currentEpoch }) {
  const wrap = el('div', '');
  wrap.style.cssText = 'display:flex;gap:5px;align-items:stretch;margin:8px 0 10px;min-height:36px;';
  if (!epochs.length) {
    const empty = el('div', '');
    empty.style.cssText = 'font-size:9px;color:var(--muted);';
    empty.textContent = 'No embodiment timeline recorded in this observation session yet.';
    wrap.appendChild(empty);
    return wrap;
  }

  const total = Math.max(1, epochs.reduce((sum, item) => sum + Math.max(1, item.endTick - item.startTick), 0));
  for (const epoch of epochs) {
    const age = Math.max(1, epoch.endTick - epoch.startTick);
    const segment = el('div', '');
    segment.style.cssText = `flex:${Math.max(.08, age / total)} 1 0;min-width:46px;padding:7px 8px;border:1px solid ${epoch.epoch === currentEpoch ? 'rgba(113,233,186,.36)' : 'rgba(98,120,136,.16)'};border-radius:7px;background:${epoch.epoch === currentEpoch ? 'rgba(113,233,186,.035)' : 'rgba(255,255,255,.01)'};`;
    const name = el('strong', '');
    name.style.cssText = 'display:block;font-size:9px;color:var(--text);';
    name.textContent = `E${epoch.epoch}`;
    const ticks = el('span', '');
    ticks.style.cssText = 'display:block;margin-top:4px;font-size:8px;color:var(--muted);';
    ticks.textContent = `t${epoch.startTick.toLocaleString()}–${epoch.endTick.toLocaleString()}`;
    segment.append(name, ticks);
    wrap.appendChild(segment);
  }
  return wrap;
}
