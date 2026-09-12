from __future__ import annotations

import argparse
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Lock, Thread
import time
from typing import Any, Callable

from .archive import ExperimentArchive, ExperimentRecord
from .experiment import ExperimentSpec, spec_from_payload
from .interpretation import StudyInterpretation, interpret_study
from .simulation import SimulationSnapshot, run_simulation
from .study import COMPARABLE_PARAMETERS, METRICS, StudyResult, run_comparative_study
from .study_archive import StudyArchive, StudyRecord


class DashboardState:
    def __init__(self, max_points: int = 600, archive: ExperimentArchive | None = None) -> None:
        self._lock = Lock()
        self._history: deque[dict[str, Any]] = deque(maxlen=max_points)
        self.running = False
        self.finished = False
        self.error: str | None = None
        self.archive_error: str | None = None
        self.experiment_number = 0
        self.spec = ExperimentSpec()
        self.archive = archive
        self.records: list[ExperimentRecord] = archive.recent(20) if archive else []

    def start(self, spec: ExperimentSpec | dict[str, Any]) -> bool:
        normalized = spec if isinstance(spec, ExperimentSpec) else spec_from_payload(spec, self.spec)
        with self._lock:
            if self.running:
                return False
            self._history.clear()
            self.running = True
            self.finished = False
            self.error = None
            self.archive_error = None
            self.spec = normalized
            self.experiment_number += 1
            return True

    def add(self, snapshot: SimulationSnapshot) -> None:
        with self._lock:
            self._history.append(snapshot.as_dict())

    def finish(self, record: ExperimentRecord | None = None) -> None:
        with self._lock:
            self.running = False
            self.finished = True
            if record is not None:
                self.records.insert(0, record)
                del self.records[20:]

    def fail(self, exc: Exception) -> None:
        with self._lock:
            self.running = False
            self.finished = True
            self.error = f"{type(exc).__name__}: {exc}"

    def archive_failed(self, exc: Exception) -> None:
        with self._lock:
            self.archive_error = f"{type(exc).__name__}: {exc}"

    def payload(self) -> dict[str, Any]:
        with self._lock:
            history = list(self._history)
            return {
                "running": self.running,
                "finished": self.finished,
                "error": self.error,
                "archive_error": self.archive_error,
                "experiment_number": self.experiment_number,
                "spec": self.spec.as_dict(),
                "current": history[-1] if history else None,
                "history": history,
                "records": [record.as_dict() for record in self.records],
            }


class StudyDashboardState:
    def __init__(self, archive: StudyArchive | None = None) -> None:
        self._lock = Lock()
        self.running = False
        self.error: str | None = None
        self.archive_error: str | None = None
        self.completed = 0
        self.total = 0
        self.phase = "idle"
        self.seed: int | None = None
        self.config: dict[str, Any] = {}
        self.result: dict[str, object] | None = None
        self.interpretation: dict[str, object] | None = None
        self.archive = archive
        self.record_id: str | None = None
        self.records: list[StudyRecord] = archive.recent(20) if archive else []

    def start(self, config: dict[str, Any], total: int) -> bool:
        with self._lock:
            if self.running:
                return False
            self.running = True
            self.error = None
            self.archive_error = None
            self.completed = 0
            self.total = total
            self.phase = "queued"
            self.seed = None
            self.config = config
            self.result = None
            self.interpretation = None
            self.record_id = None
            return True

    def progress(self, completed: int, total: int, phase: str, seed: int) -> None:
        with self._lock:
            self.completed = completed
            self.total = total
            self.phase = phase
            self.seed = seed

    def finish(
        self,
        result: StudyResult,
        interpretation: StudyInterpretation | None = None,
        record: StudyRecord | None = None,
    ) -> None:
        if interpretation is None:
            interpretation = interpret_study(result)
        with self._lock:
            self.running = False
            self.phase = "finished"
            self.result = result.as_dict()
            self.interpretation = interpretation.as_dict()
            if record is not None:
                self.record_id = record.record_id
                self.records.insert(0, record)
                del self.records[20:]

    def fail(self, exc: Exception) -> None:
        with self._lock:
            self.running = False
            self.phase = "error"
            self.error = f"{type(exc).__name__}: {exc}"

    def archive_failed(self, exc: Exception) -> None:
        with self._lock:
            self.archive_error = f"{type(exc).__name__}: {exc}"

    def payload(self) -> dict[str, Any]:
        with self._lock:
            return {
                "running": self.running,
                "error": self.error,
                "archive_error": self.archive_error,
                "completed": self.completed,
                "total": self.total,
                "phase": self.phase,
                "seed": self.seed,
                "config": dict(self.config),
                "result": self.result,
                "interpretation": self.interpretation,
                "record_id": self.record_id,
                "records": [record.as_dict() for record in self.records],
            }


def run_experiment(state: DashboardState, spec: ExperimentSpec) -> None:
    def publish(snapshot: SimulationSnapshot) -> None:
        state.add(snapshot)
        if spec.delay > 0:
            time.sleep(spec.delay)

    try:
        result, _ = run_simulation(
            spec.hosts,
            spec.steps,
            spec.seed,
            spec.threat_rate,
            spec.poison_fraction,
            spec.heterogeneity,
            spec.drift_step,
            spec.drift_fraction,
            spec.drift_magnitude,
            on_snapshot=publish,
        )
        record = None
        if state.archive is not None:
            try:
                record = state.archive.append(spec, result, source="dashboard")
            except OSError as exc:
                state.archive_failed(exc)
        state.finish(record)
    except Exception as exc:
        state.fail(exc)


def start_experiment(
    state: DashboardState,
    study_state: StudyDashboardState,
    spec: ExperimentSpec,
) -> bool:
    if study_state.running or not state.start(spec):
        return False
    Thread(target=run_experiment, args=(state, spec), daemon=True).start()
    return True


def _parse_seeds(raw: object) -> tuple[int, ...]:
    parts = raw if isinstance(raw, list) else str(raw or "").split(",")
    seeds = tuple(int(str(part).strip()) for part in parts if str(part).strip())
    if not seeds:
        raise ValueError("study requires at least one seed")
    if len(seeds) > 50:
        raise ValueError("dashboard studies are limited to 50 seeds")
    return seeds


def run_study_dashboard(
    state: StudyDashboardState,
    base_spec: ExperimentSpec,
    *,
    title: str,
    parameter: str,
    baseline: float,
    variant: float,
    seeds: tuple[int, ...],
    parent_record_id: str | None = None,
) -> None:
    try:
        result = run_comparative_study(
            base_spec,
            parameter=parameter,
            baseline_value=baseline,
            variant_value=variant,
            seeds=seeds,
            title=title,
            on_progress=state.progress,
        )
        interpretation = interpret_study(result)
        record = None
        if state.archive is not None:
            try:
                record = state.archive.append(
                    base_spec,
                    result,
                    interpretation,
                    source="dashboard",
                    parent_record_id=parent_record_id,
                )
            except OSError as exc:
                state.archive_failed(exc)
        state.finish(result, interpretation, record)
    except Exception as exc:
        state.fail(exc)


def start_study(
    experiment_state: DashboardState,
    state: StudyDashboardState,
    base_spec: ExperimentSpec,
    *,
    title: str,
    parameter: str,
    baseline: float,
    variant: float,
    seeds: tuple[int, ...],
    parent_record_id: str | None = None,
) -> bool:
    if experiment_state.running:
        return False
    config = {
        "title": title,
        "parameter": parameter,
        "baseline": baseline,
        "variant": variant,
        "seeds": seeds,
        "base_spec": base_spec.as_dict(),
        "parent_record_id": parent_record_id,
    }
    if not state.start(config, len(seeds) * 2):
        return False
    Thread(
        target=run_study_dashboard,
        args=(state, base_spec),
        kwargs={
            "title": title,
            "parameter": parameter,
            "baseline": baseline,
            "variant": variant,
            "seeds": seeds,
            "parent_record_id": parent_record_id,
        },
        daemon=True,
    ).start()
    return True


HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Symbiont Lab</title>
<style>
:root{color-scheme:dark;--bg:#0b0f14;--panel:#131a22;--line:#263241;--text:#eaf1f8;--muted:#8fa3b8;--accent:#76d7b0;--warn:#f7c873;--bad:#ff8b8b}
*{box-sizing:border-box}body{margin:0;font:14px/1.45 system-ui,sans-serif;background:var(--bg);color:var(--text)}
main{max-width:1420px;margin:auto;padding:24px}.top{display:flex;justify-content:space-between;gap:20px;align-items:start;margin-bottom:18px}
h1,h2,h3{margin:0}.sub,.small{color:var(--muted)}.badge,.pill{border:1px solid var(--line);border-radius:99px;padding:5px 9px;color:var(--accent)}
.panel,.card,.chart,.section{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px}.launcher{margin-bottom:12px}
.formgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:12px}.wide{grid-column:span 2}.full{grid-column:1/-1}
label{display:block;color:var(--muted);font-size:12px;margin-bottom:4px}input,textarea,button,select{width:100%;border:1px solid var(--line);border-radius:8px;background:#0f151d;color:var(--text);padding:8px;font:inherit}
textarea{min-height:68px;resize:vertical}button{background:#18352d;color:#dff9ef;font-weight:700;cursor:pointer}button:disabled{opacity:.45;cursor:not-allowed}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.label{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.08em}
.value{font-size:26px;font-weight:700;margin-top:5px}.charts{display:grid;grid-template-columns:2fr 1fr;gap:12px;margin-top:12px}.chart canvas{width:100%;height:260px;display:block}
.split{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}.item{border-top:1px solid var(--line);padding:10px 0}.item:first-of-type{border-top:0}
.meta{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-top:8px}.warn{color:var(--warn)}.bad{color:var(--bad)}.history{overflow:auto;margin-top:12px}
table{width:100%;border-collapse:collapse;min-width:900px}th,td{text-align:left;padding:8px;border-bottom:1px solid var(--line);font-size:12px}th{color:var(--muted);font-weight:600}
td button{width:auto;padding:4px 8px;font-size:11px}.progressbar{height:8px;background:#202b38;border-radius:99px;overflow:hidden;margin-top:8px}.progressbar div{height:100%;background:var(--accent);width:0}
.finding{padding:9px 0;border-top:1px solid var(--line)}.finding:first-child{border-top:0}.strong{color:var(--accent)}.moderate{color:var(--warn)}
@media(max-width:900px){.formgrid,.grid{grid-template-columns:repeat(2,1fr)}.wide{grid-column:span 2}.charts,.split{grid-template-columns:1fr}}
@media(max-width:560px){.formgrid,.grid{grid-template-columns:1fr}.wide,.full{grid-column:auto}.top{flex-direction:column}}
</style>
</head>
<body><main>
<div class="top"><div><h1>Symbiont Lab</h1><div class="sub">v0.12 — study memory, lineage and observer-side interpretation</div></div><div id="status" class="badge">connecting…</div></div>

<div class="panel launcher">
<h2>Single experiment</h2><div class="small">This configuration is also the base world used by comparative studies.</div>
<div class="formgrid">
<div class="wide"><label>Title</label><input id="title" value="Curiosity under drift"></div><div><label>Hosts</label><input id="hosts" type="number" value="100" min="1"></div><div><label>Steps</label><input id="steps" type="number" value="300" min="1"></div>
<div class="wide"><label>Hypothesis</label><textarea id="hypothesis">Curiosity focus should rise when uncertainty increases after benign drift.</textarea></div><div class="wide"><label>Success criteria</label><textarea id="criteria">After the drift, epistemic pressure rises and later settles while recent drift false positives decline.</textarea></div>
<div><label>Seed</label><input id="seed" type="number" value="7"></div><div><label>Threat rate</label><input id="threat_rate" type="number" step="0.001" value="0.018"></div><div><label>Poison fraction</label><input id="poison_fraction" type="number" step="0.01" value="0.08"></div><div><label>Heterogeneity</label><input id="heterogeneity" type="number" step="0.01" value="0.12"></div>
<div><label>Drift step (-1=auto)</label><input id="drift_step" type="number" value="-1"></div><div><label>Drift fraction</label><input id="drift_fraction" type="number" step="0.01" value="0.35"></div><div><label>Drift magnitude</label><input id="drift_magnitude" type="number" step="0.01" value="0.22"></div><div><label>Delay / step</label><input id="delay" type="number" step="0.01" value="0.04"></div>
<div class="wide"><label>Notes</label><textarea id="notes" placeholder="Optional context, variant, comparison target…"></textarea></div><div class="wide" style="display:flex;align-items:end"><button id="launch" onclick="launchExperiment()">Launch experiment</button></div>
</div></div>

<div class="panel launcher">
<h2>Comparative study</h2><div class="small">Runs the same seed set twice, changing only one whitelisted synthetic parameter.</div>
<div class="formgrid"><div class="wide"><label>Study title</label><input id="study_title" value="Poisoning resilience"></div><div><label>Parameter</label><select id="study_parameter"><option>poison_fraction</option><option>threat_rate</option><option>heterogeneity</option><option>drift_fraction</option><option>drift_magnitude</option></select></div><div><label>Seeds</label><input id="study_seeds" value="3,7,11,17,23"></div><div><label>Baseline</label><input id="study_baseline" type="number" step="0.01" value="0"></div><div><label>Variant</label><input id="study_variant" type="number" step="0.01" value="0.12"></div><div class="wide" style="display:flex;align-items:end"><button id="launchStudy" onclick="launchStudy()">Launch comparative study</button></div></div>
<div id="studyStatus" class="small" style="margin-top:10px">Idle.</div><div class="progressbar"><div id="studyProgress"></div></div>
<div id="studyParent" class="small" style="margin-top:8px">Parent study: none</div><button style="margin-top:6px;width:auto" onclick="clearStudyParent()">Start new lineage</button><div id="studyArchiveWarning" class="warn small"></div>
<div class="history"><table><thead><tr><th>Metric</th><th>Baseline mean</th><th>Variant mean</th><th>Delta</th><th>Paired agreement</th><th>σ Δ</th></tr></thead><tbody id="studyRows"><tr><td colspan="6" class="small">No completed study.</td></tr></tbody></table></div>
<div class="section" style="margin-top:12px"><div class="label">Observer interpretation</div><div id="studyInterpretation" class="small">No interpretation yet.</div><button id="useFollowUp" style="margin-top:10px;display:none" onclick="useFollowUp()">Load suggested follow-up</button></div>
</div>

<div class="section">
<div class="label">Study memory</div>
<div class="small">Completed comparative studies and their observer-side lineage. Loading or following up never launches automatically.</div>
<div class="history"><table><thead><tr><th>ID</th><th>Parent</th><th>Title</th><th>Parameter</th><th>Change</th><th>Seeds</th><th>Interpretation</th><th></th><th></th></tr></thead><tbody id="studyHistoryRows"><tr><td colspan="9" class="small">No recorded studies.</td></tr></tbody></table></div>
</div>

<div class="section"><div class="label">Current experiment</div><div id="experimentMeta" class="small">No experiment yet.</div></div>
<div class="grid" style="margin-top:12px"><div class="card"><div class="label">Progress</div><div id="progress" class="value">0%</div></div><div class="card"><div class="label">Curiosity focus</div><div id="focus" class="value">—</div></div><div class="card"><div class="label">Open questions</div><div id="openq" class="value">0</div></div><div class="card"><div class="label">Epistemic pressure</div><div id="epi" class="value">—</div></div><div class="card"><div class="label">Self confidence</div><div id="conf" class="value">—</div></div><div class="card"><div class="label">Mean novelty</div><div id="novelty" class="value">—</div></div><div class="card"><div class="label">Recent drift FP</div><div id="driftfp" class="value">—</div></div><div class="card"><div class="label">Detection</div><div id="detection" class="value">—</div></div></div>
<div class="charts"><div class="chart"><div class="label">Cognitive dynamics</div><canvas id="rates"></canvas></div><div class="chart"><div class="label">Species state</div><canvas id="species"></canvas></div></div>
<div class="split"><div class="section"><div class="label">Curiosity agenda</div><div id="probes" class="small">No probe selected.</div></div><div class="section"><div class="label">Bounded hypotheses</div><div id="hypotheses" class="small">No unresolved hypothesis.</div></div></div>
<div class="section"><div class="label">Research memory</div><div class="small">Completed single runs recorded by the observer. These records never feed back into the simulated species.</div><div id="archiveWarning" class="warn small"></div><div class="history"><table><thead><tr><th>ID</th><th>Title</th><th>Source</th><th>Seed</th><th>Detection</th><th>Precision</th><th>Calibration</th><th>Blind spots</th><th>Drift FP</th><th>Curiosity</th><th></th></tr></thead><tbody id="historyRows"><tr><td colspan="11" class="small">No recorded experiments.</td></tr></tbody></table></div></div>

<script>
const $=id=>document.getElementById(id),pct=v=>(100*Number(v||0)).toFixed(1)+'%';
let lastRecords=[],lastStudy=null,lastStudyRecords=[],parentStudyId=null,currentStudyRecordId=null;
const studyMetrics=['detection_rate','precision','false_positive_rate','calibration_error','blind_spot_rate','recent_drift_false_positive_rate','top_probe_utility','self_confidence','epistemic_pressure'];
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function num(id){return Number($(id).value)}
function payload(){return {title:$('title').value,hypothesis:$('hypothesis').value,success_criteria:$('criteria').value,notes:$('notes').value,hosts:num('hosts'),steps:num('steps'),seed:num('seed'),threat_rate:num('threat_rate'),poison_fraction:num('poison_fraction'),heterogeneity:num('heterogeneity'),drift_step:num('drift_step'),drift_fraction:num('drift_fraction'),drift_magnitude:num('drift_magnitude'),delay:num('delay')}}
async function launchExperiment(){try{const r=await fetch('/api/experiments/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload())});const d=await r.json();if(!r.ok)alert(d.error||'Could not start experiment')}catch(e){alert(String(e))}finally{setTimeout(refresh,100)}}
async function launchStudy(){const p={...payload(),study_title:$('study_title').value,parameter:$('study_parameter').value,baseline:num('study_baseline'),variant:num('study_variant'),seeds:$('study_seeds').value,parent_study_id:parentStudyId};try{const r=await fetch('/api/studies/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});const d=await r.json();if(!r.ok)alert(d.error||'Could not start study')}catch(e){alert(String(e))}finally{setTimeout(refresh,100)}}
function renderInterpretation(i){lastStudy=i;if(!i){$('studyInterpretation').textContent='No interpretation yet.';$('useFollowUp').style.display='none';return}const findings=(i.findings||[]).filter(x=>x.classification!=='stable'||x.evidence!=='weak').slice(0,5);$('studyInterpretation').innerHTML=`<div><b>${esc(i.summary)}</b> <span class="pill">confidence ${pct(i.confidence)}</span></div>${findings.map(f=>`<div class="finding ${esc(f.evidence)}"><b>${esc(f.metric)}</b> · ${esc(f.evidence)}<div>${esc(f.text)}</div></div>`).join('')}<div class="finding"><b>Next study</b><div>${esc(i.follow_up.rationale)}</div><div class="small">${esc(i.follow_up.parameter)}: ${Number(i.follow_up.baseline).toFixed(4)} → ${Number(i.follow_up.variant).toFixed(4)} · ~${i.follow_up.recommended_seed_count} paired seeds</div></div>`;$('useFollowUp').style.display='block'}
function useFollowUp(){if(!lastStudy||!lastStudy.follow_up)return;const f=lastStudy.follow_up;parentStudyId=currentStudyRecordId||parentStudyId;$('studyParent').textContent='Parent study: '+(parentStudyId||'none');$('study_parameter').value=f.parameter;$('study_baseline').value=f.baseline;$('study_variant').value=f.variant;const seeds=[];for(let i=0;i<f.recommended_seed_count;i++)seeds.push(3+i*4);$('study_seeds').value=seeds.join(',');$('study_title').value='Follow-up: '+f.parameter;scrollTo({top:0,behavior:'smooth'})}
function renderStudy(s){currentStudyRecordId=s.record_id||null;const p=s.total?100*s.completed/s.total:0;$('studyProgress').style.width=p+'%';$('studyStatus').textContent=s.error?`Error: ${s.error}`:s.running?`${s.phase} seed ${s.seed??'—'} — ${s.completed}/${s.total}`:s.result?`Finished — ${s.result.seeds.length} paired seeds${s.record_id?' · '+s.record_id:''}`:'Idle.';$('studyParent').textContent='Parent study: '+(parentStudyId||s.config?.parent_record_id||'none');$('studyArchiveWarning').textContent=s.archive_error?`Study archive warning: ${s.archive_error}`:'';renderStudyHistory(s.records||[]);const r=s.result;if(!r){$('studyRows').innerHTML='<tr><td colspan="6" class="small">No completed study.</td></tr>';renderInterpretation(null);return}$('studyRows').innerHTML=studyMetrics.map(m=>{const b=r.baseline.metrics[m],v=r.variant.metrics[m],d=r.deltas[m],p=r.paired_deltas[m];return `<tr><td>${esc(m)}</td><td>${b.mean.toFixed(4)}</td><td>${v.mean.toFixed(4)}</td><td>${d>=0?'+':''}${d.toFixed(4)}</td><td>${pct(p.direction_agreement)}</td><td>${p.stdev.toFixed(4)}</td></tr>`}).join('');renderInterpretation(s.interpretation)}
function loadBaseSpec(s){setVal('title',s.title);setVal('hypothesis',s.hypothesis);setVal('criteria',s.success_criteria);setVal('notes',s.notes);setVal('hosts',s.hosts);setVal('steps',s.steps);setVal('seed',s.seed);setVal('threat_rate',s.threat_rate);setVal('poison_fraction',s.poison_fraction);setVal('heterogeneity',s.heterogeneity);setVal('drift_step',s.drift_step===null?-1:s.drift_step);setVal('drift_fraction',s.drift_fraction);setVal('drift_magnitude',s.drift_magnitude);setVal('delay',s.delay)}
function loadStudyRecord(index,follow=false){const r=lastStudyRecords[index];if(!r)return;const s=r.study||{},base=r.base_spec||{};loadBaseSpec(base);setVal('study_title',s.title);setVal('study_parameter',s.parameter);setVal('study_baseline',s.baseline?.parameter_value);setVal('study_variant',s.variant?.parameter_value);setVal('study_seeds',(s.seeds||[]).join(','));parentStudyId=follow?r.record_id:r.parent_record_id||null;$('studyParent').textContent='Parent study: '+(parentStudyId||'none');scrollTo({top:0,behavior:'smooth'})}
function clearStudyParent(){parentStudyId=null;$('studyParent').textContent='Parent study: none'}
function renderStudyHistory(records){lastStudyRecords=records||[];$('studyHistoryRows').innerHTML=lastStudyRecords.length?lastStudyRecords.map((r,i)=>{const s=r.study||{},interp=r.interpretation||{};return `<tr><td>${esc(r.record_id)}</td><td>${esc(r.parent_record_id||'—')}</td><td>${esc(s.title)}</td><td>${esc(s.parameter)}</td><td>${Number(s.baseline?.parameter_value??0).toFixed(3)}→${Number(s.variant?.parameter_value??0).toFixed(3)}</td><td>${(s.seeds||[]).length}</td><td>${esc(interp.summary||'—')}</td><td><button onclick="loadStudyRecord(${i},false)">Load</button></td><td><button onclick="loadStudyRecord(${i},true)">Follow up</button></td></tr>`}).join(''):'<tr><td colspan="9" class="small">No recorded studies.</td></tr>'}

function setVal(id,v){if(v!==undefined&&v!==null)$(id).value=v}
function loadRecord(index){const r=lastRecords[index];if(!r)return;const s=r.spec||{};setVal('title',s.title);setVal('hypothesis',s.hypothesis);setVal('criteria',s.success_criteria);setVal('notes',s.notes);setVal('hosts',s.hosts);setVal('steps',s.steps);setVal('seed',s.seed);setVal('threat_rate',s.threat_rate);setVal('poison_fraction',s.poison_fraction);setVal('heterogeneity',s.heterogeneity);setVal('drift_step',s.drift_step===null?-1:s.drift_step);setVal('drift_fraction',s.drift_fraction);setVal('drift_magnitude',s.drift_magnitude);setVal('delay',s.delay);scrollTo({top:0,behavior:'smooth'})}
function renderHistory(records){lastRecords=records||[];$('historyRows').innerHTML=lastRecords.length?lastRecords.map((r,i)=>{const s=r.spec||{},m=r.metrics||{};return `<tr><td>${esc(r.record_id)}</td><td>${esc(s.title)}</td><td>${esc(r.source)}</td><td>${esc(s.seed)}</td><td>${pct(m.detection_rate)}</td><td>${pct(m.precision)}</td><td>${Number(m.calibration_error||0).toFixed(3)}</td><td>${pct(m.blind_spot_rate)}</td><td>${pct(m.recent_drift_false_positive_rate)}</td><td>${Number(m.top_probe_utility||0).toFixed(2)}</td><td><button onclick="loadRecord(${i})">Load</button></td></tr>`}).join(''):'<tr><td colspan="11" class="small">No recorded experiments.</td></tr>'}
function lineChart(canvas,series){const dpr=devicePixelRatio||1,w=canvas.clientWidth,h=canvas.clientHeight;canvas.width=w*dpr;canvas.height=h*dpr;const c=canvas.getContext('2d');c.scale(dpr,dpr);c.clearRect(0,0,w,h);c.strokeStyle='#263241';for(let i=0;i<=4;i++){let y=20+(h-40)*i/4;c.beginPath();c.moveTo(30,y);c.lineTo(w-10,y);c.stroke()}series.forEach((s,si)=>{if(s.length<2)return;c.strokeStyle=['#76d7b0','#73a9ff','#f7c873','#d896ff'][si];c.lineWidth=2;c.beginPath();s.forEach((v,i)=>{let x=30+(w-40)*i/(s.length-1),y=20+(h-40)*(1-Math.max(0,Math.min(1,v)));i?c.lineTo(x,y):c.moveTo(x,y)});c.stroke()})}
function barChart(canvas,items){const dpr=devicePixelRatio||1,w=canvas.clientWidth,h=canvas.clientHeight;canvas.width=w*dpr;canvas.height=h*dpr;const c=canvas.getContext('2d');c.scale(dpr,dpr);c.clearRect(0,0,w,h);let max=Math.max(1,...items.map(x=>x[1]));items.forEach((it,i)=>{let y=28+i*48;c.fillStyle='#8fa3b8';c.fillText(it[0],12,y);c.fillStyle='#263241';c.fillRect(12,y+9,w-24,16);c.fillStyle='#76d7b0';c.fillRect(12,y+9,(w-24)*it[1]/max,16);c.fillStyle='#eaf1f8';c.fillText(String(it[1]),16,y+22)})}
function renderProbes(items){$('probes').innerHTML=items&&items.length?items.map(p=>`<div class="item"><b>${esc(p.feature)} ${esc(p.change)}</b> <span class="pill">utility ${Number(p.utility).toFixed(2)}</span><div class="small">EIG ${Number(p.expected_information_gain).toFixed(2)} · ${esc(p.counterfactual_fingerprint)}</div><div>? ${esc(p.question)}</div></div>`).join(''):'No probe selected.'}
function renderHyp(items){$('hypotheses').innerHTML=items&&items.length?items.map(h=>`<div class="item"><b>${esc(h.title)}</b> <span class="pill">${Number(h.priority).toFixed(2)}</span><div class="small">${esc(h.rationale)}</div></div>`).join(''):'No unresolved hypothesis.'}
function renderSpec(d){const s=d.spec||{};$('experimentMeta').innerHTML=`<b>#${d.experiment_number||0} — ${esc(s.title)}</b><div class="meta"><div><span class="label">Hypothesis</span><br>${esc(s.hypothesis)||'—'}</div><div><span class="label">Success criteria</span><br>${esc(s.success_criteria)||'—'}</div><div><span class="label">Notes</span><br>${esc(s.notes)||'—'}</div><div><span class="label">Parameters</span><br>${s.hosts} hosts · ${s.steps} steps · seed ${s.seed}</div></div>`}
async function refresh(){try{const r=await fetch('/api/state',{cache:'no-store'}),d=await r.json(),c=d.current,s=d.study||{};$('status').textContent=d.error?'error':d.running?'experiment running':s.running?'study running':d.finished?'finished':'ready';$('launch').disabled=!!d.running||!!s.running;$('launchStudy').disabled=!!d.running||!!s.running;renderStudy(s);renderSpec(d);renderHistory(d.records);$('archiveWarning').textContent=d.archive_error?`Archive warning: ${d.archive_error}`:'';if(!c)return;$('progress').textContent=pct(c.step/c.total_steps);$('focus').textContent=c.curiosity_focus.toFixed(2);$('openq').textContent=c.open_questions;$('epi').textContent=pct(c.epistemic_pressure);$('conf').textContent=pct(c.self_confidence);$('novelty').textContent=pct(c.mean_novelty);$('driftfp').textContent=pct(c.recent_drift_false_positive_rate);$('detection').textContent=pct(c.detection_rate);renderProbes(c.curiosity_probes);renderHyp(c.reasoning_hypotheses);lineChart($('rates'),[d.history.map(x=>x.curiosity_focus),d.history.map(x=>x.epistemic_pressure),d.history.map(x=>x.mean_novelty),d.history.map(x=>x.self_confidence)]);barChart($('species'),[['patterns',c.collective_patterns],['questions',c.open_questions],['probes',c.curiosity_probes.length],['adaptations',c.drift_adaptations],['memories',c.consolidated_episodes]])}catch(e){$('status').textContent='disconnected'}}
setInterval(refresh,350);refresh();addEventListener('resize',refresh);
</script>
</main></body></html>'''


def make_handler(
    experiment_state: DashboardState,
    study_state: StudyDashboardState,
    experiment_starter: Callable[[ExperimentSpec], bool],
    study_starter: Callable[..., bool],
) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/api/state":
                payload = experiment_state.payload()
                payload["study"] = study_state.payload()
                self._send_json(200, payload)
                return
            if self.path in ("/", "/index.html"):
                body = HTML.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self._send_json(404, {"error": "not found"})

        def _payload(self) -> dict[str, Any]:
            length = min(int(self.headers.get("Content-Length", "0")), 32768)
            payload = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(payload, dict):
                raise ValueError("JSON object required")
            return payload

        def do_POST(self) -> None:  # noqa: N802
            try:
                payload = self._payload()
            except (ValueError, json.JSONDecodeError) as exc:
                self._send_json(400, {"error": str(exc)})
                return

            if self.path == "/api/experiments/start":
                spec = spec_from_payload(payload, experiment_state.spec)
                if not experiment_starter(spec):
                    self._send_json(409, {"error": "another experiment or study is already running"})
                    return
                self._send_json(
                    202,
                    {
                        "started": True,
                        "experiment_number": experiment_state.experiment_number,
                        "spec": spec.as_dict(),
                    },
                )
                return

            if self.path == "/api/studies/start":
                try:
                    spec = spec_from_payload(payload, experiment_state.spec)
                    title = str(payload.get("study_title") or "Comparative study")[:160]
                    parameter = str(payload.get("parameter") or "")
                    if parameter not in COMPARABLE_PARAMETERS:
                        raise ValueError("unsupported study parameter")
                    baseline = float(payload.get("baseline"))
                    variant = float(payload.get("variant"))
                    seeds = _parse_seeds(payload.get("seeds"))
                    parent_record_id = str(payload.get("parent_study_id") or "").strip() or None
                    if parent_record_id is not None and len(parent_record_id) > 64:
                        raise ValueError("parent study id is too long")
                except (TypeError, ValueError) as exc:
                    self._send_json(400, {"error": str(exc)})
                    return
                if not study_starter(
                    spec,
                    title=title,
                    parameter=parameter,
                    baseline=baseline,
                    variant=variant,
                    seeds=seeds,
                    parent_record_id=parent_record_id,
                ):
                    self._send_json(409, {"error": "another experiment or study is already running"})
                    return
                self._send_json(202, {"started": True, "runs": len(seeds) * 2})
                return

            self._send_json(404, {"error": "not found"})

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def _spec_from_args(args: argparse.Namespace) -> ExperimentSpec:
    return ExperimentSpec(
        title=args.title,
        hypothesis=args.hypothesis,
        success_criteria=args.success_criteria,
        notes=args.notes,
        hosts=args.hosts,
        steps=args.steps,
        seed=args.seed,
        threat_rate=args.threat_rate,
        poison_fraction=args.poison_fraction,
        heterogeneity=args.heterogeneity,
        drift_step=None if args.drift_step < 0 else args.drift_step,
        drift_fraction=args.drift_fraction,
        drift_magnitude=args.drift_magnitude,
        delay=max(args.delay, 0.0),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch and visualize Symbiont Lab experiments and studies")
    parser.add_argument("--title", default="Dashboard experiment")
    parser.add_argument("--hypothesis", default="")
    parser.add_argument("--success-criteria", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--hosts", type=int, default=100)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--threat-rate", type=float, default=0.018)
    parser.add_argument("--poison-fraction", type=float, default=0.08)
    parser.add_argument("--heterogeneity", type=float, default=0.12)
    parser.add_argument("--drift-step", type=int, default=-1)
    parser.add_argument("--drift-fraction", type=float, default=0.35)
    parser.add_argument("--drift-magnitude", type=float, default=0.22)
    parser.add_argument("--delay", type=float, default=0.04)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--archive", default=".symbiont/experiments.jsonl")
    parser.add_argument("--study-archive", default=".symbiont/studies.jsonl")
    parser.add_argument("--no-record", action="store_true")
    parser.add_argument("--no-autorun", action="store_true")
    args = parser.parse_args()

    initial_spec = _spec_from_args(args)
    archive = None if args.no_record else ExperimentArchive(args.archive)
    study_archive = None if args.no_record else StudyArchive(args.study_archive)
    experiment_state = DashboardState(archive=archive)
    experiment_state.spec = initial_spec
    study_state = StudyDashboardState(archive=study_archive)

    experiment_starter = lambda spec: start_experiment(experiment_state, study_state, spec)
    study_starter = lambda spec, **kwargs: start_study(
        experiment_state,
        study_state,
        spec,
        **kwargs,
    )
    if not args.no_autorun:
        experiment_starter(initial_spec)

    server = ThreadingHTTPServer(
        ("127.0.0.1", args.port),
        make_handler(experiment_state, study_state, experiment_starter, study_starter),
    )
    print(f"Symbiont Lab dashboard: http://127.0.0.1:{args.port}")
    print(f"Research archive: {archive.path}" if archive else "Research archive disabled.")
    print(f"Study archive: {study_archive.path}" if study_archive else "Study archive disabled.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
