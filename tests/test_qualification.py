import json,unittest
from tools.check import ROOT,load,validate_receipt
from schedule_hq.evidence.public import public_receipt_from_json
from schedule_hq.contracts.identity import same_repository
from schedule_hq.policy.scheduling import observed_state
class Qualification(unittest.TestCase):
    def setUp(self):
        self.r=load(ROOT/"examples/receipt.json")
        self.r.update(example=False,classification="BLOCKED")
    def test_private_fields_dropped(self):
        secret="SYNTHETIC_PRIVATE_MARKER<script>alert(1)</script>"
        r=self.r|{"positives":[secret],"negatives":[secret],"next_action":secret,"proof_links":["https://github.com/owner/private/actions/runs/123"],"source_head":"a"*40}
        output=public_receipt_from_json(json.dumps(r).encode())
        self.assertNotIn(b"SYNTHETIC",output)
        self.assertNotIn(b"private",output)
        self.assertEqual(set(json.loads(output)),{"schema_version","example","task_id","scheduled_at","started_at","completed_at","classification"})
    def test_malformed_ingress_generic(self):
        for payload in [b'{"secret":"SYNTHETIC_PRIVATE_MARKER"}',b'{"x":1,"x":2}',b'{"x":NaN}',b'\xff',b'['*4000,b' '*65537,"not bytes"]:
            with self.subTest(kind=type(payload).__name__),self.assertRaisesRegex(ValueError,"^invalid private receipt$"):
                public_receipt_from_json(payload)
    def test_unknown_private_field_rejected(self):
        with self.assertRaisesRegex(ValueError,"^invalid private receipt$"):
            public_receipt_from_json(json.dumps(self.r|{"credential":"SYNTHETIC"}).encode())
    def test_same_id_renamed(self):
        for name in ("owner/old-name","owner/new-name","newowner/new-name"):
            self.assertTrue(same_repository(123,{"id":123,"full_name":name},observation_verified=True))
    def test_wrong_id_and_unverified(self):
        for obj,verified in [({"id":124,"full_name":"owner/old-name"},True),({"id":True,"full_name":"owner/old-name"},True),({"id":123,"full_name":"owner/old-name"},False),({"id":123,"full_name":"https://evil.invalid"},True),({"id":123,"full_name":"owner/.."},True),([],True)]:
            self.assertFalse(same_repository(123,obj,observation_verified=verified))
    def test_early_host_execution(self):
        scheduled="2026-01-01T01:00:00Z"; start="2026-01-01T00:40:00Z"; end="2026-01-01T00:45:00Z"
        r=self.r|{"scheduled_at":scheduled,"started_at":start,"completed_at":end}
        validate_receipt(r)
        self.assertEqual(observed_state(scheduled,start,end,end,60),"COMPLETED")
    def test_bad_actual_interval(self):
        r=self.r|{"started_at":"2026-01-01T01:00:00Z","completed_at":"2026-01-01T00:59:00Z"}
        with self.assertRaises(ValueError): validate_receipt(r)
