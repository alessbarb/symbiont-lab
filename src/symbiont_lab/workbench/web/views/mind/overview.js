import { el } from '../shared/dom.js';
import { PAL } from './config.js';
import { bigMetric, inspectorMetric, panelSection } from './components.js';
import { currentMotorOutputEdges, currentPhysiologyState } from './derived.js';
import { milestones, mindHistory, snap, tel } from './state.js';
import { finiteNumber, pct } from './util.js';

export function renderOverview({ onOpenHistoryTick = () => {} } = {}) {
  const root = document.getElementById('mind-overview-wrap');
  if (!root) return;
  root.innerHTML = '';

  const topology = snap.topology ?? {nodes:[], edges:[]};
  const nodes = topology.nodes ?? [];
  const sensorimotor = snap.sensorimotor ?? {};
  const outcome = snap.outcome ?? {};
  const physiology = currentPhysiologyState();
  const concepts = nodes.filter(n => n.kind === 'concept').length;
  const predictors = nodes.filter(n => n.kind === 'predictor').length;
  const motorEdges = currentMotorOutputEdges(topology);
  const energy = tel.metabolicReserve;
  const repertoire = Array.isArray(sensorimotor.active_motor_repertoire) ? sensorimotor.active_motor_repertoire.length : 0;
  const readoutCount = nodes.filter(n => n.kind === 'readout' && (String(n.id).startsWith('readout_motor:') || String(n.id).startsWith('readout_primitive:'))).length;

  const heading = el('div','');
  heading.style.cssText='display:flex;justify-content:space-between;gap:20px;align-items:flex-start;margin-bottom:14px;';
  const copy=el('div','');
  const h=el('h2',''); h.style.cssText='font-size:16px;margin:0;color:var(--text);'; h.textContent='Organism overview';
  const sub=el('p',''); sub.style.cssText='font-size:10px;color:var(--muted);margin:4px 0 0;'; sub.textContent='What exists, what has been learned, and what the organism can actually use.';
  copy.append(h,sub);
  const phase=el('strong',''); phase.style.cssText='font-size:12px;text-transform:uppercase;letter-spacing:.08em;'; phase.style.color =
    physiology==='dead'?PAL.coral:physiology==='dormant'?PAL.amber:physiology==='stressed'?PAL.coral:PAL.mint;
  const epochLabel=tel.embodimentEpoch!=null?`E${tel.embodimentEpoch}`:'';
  const reacclimationLabel=tel.reacclimating
    ? `reacclimating ${tel.reacclimationRemaining ?? '?'}t`
    : '';
  phase.textContent=[physiology,epochLabel,reacclimationLabel].filter(Boolean).join(' · ');
  heading.append(copy,phase);
  root.appendChild(heading);

  const metrics=el('div','');
  metrics.style.cssText='display:grid;grid-template-columns:repeat(5,minmax(120px,1fr));gap:8px;margin-bottom:12px;';
  metrics.append(
    bigMetric('Tick', tel.tick ?? '—'),
    bigMetric('Energy', energy != null ? pct(energy) : '—', energy != null && energy < .2 ? PAL.coral : PAL.mint),
    bigMetric('Resource progress', tel.resourceProgress != null ? `${tel.resourceProgress >=0?'+':''}${tel.resourceProgress.toFixed(2)} m` : '—'),
    bigMetric('Cognition', `${concepts} C · ${predictors} P`, PAL.violet),
    bigMetric('Motor origin', tel.motorOrigin ?? '—', tel.motorOrigin === 'babbling' ? PAL.amber : PAL.mint),
  );
  root.appendChild(metrics);

  if (mindHistory.length > 1) {
    const phaseStrip = panelSection('Observed physiology timeline','Session-local phase history; it never backdates states seen before attachment.');
    phaseStrip.style.marginBottom='12px';
    const track=el('div','');
    track.style.cssText='height:18px;display:flex;overflow:hidden;border-radius:5px;background:rgba(98,120,136,.12);';
    const points=mindHistory;
    const t0=points[0].tick;
    const t1=points[points.length-1].tick;
    const runs=[];
    let runStart=points[0].tick;
    let runState=points[0].physiology;
    for(let i=1;i<points.length;i++){
      if(points[i].physiology!==runState){
        runs.push({state:runState,start:runStart,end:points[i].tick});
        runStart=points[i].tick; runState=points[i].physiology;
      }
    }
    runs.push({state:runState,start:runStart,end:t1+1});
    for(const run of runs){
      const seg=el('div','');
      const width=Math.max(1,((run.end-run.start)/Math.max(1,t1-t0+1))*100);
      const color=run.state==='dead'?PAL.coral:run.state==='dormant'?PAL.amber:run.state==='stressed'?'#d77676':PAL.mint;
      seg.style.cssText=`width:${width}%;background:${color};opacity:.62;position:relative;`;
      seg.title=`${run.state} · t${run.start}–t${run.end}`;
      track.appendChild(seg);
    }
    phaseStrip.appendChild(track);
    const labels=el('div','');
    labels.style.cssText='display:flex;justify-content:space-between;margin-top:4px;font-size:8px;color:var(--muted);';
    labels.innerHTML=`<span>t${t0}</span><span>t${t1}</span>`;
    phaseStrip.appendChild(labels);
    root.appendChild(phaseStrip);
  }

  const grid=el('div','');
  grid.style.cssText='display:grid;grid-template-columns:1.15fr 1fr;gap:12px;';

  const pipeline=panelSection('Learning pipeline','Three distinct levels: exists → learned → usable.');
  const stages=[
    ['Sensory system', `${snap.sensoryPhenotype?.sensors?.length ?? nodes.filter(n=>n.kind==='sense').length} sensors`, true],
    ['Sensorimotor patterns', `${tel.sensorimotorPatterns ?? sensorimotor.known_patterns ?? 0}`, (tel.sensorimotorPatterns ?? sensorimotor.known_patterns ?? 0) > 0],
    ['Motor primitives', `${tel.motorPrimitives ?? sensorimotor.primitives ?? 0}`, (tel.motorPrimitives ?? sensorimotor.primitives ?? 0) > 0],
    ['Cognitive structure', `${concepts} concepts · ${predictors} predictors`, concepts > 0],
    ['Motor repertoire', `${repertoire}`, repertoire > 0],
    ['Motor readouts', `${readoutCount}`, readoutCount > 0],
    ['Cognition → motor edges', `${motorEdges}`, motorEdges > 0],
    ['Cognitive motor use', tel.motorOrigin ?? 'none', ['cognition','mixed'].includes(tel.motorOrigin) || String(tel.motorOrigin).includes('primitive')],
  ];
  stages.forEach(([label,value,ok],idx)=>{
    const row=el('div','');
    row.style.cssText='display:grid;grid-template-columns:18px 1fr auto;gap:8px;align-items:center;padding:7px 0;border-top:1px solid rgba(98,120,136,.12);font-size:9px;';
    const dot=el('span',''); dot.textContent=ok?'●':'○'; dot.style.color=ok?PAL.mint:PAL.muted;
    const name=el('span',''); name.textContent=label; name.style.color='var(--text)';
    const val=el('strong',''); val.textContent=value; val.style.color=ok?'var(--text)':'var(--muted)';
    row.append(dot,name,val); pipeline.appendChild(row);
    if(idx<stages.length-1){
      const arrow=el('div',''); arrow.textContent='↓'; arrow.style.cssText='margin:-2px 0 -2px 4px;color:rgba(98,120,136,.45);font-size:9px;';
      pipeline.appendChild(arrow);
    }
  });

  const outcomePanel=panelSection('Outcome','External behavioral result; not a reward signal fed into cognition.');
  const startDist=finiteNumber(outcome.initial_resource_distance, NaN);
  const minDist=finiteNumber(outcome.minimum_resource_distance, NaN);
  const currentDist=finiteNumber(tel.resourceDistance ?? outcome.current_resource_distance, NaN);
  const consumed=finiteNumber(tel.absorbedEnergy ?? outcome.absorbed_energy, 0);
  [
    ['Start distance', Number.isFinite(startDist)?`${startDist.toFixed(2)} m`:'—'],
    ['Best distance', Number.isFinite(minDist)?`${minDist.toFixed(2)} m`:'—'],
    ['Current distance', Number.isFinite(currentDist)?`${currentDist.toFixed(2)} m`:'—'],
    ['Progress', tel.resourceProgress!=null?`${tel.resourceProgress>=0?'+':''}${tel.resourceProgress.toFixed(2)} m`:'—'],
    ['Consumed energy', consumed.toFixed(2)],
    ['Resource remaining', tel.resourceRemaining!=null?tel.resourceRemaining.toFixed(2):outcome.resource_remaining ?? '—'],
  ].forEach(([key,value])=>inspectorMetric(outcomePanel,key,value));

  grid.append(pipeline,outcomePanel);
  root.appendChild(grid);

  const timeline=panelSection('Major milestones','First-occurrence lifecycle and learning events captured in the current browser session.');
  timeline.style.marginTop='12px';
  if(!milestones.length){
    const empty=el('div',''); empty.style.cssText='font-size:9px;color:var(--muted);'; empty.textContent='No milestones recorded yet.'; timeline.appendChild(empty);
  } else {
    const strip=el('div',''); strip.style.cssText='display:flex;gap:6px;align-items:flex-start;overflow-x:auto;padding:4px 0 2px;';
    for(const milestone of milestones){
      const button=el('button',''); button.type='button'; button.style.cssText='min-width:110px;text-align:left;padding:7px 8px;border:1px solid rgba(98,120,136,.2);border-radius:7px;background:rgba(255,255,255,.015);color:var(--text);cursor:pointer;';
      button.innerHTML=`<strong style="font-size:9px">t${milestone.tick}</strong><br><span style="font-size:8px;color:var(--muted)">${milestone.label}</span>`;
      button.addEventListener('click',()=>onOpenHistoryTick(milestone.tick)); strip.appendChild(button);
    }
    timeline.appendChild(strip);
  }
  root.appendChild(timeline);
}
