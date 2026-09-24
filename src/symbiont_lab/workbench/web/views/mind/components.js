import { el } from '../shared/dom.js';

export function panelSection(title, subtitle = '') {
  const section = el('section', 'mind-panel-section');
  const heading = el('h3', 'mind-panel-section-title');
  heading.textContent = title;
  section.appendChild(heading);

  if (subtitle) {
    const copy = el('p', 'mind-panel-section-copy');
    copy.textContent = subtitle;
    section.appendChild(copy);
  }
  return section;
}

export function bigMetric(label, value, tone = null) {
  const wrap = el('div', 'mind-big-metric');
  const labelNode = el('div', 'mind-big-metric-label');
  labelNode.textContent = label;

  const valueNode = el('strong', 'mind-big-metric-value');
  if (tone) valueNode.style.color = tone;
  valueNode.textContent = String(value);

  wrap.append(labelNode, valueNode);
  return wrap;
}

export function inspectorMetric(parent, label, value, color = null) {
  const row = el('div', 'mind-inspector-metric');
  const key = el('span', 'mind-inspector-metric-key');
  key.textContent = label;

  const val = el('strong', 'mind-inspector-metric-value');
  if (color) val.style.color = color;
  val.textContent = String(value);

  row.append(key, val);
  parent.appendChild(row);
}
