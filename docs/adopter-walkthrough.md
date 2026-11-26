# Build and verify two project versions

Start in a clean Veraphify checkout. Use Bash, Git, Node.js 24, and CPython 3.12 with venv support on Linux x86-64. The walkthrough creates a disposable Git project, fetches the existing Graphify evidence builder at a fixed commit, and installs its hash-locked wheels into a temporary environment.

Run the block from the Veraphify repository root. Build output and archives stay under a temporary directory and are removed at exit.

```bash
set -euo pipefail
cli="$PWD/veraphifiy.mjs"
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
kit="$work/kit"
project="$work/project"
archive="$work/archive"
identity=example/veraphifiy-walkthrough
producer=6af3c2025be3f51e02dca4e4502088c526aae6d1

git init -q "$kit"
git -C "$kit" fetch -q --no-tags --depth=1 https://github.com/vixttha/Blender-Agent-Refinement-Toolkit.git "$producer"
git -C "$kit" checkout -q --detach "$producer"
kit="$kit/versions/v0.0.8"
python3.12 -m venv "$work/.venv"
python="$work/.venv/bin/python"
export PATH="$work/.venv/bin:$PATH"
"$python" -m pip install --require-hashes --no-deps --only-binary=:all: -r "$kit/requirements.txt"
"$python" -m pip check

git init -q "$project"
mkdir -p "$project/src"
printf '# Export\nExports a status.\n' > "$project/notes.md"
commit_fixture() {
  git -C "$project" add notes.md src/feature.py test_feature.py
  git -C "$project" -c user.name=Walkthrough -c user.email=walkthrough@example.invalid \
    -c commit.gpgsign=false commit -qm "$1"
}
build_and_import() {
  local version=$1 value=$2 source
  source=$(git -C "$project" rev-parse HEAD)
  "$python" - "$work/$version.manifest.json" "$identity" "$source" "$value" <<'PY'
import json
import sys
from pathlib import Path

path, project, source, value = sys.argv[1:]
feature = {
    "id": "export",
    "label": "Export status",
    "documented_in": [{"path": "notes.md", "anchor": "# Export"}],
    "changed_in": [{"path": "notes.md", "anchor": "Exports a status."}],
    "tested_by": [{"path": "test_feature.py", "anchor": "def test_export():"}],
    "implemented_in": [{"path": "src/feature.py", "anchor": f"return {value!r}"}],
}
Path(path).write_text(json.dumps({
    "repository": project,
    "source_commit": source,
    "title": "Veraphify adopter walkthrough",
    "source_files": ["src/feature.py"],
    "features": [feature],
}), encoding="utf-8")
PY
  (cd "$project" && GRAPHIFY_QUERY_LOG_DISABLE=1 PYTHONHASHSEED=0 \
    "$python" "$kit/evidence_map.py" "$work/$version.manifest.json" "$work/$version-evidence")
  node "$cli" import --archive "$archive" --project "$identity" --version "$version" \
    --source "$source" --checkout "$project" --evidence "$work/$version-evidence" > "$work/$version-pins.json"
}

printf "# Export implementation\ndef export():\n    return 'ready'\n" > "$project/src/feature.py"
printf "from src.feature import export\ndef test_export():\n    assert export() == 'ready'\n" > "$project/test_feature.py"
commit_fixture 'Initial export'
build_and_import v1.0.0 ready
first_archive=$(find "$archive" -maxdepth 1 -name '*.json' -print)
cp "$first_archive" "$work/first-entry.json"

printf "# Export implementation\n# Revised status\ndef export():\n    return 'updated'\n" > "$project/src/feature.py"
printf "from src.feature import export\n# Revised status test\ndef test_export():\n    assert export() == 'updated'\n" > "$project/test_feature.py"
commit_fixture 'Update the exported status'
build_and_import v1.1.0 updated
cmp "$first_archive" "$work/first-entry.json"

for version in v1.0.0 v1.1.0; do
  read -r source digest < <("$python" -c \
    'import json,sys; p=json.load(open(sys.argv[1])); print(p["source"],p["archive_sha256"])' \
    "$work/$version-pins.json")
  node "$cli" verify --archive "$archive" --project "$identity" --version "$version" \
    --source "$source" --archive-sha256 "$digest"
  node "$cli" lookup --archive "$archive" --project "$identity" --version "$version" \
    --source "$source" --archive-sha256 "$digest" --feature feature:export | tee "$work/$version-lookup.json"
done

"$python" - "$work" <<'PY'
import json
import sys
from pathlib import Path

work = Path(sys.argv[1])
sources = set()
for version, line, test_line in (("v1.0.0", 3, 2), ("v1.1.0", 4, 3)):
    lookup = json.loads((work / f"{version}-lookup.json").read_text())
    assert lookup["version"] == version, lookup
    assert lookup["citations"] == [{"path": "src/feature.py", "line": line}], lookup
    sources.add(lookup["source"])
    graph = json.loads((work / f"{version}-evidence" / "graph.json").read_text())
    tests = [link for link in graph["links"] if link["relation"] == "tested_by"]
    assert any(link["target"] == f"tested_by:test_feature.py:L{test_line}" for link in tests), tests
    print(f"{version} verified at {lookup['source']}, citation src/feature.py:{line}")
assert len(sources) == 2, sources
PY

if node "$cli" verify --archive "$archive" --project "$identity" --version v2.0.0 > "$work/missing.log" 2>&1; then
  echo 'An unarchived version unexpectedly verified' >&2
  exit 1
fi
grep -F 'Project version is not archived' "$work/missing.log"
```

The two lookups report distinct Git commits and citations at `src/feature.py:3` and `src/feature.py:4`. The earlier archive remains byte-for-byte identical after importing the newer version. For a real project, record the source commit and archive hash from a trusted import separately from the archive. Supply both pins when verifying the exact entry.
