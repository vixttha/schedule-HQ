# Provenistem — portable product provenance boundaries

**Product:** Provenistem  
**Historical private release:** v0.0.2, immutable tag `provenistem-v0.0.2`  
**Owner-approved architecture revision:** `GB-PROVENISTEM-OPTIONAL-RELATIONSHIP-2026-11-12`  
**This branch:** forward-looking documentation and neutrality candidate, **not a new release**.

## What provenance means

Provenistem records the source, lifecycle and supporting evidence **references** of ideas and features. An evidence reference must not be confused with independently authenticated proof, a real approval, a task assignment, or official product-release membership. The project's own repository and release authority remain canonical for those claims.

The portable distribution must not import another organization's ideas, features, decisions, actual adopter test receipts, private repository addresses or CI runner configuration. Canonical `ideas/records/` and `features/records/` start empty; examples are explicitly fictional.

## Source and build traceability, kept out of consumer defaults

A package release is tied to its actual immutable Git tag and reviewed package commit. Full internal development histories, source-testing runs, adopter receipts and developer repository names remain in their own **separate development audit records**. They must not be embedded as a runtime/default product dependency or expose a customer in a generic distributed package.

The historical private v0.0.2 artifact is intentionally **not rewritten** by this new neutrality decision. Future neutral packages must be created at new, separately approved and tested commits. No existing test receipt can be silently transferred to a new SHA.

## Relationship to other systems

Provenistem stands alone. A host project may build its own optional, owner-approved adapter; that adapter may be distributed independently but never becomes a mandatory Provenistem core import. The host's policy, existing canonical Ideas/Features, authentication, security review and release decisions remain its own.

See [the locked module boundary](PORTABILITY-AND-MODULE-CONTRACT.md), [the one-way runtime contract](ONE-WAY-BOUNDARY.md) and [the adoption guide](ADOPTION.md).
