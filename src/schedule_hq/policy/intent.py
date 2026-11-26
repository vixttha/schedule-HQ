"""Bind verified historical write intent to current policy and recovery facts."""
from schedule_hq.contracts.validation import SHA
from schedule_hq.policy.authority import may_publish
from schedule_hq.policy.recovery import recovery
def assess(intent,authority,*,observed,observation_verified=False,intent_verified=False):
    if type(intent) is not dict or set(intent)!={"repository_id","issue","actor","before","expected","fence"} or type(authority) is not dict:return "BLOCKED"
    if any(type(intent[k]) is not int or intent[k]<=0 for k in ("repository_id","issue","fence")):return "BLOCKED"
    if any(type(intent[k]) is not str or SHA.fullmatch(intent[k]) is None for k in ("before","expected")):return "BLOCKED"
    if type(intent["actor"]) is not str or not intent["actor"].strip():return "BLOCKED"
    if any(intent[k]!=authority.get(k) for k in ("repository_id","issue","fence")):return "BLOCKED"
    if intent["actor"]!=authority.get("authenticated_actor") or intent["before"]!=authority.get("head"):return "BLOCKED"
    if authority.get("task")!="development":return "BLOCKED"
    try:allowed=may_publish(**authority)
    except (TypeError,ValueError):return "BLOCKED"
    return recovery(before=intent["before"],expected=intent["expected"],observed=observed,
                    observation_verified=observation_verified,intent_verified=intent_verified,
                    same_fence=allowed,atomic_supported=allowed)
