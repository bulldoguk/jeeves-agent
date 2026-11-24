"""HA-55: a watched entity ID that no longer exists in Home Assistant raises its own issue.

Run from jeeves_agent/:  python3 -m unittest discover -s tests -t .
Entity IDs here are made up.
"""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from jeeves import watchers as W
from jeeves.store import IssueStore

T0 = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)


class NotFound(Exception):
    """Shaped like requests.HTTPError for a 404."""
    def __init__(self):
        super().__init__("404 Client Error: Not Found")
        self.response = SimpleNamespace(status_code=404)


class FakeHA:
    def __init__(self, present, fail=False):
        self.present, self.fail = set(present), fail

    def get_all_states(self):
        if self.fail:
            raise ConnectionError("HA down")
        return [{"entity_id": e, "state": "21", "last_changed": T0.isoformat()} for e in self.present]

    def get_state(self, entity_id):
        if entity_id not in self.present:
            raise NotFound()
        return {"entity_id": entity_id, "state": "21", "last_changed": T0.isoformat()}

    def get_history(self, entity_id, hours=24):
        if entity_id not in self.present:
            raise NotFound()
        return []


def config(**kw):
    base = dict(watch_temperature_entities=[], watch_humidity_entities=[], watch_camera_entities=[],
                watch_camera_motion_entities=[], circuit_switches=[])
    base.update(kw)
    return SimpleNamespace(**base)


class MissingEntities(unittest.TestCase):
    def setUp(self):
        self.store = IssueStore(":memory:")

    def run_at(self, ha, cfg, minutes):
        return W.check_missing_entities(ha, None, self.store, cfg, T0 + timedelta(minutes=minutes))

    def test_present_ids_raise_nothing(self):
        cfg = config(watch_temperature_entities=["sensor.lounge_temperature"])
        self.assertEqual(self.run_at(FakeHA(["sensor.lounge_temperature"]), cfg, 0), [])

    def test_missing_id_waits_out_the_grace_period_then_opens(self):
        cfg = config(watch_humidity_entities=["sensor.old_humidity"])
        ha = FakeHA(["sensor.something_else"])
        self.assertEqual(self.run_at(ha, cfg, 0), [])
        self.assertEqual(self.run_at(ha, cfg, W.MISSING_GRACE_MINUTES - 1), [])
        issues = self.run_at(ha, cfg, W.MISSING_GRACE_MINUTES)
        self.assertEqual([i.key for i in issues], ["missing:sensor.old_humidity"])
        self.assertIn("doesn't exist in Home Assistant", issues[0].summary)

    def test_an_id_that_comes_back_resets_the_clock(self):
        cfg = config(watch_camera_entities=["camera.porch"])
        self.run_at(FakeHA(["x.y"]), cfg, 0)
        self.assertEqual(self.run_at(FakeHA(["camera.porch"]), cfg, 10), [])
        self.assertEqual(self.run_at(FakeHA(["x.y"]), cfg, 20), [])           # new absence, new grace period
        self.assertEqual(len(self.run_at(FakeHA(["x.y"]), cfg, 20 + W.MISSING_GRACE_MINUTES)), 1)

    def test_an_open_issue_stays_open_without_waiting_again(self):
        cfg = config(watch_temperature_entities=["sensor.gone"])
        self.store.open_issue("missing:sensor.gone", "x", T0.isoformat())
        self.assertEqual(len(self.run_at(FakeHA(["x.y"]), cfg, 0)), 1)

    def test_failed_or_empty_state_fetch_raises_nothing(self):
        cfg = config(watch_temperature_entities=["sensor.a"], watch_camera_motion_entities=["binary_sensor.b"])
        self.assertEqual(self.run_at(FakeHA([], fail=True), cfg, 0), [])
        self.assertEqual(self.run_at(FakeHA([]), cfg, 999), [])             # HA half-started: no flood
        self.assertEqual(self.store.get_meta("missing_since:sensor.a"), "")  # and no clock started

    def test_a_mix_reports_only_the_missing_ids_including_motion_and_circuit_pairs(self):
        cfg = config(watch_temperature_entities=["sensor.here", "sensor.gone"],
                     watch_camera_motion_entities=["binary_sensor.gone_motion"],
                     circuit_switches=["switch.here:light.gone_bulb", "switch.gone:light.here"])
        ha = FakeHA(["sensor.here", "switch.here", "light.here"])
        self.run_at(ha, cfg, 0)
        keys = sorted(i.key for i in self.run_at(ha, cfg, W.MISSING_GRACE_MINUTES))
        self.assertEqual(keys, ["missing:binary_sensor.gone_motion", "missing:light.gone_bulb",
                                "missing:sensor.gone", "missing:switch.gone"])

    def test_nothing_configured_makes_no_call(self):
        class Boom(FakeHA):
            def get_all_states(self):
                raise AssertionError("should not be called")
        self.assertEqual(self.run_at(Boom([]), config(), 0), [])


class NoDoubleAlert(unittest.TestCase):
    """A 404 is the missing watcher's issue; the per-entity checks no longer call it 'unreachable'."""

    def test_missing_ids_are_not_also_unreachable(self):
        cfg = config(watch_temperature_entities=["sensor.gone"], watch_humidity_entities=["sensor.gone_h"],
                     watch_camera_entities=["camera.gone"], watch_camera_motion_entities=["binary_sensor.gone"])
        ha, store = FakeHA([]), IssueStore(":memory:")
        for check in (W.check_stale_entities, W.check_temperature_anomalies, W.check_humidity_anomalies,
                      W.check_camera_event_rate):
            self.assertEqual(check(ha, None, store, cfg, T0), [], check.__name__)

    def test_other_errors_are_still_unreachable(self):
        class Down(FakeHA):
            def get_state(self, entity_id):
                raise ConnectionError("timeout")
        issues = W.check_stale_entities(Down([]), None, IssueStore(":memory:"),
                                        config(watch_temperature_entities=["sensor.a"]), T0)
        self.assertEqual([i.key for i in issues], ["unreachable:sensor.a"])

    def test_the_watcher_is_registered(self):
        self.assertIn(W.check_missing_entities, W.WATCHERS)


if __name__ == "__main__":
    unittest.main()
