import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as Obj

from observatory.adapter import envelope, project_tick, write_replay


class AdapterTests(unittest.TestCase):
    def result(self):
        dissent = Obj(capability_id="compute.logical_cpu")
        narrative = Obj(capability_id="compute.logical_cpu", summary="Still learning this host.", uncertainty=3.0, evidence_gathered=2, dissent=dissent, contested=True)
        return Obj(tick=7, percepts=(Obj(name="system_load", quality=Obj(value="nominal")),), allocations=(Obj(name="compute.logical_cpu"),), investigated_capability="compute.logical_cpu", drift_observations={"system_load": Obj(kind=Obj(value="regime_shift"))}, dissent=dissent, narrative=(narrative,))

    def test_projects_only_bounded_abstract_state(self):
        acclimation = Obj(known_capabilities=("cpu", "disk"), acclimated_capabilities=("cpu",))
        snapshot = project_tick(self.result(), acclimation=acclimation, display_id="A-17", ticks_remaining=4)
        self.assertEqual(snapshot["schema_version"], 1)
        self.assertEqual(snapshot["organism"]["state"], "reflecting")
        self.assertEqual(snapshot["organism"]["acclimation"], 0.5)
        self.assertEqual(snapshot["organism"]["resource_budget"], {"ticks_remaining": 4})
        self.assertNotIn("value", snapshot["organism"]["percepts"][0])
        self.assertTrue(all(len(event["id"]) <= 64 for event in snapshot["organism"]["events"]))
        self.assertTrue(all(len(item) <= 200 for item in snapshot["organism"]["memory"]))
        def keys(value):
            if isinstance(value, dict):
                return set(value).union(*(keys(item) for item in value.values()))
            if isinstance(value, list):
                return set().union(*(keys(item) for item in value)) if value else set()
            return set()
        self.assertTrue({"hostname", "username", "timestamp", "source", "provider_id", "raw_value", "threat", "command"}.isdisjoint(keys(snapshot)))

    def test_envelope_matches_browser_contract(self):
        wrapped = envelope(project_tick(self.result()))
        self.assertEqual(wrapped["type"], "symbiont-observatory-snapshot")
        self.assertEqual(wrapped["snapshot"]["tick"], 7)

    def test_replay_is_atomic_and_bounded(self):
        snapshot = project_tick(self.result())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "replay.json"
            write_replay(path, [snapshot])
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["snapshots"][0]["tick"], 7)
            with self.assertRaises(ValueError):
                write_replay(path, [])


if __name__ == "__main__":
    unittest.main()
