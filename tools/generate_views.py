"""Generate deterministic public views from the approved registry."""
import argparse
import html
import json
from pathlib import Path
from check import ROOT, load, validate
def outputs():
    cfg=load(ROOT/"config/schedule.json")
    validate(cfg)
    common=(ROOT/"prompts/common.md").read_text(encoding="utf-8").strip()
    sections=["# Reusable prompts","Generated from config/schedule.json and prompts/. Do not edit.",common]
    rows=[]
    for t in cfg["tasks"]:
        extra=(ROOT/"prompts/roles"/(t["id"]+".md")).read_text(encoding="utf-8").strip()
        sections.extend(["## "+t["title"]+" ("+t["cron"]+")",t["purpose"]+" "+extra])
        rows.append("<tr>"+"".join("<td>"+html.escape(t[k])+"</td>" for k in ("cron","title","authority"))+"</tr>")
    page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Schedule HQ template</title><style>body{font:16px system-ui;max-width:760px;margin:32px auto;padding:0 16px;color:#172033;background:#f5f7fa}table{width:100%;border-collapse:collapse;background:white}th,td{text-align:left;padding:10px;border-bottom:1px solid #ccd4dd}caption{text-align:left;font-weight:bold}</style><main><h1>'+html.escape(cfg["display_name"])+'</h1><p>Template only; no live telemetry supplied.</p><table><caption>Nominal UTC schedule</caption><thead><tr><th scope="col">Timing</th><th scope="col">Task</th><th scope="col">Authority</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table><p>No missing evidence is treated as success.</p></main></html>\n'
    return {"schedule.json":json.dumps(cfg,indent=2,ensure_ascii=False)+"\n","TASKS.md":"\n\n".join(sections)+"\n","dashboard/index.html":page,"dashboard.html":page}
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    for name,data in outputs().items():
        path=ROOT/name
        if args.check:
            if path.read_text(encoding="utf-8")!=data: raise ValueError("generated view drift: "+name)
        else:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(data,encoding="utf-8",newline="\n")
    print("PASS: canonical registry generated views")
if __name__=="__main__": main()
