import unittest,copy
from dataclasses import replace
from tools.check import ROOT,load
from schedule_hq.policy.authority import Lease,may_publish
from schedule_hq.policy.reporting import fingerprint,delivery_decision
from schedule_hq.policy.recovery import recovery
from schedule_hq.policy.scheduling import slots,local_stamp,observed_state
from schedule_hq.evidence.public import public_summary
from schedule_hq.adapters.capabilities import available
A="a"*40; B="b"*40; C="c"*40
T="2026-11-01T05:30:00Z"; U="2026-11-01T06:30:00Z"; V="2026-11-01T07:00:00Z"
class Policy(unittest.TestCase):
    def setUp(self):
        self.lease=Lease(1,2,"worker",A,3,U)
        self.args=dict(task="development",authorized=True,authenticated_actor="worker",lease=self.lease,repository_id=1,issue=2,head=A,fence=3,now=T,competing=False,atomic_supported=True)
        self.r=load(ROOT/"examples/receipt.json")
        self.r.update(example=False,classification="BLOCKED",source_head=A)
    def test_allowed(self): self.assertTrue(may_publish(**self.args))
    def test_rejections(self):
        for k,v in [("task","audit"),("authorized",1),("authenticated_actor","other"),("lease",None),("repository_id",2),("issue",True),("head",B),("fence",2),("now",U),("now","bad"),("competing",True),("atomic_supported",False)]:
            with self.subTest(k=k): self.assertFalse(may_publish(**(self.args|{k:v})))
    def test_malformed_lease(self):
        for field,value in [("repository_id",True),("issue",False),("fence",True),("actor",""),("expires_at","bad")]:
            with self.subTest(field=field): self.assertFalse(may_publish(**(self.args|{"lease":replace(self.lease,**{field:value})})))
    def test_dedup_time(self):
        r=self.r|{"scheduled_at":T}; self.assertEqual(fingerprint(r),fingerprint(self.r))
    def test_dedup_order(self):
        self.assertEqual(fingerprint(self.r|{"negatives":["a","b","a"]}),fingerprint(self.r|{"negatives":["b","a"]}))
    def test_changed_head(self): self.assertNotEqual(fingerprint(self.r),fingerprint(self.r|{"source_head":B}))
    def test_changed_blocker(self): self.assertNotEqual(fingerprint(self.r),fingerprint(self.r|{"negatives":["different"]}))
    def test_delivery(self):
        for previous,assoc,cap,want in [(None,True,True,"REPORT"),(fingerprint(self.r),True,True,"SUPPRESS"),(None,False,True,"BLOCKED"),(None,True,False,"BLOCKED")]:
            with self.subTest(want=want): self.assertEqual(delivery_decision(self.r,previous,associated=assoc,capability=cap),want)
    def test_recovery(self):
        base=dict(before=A,expected=B,observed=A,observation_verified=True,intent_verified=True,same_fence=True,atomic_supported=True)
        for change,want in [({},"REAUTHORIZE"),({"observed":B},"ALREADY_APPLIED"),({"observed":C},"CONFLICT"),({"observation_verified":False},"BLOCKED"),({"intent_verified":False},"BLOCKED"),({"same_fence":False},"BLOCKED"),({"atomic_supported":False},"BLOCKED"),({"expected":A},"BLOCKED"),({"observed":"bad"},"BLOCKED")]:
            with self.subTest(change=change): self.assertEqual(recovery(**(base|change)),want)
    def test_slots(self):
        a="2026-11-01T00:00:00Z"; b="2026-11-02T00:00:00Z"
        for task,count in [("development",24),("handoff",24),("verification",24),("audit",24),("release",6)]:
            with self.subTest(task=task): self.assertEqual(len(slots(task,a,b)),count)
    def test_slot_bounds(self):
        self.assertEqual(slots("verification",T,U),[T])
        self.assertEqual(slots("verification","2026-11-01T05:30:01Z",U),[])
        for task,start,end in [("unknown",T,U),("audit",U,T),("audit",T,"2026-11-10T00:00:00Z")]:
            with self.assertRaises(ValueError): slots(task,start,end)
    def test_dst_observed_offsets(self):
        self.assertEqual(local_stamp(T,-240),"2026-11-01T01:30:00-04:00")
        self.assertEqual(local_stamp(U,-300),"2026-11-01T01:30:00-05:00")
    def test_offset_invalid(self):
        for offset in [True,841,-841,"-300"]:
            with self.assertRaises(ValueError): local_stamp(T,offset)
    def test_observation(self):
        for start,end,now,want in [(None,None,T,"PENDING"),(None,None,V,"NOT OBSERVED"),(T,None,U,"RUNNING"),(T,U,V,"COMPLETED")]:
            with self.subTest(want=want): self.assertEqual(observed_state(T,start,end,now,60),want)
    def test_bad_observation(self):
        for a,b,n in [(None,U,V),(U,T,V),(V,None,U)]:
            with self.assertRaises(ValueError): observed_state(T,a,b,n,60)
    def test_public_projection(self):
        r=self.r|{"negatives":["private conversation secret"],"next_action":"private details"}
        p=public_summary(r); self.assertNotIn("negatives",p); self.assertNotIn("next_action",p); self.assertNotIn("source_head",p)
    def test_adapter(self):
        self.assertFalse(available(None,"atomic")); self.assertFalse(available({"atomic":1},"atomic")); self.assertTrue(available({"atomic":True},"atomic"))
