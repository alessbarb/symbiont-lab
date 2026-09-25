/**
 * Cognition inspector.
 *
 * Owns observer-side inspector projection and DOM only. Graph simulation,
 * camera/rendering and animation lifecycle remain in cognition-controller.js.
 */
import { el } from '../shared/dom.js';
import { inspectorMetric } from './components.js';
import { PAL } from './config.js';
import { graphSubgraphIds } from './graph-selection.js';
import { observerContextForNode } from './semantics.js';
import { graph, observerUsage, snap } from './state.js';
import { finiteNumber, pct, shortId } from './util.js';
import { summarizeDiff } from './cognitive-refinement.js';
import { appendInspectorLine, appendInspectorStage } from './inspector-view.js';

export function createCognitionInspector({
  atlasModeMeta,
  atlasRegionScore,
  onSelectNode = () => {},
  onRebuild = () => {},
  onReheat = () => {},
} = {}) {
  const selectCognitiveNode = onSelectNode;

  function focusedSectorContext() {
    const sectorId = graph.focusedSectorId;
    if (!sectorId) return null;
    const local = new Set(
      graph.nodes
        .filter(node => node.community === sectorId)
        .map(node => node.id)
    );
    if (!local.size) return null;
  
    const bridges = new Set();
    for (const edge of graph.edges) {
      const sourceLocal = local.has(edge.source.id);
      const targetLocal = local.has(edge.target.id);
      if (sourceLocal === targetLocal) continue;
      bridges.add(sourceLocal ? edge.target.id : edge.source.id);
    }
    return {
      sectorId,
      local,
      bridges,
      visible: new Set([...local, ...bridges]),
    };
  }
  
  function currentRenderedTopology() {
    return {
      nodes: graph.nodes.map(node => ({ id: node.id, kind: node.kind })),
      edges: graph.edges.map(edge => ({
        sourceId: edge.source.id,
        targetId: edge.target.id,
        kind: edge.kind,
        support: edge.support,
        weight: edge.weight,
        plasticity: edge.plasticity,
        ageTicks: edge.ageTicks,
        stableTicks: edge.stableTicks,
        lastUseTick: edge.lastUseTick,
        correlation: edge.correlation,
        samples: edge.samples,
        learnedLayer: edge.learnedLayer,
      })),
    };
  }
  
  function cognitionNodeFacts(nodeId) {
    const topology = currentRenderedTopology();
    const edges = topology.edges ?? [];
    const inbound = edges.filter(edge => edge.targetId === nodeId);
    const outbound = edges.filter(edge => edge.sourceId === nodeId);
    const localIds = graphSubgraphIds(topology, nodeId, graph.pathDepth) ?? new Set([nodeId]);
    const reachesMotor = [...localIds].some(id =>
      String(id).startsWith('readout_motor:') ||
      String(id).startsWith('readout_primitive:') ||
      String(id).startsWith('motor_primitive:') ||
      String(id).startsWith('actuator.')
    );
    return { inbound, outbound, localIds, reachesMotor };
  }
  
  function inspectorGroup(parent, title, open = true) {
    const group = document.createElement('details');
    group.className = 'mind-inspector-group';
    group.open = open;
    const summary = document.createElement('summary');
    summary.className = 'mind-inspector-group-summary';
    summary.textContent = title;
    group.appendChild(summary);
    parent.appendChild(group);
    return group;
  }

  function renderCognitionInspector() {
    const panel = document.getElementById('mind-cognition-inspector-body');
    if (!panel) return;
    panel.replaceChildren();
  
    const selected = graph.nodes.find(node => node.id === graph.selectedNodeId) ?? null;
    if (selected) {
      const title = el('div', 'mind-inspector-title');
      title.textContent = selected.label ?? selected.id;
      const subtitle = el('div', 'mind-inspector-subtitle');
      subtitle.textContent = `${selected.kind} · selected node`;
      panel.append(title, subtitle);
      const identityGroup = inspectorGroup(panel, 'Identity', true);
      const topologyGroup = inspectorGroup(panel, 'Topology', true);
      const dynamicsGroup = inspectorGroup(panel, 'Dynamics', false);
      const roleGroup = inspectorGroup(panel, 'Role', true);
      const relationsGroup = inspectorGroup(panel, 'Relations & pathway', true);
  
      const facts = cognitionNodeFacts(selected.id);
      const observerContext = observerContextForNode(
        graph.replaySnapshot?.topology ?? snap.topology,
        graph.replaySnapshot?.observerSemantics ?? snap.observerSemantics,
        selected.id,
        2,
      );
      const motorSemantic = selected.learnedLayer === 'motor' && selected.observerLabel
        ? {
            summary: selected.observerLabel,
            kind: selected.kind === 'actuator' ? 'exact-source' : 'composition',
            distance: 0,
          }
        : null;
      const displayedSemantic = motorSemantic ?? observerContext;
      inspectorMetric(identityGroup, 'Self label', selected.id, PAL.violet);
      inspectorMetric(
        identityGroup,
        displayedSemantic.kind === 'exact-source'
          ? 'Observer truth'
          : displayedSemantic.kind === 'composition'
            ? 'Observer composition'
            : 'Observer context',
        displayedSemantic.summary ?? 'unresolved',
        displayedSemantic.summary ? PAL.cyan : PAL.muted,
      );
      inspectorMetric(
        identityGroup,
        'Semantic relation',
        displayedSemantic.kind === 'exact-source'
          ? 'exact source mapping'
          : displayedSemantic.kind === 'composition'
            ? 'physical composition only'
            : displayedSemantic.kind === 'sensory-context'
              ? `linked within ${displayedSemantic.distance} hops`
              : 'unresolved',
      );
      inspectorMetric(identityGroup, 'Kind', selected.kind);
      if (selected.kind === 'motor_primitive') {
        inspectorMetric(roleGroup, 'Cognitive reuse', selected.cognitivePrimitive ? 'eligible' : 'not yet');
        inspectorMetric(roleGroup, 'Samples', selected.samples);
        inspectorMetric(roleGroup, 'Controllability', selected.controllability.toFixed(4), PAL.mint);
        inspectorMetric(roleGroup, 'Directional consistency', pct(selected.directionalConsistency));
        inspectorMetric(roleGroup, 'Effect variance', selected.effectVariance.toFixed(4));
        inspectorMetric(roleGroup, 'Actuators', selected.actuatorIds.length);
        inspectorMetric(roleGroup, 'Replay', selected.replayActive ? 'active now' : 'inactive', selected.replayActive ? PAL.mint : PAL.muted);
      }
      if (selected.kind === 'actuator') {
        inspectorMetric(roleGroup, 'Observer effector', selected.observerLabel ?? 'unresolved', PAL.cyan);
        inspectorMetric(roleGroup, 'Motor repertoire', selected.activeRepertoire ? 'active' : 'not promoted');
        inspectorMetric(roleGroup, 'Effect strength', selected.effectStrength.toFixed(3), PAL.mint);
        inspectorMetric(roleGroup, 'Effect relations', selected.causalRelationCount);
        inspectorMetric(roleGroup, 'Activations observed', selected.activations);
      }
      // Spec Sec 59: Motor/Embodiment tabs shown only when relevant to the
      // selected node's real kind -- never fabricated for kinds that don't
      // carry this data.
      if (selected.kind === 'motor_competence') {
        const motorGroup = inspectorGroup(panel, 'Motor', true);
        inspectorMetric(motorGroup, 'State', selected.state ?? 'unknown', selected.state === 'usable' ? PAL.mint : PAL.muted);
        inspectorMetric(motorGroup, 'Maturity', selected.maturity ?? 'unknown');
        inspectorMetric(motorGroup, 'Support', selected.support ?? 0);
        inspectorMetric(motorGroup, 'Controllability', finiteNumber(selected.controllability, 0).toFixed(3), PAL.mint);
      }
      if (selected.kind === 'effect') {
        const motorGroup = inspectorGroup(panel, 'Motor', true);
        inspectorMetric(motorGroup, 'Support', selected.support ?? 0);
        inspectorMetric(motorGroup, 'Confidence', finiteNumber(selected.confidence, 0).toFixed(3), PAL.mint);
      }
      if (selected.kind === 'controller') {
        const motorGroup = inspectorGroup(panel, 'Motor', true);
        inspectorMetric(motorGroup, 'Strategy ref', selected.strategyRef ?? 'unresolved', selected.strategyRef ? PAL.cyan : PAL.muted);
      }
      if (selected.kind === 'action_dimension') {
        const motorGroup = inspectorGroup(panel, 'Motor', true);
        inspectorMetric(motorGroup, 'Availability', selected.availability ? 'available' : 'unavailable');
        inspectorMetric(motorGroup, 'Controllability', finiteNumber(selected.controllability, 0).toFixed(3), PAL.mint);
        inspectorMetric(motorGroup, 'Confidence', finiteNumber(selected.confidence, 0).toFixed(3));
        inspectorMetric(motorGroup, 'Embodiment bound', selected.embodimentBound ? 'yes' : 'no', selected.embodimentBound ? PAL.mint : PAL.muted);
      }
      if (selected.kind === 'embodiment_binding') {
        const embodimentGroup = inspectorGroup(panel, 'Embodiment', true);
        inspectorMetric(embodimentGroup, 'Surface fingerprint', selected.surfaceFingerprint ?? 'unresolved', PAL.cyan);
        inspectorMetric(embodimentGroup, 'Reliability', finiteNumber(selected.reliability, 0).toFixed(3), PAL.mint);
        inspectorMetric(embodimentGroup, 'Controllability', finiteNumber(selected.controllability, 0).toFixed(3));
      }
      if (selected.kind === 'body_schema') {
        const embodimentGroup = inspectorGroup(panel, 'Embodiment', true);
        inspectorMetric(embodimentGroup, 'Subkind', selected.subkind ?? 'unknown');
        inspectorMetric(embodimentGroup, 'Confidence class', selected.confidenceClass ?? 'unknown');
        inspectorMetric(embodimentGroup, 'Maturity class', selected.maturityClass ?? 'unknown');
      }
      inspectorMetric(topologyGroup, 'Degree', selected.neighbors?.size ?? 0);
      inspectorMetric(dynamicsGroup, 'Activity', pct(selected.activationLevel ?? 0), PAL.cyan);
      inspectorMetric(topologyGroup, 'Structural importance', pct(selected.structuralImportance ?? selected.visualValue ?? 0));
      inspectorMetric(topologyGroup, 'Component', selected.isolated ? 'unintegrated' : `#${(selected.componentRank ?? 0) + 1} · ${selected.componentSize ?? 1} nodes`);
      inspectorMetric(topologyGroup, 'Sector', selected.community && selected.community !== 'isolated'
        ? (graph.sectorLabels.get(selected.community) ?? 'unresolved')
        : 'none');
      inspectorMetric(topologyGroup, 'Inbound / outbound', `${facts.inbound.length} / ${facts.outbound.length}`);
      inspectorMetric(topologyGroup, `Within ${graph.pathDepth} hops`, facts.localIds.size);
      inspectorMetric(
        roleGroup,
        'Motor path nearby',
        facts.reachesMotor ? 'yes' : 'no',
        facts.reachesMotor ? PAL.mint : PAL.muted,
      );
      const structureRoles = [];
      if ((graph.cognitiveStructures?.hubs ?? []).some(item => item.id === selected.id)) {
        structureRoles.push('hub');
      }
      if ((graph.cognitiveStructures?.bottlenecks ?? []).some(item => item.id === selected.id)) {
        structureRoles.push('bottleneck');
      }
      const loopCount = (graph.cognitiveStructures?.loops ?? [])
        .filter(loop => loop.includes(selected.id))
        .length;
      if (loopCount) structureRoles.push(`${loopCount} recurrent loop${loopCount === 1 ? '' : 's'}`);
      const flowCount = (graph.observedFlow?.paths ?? [])
        .filter(path => path.nodeIds.includes(selected.id))
        .length;
      inspectorMetric(
        roleGroup,
        'Higher-order role',
        structureRoles.length ? structureRoles.join(' · ') : 'none detected',
        structureRoles.length ? PAL.amber : PAL.muted,
      );
      inspectorMetric(
        roleGroup,
        'Recent flow paths',
        flowCount,
        flowCount ? PAL.cyan : PAL.muted,
      );
      if (selected.errorCls) inspectorMetric(dynamicsGroup, 'Prediction error', selected.errorCls, PAL.coral);
      if (selected.readoutVal != null) inspectorMetric(dynamicsGroup, 'Readout', selected.readoutVal, PAL.mint);
  
      const relTitle = el('div', 'mind-inspector-section-title');
      relTitle.textContent = 'Direct relations';
      relationsGroup.appendChild(relTitle);
  
      const direct = [
        ...facts.inbound.map(edge => ({ dir: '←', other: edge.sourceId, edge })),
        ...facts.outbound.map(edge => ({ dir: '→', other: edge.targetId, edge })),
      ]
        .sort((a,b) => finiteNumber(b.edge.support,0) - finiteNumber(a.edge.support,0))
        .slice(0, 12);
  
      if (!direct.length) {
        const empty = el('div', 'mind-inspector-empty');
        empty.textContent = 'No direct graph relations.';
        relationsGroup.appendChild(empty);
      } else {
        for (const relation of direct) {
          const row = el('button', 'mind-inspector-relation-button mind-inspector-relation-compact');
          row.type = 'button';
          row.textContent = `${relation.dir} ${shortId(relation.other, 9, 5)} · ${relation.edge.kind ?? 'edge'} · sup ${finiteNumber(relation.edge.support,0)}`;
          row.title =
            `${relation.other}\nkind ${relation.edge.kind ?? 'edge'} · weight ${finiteNumber(relation.edge.weight,0).toFixed(3)} · plasticity ${finiteNumber(relation.edge.plasticity,0).toFixed(3)}\nsupport ${finiteNumber(relation.edge.support,0)} · age ${finiteNumber(relation.edge.ageTicks,0)} · stable ${finiteNumber(relation.edge.stableTicks,0)} · last use t${finiteNumber(relation.edge.lastUseTick,0)}`;
          row.addEventListener('click', () => selectCognitiveNode(relation.other));
          relationsGroup.appendChild(row);
        }
      }
  
      if (graph.atlasPath?.nodeIds?.length > 1) {
        const pathTitle = el('div', 'mind-inspector-section-title');
        pathTitle.textContent = 'Cognitive pathway';
        relationsGroup.appendChild(pathTitle);

        const pathCopy = el('div', 'mind-inspector-path-copy');
        pathCopy.textContent = graph.atlasPath.nodeIds
          .map(id => {
            const node = graph.nodes.find(item => item.id === id);
            return node ? `${node.kind}: ${shortId(node.id, 9, 5)}` : shortId(id, 9, 5);
          })
          .join(' → ');
        relationsGroup.appendChild(pathCopy);

        for (const id of graph.atlasPath.nodeIds) {
          const node = graph.nodes.find(item => item.id === id);
          if (!node) continue;
          const row = el('button', 'mind-inspector-path-button');
          row.type = 'button';
          row.textContent = `${node.kind} · ${node.observerLabel ?? shortId(node.id, 10, 5)}`;
          row.addEventListener('click', () => selectCognitiveNode(node.id));
          relationsGroup.appendChild(row);
        }
      }

      const clear = el('button', 'mind-ctrl-btn mind-inspector-wide-button');
      clear.type = 'button';
      clear.textContent = 'Clear selection';
      clear.addEventListener('click', () => {
        graph.selectedNodeId = null;
        const canvas = document.getElementById('mind-cognition-canvas');
        if (canvas) onRebuild?.(canvas.width || 900, canvas.height || 600);
        renderCognitionInspector();
        graph.alpha = Math.max(graph.alpha, 0.08);
        onReheat?.();
      });
      panel.appendChild(clear);
      return;
    }
  
    const sectorFocus = focusedSectorContext();
    if (sectorFocus) {
      const label = graph.sectorLabels.get(sectorFocus.sectorId) ?? 'S-???';
      const description = graph.sectorDescriptions.get(sectorFocus.sectorId);
      const members = graph.nodes.filter(node => sectorFocus.local.has(node.id));
      const bridgeEdges = graph.edges.filter(edge => {
        const sourceLocal = sectorFocus.local.has(edge.source.id);
        const targetLocal = sectorFocus.local.has(edge.target.id);
        return sourceLocal !== targetLocal;
      });
      const kinds = {};
      for (const node of members) kinds[node.kind] = (kinds[node.kind] ?? 0) + 1;
      const activity = members.length
        ? members.reduce((sum, node) => sum + finiteNumber(node.activationLevel, 0), 0) / members.length
        : 0;
  
      const title = el('div', 'mind-inspector-title');
      title.textContent = `${label} · ${description?.interpretation ?? 'emergent sector'}`;
      const subtitle = el('div', 'mind-inspector-subtitle');
      subtitle.textContent = 'Observer-side region focus. Shape and membership are derived from graph relations and are not fed back to Symbiont.';
      panel.append(title, subtitle);
  
      inspectorMetric(panel, 'Nodes', members.length);
      inspectorMetric(panel, 'Mean activity', pct(activity), PAL.cyan);
      const lineageLabel = graph.sectorLabels.get(sectorFocus.sectorId) ?? null;
      const lineage = lineageLabel ? graph.regionLineage.get(lineageLabel) : null;
      if (!graph.replaySnapshot && lineage) {
        inspectorMetric(panel, 'Region since', `t${lineage.firstTick}`);
        inspectorMetric(panel, 'Lineage observations', lineage.observations);
      }
      const regionShape = graph.dimension === '3d'
        ? graph.atlasRegionGeometry3d.get(sectorFocus.sectorId)
        : graph.atlasRegionGeometry2d.get(sectorFocus.sectorId);
      const proto = graph.protoSubregions.get(sectorFocus.sectorId) ?? [];
      if (regionShape) {
        inspectorMetric(panel, 'Boundary tension', pct(regionShape.tension ?? 0), (regionShape.tension ?? 0) > 0.6 ? PAL.amber : PAL.muted);
        inspectorMetric(panel, 'Proto-subregions', proto.length, proto.length ? PAL.violet : PAL.muted);
        inspectorMetric(panel, 'Cartographic functional center', `${regionShape.functionalCenter?.x?.toFixed?.(0) ?? '—'}, ${regionShape.functionalCenter?.y?.toFixed?.(0) ?? '—'}`);
        const trail = regionShape.trail ?? [];
        const displacement = trail.length > 1
          ? Math.hypot(
              trail[trail.length - 1].x - trail[0].x,
              trail[trail.length - 1].y - trail[0].y,
            )
          : 0;
        inspectorMetric(panel, 'Center displacement (observer layout)', displacement.toFixed(1));
      }
      inspectorMetric(panel, 'External bridge endpoints', sectorFocus.bridges.size);
      inspectorMetric(panel, 'Cross-region relations', bridgeEdges.length);
      inspectorMetric(
        panel,
        'Composition',
        Object.entries(kinds)
          .sort((a,b) => b[1] - a[1])
          .map(([kind, count]) => `${count} ${kind}`)
          .join(' · ') || '—',
      );
  
      const bridgeTitle = el('div', 'mind-inspector-section-title');
      bridgeTitle.textContent = 'Corridors to other regions';
      panel.appendChild(bridgeTitle);
  
      const bridgeGroups = new Map();
      for (const edge of bridgeEdges) {
        const outside = sectorFocus.local.has(edge.source.id) ? edge.target : edge.source;
        const outsideSector = outside.community && outside.community !== 'isolated'
          ? (graph.sectorLabels.get(outside.community) ?? 'unresolved')
          : 'unintegrated';
        const item = bridgeGroups.get(outsideSector) ?? { count: 0, nodes: new Set() };
        item.count += 1;
        item.nodes.add(outside.id);
        bridgeGroups.set(outsideSector, item);
      }
  
      if (!bridgeGroups.size) {
        const empty = el('div', 'mind-inspector-empty');
        empty.textContent = 'No external bridges in the current view.';
        panel.appendChild(empty);
      } else {
        for (const [target, item] of [...bridgeGroups.entries()].sort((a,b) => b[1].count - a[1].count)) {
          appendInspectorLine(panel, [
            { text: target, strong: true },
            ` · ${item.count} relations · ${item.nodes.size} endpoints`,
          ], 'mind-inspector-line mind-inspector-divider');
        }
      }
  
      const back = el('button', 'mind-ctrl-btn mind-inspector-wide-button');
      back.type = 'button';
      back.textContent = 'Back to all regions';
      back.addEventListener('click', () => {
        graph.focusedSectorId = null;
        graph.selectedNodeId = null;
        renderCognitionInspector();
        graph.alpha = Math.max(graph.alpha, 0.12);
        onReheat?.();
      });
      panel.appendChild(back);
      return;
    }
  
    const title = el('div', 'mind-inspector-title');
    title.textContent = 'Cognitive Atlas';
    const subtitle = el('div', 'mind-inspector-subtitle');
    subtitle.textContent = `${atlasModeMeta().label} · ${atlasModeMeta().description}. Regions are observer-derived from graph relations and never fed back to Symbiont.`;
    panel.append(title, subtitle);

    const situation = graph.cognitiveSituation;
    if (situation) {
      const situationTitle = el('div', 'mind-inspector-section-title mind-inspector-situation-title');
      situationTitle.textContent = 'Current observed process';
      panel.appendChild(situationTitle);

      const stageWrap = el('div', 'mind-inspector-stage-list');
      for (const stage of situation.stages ?? []) {
        appendInspectorStage(stageWrap, stage);
      }
      panel.appendChild(stageWrap);

      inspectorMetric(panel, 'Active regions', situation.activeRegionCount, PAL.cyan);
      inspectorMetric(panel, 'Prediction pressure', pct(situation.prediction.pressure), situation.prediction.pressure > 0.5 ? PAL.amber : PAL.muted);
      inspectorMetric(panel, 'Learning zones', situation.learning.zones, situation.learning.zones ? PAL.amber : PAL.muted);
      inspectorMetric(panel, 'Recent relation coverage', pct(situation.flow.relationCoverage), PAL.cyan);
      inspectorMetric(panel, 'Observed motor paths', situation.flow.motorPaths, situation.flow.motorPaths ? PAL.mint : PAL.muted);
      inspectorMetric(panel, 'Motor origin', situation.motorOrigin ?? 'none');

      const evidenceNote = el('div', 'mind-inspector-evidence-note');
      evidenceNote.textContent =
        'Observer evidence only · no inferred intent · no feedback to Symbiont.';
      panel.appendChild(evidenceNote);
    }
  
    const componentSizes = (graph.components ?? []).map(component => component.length);
    if (componentSizes.length) {
      const isolates = componentSizes.filter(size => size === 1).length;
      const objective = el('div', 'mind-inspector-objective');
      appendInspectorLine(objective, [{ text: 'Connected components', strong: true }]);
      appendInspectorLine(
        objective,
        [`${componentSizes.length} total · main ${componentSizes[0] ?? 0} nodes · ${isolates} isolates`],
      );
      panel.appendChild(objective);
    }
  
    const sectors = [...graph.communities.entries()]
      .map(([id, ids]) => {
        const sectorNodes = ids.map(nodeId => graph.nodes.find(node => node.id === nodeId)).filter(Boolean);
        const kinds = {};
        for (const node of sectorNodes) kinds[node.kind] = (kinds[node.kind] ?? 0) + 1;
        const activity = sectorNodes.length
          ? sectorNodes.reduce((sum, node) => sum + finiteNumber(node.activationLevel, 0), 0) / sectorNodes.length
          : 0;
        const atlasRegion = (graph.atlasRegions ?? []).find(region => region.id === id) ?? null;
        return { id, ids, sectorNodes, kinds, activity, atlasRegion };
      })
      .sort((a, b) => b.ids.length - a.ids.length);
  
    if (!sectors.length) {
      const empty = el('div', 'mind-inspector-empty');
      empty.textContent = 'No multi-node sectors in the current view.';
      panel.appendChild(empty);
    }
  
    sectors.slice(0, 10).forEach((sector) => {
      const card = el('button', 'mind-inspector-sector-card');
      card.type = 'button';
      card.dataset.sectorId = sector.id;
      const head = el('div', 'mind-inspector-sector-head');
      const name = el('strong', '');
      const description = graph.sectorDescriptions.get(sector.id);
      name.textContent = `${graph.sectorLabels.get(sector.id) ?? 'S-???'} · ${description?.interpretation ?? 'emergent sector'}`;
      const count = el('span', '');
      count.style.color = 'var(--muted)';
      count.textContent = `${sector.ids.length} nodes`;
      head.append(name, count);
      const composition = el('div', 'mind-inspector-sector-composition');
      composition.textContent = Object.entries(sector.kinds)
        .sort((a,b) => b[1] - a[1])
        .map(([kind, n]) => `${n} ${kind}`)
        .join(' · ');
      const activity = el('div', 'mind-inspector-sector-activity');
      const regionScore = atlasRegionScore(sector.atlasRegion);
      activity.textContent = `${atlasModeMeta().label.toLowerCase()} ${pct(regionScore)} · activity ${pct(sector.activity)} · ${sector.atlasRegion?.bridges ?? 0} bridges`;
      card.append(head, composition, activity);
      card.addEventListener('click', () => {
        graph.focusedSectorId = sector.id;
        graph.selectedNodeId = null;
        renderCognitionInspector();
        graph.alpha = Math.max(graph.alpha, 0.12);
        onReheat?.();
      });
      panel.appendChild(card);
    });
  
    const structures = graph.cognitiveStructures ?? { hubs: [], bottlenecks: [], loops: [] };
    const structuresTitle = el('div', 'mind-inspector-section-title mind-inspector-section-title-spaced');
    structuresTitle.textContent = 'Higher-order structures';
    panel.appendChild(structuresTitle);

    appendInspectorLine(panel, [
      { text: structures.hubs.length, strong: true }, ' hubs · ',
      { text: structures.bottlenecks.length, strong: true }, ' bottlenecks · ',
      { text: structures.loops.length, strong: true }, ' recurrent loops',
    ], 'mind-inspector-line');

    for (const item of structures.hubs.slice(0, 3)) {
      const row = el('button', 'mind-inspector-structure-button');
      row.type = 'button';
      const label = el('span', '');
      label.append(document.createTextNode('hub · '));
      const id = el('strong', '');
      id.textContent = shortId(item.id, 10, 5);
      label.appendChild(id);
      const degree = el('span', '');
      degree.textContent = `degree ${item.degree}`;
      row.append(label, degree);
      row.addEventListener('click', () => selectCognitiveNode(item.id));
      panel.appendChild(row);
    }

    const flow = graph.observedFlow ?? { paths: [], recentEdgeCount: 0, windowTicks: 48 };
    const flowTitle = el('div', 'mind-inspector-section-title mind-inspector-section-title-spaced');
    flowTitle.textContent = 'Observed cognitive flow';
    panel.appendChild(flowTitle);
    const flowSummary = el('div', 'mind-inspector-flow-summary');
    flowSummary.textContent =
      `${flow.recentEdgeCount} relations used within ${flow.windowTicks} ticks · ${flow.paths.length} observed paths`;
    panel.appendChild(flowSummary);
    for (const path of flow.paths.slice(0, 3)) {
      const row = el('div', 'mind-inspector-history-row');
      row.textContent = path.nodeIds
        .slice(0, 6)
        .map(id => shortId(id, 7, 4))
        .join(' → ') + (path.nodeIds.length > 6 ? ' → …' : '');
      panel.appendChild(row);
    }

    if ((graph.cognitiveEpisodes ?? []).length) {
      const episodeTitle = el('div', 'mind-inspector-section-title mind-inspector-section-title-spaced');
      episodeTitle.textContent = 'Recent Cognitive Episodes';
      panel.appendChild(episodeTitle);
      for (const episode of graph.cognitiveEpisodes.slice(-3).reverse()) {
        const totals = episode.totals ?? {};
        const context = episode.context ?? {};
        const row = el('div', 'mind-inspector-episode');
        appendInspectorLine(row, [
          { text: `t${episode.startTick}–t${episode.endTick}`, strong: true },
          ` · ${episode.events.length} windows`,
        ]);
        appendInspectorLine(row, [
          `+${totals.addedNodes ?? 0}/-${totals.removedNodes ?? 0} nodes · ` +
          `+${totals.addedEdges ?? 0}/-${totals.removedEdges ?? 0} relations`,
        ]);
        if (context.motorOrigins?.length) {
          appendInspectorLine(row, [`motor: ${context.motorOrigins.join(' → ')}`]);
        }
        panel.appendChild(row);
      }
    }

    if (graph.atlasDiff) {
      const diff = graph.atlasDiff;
      const diffTitle = el('div', 'mind-inspector-section-title mind-inspector-section-title-spaced');
      diffTitle.textContent = `Diff from t${graph.diffBaselineTick ?? '—'}`;
      panel.appendChild(diffTitle);
      const diffSummary = el('div', 'mind-inspector-diff');
      const diffInsight = summarizeDiff(diff, graph.nodes, graph.atlasRegions);
      appendInspectorLine(diffSummary, [
        `+${diff.addedNodes.length} nodes · -${diff.removedNodes.length} nodes · +${diff.addedEdges.length} relations · -${diff.removedEdges.length} relations · ${diff.changedEdges.length} changed`,
      ]);
      if (diffInsight?.topRegion) {
        appendInspectorLine(diffSummary, [
          'top changed region: ',
          { text: diffInsight.topRegion.label ?? diffInsight.topRegion.id, strong: true },
        ]);
      }
      if (diffInsight?.topNode) {
        appendInspectorLine(diffSummary, [
          'most changed node: ',
          { text: shortId(diffInsight.topNode.id, 10, 5), strong: true },
        ]);
      }
      appendInspectorLine(diffSummary, [
        'largest delta type: ',
        { text: diffInsight?.largestDeltaType ?? 'none', strong: true },
      ]);
      appendInspectorLine(diffSummary, [
        'cognition→motor linkage changed: ',
        { text: diffInsight?.motorLinkageChanged ? 'yes' : 'no', strong: true },
      ]);
      panel.appendChild(diffSummary);
    }

    if ((graph.regionEventHistory ?? []).length) {
      const regionTitle = el('div', 'mind-inspector-section-title mind-inspector-section-title-spaced');
      regionTitle.textContent = 'Region lineage';
      panel.appendChild(regionTitle);
      for (const event of graph.regionEventHistory.slice(-5).reverse()) {
        const row = el('div', 'mind-inspector-history-row');
        const detail =
          event.type === 'region-split' ? ` → ${(event.into ?? []).join(', ')}` :
          event.type === 'region-merged' ? ` ← ${(event.from ?? []).join(', ')}` :
          '';
        row.textContent = `t${event.tick} · ${event.label} · ${event.type.replace('region-', '')}${detail}`;
        panel.appendChild(row);
      }
    }

    if ((graph.learningFrontierClusters ?? []).length) {
      const frontierTitle = el('div', 'mind-inspector-section-title mind-inspector-section-title-spaced');
      frontierTitle.textContent = 'Learning frontier zones';
      panel.appendChild(frontierTitle);
      for (const cluster of graph.learningFrontierClusters.slice(0, 5)) {
        const block = el('div', 'mind-inspector-frontier');
        appendInspectorLine(block, [
          { text: `${cluster.nodeIds.length} learning nodes`, strong: true },
          ` · peak ${Math.round(cluster.maxScore * 100)}% · mean ${Math.round(cluster.meanScore * 100)}%`,
        ]);
        appendInspectorLine(block, [
          `${cluster.boundaryIds.length} boundary contacts · ${cluster.communities.length} regions · ${cluster.observations ?? 1} observations`,
        ]);
        appendInspectorLine(block, [
          `+${cluster.enteredIds?.length ?? 0} entered · -${cluster.exitedIds?.length ?? 0} exited · continuity ${Math.round((cluster.previousOverlap ?? 0) * 100)}%`,
        ]);
        panel.appendChild(block);
        for (const id of cluster.nodeIds.slice(0, 3)) {
          const node = graph.nodes.find(item => item.id === id);
          if (!node) continue;
          const row = el('button', 'mind-inspector-frontier-button');
          row.type = 'button';
          row.textContent = `${node.kind} · ${node.observerLabel ?? shortId(node.id, 10, 5)}`;
          row.addEventListener('click', () => selectCognitiveNode(node.id));
          panel.appendChild(row);
        }
      }
    }

    const usage = el('div', 'mind-inspector-usage');
    const topMode = Object.entries(observerUsage.modeChanges ?? {})
      .sort((a,b) => b[1] - a[1])[0];
    usage.textContent =
      `observer use · selections ${observerUsage.selections} · regions ${observerUsage.regionFocuses} · timeline ${observerUsage.timelineScrubs} · diff ${observerUsage.diffUses} · traces ${observerUsage.flowTraces}` +
      (topMode ? ` · top mode ${topMode[0]}` : '');
    panel.appendChild(usage);

    const hint = el('div', 'mind-inspector-hint');
    hint.textContent = 'Region → local graph → node → exact evidence. Select a node to reveal a real cognitive pathway when one exists.';
    panel.appendChild(hint);
  }
  

  return {
    render: renderCognitionInspector,
  };
}
