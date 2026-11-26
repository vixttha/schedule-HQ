# Schedule HQ — v0.0.0.2 architecture candidate

Working name; IDs and file paths are independent of the brand. A portable operating template for scheduled engineering tasks. Copy this isolated template only with owner permission. GitHub is canonical; Notion and Supabase are optional, never mandatory. No live schedules are enabled by this branch.

Start with [workflow](WORKFLOW.md), [configuration](schedule.json), [task prompts](TASKS.md), [receipt example](examples/receipt.json), and [dashboard](dashboard.html). Use the GitHub Actions proof from the candidate branch. Do not publish private scheduler logs, conversation IDs, credentials or personal details.

Installations: VIB, Veraphify, Provenistem are separate branches; do not merge their contents into product source. See [pins](dependencies.json). Product acceptance requires fresh adopter evidence, not merely upstream green runs.

## Architecture migration
Canonical configuration: [schedule](config/schedule.json) and [dependency lock](config/dependencies.lock.json). [Versioned schemas](schemas/v1), [approved decisions](docs/decisions/v0.0.0.2.md), [migration/rollback](docs/migrations/v0.0.0.2.md). Root schedule, TASKS and dashboard are compatibility outputs. Actual host enforcement is not implemented.
