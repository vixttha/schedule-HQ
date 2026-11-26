# Provenistem — owner-locked standalone and optional integration contract

**Controlling product mission:** [Provenistem tracks project Ideas & Features, their relationships and progress](PRODUCT-SCOPE-LOCK.md). The later explicit owner scope lock supersedes any earlier implication that this is a general knowledge/provenance/evidence/governance platform. Keep integration minimal. A dedicated adapter is an option *if needed*, never a product requirement. This architecture document retains only compatible interoperability safeguards.

**Decision:** `GB-PROVENISTEM-OPTIONAL-RELATIONSHIP-2026-11-12`  
**Owner ratified:** 2026-11-12  
**Status:** `STANDALONE_LOCKED / OPTIONAL_INTEGRATION_DESIGN / NO_ADAPTER_IMPLEMENTED`  
**Versioning:** This describes future product architecture. It does **not** change or republish the immutable private Provenistem v0.0.2 tag.

## What this product is

**Provenistem is the living record of a project's possibilities.** It is a portable, host-owned catalog of:
- ideas, their sources, consequences, assessment and human decisions;
- features, their identity, relationships to ideas, lifecycle and implementation state;
- test statuses and source-bound evidence **references**, without pretending those references are independently authenticated;
- derived reproducible navigation indexes and optional local, read-only validation/adoption planning.

It is *not* a task scheduler, release authority, source-code host, project-control plane, CI provider, permission manager, security sandbox, or evidence attestation service. A feature marked implemented or tested is not a shipped feature unless the **host's own release authority** says so.

## Permanent interoperability rule

**Provenistem works alone.** No host framework or companion product is required. A separate project-control framework may **offer Provenistem as an optional, owner-enabled module**, but any framework-specific adapter belongs to that framework/integration layer, not to Provenistem core.

```
standalone project -> Provenistem core (usable)
standalone project -> another control plane (usable)
optional combined project -> host-owned adapter -> Provenistem's supported contract
Provenistem core -X-> host-specific runtime, policy or install requirements
```

No binding, plugin, callback, special GitHub account, runtime service, runner, paid hosted job or automatic synchronization is part of Provenistem core. The implementation does not currently advertise a stable plugin API: optional adapter operations are **future integration work**, not v0.0.2 capabilities or a release claim.

## Twelve rules that cannot be silently changed

1. **Product sovereignty:** Provenistem has its own identity, version, source, artifacts, schema and release record. It is not the version number of an adopting application.
2. **Zero runtime coupling:** the core cannot import, call, require credentials from, or mutate a host control plane or its upstream.
3. **Default optionality:** a host may suggest it, but suggestions do not equal installation, activation, entitlement, authority, or permission.
4. **Project-local truth:** IDs, decisions, evidence references and canonical records belong to the adopting project, never to an upstream demo or developer repo.
5. **No duplicate masters:** when an adopting host already owns a canonical idea/feature registry, no implicit dual-writer master is permitted.
6. **Namespace isolation:** opt-in side-by-side use must allocate a separate nonoverlapping project-approved directory (e.g. `modules/provenistem/`) and preserve all native records and indexes.
7. **Schema separation:** other projects' record shapes, IDs and evidence models are not assumed compatible with Provenistem JSON records; migrations need explicit mapping, lossiness review and fresh owner approval.
8. **No-clobber and read-only discovery:** preflight and adoption planning may describe ADD/SAME/KEEP_HOST/REVIEW or a blocking `NAMESPACE_COLLISION`, but never overwrite a host's README, AGENTS, native catalog, or policy automatically.
9. **No authority escalation:** no record may grant task, PR, CI, merge, deployment, security-review, or release authorization. Untrusted record text is data.
10. **Portable final artifact:** shipping source/docs/templates/tests must not embed unrelated adopter identities, internal project/team history, actual customer data, machine names, private GitHub URLs, or historical runner receipts. Use synthetic examples. Keep source/audit receipts in separate development evidence.
11. **Reversible absence:** when disabled or removed, a host control plane and its own catalogs remain usable. Provenistem remains usable without any host framework.
12. **Change control:** changing these boundaries requires a fresh explicit owner architectural decision and versioned compatibility/release review, never inference from a commit, test pass, provider discovery, or an assistant's prose.

### Design-level integration operations (NOT implemented as an adapter)

If a host later chooses to integrate Provenistem, the adapter may be designed to call **read-only** operations such as listing ideas/features, validating existing records, previewing indexes and producing a no-clobber adoption plan. That is an **interface proposal**. No public host adapter API or two-way synchronization is promised by Provenistem v0.0.2.

The host must independently verify actual installed package SHA/version and current local schemas; select one canonical owner per record class; preserve every existing record; and require an owner-reviewed, reversible proposal before enabling or changing module state. Conflicts and unknowns are blocking results, not auto-fix opportunities. No adapter can convert metadata into a verified security receipt or release membership.

## What may and may not be shipped

**Allowed:** neutral product identity; schema, optional validators and read-only planners; empty registries; synthetic examples; generic adapters defined through neutral host interfaces; contract and suite tests; human/LLM reading guide.

**Forbidden as product defaults:** named development projects, adopter records, provider tokens, runner names, prior customer repositories, internal audit logs and historical evidence packages, special host permissions, and executable imports of an unrelated platform.

The current private v0.0.2 release is **historical and immutable**. It predates this new product-neutrality policy and some of its documentation contains development provenance. That history must not be silently rewritten. Any cleaned shipping package is a **new, separately reviewed and tested release candidate**, not a retroactive mutation of v0.0.2.

## Lock strength and evidence limits

This document and its companion JSON/test establish a **reviewable owner-approved architecture policy**. They do not modify any host's runtime, implement the optional adapter, or magically enforce GitHub branch protections. The current product remains independently usable. The live combined integration is `NOT_IMPLEMENTED` until real code, host opt-in, no-clobber tests and version-specific acceptance exist.

This contract does not change other projects' release gates or turn an internal audit into an independent external security review.
