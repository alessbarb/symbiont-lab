import { el } from '../shared/dom.js';
import { PAL } from './config.js';
import { inspectorMetric, panelSection } from './components.js';
import { motorEpochEvents, snap, streamState, tel } from './state.js';
import { pct } from './util.js';
import { historyForCurrentSession } from './motor-learning-history.js';
import { deriveMotorLearningModel } from './motor-learning-model.js';
import { embodimentTimeline, motorSparkline } from './motor-learning-chart.js';

function metricValue(value, digits = 3) {
  return Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : '—';
}

function trendText(trend) {
  if (!trend || trend.per1kTicks == null) return 'insufficient trend';
  const sign = trend.per1kTicks > 0 ? '+' : '';
  const arrow = trend.state === 'rising' ? '↑' : trend.state === 'falling' ? '↓' : '→';
  return `${arrow} ${sign}${trend.per1kTicks.toFixed(3)} / 1k ticks`;
}

function makeStageRail(stage) {
  const stages = [
    ['BABBLING', 'babbling'],
    ['DISCOVERY', 'discovery'],
    ['CONSOLIDATION', 'consolidation'],
    ['CONTROL', 'control'],
    ['SKILL', 'skill'],
  ];
  const rail = el('div', '');
  rail.style.cssText = 'display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:0;margin:10px 0 10px;position:relative;';
  stages.forEach(([label, id], index) => {
    const active = stage?.id === id;
    const reached = stage?.index >= index && stage?.index >= 0 && id !== 'skill';
    const item = el('div', '');
    item.style.cssText = 'position:relative;text-align:center;padding-top:17px;min-width:0;';
    const line = el('div', '');
    line.style.cssText = `position:absolute;top:6px;left:${index===0?'50%':'0'};right:${index===stages.length-1?'50%':'0'};height:1px;background:${reached?'rgba(113,233,186,.44)':'rgba(98,120,136,.22)'};`;
    const dot = el('div', '');
    dot.style.cssText = `position:absolute;top:2px;left:50%;width:9px;height:9px;border-radius:50%;transform:translateX(-50%);border:1px solid ${reached?PAL.mint:'rgba(98,120,136,.5)'};background:${active?PAL.mint:'var(--panel, #081522)'};box-shadow:${active?'0 0 0 4px rgba(113,233,186,.08)':'none'};`;
    const text = el('span', '');
    text.style.cssText = `font-size:8px;letter-spacing:.07em;color:${active?PAL.mint:'var(--muted)'};white-space:nowrap;`;
    text.textContent = id === 'skill' ? 'SKILL · UNDEFINED' : label;
    item.append(line, dot, text);
    rail.appendChild(item);
  });
  return rail;
}

function makeMeter(label, value, displayValue, trend = null) {
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
    fill.style.cssText = `height:100%;width:${Math.max(0,Math.min(100,Math.round(value*100)))}%;border-radius:inherit;background:${PAL.mint};transition:width .35s ease;`;
    track.appendChild(fill);
    wrap.appendChild(track);
  }

  if (trend) {
    const t = el('div', '');
    t.style.cssText = 'margin-top:4px;font-size:8px;color:var(--muted);';
    t.textContent = trendText(trend);
    wrap.appendChild(t);
  }
  return wrap;
}

function makeCount(label, value, sub = '') {
  const card = el('div', '');
  card.style.cssText = 'padding:10px 11px;border:1px solid rgba(98,120,136,.15);border-radius:8px;background:rgba(255,255,255,.012);min-width:0;';
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

function statusLabel(observation) {
  if (observation.status === 'historical') return 'HISTORICAL SNAPSHOT';
  if (observation.status === 'stale') return 'LAST OBSERVED STATE';
  if (observation.live && !observation.coherent) return 'PARTIAL OBSERVATION';
  if (observation.live) return 'LIVE';
  return 'WAITING';
}

function makeObservationBanner(model) {
  const banner = el('div', '');
  const live = model.observation.live && model.observation.coherent;
  banner.style.cssText = `display:flex;align-items:center;justify-content:space-between;gap:12px;padding:7px 9px;margin:10px 0;border:1px solid ${live?'rgba(113,233,186,.16)':'rgba(98,120,136,.18)'};border-radius:8px;background:${live?'rgba(113,233,186,.025)':'rgba(98,120,136,.025)'};`;
  const left = el('strong', '');
  left.style.cssText = `font-size:9px;letter-spacing:.07em;color:${live?PAL.mint:'var(--muted)'};`;
  left.textContent = statusLabel(model.observation);
  const right = el('span', '');
  right.style.cssText = 'font-size:8px;color:var(--muted);';
  right.textContent = [
    model.observation.source,
    model.observation.runId,
    model.observation.tick != null ? `t${Number(model.observation.tick).toLocaleString()}` : null,
  ].filter(Boolean).join(' · ');
  banner.append(left, right);
  return banner;
}

export function renderMotorLearning() {
  const root = document.getElementById('mind-motor-wrap');
  if (!root) return;
  root.innerHTML = '';

  const model = deriveMotorLearningModel({ tel, snap, streamState });
  const { evidence, observation, stage, agency, bottleneck, trends, embodiment } = model;
  const history = historyForCurrentSession();
  const epochEvents = motorEpochEvents.filter(event =>
    event.source === observation.source &&
    event.runId === observation.runId &&
    event.instanceId === observation.instanceId
  );

  const heading = el('div', '');
  heading.style.cssText = 'display:flex;align-items:flex-end;justify-content:space-between;gap:16px;';
  const titleWrap = el('div', '');
  const title = el('h2', '');
  title.style.cssText = 'font-size:16px;margin:0 0 4px;';
  title.textContent = 'Motor learning';
  const copy = el('p', '');
  copy.style.cssText = 'font-size:10px;color:var(--muted);margin:0;';
  copy.textContent = 'How sensorimotor regularities become reusable control across embodiment changes.';
  titleWrap.append(title, copy);
  const context = el('div', '');
  context.style.cssText = 'display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end;';
  [
    embodiment.epoch != null ? `BODY E${embodiment.epoch}` : null,
    observation.tick != null ? `TICK ${Number(observation.tick).toLocaleString()}` : null,
    embodiment.reacclimating ? 'REACCLIMATING' : null,
  ].filter(Boolean).forEach(text => {
    const chip = el('span', '');
    chip.style.cssText = 'padding:5px 7px;border:1px solid rgba(98,120,136,.2);border-radius:999px;font-size:8px;letter-spacing:.05em;color:var(--muted);';
    chip.textContent = text;
    context.appendChild(chip);
  });
  heading.append(titleWrap, context);
  root.append(heading, makeObservationBanner(model));

  const hero = panelSection('Motor development', 'Observer interpretation only · no feedback, goals or thresholds are introduced into Symbiont.');
  hero.appendChild(makeStageRail(stage));
  const stageMeta = el('div', '');
  stageMeta.style.cssText = 'font-size:8px;color:var(--muted);margin:-2px 0 10px;';
  stageMeta.textContent = stage.id
    ? `Observer interpretation: ${stage.id.toUpperCase()} · confidence ${stage.confidence.toUpperCase()}`
    : 'Observer interpretation unavailable until observation is live and coherent.';
  hero.appendChild(stageMeta);

  const heroGrid = el('div', '');
  heroGrid.style.cssText = 'display:grid;grid-template-columns:minmax(0,1.2fr) minmax(250px,.8fr);gap:18px;align-items:start;';
  const metrics = el('div', '');
  metrics.append(
    makeMeter('Babbling coverage', evidence.coverage, evidence.coverage != null ? pct(evidence.coverage) : '—'),
    makeMeter('Best controllability', evidence.controllability, metricValue(evidence.controllability), trends.controllability),
    makeMeter('Directional consistency', evidence.directionalConsistency, metricValue(evidence.directionalConsistency), trends.directionalConsistency),
  );

  const agencyPanel = el('div', '');
  agencyPanel.style.cssText = 'padding:12px;border:1px solid rgba(113,233,186,.16);border-radius:9px;background:rgba(113,233,186,.025);';
  const originLabel = el('div', '');
  originLabel.style.cssText = 'font-size:8px;letter-spacing:.07em;color:var(--muted);';
  originLabel.textContent = 'CURRENT MOTOR ORIGIN';
  const originValue = el('strong', '');
  originValue.style.cssText = 'display:block;margin-top:5px;font-size:17px;color:var(--text);';
  originValue.textContent = String(evidence.origin).toUpperCase();
  const agencyLabel = el('div', '');
  agencyLabel.style.cssText = 'font-size:8px;letter-spacing:.07em;color:var(--muted);margin-top:12px;';
  agencyLabel.textContent = 'LEARNED AGENCY';
  const agencyValue = el('strong', '');
  agencyValue.style.cssText = `display:block;margin-top:5px;font-size:20px;color:${agency.status === 'active' ? PAL.mint : 'var(--text)'};`;
  agencyValue.textContent = agency.status.toUpperCase();
  const agencyCopy = el('p', '');
  agencyCopy.style.cssText = 'margin:7px 0 0;font-size:9px;line-height:1.45;color:var(--muted);';
  agencyCopy.textContent =
    agency.status === 'active' ? 'Learned motor structure is participating in current output.' :
    agency.status === 'emerging' ? 'Reusable structure is visible, but learned control is not clearly driving output.' :
    agency.status === 'absent' ? 'Current output is still babbling without visible reusable cognitive motor control.' :
    'Live coherent evidence is insufficient to classify learned agency.';
  agencyPanel.append(originLabel, originValue, agencyLabel, agencyValue, agencyCopy);
  heroGrid.append(metrics, agencyPanel);
  hero.appendChild(heroGrid);
  root.appendChild(hero);

  const layers = el('div', '');
  layers.style.cssText = 'display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:12px;';
  const groups = [
    ['1 · Discovery', 'Does action repeatedly produce an observable effect?', [
      ['Sensorimotor patterns', evidence.patterns, 'observed regularities'],
      ['Motor primitives', evidence.primitives, 'candidate reusable effects'],
      ['Recurrent candidates', evidence.recurrent, 'effects observed repeatedly'],
    ]],
    ['2 · Consolidation', 'Is discovered structure being integrated and retained?', [
      ['Motor repertoire', evidence.repertoire, 'currently usable entries'],
      ['Motor readouts', evidence.motorReadouts, 'cognitive readout structure'],
      ['Structural motor associations', evidence.motorEdges, 'cognition-to-motor graph relations'],
    ]],
    ['3 · Agency', 'Can learned structure actually participate in control?', [
      ['Cognitive primitives', evidence.cognitivePrimitives, 'reusable cognitive motor units'],
      ['Max evidence samples', evidence.samples, 'best observed primitive evidence count'],
      ['Competence candidates', evidence.competence, 'full competence gate candidates'],
    ]],
  ];
  for (const [name, subtitle, items] of groups) {
    const section = panelSection(name, subtitle);
    const grid = el('div', '');
    grid.style.cssText = 'display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px;';
    for (const [label, value, sub] of items) grid.appendChild(makeCount(label, value, sub));
    section.appendChild(grid);
    layers.appendChild(section);
  }
  root.appendChild(layers);

  const diag = panelSection('Development bottleneck', 'First observable bottleneck in the passive evidence chain.');
  diag.style.cssText += ';margin-top:12px;';
  const headline = el('strong', '');
  headline.style.cssText = 'display:block;font-size:13px;color:var(--text);margin:3px 0 6px;';
  headline.textContent = bottleneck.title;
  const body = el('p', '');
  body.style.cssText = 'margin:0;font-size:9px;line-height:1.5;color:var(--muted);max-width:880px;';
  body.textContent = bottleneck.body;
  const focus = el('div', '');
  focus.style.cssText = 'margin-top:9px;font-size:8px;color:var(--muted);';
  focus.textContent = `Dominant limitation: ${bottleneck.focus}`;
  diag.append(headline, body, focus);
  root.appendChild(diag);

  const trajectories = panelSection('Motor learning trajectories', 'Organism tick is the scientific time axis. Reembodiment markers are observer-side annotations.');
  trajectories.style.cssText += ';margin-top:12px;';
  trajectories.append(
    motorSparkline({ label: 'Controllability', history, key: 'controllability', epochEvents }),
    motorSparkline({ label: 'Directional consistency', history, key: 'directionalConsistency', epochEvents }),
    motorSparkline({ label: 'Cognitive motor primitives', history, key: 'cognitivePrimitives', epochEvents }),
  );
  root.appendChild(trajectories);

  const embodimentPanel = panelSection('Embodiment history', 'Same organism across body epochs; transfer remains an observer interpretation.');
  embodimentPanel.style.cssText += ';margin-top:12px;';
  embodimentPanel.appendChild(embodimentTimeline({ epochs: embodiment.epochs, currentEpoch: embodiment.epoch }));
  inspectorMetric(embodimentPanel, 'Current epoch', embodiment.epoch ?? '—');
  inspectorMetric(embodimentPanel, 'Ticks in current body', embodiment.ageTicks ?? '—');
  inspectorMetric(embodimentPanel, 'Reacclimating', embodiment.reacclimating == null ? '—' : (embodiment.reacclimating ? 'yes' : 'no'));
  inspectorMetric(embodimentPanel, 'Reacclimation remaining', embodiment.reacclimationRemaining ?? '—');
  inspectorMetric(embodimentPanel, 'Transfer evidence', String(embodiment.transfer).replaceAll('-', ' '));
  root.appendChild(embodimentPanel);

  const details = el('details', '');
  details.style.cssText = 'max-width:none;margin-top:12px;border:1px solid rgba(98,120,136,.14);border-radius:9px;background:rgba(255,255,255,.01);padding:10px 12px;';
  const summary = el('summary', '');
  summary.style.cssText = 'cursor:pointer;font-size:9px;color:var(--muted);user-select:none;';
  summary.textContent = 'Raw evidence';
  const detailBody = el('div', '');
  detailBody.style.cssText = 'margin-top:8px;';
  [
    ['Observation status', observation.status],
    ['Coherent frame', observation.coherent ? 'yes' : 'no'],
    ['Current motor origin', evidence.origin],
    ['Motor origin detail', evidence.originDetail ?? '—'],
    ['Babbling coverage', evidence.coverage != null ? pct(evidence.coverage) : '—'],
    ['Best controllability', metricValue(evidence.controllability)],
    ['Best directional consistency', metricValue(evidence.directionalConsistency)],
    ['Primitive replay', evidence.replayActive ? 'active' : 'inactive'],
    ['Cognitive primitives', evidence.cognitivePrimitives],
    ['Max primitive samples', evidence.samples],
    ['Full competence candidates', evidence.competence],
    ['Structural motor associations', evidence.motorEdges],
  ].forEach(([key, value]) => inspectorMetric(detailBody, key, value));
  details.append(summary, detailBody);
  root.appendChild(details);

  if (observation.stale) root.style.opacity = '.86';
  else root.style.opacity = '1';
}
