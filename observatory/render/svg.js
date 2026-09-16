const NS = "http://www.w3.org/2000/svg";

const palette = { cyan: "#50d9ff", violet: "#a777ff", amber: "#ffbd54", coral: "#ff7f83", mint: "#71e9ba" };

function svg(tag, attrs = {}) {
  const node = document.createElementNS(NS, tag);
  Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
  return node;
}

function eventColor(type) { return ({ perception: palette.cyan, attention: palette.amber, revision: palette.violet, contradiction: palette.coral })[type] || palette.cyan; }

// Snapshot and replay values are untrusted input, even though the Observatory
// only accepts local/read-only transports. Keep HTML templates safe when a
// malformed or hand-edited replay contains markup.
function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>\"']/g, character => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[character]);
}

export { NS, palette, svg, eventColor, escapeHtml };
