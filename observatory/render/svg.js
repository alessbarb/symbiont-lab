const NS = "http://www.w3.org/2000/svg";

const palette = { cyan: "#50d9ff", violet: "#a777ff", amber: "#ffbd54", coral: "#ff7f83", mint: "#71e9ba" };

function svg(tag, attrs = {}) {
  const node = document.createElementNS(NS, tag);
  Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
  return node;
}

function eventColor(type) { return ({ perception: palette.cyan, attention: palette.amber, revision: palette.violet, contradiction: palette.coral })[type] || palette.cyan; }

export { NS, palette, svg, eventColor };
