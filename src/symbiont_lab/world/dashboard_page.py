"""HTML page for the World dashboard: a single <pre> block that polls
/api/state and replaces its text. No form, no button, no POST -- there is
nothing on this page that can send a WorldAction (docs/design/
symbiont-world-v2.md §8)."""

HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Symbiont World</title>
<style>
:root{color-scheme:dark;--bg:#0b0f14;--panel:#131a22;--line:#263241;--text:#eaf1f8;--muted:#8fa3b8;--accent:#76d7b0;--bad:#ff8b8b}
*{box-sizing:border-box}body{margin:0;font:14px/1.45 system-ui,sans-serif;background:var(--bg);color:var(--text)}
main{max-width:1200px;margin:auto;padding:24px}
.top{display:flex;justify-content:space-between;gap:20px;align-items:baseline;margin-bottom:14px}
h1{margin:0}.sub{color:var(--muted)}.badge{border:1px solid var(--line);border-radius:99px;padding:5px 9px;color:var(--accent)}
.badge.bad{color:var(--bad)}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:16px}
svg{display:block;width:100%;height:auto}
.hexcell{fill:#0f151d;stroke:var(--line);stroke-width:1}
.hexorg{stroke:#0b0f14;stroke-width:1.5}
.hexlabel{fill:var(--text);font-size:9px;font-family:system-ui,sans-serif;text-anchor:middle;pointer-events:none}
.legend{display:flex;gap:14px;flex-wrap:wrap;margin-top:10px;color:var(--muted);font-size:12px}
.legend .swatch{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:middle}
.fields{display:flex;gap:16px;flex-wrap:wrap;color:var(--muted);font-size:12px;margin-top:10px}
pre{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px;overflow:auto;white-space:pre-wrap;max-height:420px}
details summary{cursor:pointer;color:var(--muted)}
</style>
</head>
<body><main>
<div class="top">
  <div><h1>Symbiont World</h1><div class="sub">read-only — no control on this page can act on the world</div></div>
  <div id="status" class="badge">connecting…</div>
</div>

<div class="panel">
  <svg id="grid" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet"></svg>
  <div class="legend" id="legend"></div>
  <div class="fields" id="fields"></div>
</div>

<details class="panel">
  <summary>Raw text view</summary>
  <pre id="view">loading…</pre>
</details>

<script>
const SVG_NS = 'http://www.w3.org/2000/svg';
const HEX_SIZE = 30;
const regionColor = {};
const PALETTE = ['#76d7b0', '#f7c873', '#8fb8ff', '#ff8b8b', '#c792ea', '#7fd7e0'];

function colorFor(key) {
  if (!(key in regionColor)) {
    regionColor[key] = PALETTE[Object.keys(regionColor).length % PALETTE.length];
  }
  return regionColor[key];
}

function axialToPixel(q, r) {
  const x = HEX_SIZE * Math.sqrt(3) * (q + r / 2);
  const y = HEX_SIZE * 1.5 * r;
  return [x, y];
}

function hexPoints(cx, cy) {
  const pts = [];
  for (let i = 0; i < 6; i++) {
    const angle = Math.PI / 180 * (60 * i - 30);
    pts.push((cx + HEX_SIZE * Math.cos(angle)).toFixed(1) + ',' + (cy + HEX_SIZE * Math.sin(angle)).toFixed(1));
  }
  return pts.join(' ');
}

function renderGrid(data) {
  const svg = document.getElementById('grid');
  svg.innerHTML = '';
  const width = data.width, height = data.height;

  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (let q = 0; q < width; q++) {
    for (let r = 0; r < height; r++) {
      const [x, y] = axialToPixel(q, r);
      minX = Math.min(minX, x - HEX_SIZE); maxX = Math.max(maxX, x + HEX_SIZE);
      minY = Math.min(minY, y - HEX_SIZE); maxY = Math.max(maxY, y + HEX_SIZE);
    }
  }
  svg.setAttribute('viewBox', `${minX - 10} ${minY - 10} ${maxX - minX + 20} ${maxY - minY + 20}`);

  for (let q = 0; q < width; q++) {
    for (let r = 0; r < height; r++) {
      const [x, y] = axialToPixel(q, r);
      const poly = document.createElementNS(SVG_NS, 'polygon');
      poly.setAttribute('points', hexPoints(x, y));
      poly.setAttribute('class', 'hexcell');
      svg.appendChild(poly);
    }
  }

  const byCell = {};
  for (const org of data.organisms) byCell[org.q + ',' + org.r] = org;

  for (const org of data.organisms) {
    const [x, y] = axialToPixel(org.q, org.r);
    const poly = document.createElementNS(SVG_NS, 'polygon');
    poly.setAttribute('points', hexPoints(x, y));
    poly.setAttribute('class', 'hexorg');
    poly.setAttribute('fill', colorFor(org.region || 'default'));
    const cellData = data.cells[org.q + ',' + org.r] || {};
    const title = document.createElementNS(SVG_NS, 'title');
    const resourceLines = Object.entries(cellData.resources || {}).map(([k, v]) => k + ': ' + v.toFixed(2));
    const hazardLines = Object.entries(cellData.hazards || {}).map(([k, v]) => k + ': ' + v.toFixed(3));
    title.textContent = [org.id, '(' + org.q + ',' + org.r + ')', ...resourceLines, ...hazardLines].join('\n');
    poly.appendChild(title);
    svg.appendChild(poly);

    const label = document.createElementNS(SVG_NS, 'text');
    label.setAttribute('x', x);
    label.setAttribute('y', y + 3);
    label.setAttribute('class', 'hexlabel');
    label.textContent = org.id.replace(/^founder-/, '#');
    svg.appendChild(label);
  }

  const legend = document.getElementById('legend');
  legend.innerHTML = Object.keys(regionColor).length
    ? Object.entries(regionColor).map(([region, color]) =>
        `<span><span class="swatch" style="background:${color}"></span>${region}</span>`).join('')
    : '';

  const fields = document.getElementById('fields');
  fields.innerHTML = Object.entries(data.fields || {}).map(([name, value]) =>
    `<span>${name} = ${value.toFixed(3)}</span>`).join('');
}

async function poll() {
  try {
    const res = await fetch('/api/state');
    const data = await res.json();
    document.getElementById('view').textContent = data.text;
    renderGrid(data);
    const status = document.getElementById('status');
    if (data.error) {
      status.textContent = 'error: ' + data.error;
      status.className = 'badge bad';
    } else {
      status.textContent = (data.running ? 'running' : 'stopped') + ' — tick ' + data.tick + ' — ' + data.alive_count + ' alive';
      status.className = 'badge';
    }
  } catch (e) {
    document.getElementById('status').textContent = 'disconnected';
  }
  setTimeout(poll, 1000);
}
poll();
</script>
</main></body>
</html>
'''
