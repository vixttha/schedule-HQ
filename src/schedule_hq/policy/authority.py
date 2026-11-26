"""Pure fail-closed decision. Caller must independently authenticate and enforce atomic CAS."""
from dataclasses import dataclass
from schedule_hq.contracts.validation import SHA, timestamp
@dataclass(frozen=True)
class Lease:
    repository_id: int
    issue: int
    actor: str
    head: str
    fence: int
    expires_at: str

def may_publish(*, task, authorized, authenticated_actor, lease, repository_id, issue, head, fence, now, competing, atomic_supported):
    if task != "development" or authorized is not True or competing is not False or atomic_supported is not True:
        return False
    if not isinstance(lease,Lease) or type(repository_id) is not int or repository_id<=0 or type(issue) is not int or issue<=0:
        return False
    if type(lease.repository_id) is not int or type(lease.issue) is not int or type(fence) is not int or type(lease.fence) is not int or fence<=0:
        return False
    if not isinstance(authenticated_actor,str) or not authenticated_actor.strip() or not isinstance(head,str) or SHA.fullmatch(head) is None:
        return False
    try:
        return (lease.repository_id==repository_id and lease.issue==issue and lease.actor==authenticated_actor and lease.head==head and lease.fence==fence and timestamp(now)<timestamp(lease.expires_at))
    except (TypeError,ValueError):
        return False
