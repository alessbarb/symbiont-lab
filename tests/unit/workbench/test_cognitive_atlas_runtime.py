"""Execute observer analytics and the 2D edge-paint block in Node, without a browser."""

import shutil
import subprocess
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[3] / "src/symbiont_lab/workbench/web"


def run_js(body: str) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for executable JavaScript regressions")
    module = (WEB / "views/mind/cognitive-atlas.js").as_uri()
    result = subprocess.run(
        [
            node,
            "--input-type=module",
            "-e",
            f'import assert from "node:assert/strict"; import * as atlas from {module!r};\n' + body,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_recurrent_edges_preserve_evidence_without_structural_bridges():
    run_js("""
      const nodes = [{id: 'a', kind: 'concept', community: 'r'}];
      const edges = [{id: 'loop', sourceId: 'a', targetId: 'a',
        kind: 'excitatory', support: 10, plasticity: 0.9, lastUseTick: 100}];
      const index = atlas.buildAtlasGraph(nodes, edges);
      assert.equal(index.edges.length, 1);
      assert.equal(index.incident.get('a').length, 1);
      assert.equal(index.incoming.get('a').length, 1);
      assert.equal(index.outgoing.get('a').length, 1);
      assert.deepEqual(index.diagnostics.selfLoops, ['loop']);
      const signals = atlas.atlasSignals(nodes, edges, 100, {index});
      assert.ok(signals.get('a').learning > 0);
      assert.ok(signals.get('a').activity > 0);
      const anatomy = atlas.atlasAnatomy(index);
      assert.equal(anatomy.bridgeEdgeIds.size, 0);
      assert.equal(anatomy.nodes.get('a').degreeCentrality, 0);
      assert.equal(atlas.cognitivePath('a', nodes, edges), null);
    """)


def test_region_summary_matches_full_anatomy_without_all_pairs_metrics():
    run_js("""
      const nodes = ['a', 'b', 'c'].map(id => ({id, kind: 'concept', community: id === 'c' ? 's' : 'r'}));
      const edges = [{id: 'ab', sourceId: 'a', targetId: 'b', kind: 'excitatory'},
                     {id: 'bc', sourceId: 'b', targetId: 'c', kind: 'excitatory'}];
      const index = atlas.buildAtlasGraph(nodes, edges);
      const signals = atlas.atlasSignals(nodes, edges, 0, {index});
      const args = [nodes, edges, new Map(), new Map(), signals, index];
      const cheap = atlas.atlasRegions(...args);
      const full = atlas.atlasRegions(...args, {anatomy: atlas.atlasAnatomy(index)});
      assert.deepEqual(cheap, full);
      assert.ok(cheap.some(region => region.articulationPoints > 0));
    """)


def test_2d_edge_paint_executes_for_ordinary_and_path_edges():
    # Execute the real paint block with an instrumented canvas. This catches
    # unresolved locals that a JavaScript syntax check cannot detect.
    source = (WEB / "views/mind/cognition-controller.js").read_text()
    start = source.index("      let color;\n      // Edges reaching")
    end = source.index("    drawPresentationGhostEdges(ctx, now);", start)
    block = source[start:end].rstrip()
    assert block.endswith("}")
    block = block[:-1]  # enclosing edge loop, not part of the paint block
    run_js(
        """
      let strokes = 0;
      const ctx = new Proxy({}, {get: (target, key) => key in target ? target[key] : key === 'stroke'
        ? () => { strokes++; } : () => {}});
      const edge = {source: {x: 0, y: 0}, target: {x: 100, y: 50}, kind: 'excitatory'};
      const isConn = false, modeScore = 0.5, liveTick = 100, now = 0;
      const finiteNumber = (v, fallback) => Number.isFinite(v) ? v : fallback;
      const presentation = {edgePresentation: () => ({progress: 1, opacity: 1})};
      for (const pathEdge of [false, true]) {
    """
        + block
        + """
      }
      assert.equal(strokes, 2);
      assert.ok(Number.isFinite(ctx.globalAlpha));
    """
    )


def test_causal_estimates_are_not_treated_as_structural_edges():
    run_js("""
      const edge = {sourceId: 'a', targetId: 'b', kind: 'causal_estimate',
        support: 10, stableTicks: 100, weight: 1};
      assert.equal(atlas.atlasEdgeScore(edge, 'structure'), 0.03);
      assert.ok(atlas.atlasEdgeScore(edge, 'evidence') > 0);
      const index = atlas.buildAtlasGraph([{id: 'a'}, {id: 'b'}], [edge]);
      assert.equal(atlas.atlasAnatomy(index).bridgeEdgeIds.size, 0);
    """)


def test_dynamics_scores_combine_activity_learning_prediction_and_recency():
    run_js("""
      const node = {id: 'a'};
      for (const [field, expected] of Object.entries({activity: .42, learning: .28,
                                                    prediction: .20, recency: .10})) {
        const signals = new Map([['a', {[field]: 1}]]);
        assert.equal(atlas.atlasModeScore(node, signals, 'dynamics'), expected);
      }
    """)
