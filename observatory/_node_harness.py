"""Compatibility forwarding shim for test harness."""

from observatory.tests._node_harness import ROOT, NODE, requires_node, call_js

__all__ = ["ROOT", "NODE", "requires_node", "call_js"]
