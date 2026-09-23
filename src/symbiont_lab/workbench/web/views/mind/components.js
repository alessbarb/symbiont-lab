import { el } from '../shared/dom.js';

export function panelSection(title, subtitle = '') {
  const section = el('section', '');
  section.style.cssText = 'border:1px solid var(--line);border-radius:10px;background:rgba(8,21,34,.72);padding:13px 14px;min-width:0;';
  const heading = el('h3', '');
  heading.style.cssText = 'font-size:12px;margin:0;color:var(--text);';
  heading.textContent = title;
  section.appendChild(heading);
  if (subtitle) {
    const copy = el('p', '');
    copy.style.cssText = 'margin:3px 0 10px;font-size:9px;line-height:1.4;color:var(--muted);';
    copy.textContent = subtitle;
    section.appendChild(copy);
  }
  return section;
}

export function bigMetric(label, value, tone = null) {
  const wrap = el('div', '');
  wrap.style.cssText = 'padding:9px 10px;border:1px solid rgba(98,120,136,.16);border-radius:8px;background:rgba(255,255,255,.015);';
  const labelNode = el('div', '');
  labelNode.style.cssText = 'font-size:8px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);';
  labelNode.textContent = label;
  const valueNode = el('strong', '');
  valueNode.style.cssText = 'display:block;margin-top:3px;font-size:18px;line-height:1;color:var(--text);';
  if (tone) valueNode.style.color = tone;
  valueNode.textContent = String(value);
  wrap.append(labelNode, valueNode);
  return wrap;
}

export function inspectorMetric(parent, label, value, color = null) {
  const row = el('div', '');
  row.style.cssText = 'display:grid;grid-template-columns:1fr auto;gap:8px;padding:5px 0;border-bottom:1px solid rgba(98,120,136,.12);font-size:9px;';
  const key = el('span', '');
  key.style.color = 'var(--muted)';
  key.textContent = label;
  const val = el('strong', '');
  val.style.cssText = 'font-size:9px;text-align:right;overflow-wrap:anywhere;';
  if (color) val.style.color = color;
  val.textContent = String(value);
  row.append(key, val);
  parent.appendChild(row);
}
