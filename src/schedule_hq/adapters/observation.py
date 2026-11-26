"""Read-only response classification; no network or credentials inside the policy."""
from schedule_hq.contracts.identity import same_repository
def classify_response(status,body,expected_repository_id,*,authenticated=False):
    if authenticated is not True or type(status) is not int:return "UNVERIFIED"
    if status==429:return "RATE LIMITED"
    if status in (401,403):return "ACCESS UNVERIFIED"
    if status==404:return "NOT OBSERVED"
    if 500<=status<=599:return "UNAVAILABLE"
    if status!=200:return "UNVERIFIED"
    if type(body) is not dict or type(body.get("id")) is not int or type(body.get("full_name")) is not str:return "MALFORMED"
    return "VERIFIED IDENTITY" if same_repository(expected_repository_id,body,observation_verified=True) else "IDENTITY MISMATCH"
