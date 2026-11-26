"""No blind retries after ambiguous writes; observe a durable intent first."""
from schedule_hq.contracts.validation import SHA
def recovery(*, before, expected, observed, observation_verified, intent_verified, same_fence, atomic_supported):
    if any(not isinstance(s,str) or SHA.fullmatch(s) is None for s in (before,expected,observed)) or before==expected:
        return "BLOCKED"
    if observation_verified is not True or intent_verified is not True: return "BLOCKED"
    if observed==expected: return "ALREADY_APPLIED"
    if observed!=before: return "CONFLICT"
    if same_fence is True and atomic_supported is True: return "REAUTHORIZE"
    return "BLOCKED"
