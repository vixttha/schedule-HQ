"""Synthetic multi-installation reference-store workload. No live scheduler invocation."""
import argparse,json,platform,tempfile,time
from pathlib import Path
from check import ROOT,load
from schedule_hq.history.store import History
from schedule_hq.history.reconcile import reconcile
from schedule_hq.history.events import event_key

TASKS={"development":"00:00","handoff":"00:15","verification":"00:30","audit":"00:45","release":"00:00"}
def fixture(i,task):
    slot=TASKS[task]
    r=load(ROOT/"examples/receipt.json")
    r.update(example=False,task_id=task,scheduled_at=f"2026-01-01T{slot}:00Z",
             started_at=f"2026-01-01T{slot}:01Z",completed_at=f"2026-01-01T{slot}:05Z",
             classification="BLOCKED",positives=["synthetic control"],negatives=["synthetic only"],
             next_action="No live action")
    return {"schema_version":1,"repository_id":i+1,"installation":f"fixture-{i}","provider":"fixture",
            "run_id":f"run-{task}","attempt":1,"sequence":1,"observed_at":f"2026-01-01T{slot}:10Z",
            "provenance":"synthetic","receipt":r}
def run(n):
    before=time.perf_counter();adds=duplicates=conflicts=reconciled=0
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp)
        for i in range(n):
            p=root/f"installation-{i}";p.mkdir(mode=0o700)
            h=History(p,i+1,f"fixture-{i}")
            for task in TASKS:
                e=fixture(i,task)
                assert h.append(e)=="ADDED";adds+=1
                assert h.append(e)=="DUPLICATE";duplicates+=1
                changed=e|{"observed_at":"2026-01-01T01:01:00Z"}
                try:h.append(changed)
                except ValueError:conflicts+=1
                else:raise AssertionError("conflicting duplicate accepted")
            h=History(p,i+1,f"fixture-{i}")
            events=h.events();assert len(events)==5
            for task in TASKS:
                result=reconcile(events,repository_id=i+1,installation=f"fixture-{i}",provider="fixture",task=task,
                     start="2026-01-01T00:00:00Z",end="2026-01-01T01:00:00Z",now="2026-01-01T01:00:00Z",
                     grace=60,history_complete=True,simulation=True)
                assert len(result)==1 and result[0]["state"]=="COMPLETED" and result[0]["scope"]=="synthetic"
                reconciled+=1
            assert h.prepare_delivery(event_key(events[0]),"fixture",associated=True,
                    delivery_supported=True,readback_supported=True,observation_verified=True)["decision"]=="BLOCKED"
            restored=root/f"restore-{i}";restored.mkdir(mode=0o700)
            copy=History(restored,i+1,f"fixture-{i}");copy.restore_empty(h.export_private())
            assert copy.events()==events
    assert adds==duplicates==conflicts==reconciled==5*n
    return dict(installations=n,added=adds,duplicate_replays=duplicates,conflicting_replays_rejected=conflicts,
                reconciled=reconciled,seconds=time.perf_counter()-before)
def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True);a=p.parse_args()
    report={"scope":"synthetic sequential installation workload; no independent agents or actual host execution",
            "platform":platform.platform(),"python":platform.python_version(),"results":[run(n) for n in (1,5,10,100)]}
    Path(a.output).write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report))
if __name__=="__main__":main()
