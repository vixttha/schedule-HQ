"""Allowlisted public projection; deliberately drops arbitrary text and all external URLs."""
from schedule_hq.contracts.validation import validate_receipt
def public_summary(receipt):
    validate_receipt(receipt)
    return {k:receipt[k] for k in ("schema_version","example","task_id","scheduled_at","started_at","completed_at","classification")}

def public_receipt_from_json(payload):
    """Bound untrusted private receipt bytes and emit only allowlisted JSON.
    Never echo input or exception details. Classification is an observation, not proof authenticity.
    """
    import json
    from schedule_hq.contracts.validation import unique,bad_constant
    if type(payload) is not bytes or len(payload)>65536:
        raise ValueError("invalid private receipt")
    try:
        receipt=json.loads(payload.decode("utf-8"),object_pairs_hook=unique,parse_constant=bad_constant)
        projected=public_summary(receipt)
        return json.dumps(projected,sort_keys=True,ensure_ascii=True,allow_nan=False,separators=(",",":")).encode("ascii")
    except (ValueError,TypeError,RecursionError,OverflowError):
        raise ValueError("invalid private receipt") from None
