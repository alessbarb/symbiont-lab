"""Execute the actual browser reducer without a DOM or WebGL dependency."""

import shutil
import subprocess
from pathlib import Path

import pytest


def test_client_rejects_gaps_and_stale_responses_and_reconciles_removals():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is needed to execute the browser reducer")
    root = Path(__file__).resolve().parents[4]
    module = root / "src/symbiont_lab/workbench/web/views/body/world-state.js"
    script = """
import assert from 'node:assert/strict';
const {reconcileWorld} = await import(MODULE);
const first={contract:'body-in-world-v1',kind:'snapshot',world_id:'w',revision:1,
 entities:{x:{position:[1,0,0]}}};
const current=reconcileWorld(null,first).state;
const gap={contract:first.contract,kind:'delta',world_id:'w',revision:3,base_revision:2};
assert.equal(reconcileWorld(current,gap).gap,true);
const delta={...gap,revision:2,base_revision:1,
 transforms:{x:{position:[2,0,0]}},upserts:{y:{position:[3,0,0]}}};
const next=reconcileWorld(current,delta).state;
assert.deepEqual(next.entities.x.position,[2,0,0]);
assert.deepEqual(current.entities.x.position,[1,0,0]);
assert.equal(reconcileWorld(next,first).state,next);
assert.equal(reconcileWorld(next,delta).state,next);
const removed=reconcileWorld(next,{...delta,revision:3,base_revision:2,
 transforms:{},upserts:{},removals:['x']}).state;
assert.equal(removed.entities.x,undefined);
assert.equal(reconcileWorld(next,{...first,world_id:'new',revision:1,
 entities:{}}).state.world_id,'new');
""".replace("MODULE", repr(module.as_uri()))
    result = subprocess.run(
        [node, "--input-type=module", "-e", script], capture_output=True, text=True, timeout=15
    )
    assert result.returncode == 0, result.stderr
