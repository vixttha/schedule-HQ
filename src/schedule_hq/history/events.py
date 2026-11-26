"""Private observation envelope; trust is supplied by a verified adapter, never by JSON alone."""
import hashlib
import json
import re
from schedule_hq.contracts.validation import keys, require, timestamp, validate_receipt, unique, bad_constant

FIELDS={"schema_version","repository_id","installation","provider","run_id","attempt","sequence",
        "observed_at","provenance","receipt"}
IDENT=re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}")
LIMIT=65536

def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=True,allow_nan=False,separators=(",",":")).encode("ascii")

def validate_event(event):
    keys(event,FIELDS)
    require(type(event["schema_version"]) is int and event["schema_version"]==1,"invalid observation schema")
    for key in ("repository_id","attempt","sequence"):
        require(type(event[key]) is int and 1<=event[key]<=9007199254740991,"invalid observation integer")
    for key in ("installation","provider","run_id"):
        require(type(event[key]) is str and IDENT.fullmatch(event[key]) is not None,"invalid observation identifier")
    require(type(event["provenance"]) is str and event["provenance"] in ("synthetic","unverified","authenticated"),"invalid provenance")
    observed=timestamp(event["observed_at"])
    r=event["receipt"]
    validate_receipt(r)
    require(r["example"] is False,"example is not an observation")
    for field in ("started_at","completed_at"):
        require(r[field] is None or timestamp(r[field])<=observed,"execution after observation")
    require(len(canonical(event))<=LIMIT,"observation too large")

def event_key(event):
    validate_event(event)
    r=event["receipt"]
    parts=[event[k] for k in ("repository_id","installation","provider","run_id","attempt","sequence")]
    parts.extend([r["task_id"],r["scheduled_at"]])
    return hashlib.sha256(canonical(parts)).hexdigest()

def event_digest(event):
    validate_event(event)
    return hashlib.sha256(canonical(event)).hexdigest()

def ingest(payload,*,authenticated=False):
    if type(payload) is not bytes or len(payload)>LIMIT:
        raise ValueError("invalid observation")
    try:
        e=json.loads(payload.decode("utf-8"),object_pairs_hook=unique,parse_constant=bad_constant)
        validate_event(e)
        require(e["provenance"]!="authenticated" or authenticated is True,"unverified source")
        return e
    except (ValueError,TypeError,OverflowError,RecursionError):
        raise ValueError("invalid observation") from None

def check_run_slot(event, seen):
    """One provider/task run identity has exactly one nominal slot, across attempts."""
    receipt=event["receipt"]
    key=(event["provider"],receipt["task_id"],event["run_id"])
    slot=receipt["scheduled_at"]
    require(key not in seen or seen[key]==slot,"contradictory host run slot")
    seen[key]=slot
