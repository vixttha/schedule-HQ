import json, subprocess, re
from pathlib import Path
root=Path(__file__).resolve().parents[1]
freeze=json.loads((root/"freeze/v0.0.0.1.json").read_text(encoding="utf-8"))
for f in freeze["components"]["Schedule-HQ-Template"]["files"]:
    if f["path"]=="README.md": continue
    actual=subprocess.check_output(["git","rev-parse","HEAD:"+f["path"]],cwd=root,text=True).strip()
    if actual!=f["blob"]: raise ValueError("Frozen runtime drift: "+f["path"])
readme=(root/"README.md").read_text(encoding="utf-8")
for path in re.findall(r"\]\(([^)]+)\)",readme):
    if not path.startswith(("https://","#")) and not (root/path.split("#")[0]).is_file():
        raise ValueError("Broken homepage path: "+path)
assert "v0.0.0.1" in readme and "not a GitHub Release" in readme
assert json.loads((root/"schedule.json").read_text(encoding="utf-8"))["enabled"] is False
print("PASS: 9/9 frozen product blobs unchanged, homepage links and disabled default")
