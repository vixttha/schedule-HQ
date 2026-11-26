import tempfile,unittest
from pathlib import Path
from tools.check import ROOT
from test_execution_history import observation
from schedule_hq.history.reconcile import reconcile
from schedule_hq.history.store import History
from schedule_hq.history.events import event_key

class DirectReconciliation(unittest.TestCase):
    def test_direct_reconciliation_rejects_cross_slot_run(self):
        first=observation()
        second=observation(sequence=2,attempt=2)
        second["receipt"]["scheduled_at"]="2026-01-01T02:00:00Z"
        for events in ([first,second],[second,first]):
            for end in ("2026-01-01T02:00:00Z","2026-01-01T03:00:00Z"):
                with self.subTest(end=end),self.assertRaises(ValueError):
                    reconcile(events,repository_id=123,installation="test-install",provider="fixture",task="development",
                        start="2026-01-01T01:00:00Z",end=end,now="2026-01-01T03:00:00Z",
                        grace=60,history_complete=True,simulation=True)
    def test_distinct_runs_in_distinct_slots_allowed(self):
        first=observation()
        second=observation(run_id="other",sequence=1)
        second["receipt"]["scheduled_at"]="2026-01-01T02:00:00Z"
        report=reconcile([first,second],repository_id=123,installation="test-install",provider="fixture",task="development",
             start="2026-01-01T01:00:00Z",end="2026-01-01T03:00:00Z",now="2026-01-01T03:00:00Z",
             grace=60,history_complete=True,simulation=True)
        self.assertEqual([r["state"] for r in report],["COMPLETED","COMPLETED"])

class HistoricalAcknowledgments(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.h=History(self.root,123,"test-install")
        self.kw=dict(associated=True,delivery_supported=True,readback_supported=True,observation_verified=True)
    def prepare(self,n,task="development"):
        e=observation(sequence=n,provenance="authenticated",observed_at=f"2026-01-01T01:{n:02d}:00Z")
        e["receipt"]["task_id"]=task
        e["receipt"]["next_action"]=f"changed result {n}"
        self.h.append(e,authenticated=True)
        p=self.h.prepare_delivery(event_key(e),"private",**self.kw)
        self.assertEqual(p["decision"],"REPORT")
        return p["intent"]
    def test_historical_ack_reuse_after_restart(self):
        one=self.prepare(1);self.h.ack_delivery(one,"private","ack-1",verified=True)
        two=self.prepare(2);self.h.ack_delivery(two,"private","ack-2",verified=True)
        self.h=History(self.root,123,"test-install")
        three=self.prepare(3,"verification")
        before=self.h.export_private()
        with self.assertRaises(ValueError):self.h.ack_delivery(three,"private","ack-1",verified=True)
        self.assertEqual(self.h.export_private(),before)
        self.assertEqual(self.h.ack_delivery(three,"private","ack-3",verified=True),"ACKNOWLEDGED")
    def test_historical_exact_ack_replay_after_restore(self):
        one=self.prepare(1);self.h.ack_delivery(one,"private","ack-1",verified=True)
        two=self.prepare(2);self.h.ack_delivery(two,"private","ack-2",verified=True)
        with tempfile.TemporaryDirectory() as d:
            restored=History(Path(d),123,"test-install");restored.restore_empty(self.h.export_private())
            before=restored.export_private()
            self.assertEqual(restored.ack_delivery(one,"private","ack-1",verified=True),"DUPLICATE")
            with self.assertRaises(ValueError):restored.ack_delivery(one,"private","different",verified=True)
            self.assertEqual(restored.export_private(),before)
