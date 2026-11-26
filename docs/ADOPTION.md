# Provenistem — Standalone adoption guide (v0.0.2)

**Purpose:** track project Ideas & Features and their status/progress, nothing broader. See [the owner-locked product scope](PRODUCT-SCOPE-LOCK.md).

## Zero-install copy
**This is a draft procedure; it is not a receipt for a completed fresh-adopter test.** Before copying, inspect the host's governing instructions, all proposed copy paths (including documentation, license, templates, tools and tests). Select a new isolated destination or stop for human-owned reconciliation; do not merge independent canonical registries automatically.

Use GitHub's web UI, Git, or whatever file tooling is already available. Copy `README.md`, `LICENSE`, `LIBRARY-AGENT-GUIDE.md`, `ideas/`, `features/`, `docs/`, and `templates/` into one isolated, collision-free library root. Select the reviewed portable package directory (`packages/provenistem/` in the development repository) as the copy source. Select an explicitly authorized host destination. Keep the blank `records/` folders (represented by `.gitkeep`). Preserve the [MIT license](../LICENSE) and its copyright and permission notices. The agent guide and example templates are optional to use; you can create records manually according to the schemas. Keep the complete basic copy for working relative links.

**Never overwrite** an existing host file or `AGENTS.md`. Stop and reconcile if a directory already exists or an ID conflicts. No account credentials, cloud API, plugin, hosted service, local runner, Python package or new execution environment is necessary for record storage or browsing.

## Host-local records
Each adopter starts at `IDEA-000001` / `FEAT-000001` in its own repository, with its own evidence, metadata and approvals. IDs are scoped **to the host repository**, not globally. Host paths are relative; do not link to another project's private data or inherit its record status.

Examples are stored in `templates/`, never in `*/records/`. Remove example-only placeholders before declaring a record meaningful. Update the two indexes manually or with the optional tool.

## Optional validation
If Python 3 is already available, add `tools/` to the complete basic copy for validation; add both `tools/` and `tests/` for offline regressions. Run commands from the library root, not the enclosing host repository. The dependency-free `tools/library.py` helper offers `check` and `build` actions. Run `python -m unittest discover -s tests -v` only in a clean, isolated starter or synthetic test copy with empty canonical record directories. For a populated host use `python tools/library.py check` (never `--expect-empty`) and run `python tools/library.py build` only with authorization to regenerate derived indexes. Do not run the full source-distribution regression suite against populated host records, and never remove records to satisfy it. For starter-distribution acceptance, also run `python tools/library.py check --expect-empty` in the clean starter. In v0.0.2, `python tools/adopter.py <host-library-root>` produces a **read-only, non-mutating** per-file upgrade plan. `SAME` files are unchanged; `KEEP_HOST` protects canonical records/indexes; `REVIEW_LOCAL_DIFFERENCE` requires host-controlled field-by-field reconciliation; `ADD` means absent but is not permission to copy. Nothing is installed or modified by the planner. Local schema additions must be retained, not overwritten. **Do not run this helper on untrusted or concurrently writable filesystems with elevated permissions.** Symlink checks are preflights, not atomic anti-race guarantees. Each new adopting repository must run its own host-specific checks; the source's accepted test receipts and two prior adopter checks do not certify every future installation. The optional helpers are not installed by default, are not a runtime dependency, and do not grant authority.

### Blocked destination ancestors
A new destination beneath an existing non-directory ancestor is blocked before any file actions are returned; the diagnostic identifies the ancestor. Missing directory components alone are permitted.

## Scope of this package
Provenistem is an isolated, optional Ideas + Features product. Installing it does **not** install, configure, update, or authorize any other framework or project. A separate control plane may offer it through an optional host-owned adapter, but no automatic install, merge, CI provisioning, host README replacement or policy mutation is part of adoption.
