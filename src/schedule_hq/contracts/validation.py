"""Strict offline v1 template contracts; no remote authority granted."""
import json
import re
from datetime import datetime
from pathlib import Path

TASKS = {"development":("0 * * * *","write-if-authorized"),
         "handoff":("15 * * * *","read-only"),
         "verification":("30 * * * *","read-only"),
         "audit":("45 * * * *","read-only"),
         "release":("0 */4 * * *","read-only")}
SCHEDULE_KEYS = {"schema_version","checkpoint","display_name","target_repository","timezone","conversation_binding","enabled","tasks"}
RECEIPT_KEYS = {"schema_version","example","task_id","scheduled_at","started_at","completed_at","source_head","base_sha","proposed_merge_sha","actual_merge_sha","installed_version","classification","positives","negatives","proof_links","next_action"}
SHA = re.compile(r"[0-9a-f]{40}")
VERSION = re.compile(r"v(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*)){2,3}")
PROOF = re.compile(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/(?:commit/[0-9a-f]{40}|actions/runs/[1-9][0-9]*(?:/attempts/[1-9][0-9]*|/artifacts/[1-9][0-9]*)?)")
def require(ok, message):
    if not ok:
        raise ValueError(message)
def unique(pairs):
    d = {}
    for k,v in pairs:
        require(k not in d, "duplicate JSON key")
        d[k] = v
    return d
def bad_constant(value):
    raise ValueError("non-finite JSON number")
def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique, parse_constant=bad_constant)
def keys(value, expected):
    require(type(value) is dict and set(value)==expected, "unknown or missing fields")
def version(value):
    return type(value) is str and VERSION.fullmatch(value) is not None
def safe_text(value):
    return type(value) is str and bool(value.strip()) and len(value)<=2000 and all(c.isprintable() for c in value)
def validate(cfg):
    keys(cfg,SCHEDULE_KEYS)
    require(type(cfg["schema_version"]) is int and cfg["schema_version"]==1,"unknown schema")
    require(version(cfg["checkpoint"]) and cfg["checkpoint"].count(".")==3,"invalid checkpoint")
    require(safe_text(cfg["display_name"]),"invalid display name")
    require(cfg["target_repository"]=="OWNER/REPO","portable placeholder required")
    require(cfg["timezone"]=="Etc/UTC","portable UTC template required")
    require(cfg["conversation_binding"]=="existing-associated-conversation","existing conversation required")
    require(cfg["enabled"] is False,"template must remain disabled")
    tasks=cfg["tasks"]
    require(type(tasks) is list and len(tasks)==5,"five tasks required")
    seen=set()
    for t in tasks:
        keys(t,{"id","title","cron","authority","purpose"})
        ident=t["id"]
        require(type(ident) is str and ident in TASKS and ident not in seen,"invalid or duplicate task")
        seen.add(ident)
        require((t["cron"],t["authority"])==TASKS[ident],"invalid schedule or authority")
        require(safe_text(t["title"]) and safe_text(t["purpose"]),"invalid text")
    require(seen==set(TASKS),"task set mismatch")
def timestamp(value):
    require(type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z",value) is not None,"expected UTC timestamp")
    return datetime.fromisoformat(value[:-1]+"+00:00")
def validate_receipt(r):
    keys(r,RECEIPT_KEYS)
    require(type(r["schema_version"]) is int and r["schema_version"]==1,"unknown receipt schema")
    require(type(r["example"]) is bool,"invalid example flag")
    require(type(r["task_id"]) is str and r["task_id"] in TASKS,"unknown task")
    timestamp(r["scheduled_at"])
    for key in ("started_at","completed_at"):
        if r[key] is not None: timestamp(r[key])
    if r["completed_at"] is not None:
        require(r["started_at"] is not None and timestamp(r["completed_at"])>=timestamp(r["started_at"]),"invalid execution interval")
    for key in ("source_head","base_sha","proposed_merge_sha","actual_merge_sha"):
        v=r[key]
        require(v is None or (type(v) is str and SHA.fullmatch(v) is not None),"invalid revision")
    require(r["installed_version"] is None or version(r["installed_version"]),"invalid installed version")
    require(type(r["classification"]) is str and r["classification"] in {"PASS","FAIL","BLOCKED","NOT RUN","UNVERIFIED"},"invalid classification")
    for key in ("positives","negatives","proof_links"):
        require(type(r[key]) is list and all(safe_text(x) for x in r[key]),"invalid receipt list")
    require(all(PROOF.fullmatch(x) for x in r["proof_links"]),"invalid public proof URL")
    require(safe_text(r["next_action"]),"invalid next action")
    if r["example"]: require(r["classification"]=="NOT RUN" and r["started_at"] is None and r["completed_at"] is None and not r["proof_links"],"synthetic evidence prohibited")
    if r["classification"]=="NOT RUN":
        require(r["started_at"] is None and r["completed_at"] is None,"NOT RUN cannot contain execution times")
    if r["classification"]=="PASS":
        require(not r["example"] and r["source_head"] and r["proof_links"] and r["started_at"] and r["completed_at"],"PASS needs exact evidence and actual times")
