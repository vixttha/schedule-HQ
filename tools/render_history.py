"""Generate or check a static synthetic example; private history is never read here."""
import argparse
from check import ROOT
from qualify_workload import fixture,TASKS
from schedule_hq.evidence.history_report import render
def main():
    p=argparse.ArgumentParser();p.add_argument("--check",action="store_true");a=p.parse_args()
    data=render([fixture(0,task) for task in TASKS])
    target=ROOT/"dashboard/execution-example.html"
    if a.check:
        if target.read_text(encoding="utf-8")!=data:raise ValueError("execution report drift")
    else:target.write_text(data,encoding="utf-8",newline="\n")
    print("PASS: deterministic redacted synthetic execution example")
if __name__=="__main__":main()
