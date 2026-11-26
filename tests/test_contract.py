import copy,json,unittest
from pathlib import Path
from tools.check import validate
class ContractTests(unittest.TestCase):
    def setUp(self): self.c=json.loads((Path(__file__).resolve().parents[1]/"schedule.json").read_text())
    def test_valid(self): validate(self.c)
    def test_competing_writer(self):
        self.c["tasks"][1]["authority"]="write-if-authorized"
        with self.assertRaises(ValueError): validate(self.c)
    def test_duplicate(self):
        self.c["tasks"][1]["id"]="development"
        with self.assertRaises(ValueError): validate(self.c)
    def test_wrong_conversation(self):
        self.c["conversation_binding"]="new"
        with self.assertRaises(ValueError): validate(self.c)
    def test_auto_enable(self):
        self.c["enabled"]=True
        with self.assertRaises(ValueError): validate(self.c)
