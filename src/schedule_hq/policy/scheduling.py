"""Nominal UTC slots only; no scheduler invocation or host-delivery promise."""
from datetime import timedelta,timezone
from schedule_hq.contracts.validation import TASKS,timestamp
def slots(task,start,end):
    if task not in TASKS: raise ValueError("unknown task")
    a,b=timestamp(start),timestamp(end)
    if b<a or b-a>timedelta(days=7): raise ValueError("invalid bounded window")
    t=a.replace(second=0,microsecond=0)
    if t<a: t+=timedelta(minutes=1)
    minute={"development":0,"handoff":15,"verification":30,"audit":45,"release":0}[task]
    result=[]
    while t<b:
        if t.minute==minute and (task!="release" or t.hour%4==0): result.append(t.isoformat().replace("+00:00","Z"))
        t+=timedelta(minutes=1)
    return result
def local_stamp(utc,offset_minutes):
    if type(offset_minutes) is not int or not -840<=offset_minutes<=840: raise ValueError("invalid observed offset")
    return timestamp(utc).astimezone(timezone(timedelta(minutes=offset_minutes))).isoformat()
def observed_state(scheduled,started,completed,now,grace_seconds):
    s,n=timestamp(scheduled),timestamp(now)
    if type(grace_seconds) is not int or grace_seconds<0: raise ValueError("invalid grace")
    if completed is not None and started is None: raise ValueError("completion without start")
    if started is not None:
        a=timestamp(started)
        if a>n: raise ValueError("invalid start")
        if completed is not None:
            b=timestamp(completed)
            if not a<=b<=n: raise ValueError("invalid completion")
            return "COMPLETED"
        return "RUNNING"
    return "NOT OBSERVED" if n>s+timedelta(seconds=grace_seconds) else "PENDING"
