import json,tempfile,unittest
from pathlib import Path
from tools.check import ROOT
from test_history_contracts import event

class LocalHistory(unittest.TestCase):
    def setUp(self):
        from schedule_hq.history.store import History
        self.History=History
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.store=History(self.root,123,"test-install")
    def test_append_replay_conflict_and_restart(self):
        e=event();self.assertEqual(self.store.append(e),"ADDED")
        self.assertEqual(self.store.append(e),"DUPLICATE")
        changed=event(observed_at="2026-01-01T01:02:00Z")
        with self.assertRaises(ValueError):self.store.append(changed)
        self.assertEqual(self.History(self.root,123,"test-install").events(),[e])
    def test_scope_isolation(self):
        with self.assertRaises(ValueError):self.store.append(event(repository_id=124))
        self.store.append(event())
        with self.assertRaises(ValueError):self.History(self.root,124,"test-install").events()
    def test_lock_fail_closed(self):
        (self.root/"history.lock").mkdir()
        with self.assertRaises(RuntimeError):self.store.append(event())
        self.assertFalse((self.root/"history.json").exists())
    def test_corrupt_snapshot_not_overwritten(self):
        p=self.root/"history.json";p.write_bytes(b'{"bad":')
        with self.assertRaises(ValueError):self.store.append(event())
        self.assertEqual(p.read_bytes(),b'{"bad":')
    def test_export_restore_no_overwrite(self):
        self.store.append(event(sequence=2));self.store.append(event())
        payload=self.store.export_private()
        with tempfile.TemporaryDirectory() as other:
            dst=self.History(Path(other),123,"test-install")
            dst.restore_empty(payload)
            self.assertEqual(dst.export_private(),payload)
            with self.assertRaises(ValueError):dst.restore_empty(payload)
    def test_tamper_detected(self):
        self.store.append(event());p=self.root/"history.json"
        d=json.loads(p.read_bytes());d["events"][0]["event"]["observed_at"]="2026-01-01T01:10:00Z"
        p.write_text(json.dumps(d),encoding="utf-8")
        with self.assertRaises(ValueError):self.store.events()
    def test_authenticated_assertion_requires_verified_ingress(self):
        with self.assertRaises(ValueError):self.store.append(event(provenance="authenticated"))
        self.assertEqual(self.store.append(event(provenance="authenticated"),authenticated=True),"ADDED")
    def test_failed_replace_leaves_existing_snapshot(self):
        from unittest.mock import patch
        self.store.append(event());before=self.store.export_private()
        with patch("schedule_hq.history.store.os.replace",side_effect=OSError("synthetic failure")):
            with self.assertRaises(OSError):self.store.append(event(sequence=2))
        self.assertEqual(self.store.export_private(),before)
    def test_symlink_snapshot(self):
        p=self.root/"target";p.write_text("private",encoding="utf-8")
        try:(self.root/"history.json").symlink_to(p)
        except OSError:self.skipTest("host cannot create symlink")
        with self.assertRaises(ValueError):self.store.append(event())
        self.assertEqual(p.read_text(encoding="utf-8"),"private")
