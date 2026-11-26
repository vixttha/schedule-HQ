import copy
import json
import tempfile
import unittest
from pathlib import Path
from tools.check import ROOT, load

def event(**changes):
    receipt=load(ROOT/"examples/receipt.json")
    receipt.update(example=False,classification="BLOCKED",scheduled_at="2026-01-01T01:00:00Z",
                   started_at="2026-01-01T00:50:00Z",completed_at="2026-01-01T00:55:00Z")
    return dict(schema_version=1,repository_id=123,installation="test-install",provider="fixture",
                run_id="run-1",attempt=1,sequence=1,observed_at="2026-01-01T01:01:00Z",
                provenance="synthetic",receipt=receipt)|changes

class HistoryContracts(unittest.TestCase):
    def test_valid_and_stable(self):
        from schedule_hq.history.events import validate_event, event_key, event_digest
        e=event();validate_event(e)
        self.assertEqual(event_key(e),event_key(copy.deepcopy(e)))
        self.assertEqual(event_digest(e),event_digest(dict(reversed(list(e.items())))))
        self.assertNotEqual(event_key(e),event_key(event(sequence=2)))
        self.assertNotEqual(event_key(e),event_key(event(repository_id=124)))
    def test_bad_fields(self):
        from schedule_hq.history.events import validate_event
        for patch in ({"repository_id":True},{"repository_id":0},{"attempt":0},{"sequence":False},
                      {"installation":"../x"},{"run_id":""},{"provider":"bad /path"},
                      {"observed_at":"2026-01-01T00:54:00Z"},{"schema_version":2},
                      {"provenance":"magic"},{"secret":"leak"}):
            with self.subTest(patch=patch),self.assertRaises(ValueError):validate_event(event(**patch))
    def test_authentication_is_external(self):
        from schedule_hq.history.events import ingest
        payload=json.dumps(event(provenance="authenticated")).encode()
        with self.assertRaises(ValueError):ingest(payload)
        self.assertEqual(ingest(payload,authenticated=True)["provenance"],"authenticated")
    def test_bad_ingress(self):
        from schedule_hq.history.events import ingest
        for data in (b'{"x":1,"x":2}',b'{"x":NaN}',b'\xff',b' '*65537,b'['*4000):
            with self.subTest(data=len(data)),self.assertRaisesRegex(ValueError,"^invalid observation$"):ingest(data)
    def test_example_not_observation(self):
        from schedule_hq.history.events import validate_event
        e=event(receipt=load(ROOT/"examples/receipt.json"))
        with self.assertRaises(ValueError):validate_event(e)
