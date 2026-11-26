#!/usr/bin/env python3
"""Optional, dependency-free structural validator and index builder.

Not a JSON-Schema compliance engine; does not authenticate evidence or approve releases.
"""
import argparse
import json
import re
import shutil
import stat
import tempfile
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]
DECISION_STATES = {"adopted", "parked", "rejected", "superseded", "duplicate", "retired"}
MAX_RECORD_BYTES = 65536
MAX_RECORD_FILES = 10000
MAX_JSON_DEPTH = 96
# Bound exponent magnitude without expanding scientific notation into strings.
MAX_DECIMAL_EXPONENT = MAX_RECORD_BYTES


SUPPORTED_SCHEMA_KEYS = {
    "$schema", "title", "type", "required", "properties",
    "additionalProperties", "const", "enum", "minLength", "maxLength", "pattern",
    "minItems", "uniqueItems", "items",
}


def schema_issues(spec, where):
    """Fail closed if the bundled schema outgrows this limited interpreter."""
    if not isinstance(spec, dict):
        return [f"{where}: expected schema object"]
    issues = [f"{where}: unsupported schema keyword {key}" for key in
              sorted(set(spec) - SUPPORTED_SCHEMA_KEYS)]
    if "type" in spec and spec["type"] not in ("object", "array", "string", "integer"):
        issues.append(f"{where}: unsupported schema type")
    for key in ("minLength", "maxLength", "minItems"):
        if key in spec and (type(spec[key]) is not int or spec[key] < 0):
            issues.append(f"{where}: invalid {key}")
    for key in ("uniqueItems", "additionalProperties"):
        if key in spec and type(spec[key]) is not bool:
            issues.append(f"{where}: invalid {key}")
    for key in ("required", "enum"):
        if key in spec and (not isinstance(spec[key], list) or
                            (key == "required" and not all(isinstance(v, str) for v in spec[key]))):
            issues.append(f"{where}: invalid {key}")
    if ("minLength" in spec and "maxLength" in spec and
            type(spec["minLength"]) is int and type(spec["maxLength"]) is int and
            spec["maxLength"] < spec["minLength"]):
        issues.append(f"{where}: maxLength below minLength")
    if "pattern" in spec:
        if not isinstance(spec["pattern"], str):
            issues.append(f"{where}: invalid pattern")
        else:
            try:
                re.compile(spec["pattern"])
            except re.error:
                issues.append(f"{where}: invalid pattern")
    props = spec.get("properties", {})
    if not isinstance(props, dict):
        issues.append(f"{where}: invalid properties")
    else:
        for key, child in props.items():
            issues.extend(schema_issues(child, f"{where}.properties.{key}"))
    if "items" in spec:
        issues.extend(schema_issues(spec["items"], f"{where}.items"))
    return issues


def within_depth(value, limit=MAX_JSON_DEPTH):
    """Bound already-parsed JSON nesting without recursive Python calls."""
    stack = [(value, 0)]
    while stack:
        item, depth = stack.pop()
        if depth > limit:
            return False
        if isinstance(item, dict):
            stack.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            stack.extend((child, depth + 1) for child in item)
    return True


def parse_decimal(literal):
    """Parse JSON fractional/exponent notation exactly, without context rounding."""
    try:
        value = Decimal(literal)
    except InvalidOperation as exc:
        raise ValueError("invalid decimal JSON number") from exc
    if not value.is_finite():
        raise ValueError("invalid nonfinite JSON number")
    parts = value.as_tuple()
    if (len(parts.digits) > MAX_RECORD_BYTES
            or abs(parts.exponent) > MAX_DECIMAL_EXPONENT
            or abs(value.adjusted()) > MAX_DECIMAL_EXPONENT):
        raise ValueError("decimal JSON number exceeds bounds")
    return value


def reject_constant(literal):
    raise ValueError("invalid nonfinite JSON constant: " + literal)


def reject_duplicate_keys(pairs):
    """Reject repeated decoded member names in each JSON object."""
    result = {}
    for key, value in pairs:
        if key in result:
            # ASCII repr keeps malformed Unicode and control characters safe to report.
            raise ValueError(f"duplicate JSON key: {ascii(key)}")
        result[key] = value
    return result


def parse_json(text):
    # Leave integer tokens as int, preserving strict existing v1 type checks.
    return json.loads(text, parse_float=parse_decimal, parse_constant=reject_constant,
                      object_pairs_hook=reject_duplicate_keys)


def valid_unicode(value):
    """Reject lone UTF-16 surrogates in parsed JSON keys and string values."""
    stack = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, str):
            try:
                item.encode("utf-8", errors="strict")
            except UnicodeEncodeError:
                return False
        elif isinstance(item, dict):
            stack.extend(item.keys())
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
    return True


def json_identity(value):
    """JSON value equality for uniqueItems; object key order is insignificant.

    Keep booleans distinct from numbers and treat 1 and 1.0 as equal.
    Caller must first enforce MAX_JSON_DEPTH on untrusted records.
    """
    if value is None:
        return ("null",)
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, Decimal):
        return ("number", value)
    if isinstance(value, (int, float)):
        return ("number", Decimal(str(value)))
    if isinstance(value, str):
        return ("string", value)
    if isinstance(value, list):
        return ("array", tuple(json_identity(item) for item in value))
    if isinstance(value, dict):
        return ("object", tuple(sorted(
            (key, json_identity(item)) for key, item in value.items())))
    raise TypeError("unsupported JSON value")


def shape(value, schema, where):
    """Check only the JSON-Schema v1 keywords used by this template."""
    issues = []
    kind = schema.get("type")
    types = {"object": lambda x: isinstance(x, dict),
             "array": lambda x: isinstance(x, list),
             "string": lambda x: isinstance(x, str),
             "integer": lambda x: type(x) is int}
    if kind in types and not types[kind](value):
        return [f"{where}: expected {kind}"]
    if "const" in schema and (type(value) is not type(schema["const"]) or value != schema["const"]):
        issues.append(f"{where}: const mismatch")
    if "enum" in schema and value not in schema["enum"]:
        issues.append(f"{where}: invalid enum value")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            issues.append(f"{where}: text too short")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            issues.append(f"{where}: text too long")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            issues.append(f"{where}: invalid format")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            issues.append(f"{where}: too few entries")
        if schema.get("uniqueItems") and len({json_identity(item) for item in value}) != len(value):
            issues.append(f"{where}: duplicate entries")
        for i, item in enumerate(value):
            issues.extend(shape(item, schema.get("items", {}), f"{where}[{i}]"))
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                issues.append(f"{where}: missing {key}")
        if schema.get("additionalProperties") is False:
            for key in value.keys() - props.keys():
                issues.append(f"{where}: unknown field {key}")
        for key in value.keys() & props.keys():
            issues.extend(shape(value[key], props[key], f"{where}.{key}"))
    return issues


def safe_repo_path(value):
    return (isinstance(value, str) and bool(value) and
            "\\" not in value and not PurePosixPath(value).is_absolute() and
            not PureWindowsPath(value).drive and
            not PureWindowsPath(value).is_absolute() and
            not any(c in value for c in '<>:"|?*') and
            not any(ord(c) < 32 or ord(c) == 127 for c in value) and
            all(p not in ("", ".", "..") for p in value.split("/")))

def has_link_component(root, path):
    """Reject pre-existing symlinks along template-owned input/output paths.

    This is a read-only preflight, NOT an atomic filesystem security boundary:
    hostile concurrent changes still require host-level isolation.
    """
    current = root
    if current.is_symlink():
        return True
    for name in path.relative_to(root).parts:
        current = current / name
        if current.is_symlink():
            return True
    return False


def read_records(root, section, schema):
    problems, records = [], {}
    folder = root / section / "records"
    if has_link_component(root, folder):
        return [f"{section}/records: symlink component is forbidden"], records
    if not folder.is_dir():
        return [f"missing {section}/records directory"], records
    try:
        entries = sorted(folder.iterdir())
    except OSError as exc:
        return [f"{section}/records: unreadable directory: {exc}"], records
    if len(entries) > MAX_RECORD_FILES:
        return [f"{section}/records: too many entries"], records
    for path in entries:
        if has_link_component(root, path):
            problems.append(f"{path}: symlink record entry forbidden")
            continue
        if path.name == ".gitkeep":
            continue
        if not path.is_file() or path.suffix != ".json":
            problems.append(f"{path}: unexpected record entry")
            continue
        try:
            if path.stat().st_size > MAX_RECORD_BYTES:
                problems.append(f"{path}: oversize record")
                continue
            row = parse_json(path.read_text(encoding="utf-8"))
        except (ValueError, OSError, RecursionError) as exc:
            problems.append(f"{path}: bad JSON: {exc}")
            continue
        if not within_depth(row):
            problems.append(f"{path}: JSON nesting exceeds {MAX_JSON_DEPTH}")
            continue
        if not valid_unicode(row):
            problems.append(f"{path}: invalid Unicode (unpaired surrogate)")
            continue
        if not isinstance(row, dict):
            problems.append(f"{path}: expected object")
            continue
        ident = row.get("id")
        if not isinstance(ident, str) or path.stem != ident:
            problems.append(f"{path}: mismatched ID and filename")
            continue
        schema_errors = shape(row, schema, str(path))
        problems.extend(schema_errors)
        if schema_errors:
            continue  # Never run semantic checks on malformed record fields.
        if ident in records:
            problems.append(f"{path}: repeated record ID")
        records[ident] = row
    return problems, records


def validate(root=ROOT):
    problems = []
    # Inspect path components before opening schemas or indexes.
    for section, filename in (("ideas", "idea"), ("features", "feature")):
        for candidate in (f"{section}/schema/v1/{filename}.schema.json",
                          f"{section}/INDEX.md"):
            if has_link_component(root, root / candidate):
                problems.append(f"{candidate}: symlink component forbidden")
    if problems:
        return problems, {}, {}
    try:
        idea_schema = parse_json((root / "ideas/schema/v1/idea.schema.json").read_text(encoding="utf-8"))
        feat_schema = parse_json((root / "features/schema/v1/feature.schema.json").read_text(encoding="utf-8"))
    except (ValueError, OSError, RecursionError) as exc:
        return [f"schema unavailable or invalid: {exc}"], {}, {}
    for name, spec in (("ideas", idea_schema), ("features", feat_schema)):
        if not within_depth(spec):
            problems.append(f"{name}: schema nesting exceeds {MAX_JSON_DEPTH}")
    if problems:
        return problems, {}, {}
    for path, schema in (("ideas", idea_schema), ("features", feat_schema)):
        problems.extend(schema_issues(schema, f"{path}.schema"))
        if not isinstance(schema, dict) or schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            problems.append(f"{path}: schema dialect changed")
    if problems:
        return problems, {}, {}
    p, ideas = read_records(root, "ideas", idea_schema)
    problems.extend(p)
    p, feats = read_records(root, "features", feat_schema)
    problems.extend(p)
    for ident, row in ideas.items():
        if row.get("lifecycle_status") in DECISION_STATES and "decision" not in row:
            problems.append(f"{ident}: decision-bearing state without recorded decision")
        if row.get("lifecycle_status") not in DECISION_STATES and "decision" in row:
            problems.append(f"{ident}: premature decision on non-decision state")
        test = row.get("testing") or {}
        if test.get("status") == "tested" and (
            test.get("outcome") not in {"pass", "fail", "mixed", "inconclusive"} or
            not test.get("refs")):
            problems.append(f"{ident}: tested without outcome and references")
        if test.get("status") != "tested" and "outcome" in test:
            problems.append(f"{ident}: premature testing outcome")
        if test.get("status") == "tested" and not row.get("evidence"):
            problems.append(f"{ident}: tested idea without evidence")
        for target in row.get("related_ideas", []):
            if target == ident or target not in ideas:
                problems.append(f"{ident}: missing or self-linked idea {target}")
        for ev in row.get("evidence", []):
            if not safe_repo_path(ev.get("path")):
                problems.append(f"{ident}: unsafe evidence path")
    compatible_states = {
        "proposed": {"not_planned"},
        "planned": {"not_planned", "planned"},
        "in_progress": {"in_progress"},
        "implemented": {"implemented"},
        "verified": {"implemented"},
        "deprecated": {"implemented", "removed"},
        "retired": {"removed"},
    }
    for ident, row in feats.items():
        impl = row.get("implementation_status")
        lifecycle = row.get("lifecycle_status")
        if lifecycle in compatible_states and impl not in compatible_states[lifecycle]:
            problems.append(f"{ident}: incompatible lifecycle and implementation status")
        if impl == "implemented" and not row.get("evidence"):
            problems.append(f"{ident}: implemented without source evidence")
        for target in row.get("idea_ids", []):
            if target not in ideas:
                problems.append(f"{ident}: unresolved idea {target}")
        test = row.get("testing") or {}
        if test.get("status") == "tested" and (
            test.get("outcome") not in {"pass", "fail", "mixed", "inconclusive"} or
            not test.get("refs")):
            problems.append(f"{ident}: tested without outcome and references")
        if test.get("status") != "tested" and "outcome" in test:
            problems.append(f"{ident}: premature testing outcome")
        if test.get("status") == "tested" and not any(
                e.get("kind") in ("test", "audit") and e.get("source_sha") and
                e.get("source_path") and e.get("receipt")
                for e in row.get("evidence", [])):
            problems.append(f"{ident}: tested without source-bound test/audit evidence")
        if row.get("lifecycle_status") == "verified":
            if (row.get("implementation_status") != "implemented" or
                test.get("status") != "tested" or test.get("outcome") != "pass" or
                not any(e.get("kind") in ("test", "audit") for e in row.get("evidence", []))):
                problems.append(f"{ident}: unsupported verified claim")
        for ev in row.get("evidence", []):
            if not safe_repo_path(ev.get("source_path")):
                problems.append(f"{ident}: unsafe evidence path")
    return problems, ideas, feats


def cell(text):
    """Escape record text as plain data inside a GitHub Markdown table."""
    value = (str(text).replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace("|", "&#124;")
             .replace("\r", " ").replace("\n", " "))
    for ch in "\\`*_[]()!~":
        value = value.replace(ch, "\\" + ch)
    return value

def index(kind, rows):
    name = "Ideas" if kind == "ideas" else "Features"
    prefix = "IDEA" if kind == "ideas" else "FEAT"
    singular = "idea" if kind == "ideas" else "feature"
    description = (f"No canonical {singular} records yet." if not rows
                   else f"Generated from canonical {singular} records.")
    output = [f"# {name} — index (derived)", "",
              (f"> {description} This index is a convenience view; the records in "
               f"`{kind}/records/` are authoritative. Optional generator: "
               "`python tools/library.py build`."), "",
              f"| ID | {singular.title()} | Lifecycle | Implementation |",
              "| --- | --- | --- | --- |"]
    for ident, data in sorted(rows.items()):
        output.append(f"| {cell(ident)} | {cell(data.get('title', ''))} | "
                      f"{cell(data.get('lifecycle_status', ''))} | "
                      f"{cell(data.get('implementation_status', ''))} |")
    return "\n".join(output) + "\n"


def replace_indexes(root, encoded):
    """Stage both views, then replace individually with best-effort rollback.

    Requires an isolated, non-concurrently modified catalog. Not a multi-file
    atomic transaction or crash/power-loss recovery protocol.
    """
    plans = []
    staged = []
    committed = []
    retained = set()
    problems = []
    try:
        for kind, content in encoded.items():
            path = root / kind / "INDEX.md"
            try:
                mode = path.lstat().st_mode
            except FileNotFoundError:
                mode = None
            if mode is not None and not stat.S_ISREG(mode):
                raise OSError("index output is not a regular file")
            if mode is not None and not mode & stat.S_IWUSR:
                raise PermissionError("index output is read-only")
            plans.append((path, content, mode))
        for path, content, mode in plans:
            directory = Path(tempfile.mkdtemp(prefix=".provenistem-index-", dir=path.parent))
            staged.append((path, directory, mode))
            if mode is not None:
                shutil.copy2(path, directory / "previous")
            new = directory / "new"
            new.write_bytes(content)
            if mode is not None:
                new.chmod(stat.S_IMODE(mode))
        for path, directory, mode in staged:
            (directory / "new").replace(path)
            committed.append((path, directory, mode))
    except OSError as exc:
        problems.append(f"{path}: index update failed: {exc}")
        for path, directory, mode in reversed(committed):
            try:
                if mode is None:
                    path.unlink()
                else:
                    (directory / "previous").replace(path)
            except OSError as rollback_error:
                retained.add(directory)
                prior = ("original index absent" if mode is None
                         else f"previous bytes at {directory / 'previous'}")
                problems.append(f"{path}: rollback failed: {rollback_error}; {prior}; "
                                f"recovery directory retained: {directory}")
    finally:
        for path, directory, _ in staged:
            if directory not in retained:
                try:
                    shutil.rmtree(directory)
                except OSError as exc:
                    problems.append(f"{path}: staging cleanup failed: {exc}; retained {directory}")
    return problems


def run(root, action):
    problems, ideas, feats = validate(root)
    if problems:
        for issue in problems:
            print("FAIL:", issue)
        return 1
    views = {"ideas": index("ideas", ideas), "features": index("features", feats)}
    if action == "build":
        # Encode every view before opening either index. A Unicode failure must
        # leave both existing files intact; bytes also preserve LF on Windows.
        encoded = {}
        for kind, content in views.items():
            try:
                encoded[kind] = content.encode("utf-8", errors="strict")
            except UnicodeEncodeError:
                print(f"FAIL: {kind}/INDEX.md: invalid Unicode (unpaired surrogate)")
                return 1
        problems.extend(replace_indexes(root, encoded))
    else:
        for kind, expected in views.items():
            path = root / kind / "INDEX.md"
            if not path.is_file() or path.read_text(encoding="utf-8") != expected:
                problems.append(f"{kind}/INDEX.md: stale or missing; run build")
    if problems:
        for issue in problems:
            print("FAIL:", issue)
        return 1
    print(f"PASS: {len(ideas)} ideas, {len(feats)} features, index {action}; "
          "STRUCTURE ONLY — no external evidence or authority verified")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["check", "build"])
    parser.add_argument("--root", type=Path, default=ROOT,
                        help="Existing host-local library root (no writes for check)")
    parser.add_argument("--expect-empty", action="store_true",
                        help="Check that a starter has zero canonical records")
    args = parser.parse_args()
    root = args.root.absolute()
    if args.expect_empty:
        problems, ideas, feats = validate(root)
        if problems:
            for issue in problems:
                print("FAIL:", issue)
            raise SystemExit(1)
        if ideas or feats:
            print("FAIL: starter must contain zero canonical records")
            raise SystemExit(1)
    raise SystemExit(run(root, args.action))
