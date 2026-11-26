"""Allowlisted public projection; deliberately drops arbitrary text and all external URLs."""
from schedule_hq.contracts.validation import validate_receipt
def public_summary(receipt):
    validate_receipt(receipt)
    return {k:receipt[k] for k in ("schema_version","example","task_id","scheduled_at","started_at","completed_at","classification")}
