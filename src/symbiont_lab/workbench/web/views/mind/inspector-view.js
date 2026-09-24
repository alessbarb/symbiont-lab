import { el } from '../shared/dom.js';

export function appendInspectorLine(parent, segments, className = 'mind-inspector-line') {
  const row = el('div', className);
  for (const segment of segments) {
    if (typeof segment === 'string' || typeof segment === 'number') {
      row.appendChild(document.createTextNode(String(segment)));
      continue;
    }
    const node = el(segment.strong ? 'strong' : 'span', segment.className ?? '');
    node.textContent = String(segment.text ?? '');
    if (segment.tone) node.style.color = segment.tone;
    row.appendChild(node);
  }
  parent.appendChild(row);
  return row;
}

export function appendInspectorStage(parent, { label, active = 0, total = 0 }) {
  const ratio = total ? Math.min(1, active / total) : 0;
  const row = el('div', 'mind-inspector-stage');

  const name = el('span', 'mind-inspector-stage-label');
  name.textContent = String(label ?? '');

  const meter = el('span', 'mind-inspector-stage-meter');
  const fill = el('i', 'mind-inspector-stage-fill');
  fill.style.width = `${Math.round(ratio * 100)}%`;
  meter.appendChild(fill);

  const count = el('span', 'mind-inspector-stage-count');
  count.textContent = `${active}/${total}`;

  row.append(name, meter, count);
  parent.appendChild(row);
  return row;
}

export function replaceInspectorSummary(panel, lines) {
  panel.replaceChildren();
  lines.forEach((segments, index) => {
    appendInspectorLine(
      panel,
      segments,
      index === 0 ? 'mind-cognition-summary-title' : 'mind-cognition-summary-line',
    );
  });
}
