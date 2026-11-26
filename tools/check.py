"""Stable v0.0.0.1 CLI; implementation moved into src."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from schedule_hq.contracts.validation import validate, validate_receipt, load
if __name__=="__main__":
    validate(load(ROOT/"config/schedule.json"))
    validate_receipt(load(ROOT/"examples/receipt.json"))
    print("PASS: strict offline template and receipt contract; no live scheduler execution asserted")
