import copy
import json
import tempfile
import unittest
from pathlib import Path
from tools.check import ROOT, validate, validate_receipt, load
class ArchitectureContracts(unittest.TestCase):
    def setUp(self):
        self.c=load(ROOT/"config/schedule.json")
        self.r=load(ROOT/"examples/receipt.json")
    def reject(self,key,value):
        self.c[key]=value
        with self.assertRaises(ValueError): validate(self.c)
    def test_schema_bool(self): self.reject("schema_version",True)
    def test_schema_unknown(self): self.reject("schema_version",2)
    def test_extra(self): self.reject("token","not-a-real-token")
    def test_missing(self):
        del self.c["tasks"]
        with self.assertRaises(ValueError): validate(self.c)
    def test_bad_target(self): self.reject("target_repository","other/repo")
    def test_timezone(self): self.reject("timezone","wrong")
    def test_checkpoint(self): self.reject("checkpoint","v0.0.1")
    def test_unknown_id(self):
        self.c["tasks"][1]["id"]="other"
        with self.assertRaises(ValueError): validate(self.c)
    def test_cron(self):
        self.c["tasks"][1]["cron"]="* * * * *"
        with self.assertRaises(ValueError): validate(self.c)
    def test_task_type(self): self.reject("tasks",{})
    def test_duplicate_json(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.json";p.write_text('{"x":1,"x":2}',encoding="utf-8")
            with self.assertRaises(ValueError): load(p)
    def test_nonfinite_json(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.json";p.write_text('{"x":NaN}',encoding="utf-8")
            with self.assertRaises(ValueError): load(p)
    def test_example(self): validate_receipt(self.r)
    def test_fake_pass(self):
        self.r["classification"]="PASS"
        with self.assertRaises(ValueError): validate_receipt(self.r)
    def test_missing_pass_proof(self):
        self.r.update(example=False,classification="PASS")
        with self.assertRaises(ValueError): validate_receipt(self.r)
    def test_bad_sha(self):
        self.r["source_head"]="123"
        with self.assertRaises(ValueError): validate_receipt(self.r)
    def test_bad_timestamp(self):
        self.r["scheduled_at"]="2026-02-30T00:00:00Z"
        with self.assertRaises(ValueError): validate_receipt(self.r)
    def test_bad_interval(self):
        self.r.update(example=False,started_at="2026-01-02T00:00:00Z",completed_at="2026-01-01T00:00:00Z")
        with self.assertRaises(ValueError): validate_receipt(self.r)
    def test_private_url(self):
        self.r.update(example=False,proof_links=["https://example.invalid/secret"])
        with self.assertRaises(ValueError): validate_receipt(self.r)
    def test_rename(self):
        self.c["display_name"]="New brand"
        validate(self.c)
    def test_frozen_pin_reconciliation(self):
        f=load(ROOT/"freeze/v0.0.0.1.json")
        d=load(ROOT/"config/dependencies.lock.json")
        self.assertEqual(d["repository_id"],f["repository_id"])
        for v in d["components"].values():
            ref=f["components"][v["branch"]]
            self.assertEqual(v["frozen_adopter_sha"],ref["commit"])
            self.assertEqual(v["tested_sha"],ref.get("tested_commit",ref["commit"]))
            self.assertEqual(v["proof_run"],ref["proof_run"])
    def test_schema_required_keys(self):
        for name,data in [("schedule",self.c),("receipt",self.r)]:
            schema=load(ROOT/"schemas/v1"/(name+".schema.json"))
            self.assertEqual(set(schema["required"]),set(data))
            self.assertFalse(schema["additionalProperties"])
