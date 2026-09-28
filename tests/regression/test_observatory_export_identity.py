"""Execute the actual export module with deterministic deferred network responses."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "scenario",
    [
        "switch",
        "fallback",
        "unavailable",
        "run_id",
        "instance_id",
        "last_sequence",
        "topology_revision",
        "summary_run",
        "manifest_run",
    ],
)
def test_async_exports_preserve_captured_identity(scenario):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is needed to execute Observatory exports")
    root = Path(__file__).resolve().parents[2]
    script = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const scenario = SCENARIO;
const snapshot = {run_id:'run-A', tick:10, cognition:{topology_revision:3}};
const state = {source:'local server', instanceId:'A', runId:'run-A',
 sequence:7, schemaVersion:4, realTick:10, acceptedSnapshots:2, rejectedSnapshots:1,
 lastRawSnapshot:scenario === 'fallback' ? null : snapshot,
 topology:{topologyRevision:3, nodes:[{id:'A'}]}};
const manifest = {projection:'observatory-provenance-v1', instance_id:'A',
 run_id:'run-A', last_sequence:7, tick:10, topology_revision:3, schema_version:4};
// The actual server summary has no instance_id/sequence and covers many ticks.
const summary = {summary_version:1, run_id:'run-A', tick_range:{min:0,max:20}, segments:[]};
if (['run_id','instance_id','last_sequence','topology_revision'].includes(scenario)) {
 manifest[scenario] = typeof manifest[scenario] === 'number' ? 99 : 'foreign';
}
if (scenario === 'summary_run') summary.run_id = 'foreign';
if (scenario === 'manifest_run') manifest.run_id = 'foreign';
let release;
const gate = new Promise(resolve => release = resolve);
const downloads = [], requests = [], toasts = [];
const context = {state, structuredClone, Blob, Date,
 currentSnapshot:()=>snapshot, showToast:message=>toasts.push(message),
 fetch:async path=>{requests.push(path); await gate;
   return {ok:scenario !== 'unavailable', status:404,
     json:async()=>path.endsWith('/manifest') ? manifest : summary};},
 URL:{createObjectURL:blob=>{downloads.push(blob);return 'blob:test';},revokeObjectURL(){}},
 document:{createElement:()=>({click(){}})}};
vm.createContext(context);
const source = fs.readFileSync('observatory/ui/exports.js','utf8')
 .replace(/^import .*;\n/gm,'').replace(/^export \{.*\};$/gm,'');
vm.runInContext(source,context);
(async()=>{
 const pending = scenario === 'manifest_run' ? context.exportManifest() : context.exportEvidenceBundle();
 snapshot.run_id = 'run-B';
 state.topology.nodes[0].id = 'B';
 Object.assign(state,{source:'replay',instanceId:'B',runId:'run-B',sequence:8,
 realTick:11,acceptedSnapshots:3,rejectedSnapshots:4});
 release();
 await pending;
 assert.ok(requests.every(path=>path.startsWith('/instance/A/')));
 if (!['switch','fallback','unavailable'].includes(scenario)) {
   assert.equal(downloads.length,0);
   assert.match(toasts.at(-1),/incompatible|compatible/);
   return;
 }
 assert.equal(downloads.length,1);
 const bundle = JSON.parse(await downloads[0].text());
 assert.equal(bundle.snapshot.run_id,'run-A');
 assert.equal(bundle.provenance.source,'local server');
 assert.equal(bundle.provenance.instance_id,'A');
 assert.equal(bundle.provenance.run_id,'run-A');
 assert.equal(bundle.provenance.sequence,7);
 assert.equal(bundle.provenance.tick,10);
 assert.equal(bundle.provenance.accepted_snapshots_browser_session,2);
 assert.equal(bundle.provenance.rejected_snapshots_browser_session,1);
 assert.equal(bundle.topology.nodes[0].id,'A');
 if (scenario === 'unavailable') {
   assert.equal(bundle.manifest,null);
   assert.equal(bundle.history_summary,null);
 } else {
   assert.equal(bundle.manifest.run_id,'run-A');
   assert.equal(bundle.history_summary.run_id,'run-A');
 }
})().catch(error=>{console.error(error);process.exitCode=1;});
""".replace("SCENARIO", json.dumps(scenario))
    result = subprocess.run(
        [node, "-e", script], cwd=root, capture_output=True, text=True, timeout=15
    )
    assert result.returncode == 0, result.stderr
