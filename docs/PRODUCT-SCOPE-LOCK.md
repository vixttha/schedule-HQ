# Provenistem — LOCKED PRODUCT SCOPE

**Decision ID:** `PROVENISTEM-SCOPE-2026-11-12`  
**Owner approval:** 2026-11-12  
**Status:** `PRODUCT_SCOPE_LOCKED`  
**Release boundary:** this is a future-branch scope correction, **not an edit to the published private v0.0.2 tag**.

## What Provenistem is

> **Provenistem is a standalone, reusable Ideas & Features tracker for any project. It records, organizes, links, and tracks project ideas and features as development progresses.**

That is its entire product purpose. It should be simple for humans and LLMs to use, and usable without any other product.

### Within scope

- **Ideas:** add, describe, categorize, review and record idea status (including adopted, rejected or parked).
- **Features:** add, describe, categorize and record planned/in-progress/implemented and testing status.
- **Relationships:** optionally link a feature to originating ideas and link related ideas.
- **Progress:** understand which items were proposed, are being explored, were implemented or still need testing.
- **Supporting tracking metadata:** optional authorship/origin, decision context, source/evidence references, stable project-local IDs, JSON validation, generated indexes, and read-only no-clobber adoption planning.

These fields help keep an accurate feature/idea list. They do **not** create separate governance, evidence-verification, approval, release, or knowledge-management product obligations. A feature status is not independent proof; a recorded implementation or test result does not mean the host has released anything.

### Out of scope

Provenistem is **not** a project-governance engine, second development workflow, issue/task scheduler, agent/team orchestration layer, build system, autonomous installer, permission/approval system, official release system, independent evidence attestor, generalized knowledge graph, or all-in-one project management platform. No automatic cross-project sync or hidden runtime service.

### Relationship to Governance-Branch

1. Provenistem works **standalone** without Governance.
2. Governance-Branch works **standalone** using its own native libraries.
3. A Governance user may **optionally choose** Provenistem specifically for Ideas & Features tracking. Integration should be the **simplest compatible approach**. A Governance-owned adapter is only a possible future mechanism if needed, **not a mandatory architecture or an implemented feature**.
4. No double-writer canonical Ideas/Features catalog, silent schema conversion, overwrites of a host's records, or automatic installation.
5. Neither product imports the other as a required runtime dependency or gains authority over the other's project/release decisions.

### Neutral distribution

Do not ship real development/adopter project names, their records, private repository links, runner names, credentials, or historical internal audit data as product defaults. Synthetic fixtures are allowed. Private development evidence may retain historical provenance separately. The published v0.0.2 tag stays immutable.

## Precedence and change control

**This scope lock supersedes any earlier description that expanded Provenistem into a general provenance/evidence/knowledge/governance system or required an elaborate adapter.** Earlier one-way interoperability and no-clobber safeguards remain in force where compatible with this simpler mission.

This decision does not implement or enable the optional Governance integration, approve any migration, or change the published v0.0.2 release. Ordinary features cannot expand the core mission. A new scope requires a **new explicit owner decision** and its own compatibility/release review.
