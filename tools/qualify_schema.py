"""Separate standards engine for structural validation; semantic checks remain mandatory."""
from check import ROOT,load,validate,validate_receipt
from jsonschema import Draft202012Validator
import copy
def main():
    schedule=load(ROOT/"config/schedule.json")
    receipt=load(ROOT/"examples/receipt.json")
    engines={}
    for name,data in (("schedule",schedule),("receipt",receipt)):
        schema=load(ROOT/"schemas/v1"/(name+".schema.json"))
        Draft202012Validator.check_schema(schema)
        engines[name]=Draft202012Validator(schema)
        engines[name].validate(data)
    count=2
    def case(name,data,want):
        nonlocal count
        engine=engines[name]
        if engine.is_valid(data)!=want: raise AssertionError("unexpected schema verdict")
        try: (validate if name=="schedule" else validate_receipt)(data); semantic=True
        except ValueError: semantic=False
        if semantic!=want: raise AssertionError("unexpected semantic verdict")
        count+=1
    for key,value in [("schema_version",True),("checkpoint","v00.0.0.2"),("enabled",True),("display_name",""),("extra","x"),("timezone","local"),("tasks",[])]:
        case("schedule",schedule|{key:value},False)
    for change in [{"id":"development"},{"authority":"write-if-authorized"},{"cron":"* * * * *"}]:
        obj=copy.deepcopy(schedule);obj["tasks"][1].update(change);case("schedule",obj,False)
    for key,value in [("classification","PASS"),("source_head","a"*39),("proof_links",["https://evil.invalid/x"]),("installed_version","v00.1.1"),("next_action",""),("schema_version",True),("started_at","2026-01-01T00:00:00Z"),("extra","x")]:
        case("receipt",receipt|{key:value},False)
    good=receipt|{"example":False,"classification":"PASS","source_head":"a"*40,"proof_links":["https://github.com/owner/repo/actions/runs/1"],"started_at":"2026-01-01T00:20:00Z","completed_at":"2026-01-01T00:25:00Z"}
    case("receipt",good,True)
    for key in ("source_head","started_at","completed_at"):
        case("receipt",good|{key:None},False)
    case("receipt",good|{"proof_links":[]},False)
    # JSON Schema defines integral floats as integers. Calendar validity and time order
    # are intentionally checked by the stricter semantic layer, not by structural schema.
    for data in (receipt|{"schema_version":1.0},receipt|{"scheduled_at":"2026-02-30T00:30:00Z"},good|{"completed_at":"2026-01-01T00:19:00Z"}):
        if not engines["receipt"].is_valid(data): raise AssertionError("unexpected structural rejection")
        try: validate_receipt(data)
        except ValueError: count+=1
        else: raise AssertionError("semantic fail-open")
    # Resolve the local schema reference without network access.
    from schedule_hq.history.events import validate_event
    schema=load(ROOT/"schemas/v1/observation.schema.json")
    Draft202012Validator.check_schema(schema)
    assert schema["properties"]["receipt"]=={"$ref":"receipt.schema.json"}
    schema["properties"]["receipt"]=load(ROOT/"schemas/v1/receipt.schema.json")
    engine=Draft202012Validator(schema)
    e=dict(schema_version=1,repository_id=1,installation="fixture",provider="fixture",run_id="r1",
           attempt=1,sequence=1,observed_at="2026-01-01T01:00:00Z",provenance="synthetic",receipt=good)
    for data,want in [(e,True),(e|{"repository_id":True},False),(e|{"attempt":0},False),
                      (e|{"installation":"../x"},False),(e|{"extra":"x"},False),(e|{"provenance":"bad"},False)]:
        if engine.is_valid(data)!=want: raise AssertionError("unexpected observation schema verdict")
        try: validate_event(data); semantic=True
        except ValueError: semantic=False
        if semantic!=want: raise AssertionError("unexpected observation semantic verdict")
        count+=1
    print(f"PASS: {count} separate-engine structural/semantic qualification cases; no independent agent or host trial asserted")
if __name__=="__main__": main()
