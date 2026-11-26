import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from tools.check import ROOT
from test_execution_history import observation

class JournalTests(unittest.TestCase):
    def setUp(self):
        from schedule_hq.history.store import History
        from schedule_hq.policy.authority import Lease
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.h=History(self.root,123,"test-install")
        self.authority=dict(task="development",authorized=True,authenticated_actor="actor",
            lease=Lease(123,4,"actor","a"*40,2,"2026-01-01T02:00:00Z"),repository_id=123,issue=4,
            head="a"*40,fence=2,now="2026-01-01T01:00:00Z",competing=False,atomic_supported=True)
    def test_write_intent_restart_readback(self):
        from schedule_hq.history.store import History
        token=self.h.prepare_write(self.authority,expected="b"*40)
        restored=History(self.root,123,"test-install")
        with self.assertRaises(ValueError):restored.prepare_write(self.authority,expected="c"*40)
        self.assertEqual(restored.reconcile_write(token,self.authority,observed="b"*40,
             observation_verified=True,intent_verified=True),"ALREADY_APPLIED")
        self.assertEqual(restored.reconcile_write(token,self.authority,observed="b"*40,
             observation_verified=True,intent_verified=True),"ALREADY_APPLIED")
        with self.assertRaises(ValueError):restored.prepare_write(self.authority,expected="b"*40)
    def test_write_denied_no_journal(self):
        for patch in ({"competing":True},{"authorized":False},{"atomic_supported":False},
                      {"now":"2026-01-01T02:00:00Z"},{"task":"verification"},{"fence":3}):
            with self.subTest(patch=patch),self.assertRaises(ValueError):
                self.h.prepare_write(self.authority|patch,expected="b"*40)
        self.assertFalse((self.root/"history.json").exists())
    def test_ambiguous_readback_does_not_clear(self):
        token=self.h.prepare_write(self.authority,expected="b"*40)
        self.assertEqual(self.h.reconcile_write(token,self.authority,observed="a"*40,
            observation_verified=True,intent_verified=True),"REAUTHORIZE")
        self.assertEqual(self.h.reconcile_write(token,self.authority,observed="c"*40,
            observation_verified=True,intent_verified=True),"CONFLICT")
        self.assertEqual(self.h.reconcile_write(token,self.authority,observed="b"*40,
            observation_verified=False,intent_verified=True),"BLOCKED")
        with self.assertRaises(ValueError):self.h.prepare_write(self.authority,expected="c"*40)
    def test_process_abandonment_preserves_history(self):
        self.h.append(observation());before=self.h.export_private()
        program="from pathlib import Path;import os,sys;p=Path(sys.argv[1]);(p/'history.lock').mkdir();(p/'.history-crash').write_bytes(b'partial');os._exit(17)"
        proc=subprocess.run([sys.executable,"-c",program,str(self.root)])
        self.assertEqual(proc.returncode,17)
        self.assertEqual(self.h.export_private(),before)
        with self.assertRaises(RuntimeError):self.h.append(observation(sequence=2))
        self.assertTrue((self.root/"history.lock").is_dir())
    def test_current_source_verification_required(self):
        from schedule_hq.history.events import event_key
        e=observation(provenance="authenticated");self.h.append(e,authenticated=True)
        self.assertEqual(self.h.prepare_delivery(event_key(e),"private",associated=True,
          delivery_supported=True,readback_supported=True)["decision"],"BLOCKED")
    def test_conflicting_run_slot_rejected(self):
        self.h.append(observation())
        e=observation(sequence=2);e["receipt"]["scheduled_at"]="2026-01-01T02:00:00Z"
        with self.assertRaises(ValueError):self.h.append(e)
    def test_replay_does_not_grant_write_after_restore(self):
        self.h.prepare_write(self.authority,expected="b"*40)
        payload=self.h.export_private()
        from schedule_hq.history.store import History
        with tempfile.TemporaryDirectory() as d:
            other=History(Path(d),123,"test-install");other.restore_empty(payload)
            with self.assertRaises(ValueError):other.prepare_write(self.authority,expected="c"*40)

    def test_suppressed_newer_observation_preserves_highwater(self):
        from schedule_hq.history.events import event_key
        first=observation(provenance="authenticated")
        newer=observation(provenance="authenticated",sequence=3,observed_at="2026-01-01T01:03:00Z")
        old=observation(provenance="authenticated",sequence=2,observed_at="2026-01-01T01:02:00Z")
        old["receipt"]["next_action"]="obsolete changed result"
        for e in (first,newer,old):self.h.append(e,authenticated=True)
        kw=dict(associated=True,delivery_supported=True,readback_supported=True,observation_verified=True)
        p=self.h.prepare_delivery(event_key(first),"private",**kw)
        self.h.ack_delivery(p["intent"],"private","ack-1",verified=True)
        self.assertEqual(self.h.prepare_delivery(event_key(newer),"private",**kw)["decision"],"SUPPRESS")
        self.assertEqual(self.h.prepare_delivery(event_key(old),"private",**kw)["decision"],"STALE")
