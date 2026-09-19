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
main{max-width:1100px;margin:auto;padding:24px}
.top{display:flex;justify-content:space-between;gap:20px;align-items:baseline;margin-bottom:14px}
h1{margin:0}.sub{color:var(--muted)}.badge{border:1px solid var(--line);border-radius:99px;padding:5px 9px;color:var(--accent)}
.badge.bad{color:var(--bad)}
pre{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px;overflow:auto;white-space:pre-wrap}
</style>
</head>
<body><main>
<div class="top">
  <div><h1>Symbiont World</h1><div class="sub">read-only — no control on this page can act on the world</div></div>
  <div id="status" class="badge">connecting…</div>
</div>
<pre id="view">loading…</pre>
<script>
async function poll() {
  try {
    const res = await fetch('/api/state');
    const data = await res.json();
    document.getElementById('view').textContent = data.text;
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
