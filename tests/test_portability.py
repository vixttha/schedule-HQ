import tempfile,unittest,subprocess
from pathlib import Path
from tools.check import ROOT,load,validate
from schedule_hq.contracts.paths import portable,confined,unique_paths
class Portability(unittest.TestCase):
    def test_unsafe_paths(self):
        for p in ["../x","a/../b","/a","C:/a","a\\b","a//b","a/./b","NUL.txt","a.","a ","a:secret",""]:
            with self.subTest(p=p),self.assertRaises(ValueError): portable(p)
    def test_collision(self):
        for paths in [["A","a"],["a","a/b"],["a/b","A"]]:
            with self.assertRaises(ValueError): unique_paths(paths)
    def test_valid(self): unique_paths(["a/b","a/c",".github/workflows/a.yml"])
    def test_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/"target").mkdir()
            try: (p/"link").symlink_to(p/"target",target_is_directory=True)
            except OSError: self.skipTest("host cannot create symlink")
            with self.assertRaises(ValueError): confined(p,"link/file")
    def test_old_wire(self):
        import json
        old=json.loads(subprocess.check_output(["git","show","e0f9e7acab71efa71fd4898625360966a5fa08a3:schedule.json"],cwd=ROOT,text=True))
        validate(old)
    def test_frozen_receipt(self):
        from schedule_hq.contracts.validation import validate_receipt
        import json
        old=json.loads(subprocess.check_output(["git","show","e0f9e7acab71efa71fd4898625360966a5fa08a3:examples/receipt.json"],cwd=ROOT,text=True))
        validate_receipt(old)
    def test_published_record(self):
        p=load(ROOT/"publication/v0.0.0.1.json");self.assertEqual(p["checkpoint"],"v0.0.0.1")
        self.assertEqual(p["frozen_source"],"139dc64a15a069a0a2bd570c9e50ca664f8e4cfc")
