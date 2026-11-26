# Provenistem — One-way runtime boundary and optional integration

**Controlling scope:** Provenistem is only a project Ideas & Features tracker. See [the owner-locked scope](PRODUCT-SCOPE-LOCK.md). A separate adapter is an optional future compatibility mechanism, **not mandatory**, and no integration is currently implemented.

**Architecture decision:** `GB-PROVENISTEM-OPTIONAL-RELATIONSHIP-2026-11-12`  
**Status:** owner-ratified future design; private v0.0.2 historical tag unchanged.

See [the locked product-neutral integration contract](PORTABILITY-AND-MODULE-CONTRACT.md).

## Permanent one-way rule

```
Provenistem core  --requires-->  no host framework
Host-owned optional adapter  -->  Provenistem's supported local contract
Host core  --requires-->  no Provenistem runtime
```

**Governance-Branch may know that Provenistem exists as an opt-in module** and, after independent owner approval, may implement a Governance-owned adapter. This narrowly supersedes the v0.0.2 *documentation* clause that forbade Governance from even being aware of the package. It does **not** allow Governance core to depend on Provenistem, nor Provenistem core to depend on Governance. No adapter is shipped by this document, and no installation/activation is assumed.

1. **No upstream registration:** Provenistem itself must never automatically register into a host's capability catalog, bootstrap, CLI, module registry, default install, dependencies or release plan. An expressly opt-in **host-owned adapter**, added through the host's own approved product process, is a separate action.
2. **No upstream modification:** Installing or updating Provenistem never writes into an unrelated control plane's source, permissions, policy, product manifests, version history or canonical records.
3. **No runtime dependency:** Provenistem works without Governance-Branch; Governance-Branch works without Provenistem. Optional adapter code is kept outside both standalone cores.
4. **No shared authority:** Ideas, decisions, source references and test states cannot grant work, publish releases, attest evidence, skip security gates, or change authorization.
5. **No imported project records:** Every adopting project owns its own IDs and data. No actual adopter, maintainer, demonstration team or development project's canonical records ship by default.
6. **No path collisions:** Do not replace an occupied `ideas/`, `features/`, `tools/`, `AGENTS.md` or governance namespace. Use a separately owner-approved location such as `modules/provenistem/`.
7. **Names are not contracts:** `IDEA-xxxxxx`, `FEAT-xxxxxx`, JSON/YAML IDs and schema versions are project-local; collisions or identical labels do not establish schema compatibility or shared authority.
8. **No inferred upstream state:** Package presence, a recommendation, an index or a cached record does not prove the live host's module status, runner readiness, provider permissions, release state or owner consent.
9. **No automatic synchronization:** Versioning, data migrations and compatibility changes need exact-source checks and project-owner authorization. No silent mirroring or cross-repo installation.
10. **Optional removal:** Either product must continue to function if the other is absent. Disabling an adapter does not delete host records or change the host's release authority.

## Collision response and real limits

A read-only planner must stop with `NAMESPACE_COLLISION` when recognized canonical namespaces conflict. The existing planner uses known root markers such as `ideas/library.yaml`, `src/governance_branch/libraries/ideas.py`, `governance/`, and incompatible canonical schema signatures. Recognizing such markers is defensive compatibility behavior, **not** a dependency or claim to recognize all possible conflicts.

Owner review is needed for unknown schemas, unverified repository state, symlink/path races and every proposed migration. The library does not secure an arbitrary compromised host. An authenticated external review is not implied by static checks.

## Product neutrality

Future **final shipping packages** must not expose or assume any unrelated customer's, adopter's or internal development project's name, private repository, real records, host-specific runner, internal CI evidence, team role or secret. Use neutral synthetic examples. Keep historical provenance in separate internal development evidence, not in portable product defaults.

Published v0.0.2 is a frozen historical artifact. This owner lock is a **future-architecture decision**; do not force-update its tag, claim the optional Governance adapter has been implemented, or silently change v0.3.1 product release scope.

## Verification limit

Static checks in `tests/test_one_way_boundary.py` guard obvious forbidden imports and the documented one-way contract. The additional modularity policy test validates the new architecture metadata. These checks are not branch protection, an installed integration, independent attestation, or runtime security proof.
