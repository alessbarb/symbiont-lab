"""Shared helper for tests that execute a pure, zero-import Observatory
frontend module via Node, since this repo has no JS test runner/bundler.
Only pure modules (no DOM, no imports) can be called this way.

IMPORTANT: a plain `import "./foo.js"` of an on-disk .js file is only
reliably treated as an ES module by Node's loader without a package.json
declaring "type": "module" on newer Node versions that auto-detect ESM
syntax (stabilized around Node 22-24) -- this repo's floor is Node 18,
where a bare .js import under `--input-type=module` can throw
"Unexpected token 'export'" because the file is parsed as CommonJS. Since
the plan's Global Constraints forbid adding a package.json just for tests,
this harness instead reads the module's source and imports it as a
`data:text/javascript;base64,...` URL -- data: URLs are unambiguously ESM
to Node's loader regardless of extension, package.json, or Node version,
so this works identically on Node 18 through 24+."""

import base64
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")

requires_node = unittest.skipUnless(NODE, "node is not on PATH")


def call_js(module_path: Path, export_name: str, arg) -> object:
    source = module_path.read_text(encoding="utf-8")
    encoded = base64.b64encode(source.encode("utf-8")).decode("ascii")
    specifier = f"data:text/javascript;base64,{encoded}"
    script = (
        f"import {{ {export_name} }} from {json.dumps(specifier)};"
        f"const result = {export_name}({json.dumps(arg)});"
        "process.stdout.write(JSON.stringify(result));"
    )
    completed = subprocess.run(
        [NODE, "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"node invocation failed: {completed.stderr}")
    return json.loads(completed.stdout)
