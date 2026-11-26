"""Prepare, verify or retire an isolated read-only Schedule HQ adoption bundle."""
import argparse,json
from check import ROOT
from schedule_hq.adoption import bundle,install,verify,uninstall

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("install","verify","uninstall"))
    p.add_argument("--checkout",required=True);p.add_argument("--repository",required=True)
    p.add_argument("--repository-id",required=True,type=int);p.add_argument("--timezone",default="Etc/UTC")
    p.add_argument("--minutes",help="JSON object with all five task minute offsets")
    p.add_argument("--release-hours",type=int,default=4);p.add_argument("--apply",action="store_true")
    a=p.parse_args()
    if a.apply and a.action!="uninstall":p.error("--apply is only for uninstall")
    try:
        files=bundle(ROOT,repository=a.repository,repository_id=a.repository_id,timezone=a.timezone,
                     minutes=json.loads(a.minutes) if a.minutes else None,release_hours=a.release_hours)
        if a.action=="install":install(a.checkout,files)
        elif a.action=="verify":verify(a.checkout,files)
        else:uninstall(a.checkout,files,apply=a.apply)
    except (ValueError,OSError) as e:
        p.exit(2,"BLOCKED: adoption validation or filesystem operation failed; inspect private checkout locally.\n")
    print("PASS: local "+a.action+(" (dry run)" if a.action=="uninstall" and not a.apply else "")+"; no host task or Git ref changed")
if __name__=="__main__":main()
