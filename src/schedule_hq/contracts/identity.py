"""Repository names are locators, never authority. Observed API facts must be authenticated externally."""
import re
NAME=re.compile(r"[A-Za-z0-9-]{1,39}/[A-Za-z0-9_.-]{1,100}")
def same_repository(expected_id, observed, *, observation_verified):
    if observation_verified is not True or type(expected_id) is not int or expected_id<=0 or type(observed) is not dict:
        return False
    ident=observed.get("id")
    name=observed.get("full_name")
    return type(ident) is int and ident==expected_id and type(name) is str and NAME.fullmatch(name) is not None and name.split("/")[-1] not in (".","..")
