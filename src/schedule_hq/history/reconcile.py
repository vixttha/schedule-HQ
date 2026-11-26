"""Reconcile bounded nominal slots against scoped observations, never infer failures."""
from datetime import timedelta
from schedule_hq.contracts.validation import require,timestamp
from schedule_hq.history.events import validate_event,event_key,event_digest
from schedule_hq.policy.scheduling import slots,observed_state

def reconcile(events,*,repository_id,installation,provider,task,start,end,now,grace,
              history_complete=False,simulation=False,source_verified=False):
    require(type(grace) is int and 0<=grace<=86400,"invalid grace")
    require(type(history_complete) is bool and type(simulation) is bool and type(source_verified) is bool,"invalid source flags")
    require(type(repository_id) is int and repository_id>0,"invalid repository")
    n=timestamp(now);expected=slots(task,start,end)
    scope=(repository_id,installation)
    unique={}
    for e in events:
        validate_event(e)
        require((e["repository_id"],e["installation"])==scope,"observation scope mismatch")
        if e["provider"]!=provider or e["receipt"]["task_id"]!=task:continue
        require(timestamp(e["observed_at"])<=n,"future observation")
        k=event_key(e)
        require(k not in unique or event_digest(unique[k])==event_digest(e),"conflicting observation")
        unique[k]=e
    byslot={}
    for e in unique.values():
        if simulation:
            if e["provenance"]!="synthetic":continue
        elif not source_verified or e["provenance"]!="authenticated":continue
        s=e["receipt"]["scheduled_at"]
        if s not in expected:continue
        runs=byslot.setdefault(s,{})
        runs.setdefault((e["run_id"],e["attempt"]),[]).append(e)
    result=[]
    complete=history_complete and (simulation or source_verified)
    for s in expected:
        runs=byslot.get(s,{})
        latest=[]
        for history in runs.values():
            history.sort(key=lambda e:e["sequence"])
            for a,b in zip(history,history[1:]):
                require(timestamp(a["observed_at"])<=timestamp(b["observed_at"]),"out-of-order source sequence")
                ra,rb=a["receipt"],b["receipt"]
                for key in ("started_at","completed_at"):
                    require(ra[key] is None or ra[key]==rb[key],"execution timestamp changed")
            latest.append(history[-1])
        if len(latest)>1:
            result.append({"scheduled_at":s,"state":"MULTIPLE OBSERVED","timing":"UNKNOWN","attempts":len(latest),"scope":"synthetic" if simulation else "authenticated observation"})
        elif latest:
            r=latest[0]["receipt"]
            state=observed_state(s,r["started_at"],r["completed_at"],now,grace)
            timing="UNKNOWN"
            if r["started_at"] is not None:
                delta=timestamp(r["started_at"])-timestamp(s)
                timing="EARLY" if delta<timedelta(0) else "LATE" if delta>timedelta(seconds=grace) else "ON TIME"
            if state=="NOT OBSERVED" and not complete:state="UNKNOWN"
            result.append({"scheduled_at":s,"state":state,"timing":timing,"attempts":1,"scope":"synthetic" if simulation else "authenticated observation"})
        else:
            state=observed_state(s,None,None,now,grace) if complete else "UNKNOWN"
            result.append({"scheduled_at":s,"state":state,"timing":"UNKNOWN","attempts":0,"scope":"synthetic" if simulation else "coverage observation"})
    return result
