#!/usr/bin/env python3
"""Read-only, no-clobber adoption/upgrade preflight.

Never copies, modifies, deletes or overwrites host or source files.
Only the selected candidate is inspected; no unrelated repository is accessed.
This is NOT an atomic safeguard against concurrent filesystem changes.
"""
import argparse
import json
from pathlib import Path

import library

PACKAGE_ROOTS = ("ideas", "features", "templates")
PACKAGE_TOPLEVEL = ("README.md", "LICENSE", "LIBRARY-AGENT-GUIDE.md")
PACKAGE_DOCS = {
    "ADOPTION.md", "ISOLATION.md", "LIFECYCLE.md",
    "ONE-WAY-BOUNDARY.md", "PROVENANCE.md",
    "PORTABILITY-AND-MODULE-CONTRACT.md", "PORTABILITY-AND-MODULE-CONTRACT.json",
    "PRODUCT-SCOPE-LOCK.md",
}
PACKAGE_TOOL_FILES = {"library.py", "adopter.py"}
PACKAGE_TEST_FILES = {
    "test_library.py", "test_one_way_boundary.py", "test_hardening.py",
    "test_adopter_profiles.py", "test_v002_six_team_repairs.py",
    "test_modularity_contract.py", "test_unicode_index_integrity.py",
}


def candidates(source):
    files = []
    for section in PACKAGE_ROOTS:
        folder = source / section
        if not folder.is_dir() or library.has_link_component(source, folder):
            raise ValueError(f"source section absent or linked: {section}")
        for path in folder.rglob("*"):
            if library.has_link_component(source, path):
                raise ValueError(f"source symlink is forbidden: {path}")
            if path.is_file():
                files.append(path.relative_to(source))
    for name in PACKAGE_TOPLEVEL:
        path = source / name
        if path.is_file():
            files.append(path.relative_to(source))
    for name in sorted(PACKAGE_DOCS):
        path = source / "docs" / name
        if path.is_file():
            files.append(path.relative_to(source))
    for prefix, allowed in (("tools", PACKAGE_TOOL_FILES), ("tests", PACKAGE_TEST_FILES)):
        for name in sorted(allowed):
            path = source / prefix / name
            if path.is_file():
                files.append(path.relative_to(source))
    ordered = sorted(set(files), key=lambda p: p.as_posix())
    for relative in ordered:
        if library.has_link_component(source, source / relative):
            raise ValueError(f"source symlink component forbidden: {relative}")
    return ordered


def governance_collision(destination):
    """Identify canonical Governance namespaces at the requested installation root.

    Do not scan parent directories: an isolated optional subdirectory is allowed.
    These are positive markers, not a claim to detect every Governance edition.
    """
    found = []
    for relative in ("ideas/library.yaml",
                     "src/governance_branch/libraries/ideas.py",
                     "governance"):
        if (destination / relative).exists() or (destination / relative).is_symlink():
            found.append(relative)
    idea_schema = destination / "ideas/schema/v1/idea.schema.json"
    if idea_schema.exists() or idea_schema.is_symlink():
        if library.has_link_component(destination, idea_schema):
            found.append("ideas/schema/v1/idea.schema.json (symlink)")
        else:
            try:
                if idea_schema.stat().st_size > library.MAX_RECORD_BYTES:
                    found.append("ideas/schema/v1/idea.schema.json (unrecognized oversized schema)")
                else:
                    spec = json.loads(idea_schema.read_text(encoding="utf-8"))
                    if isinstance(spec, dict) and (
                        "uid" in spec.get("required", []) or
                        "uid" in spec.get("properties", {}) or
                        "$defs" in spec or "$ref" in spec):
                        found.append("ideas/schema/v1/idea.schema.json (Governance schema signature)")
            except (OSError, ValueError, TypeError, RecursionError):
                found.append("ideas/schema/v1/idea.schema.json (unreadable schema)")
    return sorted(set(found))


def plan(source, destination):
    source = Path(source).absolute()
    destination = Path(destination).absolute()
    if source == destination:
        raise ValueError("source and host destination may not be the same")
    if library.has_link_component(source, source):
        raise ValueError("source root symlink")
    # Check ancestors first: exists() can hide ENOTDIR for a missing child.
    for parent in reversed(destination.parents):
        if (parent.exists() or parent.is_symlink()) and not parent.is_dir():
            raise ValueError(f"host destination ancestor is not a directory: {parent}")
    if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
        raise ValueError("host destination is not a safe directory")
    if not destination.exists():
        # Parent path cannot be treated as an authorized installation.
        return {"status": "NEW_DESTINATION", "writes": False,
                "entries": [{"path": p.as_posix(), "action": "ADD"}
                            for p in candidates(source)]}
    if library.has_link_component(destination, destination):
        raise ValueError("host root symlink")
    collision = governance_collision(destination)
    if collision:
        # Deliberately no upgrade file actions: this is a hard stop.
        return {"status": "NAMESPACE_COLLISION", "writes": False,
                "entries": [], "markers": collision}
    entries = []
    for relative in candidates(source):
        target = destination / relative
        if library.has_link_component(destination, target):
            raise ValueError(f"host path symlink: {relative}")
        if target.is_dir():
            entries.append({"path": relative.as_posix(), "action": "CONFLICT_DIRECTORY"})
        elif target.is_file():
            # Do not interpret canonical host data or user documentation as upstream-managed.
            if "records" in relative.parts or relative.name == "INDEX.md":
                action = "KEEP_HOST"
            elif target.read_bytes() == (source / relative).read_bytes():
                action = "SAME"
            else:
                action = "REVIEW_LOCAL_DIFFERENCE"
            entries.append({"path": relative.as_posix(), "action": action})
        else:
            entries.append({"path": relative.as_posix(), "action": "ADD"})
    return {"status": "EXISTING_DESTINATION", "writes": False, "entries": entries}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="chosen host library directory")
    parser.add_argument("--source", type=Path, default=library.ROOT)
    args = parser.parse_args(argv)
    try:
        result = plan(args.source, args.destination)
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "BLOCKED", "writes": False, "error": str(exc)}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] == "NAMESPACE_COLLISION":
        return 2
    return 1 if any(e["action"] in ("REVIEW_LOCAL_DIFFERENCE", "CONFLICT_DIRECTORY")
                    for e in result["entries"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
