import { el } from '../shared/dom.js';
import { PAL } from './config.js';
import { inspectorMetric, panelSection } from './components.js';
import { currentMotorOutputEdges } from './derived.js';
import { snap, tel } from './state.js';
import { finiteNumber, pct } from './util.js';

export function renderMotorLearning() {
  const root=document.getElementById('mind-motor-wrap');
  if(!root) return;
  root.innerHTML='';
  const sm=snap.sensorimotor ?? {};
  const topology=snap.topology ?? {nodes:[],edges:[]};
  const nodes=topology.nodes ?? [];
  const motorEdges=finiteNumber(tel.cognitiveMotorOutputEdges ?? currentMotorOutputEdges(topology),0);
  const repertoire=finiteNumber(
    tel.motorRepertoireSize ?? (
      Array.isArray(sm.active_motor_repertoire)?sm.active_motor_repertoire.length:0
    ),
    0,
  );
  const motorReadouts=finiteNumber(
    tel.motorReadoutNodes ?? nodes.filter(n=>n.kind==='readout'&&(String(n.id).startsWith('readout_motor:')||String(n.id).startsWith('readout_primitive:'))).length,
    0,
  );
  const values=[
    ['Sensorimotor patterns', finiteNumber(tel.sensorimotorPatterns ?? sm.known_patterns,0), true, 'EXISTS'],
    ['Motor primitives', finiteNumber(tel.motorPrimitives ?? sm.primitives,0), true, 'LEARNED'],
    ['Recurrent candidates', finiteNumber(tel.recurrentPrimitiveCandidates ?? sm.recurrent_primitive_candidates,0), true, 'LEARNED'],
    ['Motor repertoire', repertoire, repertoire>0, 'USABLE'],
    ['Motor readouts', motorReadouts, motorReadouts>0, 'USABLE'],
    ['Cognitive motor edges', motorEdges, motorEdges>0, 'USABLE'],
    ['Actual cognitive control', tel.motorOrigin ?? 'none', ['cognition','mixed'].includes(tel.motorOrigin)||String(tel.motorOrigin).includes('primitive'), 'USED'],
  ];

  const heading=el('h2',''); heading.style.cssText='font-size:16px;margin:0 0 4px;'; heading.textContent='Motor learning';
  const copy=el('p',''); copy.style.cssText='font-size:10px;color:var(--muted);margin:0 0 16px;'; copy.textContent='A funnel from discovered sensorimotor regularity to actual cognitive control.';
  root.append(heading,copy);
  const funnel=el('div',''); funnel.style.cssText='max-width:760px;margin:0 auto;';
  values.forEach(([label,value,ok,level],i)=>{
    const width=100-i*7;
    const row=el('div',''); row.style.cssText=`width:${width}%;margin:0 auto 4px;padding:10px 12px;display:grid;grid-template-columns:58px 1fr auto;gap:10px;border:1px solid ${ok?'rgba(113,233,186,.24)':'rgba(98,120,136,.18)'};border-radius:8px;background:${ok?'rgba(113,233,186,.035)':'rgba(255,255,255,.012)'};`;
    const badge=el('span',''); badge.style.cssText='font-size:7px;letter-spacing:.08em;color:var(--muted);'; badge.textContent=level;
    const name=el('span',''); name.style.cssText='font-size:10px;color:var(--muted);'; name.textContent=label;
    const val=el('strong',''); val.style.cssText='font-size:12px;'; val.style.color=ok?PAL.mint:PAL.muted; val.textContent=String(value);
    row.append(badge,name,val); funnel.appendChild(row);
    if(i<values.length-1){const arrow=el('div',''); arrow.textContent='↓'; arrow.style.cssText='text-align:center;color:rgba(98,120,136,.45);height:12px;'; funnel.appendChild(arrow);}
  });
  root.appendChild(funnel);

  const diag=panelSection('Why is control blocked?','Current readiness gates from the passive runtime snapshot.');
  diag.style.cssText += ';max-width:760px;margin:16px auto 0;';
  [
    ['Babbling coverage', sm.babbling_coverage!=null?pct(sm.babbling_coverage):'—'],
    ['Best controllability', sm.best_controllability!=null?sm.best_controllability.toFixed(3):'—'],
    ['Best directional consistency', sm.best_directional_consistency!=null?sm.best_directional_consistency.toFixed(3):'—'],
    ['Primitive replay', sm.replay_active?'active':'inactive'],
    ['Cognitive primitives', finiteNumber(tel.cognitiveMotorPrimitives ?? sm.cognitive_primitives,0)],
    ['Max primitive samples', finiteNumber(tel.maxPrimitiveSamples ?? sm.max_primitive_samples,0)],
    ['Full competence candidates', finiteNumber(tel.fullCompetenceGateCandidates ?? sm.full_competence_gate_candidates,0)],
    ['Cognitive motor edges', motorEdges],
    ['Current motor origin', tel.motorOrigin ?? '—'],
  ].forEach(([key,value])=>inspectorMetric(diag,key,value));
  root.appendChild(diag);
}
