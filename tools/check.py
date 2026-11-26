import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def validate(cfg):
    tasks=cfg["tasks"]
    if len(tasks)!=5 or len({t["id"] for t in tasks})!=5: raise ValueError("five unique tasks required")
    if [t["id"] for t in tasks if t["authority"]=="write-if-authorized"]!=["development"]: raise ValueError("single writer required")
    if any(t["authority"] not in {"read-only","write-if-authorized"} for t in tasks): raise ValueError("invalid authority")
    if cfg["conversation_binding"]!="existing-associated-conversation": raise ValueError("conversation binding required")
    if cfg["enabled"] is not False: raise ValueError("template must remain disabled")
    if not all(t["cron"] and t["purpose"] for t in tasks): raise ValueError("missing task contract")
if __name__=="__main__":
    validate(json.loads((ROOT/"schedule.json").read_text(encoding="utf-8")))
    print("PASS: template contract; no live scheduler execution asserted")
