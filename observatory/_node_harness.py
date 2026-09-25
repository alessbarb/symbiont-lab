"""Compatibility forwarding shim for test harness."""

from observatory.tests._node_harness import NODE, ROOT, call_js, requires_node

__all__ = ["ROOT", "NODE", "requires_node", "call_js"]
