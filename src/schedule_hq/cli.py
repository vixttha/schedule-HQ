"""Offline CLI entry point; no scheduling or remote writes."""
from pathlib import Path
from schedule_hq.contracts.validation import load,validate,validate_receipt
def check(root):
    root=Path(root)
    validate(load(root/"config/schedule.json"))
    validate_receipt(load(root/"examples/receipt.json"))
