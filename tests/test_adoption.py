import json,subprocess,tempfile,unittest
from pathlib import Path
from tools.check import ROOT
from schedule_hq.adoption import bundle,install,uninstall
class Adoption(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.repo=Path(self.tmp.name)
        self.git("init","-b","schedule-hq")
        self.git("remote","add","origin","https://github.com/fixture/test-repo.git")
        (self.repo/"README.md").write_text("fixture",encoding="utf-8")
        self.git("add","README.md")
        self.git("-c","user.name=Fixture","-c","user.email=fixture@example.invalid","commit","-m","fixture")
    def git(self,*args):
        return subprocess.check_output(["git","-C",str(self.repo),*args],stderr=subprocess.STDOUT,text=True).strip()
    def plan(self,**changes):
        return bundle(ROOT,**(dict(repository="fixture/test-repo",repository_id=123,timezone="Etc/UTC")|changes))
    def test_five_standalone_disabled_prompts(self):
        p=self.plan();cfg=json.loads(p["installation.json"])
        self.assertFalse(cfg["enabled"]);self.assertEqual(len(cfg["tasks"]),5)
        for t in cfg["tasks"]:
            s=p["prompts/"+t["id"]+".md"].decode()
            self.assertIn("fixture/test-repo",s);self.assertIn("123",s)
            self.assertIn("existing associated conversation",s)
            self.assertIn("read-only",s)
            self.assertNotIn("OWNER/REPO",s)
        self.assertEqual(p,self.plan())
    def test_invalid_configuration(self):
        for x in ({"repository":"https://evil.invalid"},{"repository":"owner/.."},{"repository_id":True},{"repository_id":0},{"timezone":"../UTC"},{"timezone":"No/Such_Zone"},{"minutes":{"development":15,"handoff":15}}):
            with self.subTest(x=x),self.assertRaises(ValueError):self.plan(**x)
    def test_custom_schedule_and_nominal_utc(self):
        p=self.plan(minutes={"development":5,"handoff":20,"verification":35,"audit":50,"release":10},release_hours=6)
        cfg=json.loads(p["installation.json"]);self.assertEqual(cfg["tasks"][0]["cron"],"5 * * * *")
        self.assertEqual(cfg["tasks"][-1]["cron"],"10 */6 * * *")
        self.assertEqual(cfg["schedule_timezone"],"Etc/UTC")
    def test_install_verify_rollback(self):
        p=self.plan();before=self.git("rev-parse","HEAD")
        install(self.repo,p)
        self.assertEqual(self.git("rev-parse","HEAD"),before)
        self.assertEqual((self.repo/".schedule-hq"/"installation.json").read_bytes(),p["installation.json"])
        with self.assertRaises(ValueError):install(self.repo,p)
        uninstall(self.repo,p,apply=False)
        self.assertTrue((self.repo/".schedule-hq").exists())
        uninstall(self.repo,p,apply=True)
        self.assertFalse((self.repo/".schedule-hq").exists())
        self.assertTrue((self.repo/".schedule-hq-removed"/"installation.json").exists())
        self.assertEqual((self.repo/"README.md").read_text(),"fixture")
    def test_wrong_branch_and_remote_rejected(self):
        p=self.plan()
        self.git("checkout","-b","other")
        with self.assertRaises(ValueError):install(self.repo,p)
        self.git("checkout","schedule-hq")
        self.git("remote","set-url","origin","https://github.com/fixture/other.git")
        with self.assertRaises(ValueError):install(self.repo,p)
    def test_uninstall_refuses_changed_or_extra_file(self):
        p=self.plan();install(self.repo,p)
        x=self.repo/".schedule-hq"/"prompts"/"development.md";old=x.read_bytes();x.write_bytes(b"changed")
        with self.assertRaises(ValueError):uninstall(self.repo,p,apply=True)
        x.write_bytes(old);(self.repo/".schedule-hq"/"extra").write_text("private")
        with self.assertRaises(ValueError):uninstall(self.repo,p,apply=True)
        self.assertTrue((self.repo/".schedule-hq").exists())
    def test_install_refuses_existing_directory(self):
        p=self.plan();(self.repo/".schedule-hq").mkdir()
        with self.assertRaises(ValueError):install(self.repo,p)

    def test_private_input_and_symlink_rejected(self):
        p=self.plan()
        with self.assertRaises(ValueError):self.plan(repository="fixture/test-repo\nprivate-token")
        self.assertNotIn(b"conversation_id",p["installation.json"])
        self.assertNotIn(b"task_token",p["installation.json"])
        sentinel=self.repo/"README.md"
        dest=self.repo/".schedule-hq"
        try:dest.symlink_to(sentinel)
        except OSError:
            self.assertEqual(sentinel.read_text(),"fixture")
            return
        with self.assertRaises(ValueError):install(self.repo,p)
        self.assertEqual(sentinel.read_text(),"fixture")
    def test_no_write_in_development_pilot(self):
        p=self.plan();text=p["prompts/development.md"].decode()
        self.assertIn("READ-ONLY PILOT",text)
        self.assertIn("do not implement, publish, claim or transfer",text)
        self.assertNotIn("one reversible fix",text)
    def test_no_destructive_rollback_over_existing_backup(self):
        p=self.plan();install(self.repo,p)
        (self.repo/".schedule-hq-removed").mkdir()
        with self.assertRaises(ValueError):uninstall(self.repo,p,apply=True)
        self.assertTrue((self.repo/".schedule-hq").exists())

    def test_forged_or_modified_bundle_refused(self):
        from schedule_hq.adoption import encoded
        p=self.plan()
        for q in (p|{"unexpected.md":b"private"},p|{"prompts/development.md":b"tampered"},p|{"manifest.json":b"{}"}):
            with self.assertRaises(ValueError):install(self.repo,q)
        self.assertFalse((self.repo/".schedule-hq").exists())
    def test_interrupted_install_does_not_change_checkout(self):
        from unittest.mock import patch
        p=self.plan()
        with patch("schedule_hq.adoption.Path.rename",side_effect=OSError("synthetic interruption")):
            with self.assertRaises(OSError):install(self.repo,p)
        self.assertFalse((self.repo/".schedule-hq").exists())
        self.assertFalse(list(self.repo.glob(".schedule-hq-stage-*")))
        self.assertEqual((self.repo/"README.md").read_text(),"fixture")
    def test_credential_bearing_remote_refused(self):
        p=self.plan();self.git("remote","set-url","origin","https://synthetic-secret@github.com/fixture/test-repo.git")
        with self.assertRaisesRegex(ValueError,"origin locator mismatch"):install(self.repo,p)
    def test_standalone_prompt_has_no_missing_workflow_reference(self):
        for k,v in self.plan().items():
            if k.startswith("prompts/"):self.assertNotIn("Follow WORKFLOW.md",v.decode())
