from __future__ import annotations

import argparse
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Lock, Thread
import time
from typing import Any

from .simulation import SimulationSnapshot, run_simulation


class DashboardState:
    def __init__(self,max_points:int=600)->None: self._lock=Lock(); self._history:deque[dict[str,Any]]=deque(maxlen=max_points); self.running=False; self.finished=False; self.error:str|None=None; self.config:dict[str,Any]={}
    def start(self,config:dict[str,Any])->None:
        with self._lock: self._history.clear(); self.running=True; self.finished=False; self.error=None; self.config=config
    def add(self,snapshot:SimulationSnapshot)->None:
        with self._lock: self._history.append(snapshot.as_dict())
    def finish(self)->None:
        with self._lock: self.running=False; self.finished=True
    def fail(self,exc:Exception)->None:
        with self._lock: self.running=False; self.finished=True; self.error=f"{type(exc).__name__}: {exc}"
    def payload(self)->dict[str,Any]:
        with self._lock:
            history=list(self._history); return {"running":self.running,"finished":self.finished,"error":self.error,"config":dict(self.config),"current":history[-1] if history else None,"history":history}


HTML=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Symbiont Lab — Experimental Curiosity</title><style>:root{color-scheme:dark;--bg:#0b0f14;--panel:#131a22;--line:#263241;--text:#eaf1f8;--muted:#8fa3b8;--accent:#76d7b0;--warn:#f7c873}*{box-sizing:border-box}body{margin:0;font:14px/1.45 system-ui,sans-serif;background:var(--bg);color:var(--text)}main{max-width:1320px;margin:auto;padding:24px}.top{display:flex;justify-content:space-between;gap:20px;align-items:end;margin-bottom:18px}h1{font-size:24px;margin:0}.sub,.small{color:var(--muted)}.badge,.pill{border:1px solid var(--line);border-radius:99px;padding:4px 8px;color:var(--accent)}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.card,.chart,.section{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px}.label{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.08em}.value{font-size:26px;font-weight:700;margin-top:5px}.charts{display:grid;grid-template-columns:2fr 1fr;gap:12px;margin-top:12px}.chart canvas{width:100%;height:260px;display:block}.section{margin-top:12px}.split{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}.item{border-top:1px solid var(--line);padding:10px 0}.item:first-of-type{border-top:0}.question{color:var(--muted);margin-top:5px}@media(max-width:850px){.grid{grid-template-columns:repeat(2,1fr)}.charts,.split{grid-template-columns:1fr}.top{align-items:start;flex-direction:column}}</style></head><body><main><div class="top"><div><h1>Symbiont Lab</h1><div class="sub">v0.7 experimental curiosity — shadow-only counterfactual agenda</div></div><div id="status" class="badge">connecting…</div></div><div class="grid"><div class="card"><div class="label">Progress</div><div id="progress" class="value">0%</div></div><div class="card"><div class="label">Curiosity focus</div><div id="focus" class="value">—</div><div class="small">top probe utility</div></div><div class="card"><div class="label">Open questions</div><div id="openq" class="value">0</div></div><div class="card"><div class="label">Epistemic pressure</div><div id="epi" class="value">—</div></div><div class="card"><div class="label">Self confidence</div><div id="conf" class="value">—</div></div><div class="card"><div class="label">Mean novelty</div><div id="novelty" class="value">—</div></div><div class="card"><div class="label">Recent drift FP</div><div id="driftfp" class="value">—</div></div><div class="card"><div class="label">Detection</div><div id="detection" class="value">—</div></div></div><div class="charts"><div class="chart"><div class="label">Cognitive dynamics</div><canvas id="rates"></canvas></div><div class="chart"><div class="label">Species state</div><canvas id="species"></canvas></div></div><div class="split"><div class="section"><div class="label">Curiosity agenda</div><div id="probes" class="small">No probe selected.</div></div><div class="section"><div class="label">Bounded hypotheses</div><div id="hypotheses" class="small">No unresolved hypothesis.</div></div></div></main><script>const $=id=>document.getElementById(id),pct=v=>(100*v).toFixed(1)+'%';function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}function lineChart(canvas,series){const dpr=devicePixelRatio||1,w=canvas.clientWidth,h=canvas.clientHeight;canvas.width=w*dpr;canvas.height=h*dpr;const c=canvas.getContext('2d');c.scale(dpr,dpr);c.clearRect(0,0,w,h);c.strokeStyle='#263241';for(let i=0;i<=4;i++){let y=20+(h-40)*i/4;c.beginPath();c.moveTo(30,y);c.lineTo(w-10,y);c.stroke()}series.forEach((s,si)=>{if(s.length<2)return;c.strokeStyle=['#76d7b0','#73a9ff','#f7c873','#d896ff'][si];c.lineWidth=2;c.beginPath();s.forEach((v,i)=>{let x=30+(w-40)*i/(s.length-1),y=20+(h-40)*(1-Math.max(0,Math.min(1,v)));i?c.lineTo(x,y):c.moveTo(x,y)});c.stroke()})}function barChart(canvas,items){const dpr=devicePixelRatio||1,w=canvas.clientWidth,h=canvas.clientHeight;canvas.width=w*dpr;canvas.height=h*dpr;const c=canvas.getContext('2d');c.scale(dpr,dpr);c.clearRect(0,0,w,h);let max=Math.max(1,...items.map(x=>x[1]));items.forEach((it,i)=>{let y=28+i*48;c.fillStyle='#8fa3b8';c.fillText(it[0],12,y);c.fillStyle='#263241';c.fillRect(12,y+9,w-24,16);c.fillStyle='#76d7b0';c.fillRect(12,y+9,(w-24)*it[1]/max,16);c.fillStyle='#eaf1f8';c.fillText(String(it[1]),16,y+22)})}function renderProbes(items){$('probes').innerHTML=items&&items.length?items.map(p=>`<div class="item"><b>${esc(p.feature)} ${esc(p.change)}</b> <span class="pill">utility ${Number(p.utility).toFixed(2)}</span><div class="small">EIG ${Number(p.expected_information_gain).toFixed(2)} · cost ${Number(p.expected_cost).toFixed(2)} · ${esc(p.counterfactual_fingerprint)}</div><div class="question">? ${esc(p.question)}</div></div>`).join(''):'No probe selected.'}function renderHyp(items){$('hypotheses').innerHTML=items&&items.length?items.map(h=>`<div class="item"><b>${esc(h.title)}</b> <span class="pill">${Number(h.priority).toFixed(2)}</span><div class="small">${esc(h.rationale)}</div></div>`).join(''):'No unresolved hypothesis.'}async function refresh(){try{const r=await fetch('/api/state',{cache:'no-store'}),d=await r.json(),c=d.current;$('status').textContent=d.error?'error':d.running?'running':d.finished?'finished':'ready';if(!c)return;$('progress').textContent=pct(c.step/c.total_steps);$('focus').textContent=c.curiosity_focus.toFixed(2);$('openq').textContent=c.open_questions;$('epi').textContent=pct(c.epistemic_pressure);$('conf').textContent=pct(c.self_confidence);$('novelty').textContent=pct(c.mean_novelty);$('driftfp').textContent=pct(c.recent_drift_false_positive_rate);$('detection').textContent=pct(c.detection_rate);renderProbes(c.curiosity_probes);renderHyp(c.reasoning_hypotheses);lineChart($('rates'),[d.history.map(x=>x.curiosity_focus),d.history.map(x=>x.epistemic_pressure),d.history.map(x=>x.mean_novelty),d.history.map(x=>x.self_confidence)]);barChart($('species'),[['patterns',c.collective_patterns],['questions',c.open_questions],['probes',c.curiosity_probes.length],['adaptations',c.drift_adaptations],['memories',c.consolidated_episodes]])}catch(e){$('status').textContent='disconnected'}}setInterval(refresh,350);refresh();addEventListener('resize',refresh);</script></body></html>'''


def make_handler(state:DashboardState)->type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self)->None:
            if self.path=="/api/state": body=json.dumps(state.payload()).encode(); self.send_response(200); self.send_header("Content-Type","application/json")
            elif self.path in ("/","/index.html"): body=HTML.encode(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8")
            else: body=b"not found"; self.send_response(404); self.send_header("Content-Type","text/plain")
            self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
        def log_message(self,format:str,*args:object)->None:return
    return Handler


def run_experiment(state:DashboardState,*,hosts:int,steps:int,seed:int,threat_rate:float,poison_fraction:float,heterogeneity:float,drift_step:int|None,drift_fraction:float,drift_magnitude:float,delay:float)->None:
    state.start({"hosts":hosts,"steps":steps,"seed":seed,"threat_rate":threat_rate,"poison_fraction":poison_fraction,"heterogeneity":heterogeneity,"drift_step":drift_step,"drift_fraction":drift_fraction,"drift_magnitude":drift_magnitude})
    def publish(snapshot:SimulationSnapshot)->None:
        state.add(snapshot)
        if delay>0: time.sleep(delay)
    try: run_simulation(hosts,steps,seed,threat_rate,poison_fraction,heterogeneity,drift_step,drift_fraction,drift_magnitude,on_snapshot=publish); state.finish()
    except Exception as exc: state.fail(exc)


def main()->None:
    p=argparse.ArgumentParser(description="Visualize a Symbiont Lab experiment live"); p.add_argument("--hosts",type=int,default=100); p.add_argument("--steps",type=int,default=300); p.add_argument("--seed",type=int,default=7); p.add_argument("--threat-rate",type=float,default=0.018); p.add_argument("--poison-fraction",type=float,default=0.08); p.add_argument("--heterogeneity",type=float,default=0.12); p.add_argument("--drift-step",type=int,default=-1); p.add_argument("--drift-fraction",type=float,default=0.35); p.add_argument("--drift-magnitude",type=float,default=0.22); p.add_argument("--delay",type=float,default=0.04); p.add_argument("--port",type=int,default=8765); a=p.parse_args(); drift=None if a.drift_step<0 else a.drift_step; state=DashboardState(); Thread(target=run_experiment,kwargs={"state":state,"hosts":a.hosts,"steps":a.steps,"seed":a.seed,"threat_rate":a.threat_rate,"poison_fraction":a.poison_fraction,"heterogeneity":a.heterogeneity,"drift_step":drift,"drift_fraction":a.drift_fraction,"drift_magnitude":a.drift_magnitude,"delay":max(a.delay,0.0)},daemon=True).start(); server=ThreadingHTTPServer(("127.0.0.1",a.port),make_handler(state)); print(f"Symbiont Lab live dashboard: http://127.0.0.1:{a.port}"); print("Press Ctrl+C to stop the dashboard.")
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()


if __name__=="__main__":main()
