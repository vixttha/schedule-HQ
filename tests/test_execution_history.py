import copy,tempfile,unittest
from pathlib import Path
from tools.check import ROOT
from test_history_contracts import event

def observation(**changes):
    e=event(**changes)
    e["receipt"]["task_id"]="development"
    return e

class Reconciliation(unittest.TestCase):
    def test_early_and_missing(self):
        from schedule_hq.history.reconcile import reconcile
        report=reconcile([observation()],repository_id=123,installation="test-install",provider="fixture",task="development",
             start="2026-01-01T01:00:00Z",end="2026-01-01T03:00:00Z",now="2026-01-01T03:00:00Z",grace=60,history_complete=True,simulation=True)
        self.assertEqual([x["state"] for x in report],["COMPLETED","NOT OBSERVED"])
        self.assertEqual(report[0]["timing"],"EARLY")
    def test_incomplete_and_synthetic_not_live(self):
        from schedule_hq.history.reconcile import reconcile
        args=dict(repository_id=123,installation="test-install",provider="fixture",task="development",
             start="2026-01-01T01:00:00Z",end="2026-01-01T03:00:00Z",now="2026-01-01T03:00:00Z",grace=60,history_complete=False)
        self.assertEqual([r["state"] for r in reconcile([observation()],**args)],["UNKNOWN","UNKNOWN"])
    def test_reordered_and_competing_runs(self):
        from schedule_hq.history.reconcile import reconcile
        e=observation();later=observation(sequence=2,observed_at="2026-01-01T01:02:00Z")
        other=observation(run_id="other")
        args=dict(repository_id=123,installation="test-install",provider="fixture",task="development",
             start="2026-01-01T01:00:00Z",end="2026-01-01T02:00:00Z",now="2026-01-01T03:00:00Z",grace=60,history_complete=True,simulation=True)
        self.assertEqual(reconcile([later,e,e],**args),reconcile([e,later],**args))
        self.assertEqual(reconcile([later,e,other],**args)[0]["state"],"MULTIPLE OBSERVED")
    def test_scope_and_conflicting_identity(self):
        from schedule_hq.history.reconcile import reconcile
        args=dict(repository_id=123,installation="test-install",provider="fixture",task="development",
             start="2026-01-01T01:00:00Z",end="2026-01-01T02:00:00Z",now="2026-01-01T03:00:00Z",grace=60,history_complete=True,simulation=True)
        with self.assertRaises(ValueError):reconcile([observation(repository_id=124)],**args)
        with self.assertRaises(ValueError):reconcile([observation(),observation(observed_at="2026-01-01T01:02:00Z")],**args)
    def test_older_observation_cannot_replace_newer(self):
        from schedule_hq.history.reconcile import reconcile
        e=observation(sequence=2,observed_at="2026-01-01T01:01:00Z")
        old=observation(sequence=1,observed_at="2026-01-01T01:02:00Z")
        args=dict(repository_id=123,installation="test-install",provider="fixture",task="development",
             start="2026-01-01T01:00:00Z",end="2026-01-01T02:00:00Z",now="2026-01-01T03:00:00Z",grace=60,history_complete=True,simulation=True)
        with self.assertRaises(ValueError):reconcile([e,old],**args)

class DurableDelivery(unittest.TestCase):
    def setUp(self):
        from schedule_hq.history.store import History
        from schedule_hq.history.events import event_key
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.store=History(self.root,123,"test-install")
        self.e=observation(provenance="authenticated")
        self.store.append(self.e,authenticated=True);self.k=event_key(self.e)
        self.kw=dict(associated=True,delivery_supported=True,readback_supported=True)
    def test_pending_restart_ack_and_suppress(self):
        from schedule_hq.history.store import History
        p=self.store.prepare_delivery(self.k,"private-binding",**self.kw)
        self.assertEqual(p["decision"],"REPORT")
        other=History(self.root,123,"test-install")
        self.assertEqual(other.prepare_delivery(self.k,"private-binding",**self.kw)["decision"],"BLOCKED")
        self.assertEqual(other.ack_delivery(p["intent"],"private-binding","ack-1",verified=True),"ACKNOWLEDGED")
        self.assertEqual(other.ack_delivery(p["intent"],"private-binding","ack-1",verified=True),"DUPLICATE")
        self.assertEqual(other.prepare_delivery(self.k,"private-binding",**self.kw)["decision"],"SUPPRESS")
    def test_missing_capability_unverified_ack_wrong_binding(self):
        self.assertEqual(self.store.prepare_delivery(self.k,"private-binding",**(self.kw|{"readback_supported":False}))["decision"],"BLOCKED")
        p=self.store.prepare_delivery(self.k,"private-binding",**self.kw)
        for bind,verify in (("other",True),("private-binding",False)):
            with self.assertRaises(ValueError):self.store.ack_delivery(p["intent"],bind,"ack-1",verified=verify)
        self.assertEqual(self.store.prepare_delivery(self.k,"other",**self.kw)["decision"],"BLOCKED")
    def test_no_synthetic_delivery(self):
        from schedule_hq.history.events import event_key
        e=observation(sequence=2);self.store.append(e)
        self.assertEqual(self.store.prepare_delivery(event_key(e),"private-binding",**self.kw)["decision"],"BLOCKED")
    def test_stale_ack_or_observation(self):
        from schedule_hq.history.events import event_key
        newer=observation(sequence=2,provenance="authenticated",observed_at="2026-01-01T01:03:00Z")
        newer["receipt"]["next_action"]="new action"
        self.store.append(newer,authenticated=True)
        p=self.store.prepare_delivery(event_key(newer),"private-binding",**self.kw)
        self.store.ack_delivery(p["intent"],"private-binding","ack-2",verified=True)
        self.assertEqual(self.store.prepare_delivery(self.k,"private-binding",**self.kw)["decision"],"STALE")
    def test_unknown_event_cannot_report(self):
        self.assertEqual(self.store.prepare_delivery("f"*64,"private-binding",**self.kw)["decision"],"BLOCKED")

class HostBoundary(unittest.TestCase):
    def test_read_only_authenticated_identity(self):
        from schedule_hq.adapters.observation import classify_response
        self.assertEqual(classify_response(200,{"id":123,"full_name":"owner/renamed"},123,authenticated=True),"VERIFIED IDENTITY")
        self.assertEqual(classify_response(200,{"id":124,"full_name":"owner/renamed"},123,authenticated=True),"IDENTITY MISMATCH")
        self.assertEqual(classify_response(200,{"id":123,"full_name":"owner/renamed"},123,authenticated=False),"UNVERIFIED")
    def test_host_failures(self):
        from schedule_hq.adapters.observation import classify_response
        for status,want in ((429,"RATE LIMITED"),(403,"ACCESS UNVERIFIED"),(404,"NOT OBSERVED"),(503,"UNAVAILABLE"),(True,"UNVERIFIED")):
            self.assertEqual(classify_response(status,{},123,authenticated=True),want)
        self.assertEqual(classify_response(200,[],123,authenticated=True),"MALFORMED")
    def test_write_intent_must_be_fenced_and_match(self):
        from schedule_hq.policy.intent import assess
        from schedule_hq.policy.authority import Lease
        lease=Lease(123,4,"actor","a"*40,1,"2026-01-01T02:00:00Z")
        params=dict(task="development",authorized=True,authenticated_actor="actor",lease=lease,
                    repository_id=123,issue=4,head="a"*40,fence=1,now="2026-01-01T01:00:00Z",
                    competing=False,atomic_supported=True)
        intent=dict(repository_id=123,issue=4,actor="actor",before="a"*40,expected="b"*40,fence=1)
        self.assertEqual(assess(intent,params,observed="b"*40,observation_verified=True,intent_verified=True),"ALREADY_APPLIED")
        self.assertEqual(assess(intent,params,observed="a"*40,observation_verified=True,intent_verified=True),"REAUTHORIZE")
        self.assertEqual(assess(intent,params|{"atomic_supported":False},observed="a"*40,observation_verified=True,intent_verified=True),"BLOCKED")
        self.assertEqual(assess(intent|{"fence":2},params,observed="a"*40,observation_verified=True,intent_verified=True),"BLOCKED")
    def test_report_has_no_private_fields(self):
        from schedule_hq.evidence.history_report import render
        e=observation();e["receipt"]["positives"]=["PRIVATE_SECRET_MARKER"]
        page=render([e])
        self.assertNotIn("PRIVATE_SECRET_MARKER",page)
        self.assertNotIn("test-install",page)
        self.assertNotIn("run-1",page)
        self.assertIn("synthetic",page.lower())
        self.assertIn("<caption>",page)
        self.assertEqual(page,render([copy.deepcopy(e)]))
