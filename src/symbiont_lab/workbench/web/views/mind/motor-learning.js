import { el } from '../shared/dom.js';
import { PAL } from './config.js';
import { inspectorMetric, panelSection } from './components.js';
import { currentMotorOutputEdges } from './derived.js';
import { snap, tel } from './state.js';
import { clamp01, finiteNumber, pct } from './util.js';

function metricValue(value, digits = 3) {
  return Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : '—';
}

function makeStageRail(activeIndex) {
  const stages = ['BABBLING', 'DISCOVERY', 'CONSOLIDATION', 'CONTROL', 'SKILL'];
  const rail = el('div', '');
  rail.style.cssText = 'display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:0;margin:10px 0 16px;position:relative;';
  stages.forEach((label, index) => {
    const item = el('div', '');
    item.style.cssText = 'position:relative;text-align:center;padding-top:17px;min-width:0;';
    const line = el('div', '');
    line.style.cssText = `position:absolute;top:6px;left:${index===0?'50%':'0'};right:${index===stages.length-1?'50%':'0'};height:1px;background:${index<=activeIndex?'rgba(113,233,186,.44)':'rgba(98,120,136,.22)'};`;
    const dot = el('div', '');
    dot.style.cssText = `position:absolute;top:2px;left:50%;width:9px;height:9px;border-radius:50%;transform:translateX(-50%);border:1px solid ${index<=activeIndex?PAL.mint:'rgba(98,120,136,.5)'};background:${index===activeIndex?PAL.mint:'var(--panel, #081522)'};box-shadow:${index===activeIndex?'0 0 0 4px rgba(113,233,186,.08)':'none'};`;
    const text = el('span', '');
    text.style.cssText = `font-size:8px;letter-spacing:.07em;color:${index===activeIndex?PAL.mint:'var(--muted)'};white-space:nowrap;`;
    text.textContent = label;
    item.append(line, dot, text);
    rail.appendChild(item);
  });
  return rail;
}

function makeMeter(label, value, displayValue, note = '') {
  const wrap = el('div', '');
  wrap.style.cssText = 'padding:9px 0;border-bottom:1px solid rgba(98,120,136,.11);';
  const top = el('div', '');
  top.style.cssText = 'display:grid;grid-template-columns:1fr auto;gap:10px;align-items:baseline;';
  const name = el('span', '');
  name.style.cssText = 'font-size:9px;color:var(--muted);';
  name.textContent = label;
  const val = el('strong', '');
  val.style.cssText = 'font-size:11px;color:var(--text);';
  val.textContent = displayValue;
  top.append(name, val);
  wrap.appendChild(top);
  if (Number.isFinite(value)) {
    const track = el('div', '');
    track.style.cssText = 'height:3px;margin-top:6px;border-radius:999px;background:rgba(98,120,136,.16);overflow:hidden;';
    const fill = el('div', '');
    fill.style.cssText = `height:100%;width:${Math.round(clamp01(value)*100)}%;border-radius:inherit;background:${PAL.mint};transition:width .35s ease;`;
    track.appendChild(fill);
    wrap.appendChild(track);
  }
  if (note) {
    const copy = el('div', '');
    copy.style.cssText = 'margin-top:4px;font-size:8px;color:var(--muted);line-height:1.35;';
    copy.textContent = note;
    wrap.appendChild(copy);
  }
  return wrap;
}

function makeCount(label, value, sub = '') {
  const card = el('div', '');
  card.style.cssText = 'padding:10px 11px;border:1px solid rgba(98,120,136,.15);border-radius:8px;background:rgba(255,255,255,.012);min-width:0;animation:motorReveal .28s ease both;';
  const valueNode = el('strong', '');
  valueNode.style.cssText = 'display:block;font-size:18px;line-height:1;color:var(--text);';
  valueNode.textContent = String(value);
  const labelNode = el('div', '');
  labelNode.style.cssText = 'margin-top:5px;font-size:9px;color:var(--muted);';
  labelNode.textContent = label;
  card.append(valueNode, labelNode);
  if (sub) {
    const subNode = el('div', '');
    subNode.style.cssText = 'margin-top:3px;font-size:8px;color:rgba(143,164,179,.72);line-height:1.3;';
    subNode.textContent = sub;
    card.appendChild(subNode);
  }
  return card;
}

function inferDevelopment({ origin, recurrent, repertoire, cognitivePrimitives, competence }) {
  const normalized = String(origin ?? '').toLowerCase();
  if (normalized.includes('cognition') || normalized.includes('primitive')) return 3;
  if (cognitivePrimitives > 0 || competence > 0) return 2;
  if (recurrent > 0 || repertoire > 0) return 1;
  return 0;
}

function bottleneckSummary(sm, cognitivePrimitives, competence, origin) {
  const coverage = Number(sm.babbling_coverage);
  const controllability = Number(sm.best_controllability);
  const directional = Number(sm.best_directional_consistency);
  const normalized = String(origin ?? '').toLowerCase();

  if (Number.isFinite(coverage) && coverage < 1) {
    return {
      title: 'Exploration is still incomplete',
      body: 'The current body has not yet accumulated full babbling coverage. More of the action space still has to be observed before later evidence can be interpreted reliably.',
      focus: 'exploration coverage',
    };
  }
  if (cognitivePrimitives <= 0) {
    return {
      title: 'No reusable cognitive primitive yet',
      body: 'Sensorimotor regularities exist, but none has crossed into a reusable cognitive motor primitive in the passive runtime snapshot.',
      focus: Number.isFinite(controllability) && Number.isFinite(directional)
        ? 'action → outcome evidence and reusable integration'
        : 'reusable cognitive integration',
    };
  }
  if (competence <= 0) {
    return {
      title: 'Primitives exist, competence has not emerged',
      body: 'The organism has reusable motor structure, but no full competence candidate is currently visible.',
      focus: 'competence formation',
    };
  }
  if (!(normalized.includes('cognition') || normalized.includes('primitive'))) {
    return {
      title: 'Capability exists but is not driving control',
      body: 'Motor competence evidence is present, yet current output is not primarily originating from cognitive motor control.',
      focus: 'cognitive deployment',
    };
  }
  return {
    title: 'Cognitive motor control is active',
    body: 'The passive snapshot shows motor output originating from learned cognitive structure. Continue watching stability and transfer across embodiment epochs.',
    focus: 'stability and transfer',
  };
}

export function renderMotorLearning() {
  const root=document.getElementById('mind-motor-wrap');
  if(!root) return;
  root.innerHTML='';

  const style=el('style','');
  style.textContent='@keyframes motorReveal{from{opacity:0;transform:translateY(3px)}to{opacity:1;transform:translateY(0)}}';
  root.appendChild(style);

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
  const patterns=finiteNumber(tel.sensorimotorPatterns ?? sm.known_patterns,0);
  const primitives=finiteNumber(tel.motorPrimitives ?? sm.primitives,0);
  const recurrent=finiteNumber(tel.recurrentPrimitiveCandidates ?? sm.recurrent_primitive_candidates,0);
  const cognitivePrimitives=finiteNumber(tel.cognitiveMotorPrimitives ?? sm.cognitive_primitives,0);
  const samples=finiteNumber(tel.maxPrimitiveSamples ?? sm.max_primitive_samples,0);
  const competence=finiteNumber(tel.fullCompetenceGateCandidates ?? sm.full_competence_gate_candidates,0);
  const origin=tel.motorOrigin ?? 'none';
  const stageIndex=inferDevelopment({origin,recurrent,repertoire,cognitivePrimitives,competence});
  const bottleneck=bottleneckSummary(sm,cognitivePrimitives,competence,origin);

  const heading=el('div','');
  heading.style.cssText='display:flex;align-items:flex-end;justify-content:space-between;gap:16px;margin-bottom:2px;';
  const titleWrap=el('div','');
  const title=el('h2','');
  title.style.cssText='font-size:16px;margin:0 0 4px;';
  title.textContent='Motor learning';
  const copy=el('p','');
  copy.style.cssText='font-size:10px;color:var(--muted);margin:0;';
  copy.textContent='How discovered sensorimotor regularities become reusable cognitive control.';
  titleWrap.append(title,copy);
  const context=el('div','');
  context.style.cssText='display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end;';
  [
    tel.embodimentEpoch!=null?`BODY EPOCH ${tel.embodimentEpoch}`:null,
    tel.tick!=null?`TICK ${Number(tel.tick).toLocaleString()}`:null,
    tel.reacclimating?'REACCLIMATING':null,
  ].filter(Boolean).forEach(text=>{
    const chip=el('span','');
    chip.style.cssText='padding:5px 7px;border:1px solid rgba(98,120,136,.2);border-radius:999px;font-size:8px;letter-spacing:.05em;color:var(--muted);';
    chip.textContent=text;
    context.appendChild(chip);
  });
  heading.append(titleWrap,context);
  root.appendChild(heading);

  const hero=panelSection('Motor development','Observer-derived development view — this does not add a new control state machine to Symbiont.');
  hero.style.cssText += ';margin-top:14px;';
  hero.appendChild(makeStageRail(stageIndex));

  const heroGrid=el('div','');
  heroGrid.style.cssText='display:grid;grid-template-columns:minmax(0,1.2fr) minmax(250px,.8fr);gap:18px;align-items:start;';
  const evidence=el('div','');
  evidence.append(
    makeMeter('Babbling coverage', Number.isFinite(Number(sm.babbling_coverage))?Number(sm.babbling_coverage):NaN, sm.babbling_coverage!=null?pct(sm.babbling_coverage):'—'),
    makeMeter('Best controllability', Number.isFinite(Number(sm.best_controllability))?Number(sm.best_controllability):NaN, metricValue(sm.best_controllability)),
    makeMeter('Directional consistency', Number.isFinite(Number(sm.best_directional_consistency))?Number(sm.best_directional_consistency):NaN, metricValue(sm.best_directional_consistency)),
  );

  const agency=el('div','');
  agency.style.cssText='padding:12px;border:1px solid rgba(113,233,186,.16);border-radius:9px;background:rgba(113,233,186,.025);';
  const agencyLabel=el('div','');
  agencyLabel.style.cssText='font-size:8px;letter-spacing:.07em;color:var(--muted);';
  agencyLabel.textContent='CURRENT MOTOR AGENCY';
  const agencyValue=el('strong','');
  agencyValue.style.cssText=`display:block;margin-top:5px;font-size:20px;color:${stageIndex>=3?PAL.mint:PAL.muted};`;
  agencyValue.textContent=String(origin).toUpperCase();
  const agencyCopy=el('p','');
  agencyCopy.style.cssText='margin:7px 0 0;font-size:9px;line-height:1.45;color:var(--muted);';
  agencyCopy.textContent=stageIndex>=3
    ? 'Learned cognitive structure is contributing directly to current motor output.'
    : 'Motor output is not yet primarily driven by reusable cognitive motor control.';
  agency.append(agencyLabel,agencyValue,agencyCopy);
  heroGrid.append(evidence,agency);
  hero.appendChild(heroGrid);
  root.appendChild(hero);

  const layers=el('div','');
  layers.style.cssText='display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:12px;';
  const layerData=[
    {
      title:'1 · Discovery',
      subtitle:'Does action repeatedly produce an observable effect?',
      items:[
        ['Sensorimotor patterns',patterns,'observed regularities'],
        ['Motor primitives',primitives,'candidate reusable effects'],
        ['Recurrent candidates',recurrent,'effects observed repeatedly'],
      ],
    },
    {
      title:'2 · Consolidation',
      subtitle:'Is discovered structure being integrated and retained?',
      items:[
        ['Motor repertoire',repertoire,'currently usable entries'],
        ['Motor readouts',motorReadouts,'cognitive readout structure'],
        ['Cognition ↔ motor edges',motorEdges,'structural motor associations'],
      ],
    },
    {
      title:'3 · Agency',
      subtitle:'Can learned structure actually participate in control?',
      items:[
        ['Cognitive primitives',cognitivePrimitives,'reusable cognitive motor units'],
        ['Best primitive evidence',samples,'maximum observed sample count'],
        ['Competence candidates',competence,'full competence gate candidates'],
      ],
    },
  ];
  layerData.forEach(group=>{
    const section=panelSection(group.title,group.subtitle);
    const grid=el('div','');
    grid.style.cssText='display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px;';
    group.items.forEach(([label,value,sub])=>grid.appendChild(makeCount(label,value,sub)));
    section.appendChild(grid);
    layers.appendChild(section);
  });
  root.appendChild(layers);

  const bottom=el('div','');
  bottom.style.cssText='display:grid;grid-template-columns:minmax(0,1.15fr) minmax(280px,.85fr);gap:12px;margin-top:12px;';

  const diag=panelSection('Development bottleneck','A passive interpretation of the evidence currently visible in the runtime snapshot.');
  const headline=el('strong','');
  headline.style.cssText=`display:block;font-size:13px;color:${stageIndex>=3?PAL.mint:'var(--text)'};margin:3px 0 6px;`;
  headline.textContent=bottleneck.title;
  const body=el('p','');
  body.style.cssText='margin:0;font-size:9px;line-height:1.5;color:var(--muted);max-width:760px;';
  body.textContent=bottleneck.body;
  const focus=el('div','');
  focus.style.cssText='margin-top:10px;padding-top:9px;border-top:1px solid rgba(98,120,136,.12);display:grid;grid-template-columns:auto 1fr;gap:8px;font-size:9px;';
  const focusLabel=el('span','');
  focusLabel.style.color='var(--muted)';
  focusLabel.textContent='Dominant limitation';
  const focusValue=el('strong','');
  focusValue.style.color='var(--text)';
  focusValue.textContent=bottleneck.focus;
  focus.append(focusLabel,focusValue);
  diag.append(headline,body,focus);

  const embodiment=panelSection('Embodiment context','Keeps motor learning interpretable across body changes.');
  inspectorMetric(embodiment,'Embodiment epoch',tel.embodimentEpoch ?? '—');
  inspectorMetric(embodiment,'Reacclimating',tel.reacclimating==null?'—':(tel.reacclimating?'yes':'no'),tel.reacclimating?PAL.mint:null);
  inspectorMetric(embodiment,'Reacclimation remaining',tel.reacclimationRemaining ?? '—');
  inspectorMetric(embodiment,'Motor activity/origin',origin,stageIndex>=3?PAL.mint:null);
  inspectorMetric(embodiment,'Primitive replay',sm.replay_active?'active':'inactive');

  bottom.append(diag,embodiment);
  root.appendChild(bottom);

  const details=el('details','');
  details.style.cssText='max-width:none;margin-top:12px;border:1px solid rgba(98,120,136,.14);border-radius:9px;background:rgba(255,255,255,.01);padding:10px 12px;';
  const summary=el('summary','');
  summary.style.cssText='cursor:pointer;font-size:9px;color:var(--muted);user-select:none;';
  summary.textContent='Evidence details';
  const detailBody=el('div','');
  detailBody.style.cssText='margin-top:8px;';
  [
    ['Babbling coverage', sm.babbling_coverage!=null?pct(sm.babbling_coverage):'—'],
    ['Best controllability', metricValue(sm.best_controllability)],
    ['Best directional consistency', metricValue(sm.best_directional_consistency)],
    ['Primitive replay', sm.replay_active?'active':'inactive'],
    ['Cognitive primitives', cognitivePrimitives],
    ['Max primitive samples', samples],
    ['Full competence candidates', competence],
    ['Cognitive motor edges', motorEdges],
    ['Current motor origin', origin],
  ].forEach(([key,value])=>inspectorMetric(detailBody,key,value));
  details.append(summary,detailBody);
  root.appendChild(details);
}
