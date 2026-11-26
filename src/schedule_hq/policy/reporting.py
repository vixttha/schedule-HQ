"""Deduplication intent; only confirmed delivery can advance a durable host cursor."""
import hashlib,json
from schedule_hq.contracts.validation import validate_receipt
MATERIAL=("task_id","source_head","base_sha","proposed_merge_sha","actual_merge_sha","installed_version","classification","positives","negatives","proof_links","next_action")
def fingerprint(receipt):
    validate_receipt(receipt)
    if receipt["example"]: raise ValueError("example is not an observation")
    value={k:receipt[k] for k in MATERIAL}
    for k in ("positives","negatives","proof_links"):
        value[k]=sorted(set(value[k]))
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=True,separators=(",",":")).encode()).hexdigest()
def delivery_decision(receipt, previous, *, associated, capability):
    if associated is not True or capability is not True: return "BLOCKED"
    return "SUPPRESS" if fingerprint(receipt)==previous else "REPORT"
