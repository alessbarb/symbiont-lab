export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[char]));
}

export function el(tag, className = '', styles = {}) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  Object.assign(node.style, styles);
  return node;
}

export function textEl(tag, text = '', className = '') {
  const node = document.createElement(tag);
  if (className) node.className = className;
  node.textContent = String(text ?? '');
  return node;
}

export function clearNode(node) {
  node?.replaceChildren();
  return node;
}

export function appendText(parent, tag, text, className = '') {
  const node = textEl(tag, text, className);
  parent.appendChild(node);
  return node;
}

export function setPressed(node, active) {
  node.setAttribute('aria-pressed', String(Boolean(active)));
  node.classList.toggle('active', Boolean(active));
}

export function setCurrent(node, current) {
  if (current) node.setAttribute('aria-current', String(current));
  else node.removeAttribute('aria-current');
}

export function svgEl(tag, attrs = {}) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value != null) node.setAttribute(key, String(value));
  }
  return node;
}
