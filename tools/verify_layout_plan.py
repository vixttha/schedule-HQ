"""Verify planning metadata without asserting any migration has occurred."""
import json
import subprocess
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()

def main():
    freeze = json.loads((ROOT / "freeze/v0.0.0.1.json").read_text(encoding="utf-8"))
    plan = json.loads((ROOT / "docs/architecture/path-map.json").read_text(encoding="utf-8"))
    src = freeze["components"]["Schedule-HQ-Template"]
    assert plan["source_commit"] == src["commit"]
    assert plan["status"] == "approved_incremental_migration"
    mapping = plan["mapping"]
    inventory = {f["path"]: f["blob"] for f in src["files"]}
    assert len(mapping) == len(inventory)
    assert {m["from"] for m in mapping} == set(inventory)
    assert len({m["to"].casefold() for m in mapping}) == len(mapping)
    for m in mapping:
        p = PurePosixPath(m["to"])
        assert not p.is_absolute() and ".." not in p.parts and "\\" not in m["to"]
    for path, blob in inventory.items():
        assert git("rev-parse", src["commit"] + ":" + path) == blob, path
        assert (ROOT / path).is_file(), path  # compatibility surface retained
    print(f"PASS: {len(inventory)} frozen template paths mapped exactly once; frozen source blobs verified; compatibility paths retained")

if __name__ == "__main__":
    main()
