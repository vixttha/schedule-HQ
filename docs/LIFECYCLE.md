# Provenistem — Lifecycle v1 (independent dimensions)

## Idea lifecycle
`captured → triaged → exploring → decision_ready` are descriptive stages, not automatic transitions. `adopted`, `parked`, `rejected`, `superseded`, `duplicate`, and `retired` require a real `decision` with `decided_by`, `decided_at` and `reason`. No lifecycle state alone authorizes implementation.

## Feature lifecycle
`proposed → planned → in_progress → implemented → verified` is a possible path, **not** an automatic transition. `deprecated` and `retired` are separate dispositions. `verified` needs source-bound evidence and review, not the mere existence of a test filename. Never assume a feature is shipped.

## Delivery and testing
`implementation_status`: `not_planned`, `planned`, `in_progress`, `implemented`, `removed` (and `not_applicable` for ideas). Testing: `untested`, `planned`, `in_progress`, `tested`; a completed test needs an outcome and checkable evidence reference. In Provenistem v0.0.2, `testing.outcome` is rejected unless `testing.status` is `tested`. A record can link to a test plan without asserting success.

## Canonical ownership
- Ideas own hypotheses and their *documented* decisions.
- Features own capabilities and specific lifecycle.
- Actual code and test results live where the adopting project stores engineering evidence.
- Official release authority alone owns shipped version and release acceptance.
- Neither library grants work, merge, runner, deployment, token, privacy, or publication authority.

A tool can check syntactic structure but cannot authenticate a receipt, determine whether an owner truly approved something, or establish production correctness.
