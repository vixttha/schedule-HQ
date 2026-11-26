# Schedule HQ

**A portable operating template for scheduled engineering tasks.**

Version **v0.0.0.2** · Architecture candidate · Working project name

Schedule HQ organizes scheduled AI-assisted engineering work into five coordinated tasks. It keeps one conditional writer, four read-only monitors, revision-bound evidence and a single associated conversation. It is a template, not a hosted scheduler or an automatic permission system.

## Quickstart

Use Python 3.12 on a clean checkout of this repository. From the repository root:

```sh
python tools/check.py
python -m unittest discover -s tests -v
```

The first command reports `PASS: strict offline template and receipt contract; no live scheduler execution asserted`. The second runs the foundation and architecture regression suites. The template is disabled by default; no task, credential, database or paid runner is needed for these offline checks.

## How it works

| UTC timing | Task | Authority |
| --- | --- | --- |
| Hourly :00 | Development Loop | One bounded write only when explicitly authorized and exclusively owned |
| Hourly :15 | Handoff Control | Read-only |
| Hourly :30 | Verification Watch | Read-only |
| Hourly :45 | Audit Evidence | Read-only |
| Every four hours | Release Control | Read-only |

**Head → Worker → Validate → Internal Auditor → Head.** Missing evidence is not a pass. A task prompt is not a lease. Do not create replacement conversations, delegate to separate agents, or replay uncertain writes.

## Navigation

| Goal | Start here |
| --- | --- |
| Understand the operating rules | [Workflow](WORKFLOW.md) |
| Configure a portable schedule | [Schedule registry](schedule.json) |
| Read the five task instructions | [Task prompts](TASKS.md) |
| Inspect a sample receipt | [Receipt example](examples/receipt.json) |
| View the static schedule | [Dashboard](dashboard.html) |
| Check the original foundation | [Frozen source and evidence](freeze/v0.0.0.1.json) |
| Find current development | [Architecture issue #2](https://github.com/vixttha/schedule-HQ/issues/2) |

## Evidence and status

The frozen template source [e0f9e7a](https://github.com/vixttha/schedule-HQ/commit/e0f9e7acab71efa71fd4898625360966a5fa08a3) passed five tests each on [Ubuntu and Windows](https://github.com/vixttha/schedule-HQ/actions/runs/45786560547). The source-specific graph has [verified archive pins](https://github.com/vixttha/schedule-HQ/blob/51b01c5ed29ca7e8c3470171b3c0e837379e9c3c/archive/v0.0.0.1-pins.json); this evidence predates the homepage publication. See the latest CI for the actual published revision. Live task execution, exclusive lease enforcement, same-conversation delivery, independent acceptance and production readiness have not been established. The next architecture checkpoint remains separate.

## Independent engineering tools

| Tool | Dedicated branch |
| --- | --- |
| Version-Issues-Hub | [VIB](https://github.com/vixttha/schedule-HQ/tree/Version-Issues-Hub) |
| Veraphify | [Veraphify](https://github.com/vixttha/schedule-HQ/tree/Veraphify) |
| Provenistem | [Provenistem](https://github.com/vixttha/schedule-HQ/tree/Provenistem) |
| README HQ | [Pinned reader adoption](https://github.com/vixttha/schedule-HQ/tree/f1ab0fa8634ce3a6a8a83fc50c29a051d177a62e) |

The [historical dependency file](dependencies.json) retains the initial installation pins; the frozen manifest identifies the qualified historical revisions. Optional tools must remain independent. GitHub is the canonical evidence source; Notion and Supabase are optional. No mandatory external service.

## Development and reuse

Use standard public GitHub-hosted runners only. Report defects with a reproducible scenario, exact SHA and proof links. Never publish private prompts, task or conversation IDs, credentials or raw logs. The owner controls scope, integration and release. No standalone reuse license has been declared for Schedule HQ; request permission before redistribution. Upstream tools keep their own terms.

This candidate preserves the published .1 foundation. It is not a GitHub Release or a claim of production acceptance.

## Architecture candidate

[Canonical schedule](config/schedule.json), [dependency lock](config/dependencies.lock.json), [approved decisions](docs/decisions/v0.0.0.2.md), [migration contract](docs/migrations/v0.0.0.2.md). Legacy root paths are retained for compatibility.

[Offline defensive contracts](docs/architecture/contracts.md) cover authority decisions, duplicate reporting, ambiguous-write recovery, UTC slots, privacy projection and portable paths. No live host enforcement is claimed.
