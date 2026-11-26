# Reusable prompts

Prepend the operating contract in WORKFLOW.md to each prompt. Replace OWNER/REPO and timezone explicitly; do not publish actual conversation identifiers. Configure existing conversation association in the scheduler; verify readback. Schedule times are nominal UTC; scheduler delays are possible.

## Development Loop (0 * * * *)

Read live canonical OWNER/REPO. Only authorized bounded repair; inspect canonical issue, branch and exclusive lease, then one reversible fix with regressions. No claim transfer, merge, release or speculative work. Follow WORKFLOW.md. Report only changed evidence with exact source head/base/proposed merge/actual merge, installed version, UTC and local timestamp, classification, positives and negatives, one next action and unavailable tools. No new conversation or separate agent. Stop after one bounded operation or blocker. Do not infer release authorization.

## Handoff Control (15 * * * *)

Read live canonical OWNER/REPO. Inspect actual canonical handoff and candidate; identify stale or competing claims, one concrete existing Worker or owner action. Never take ownership. Follow WORKFLOW.md. Report only changed evidence with exact source head/base/proposed merge/actual merge, installed version, UTC and local timestamp, classification, positives and negatives, one next action and unavailable tools. No new conversation or separate agent. Stop after one bounded operation or blocker. Do not infer release authorization.

## Verification Watch (30 * * * *)

Read live canonical OWNER/REPO. Inspect exact-head and proposed-merge runner logs, artifacts and review threads; identify changed verification only. Follow WORKFLOW.md. Report only changed evidence with exact source head/base/proposed merge/actual merge, installed version, UTC and local timestamp, classification, positives and negatives, one next action and unavailable tools. No new conversation or separate agent. Stop after one bounded operation or blocker. Do not infer release authorization.

## Audit Evidence (45 * * * *)

Read live canonical OWNER/REPO. One bounded missing evidence gate per run; inspect actual artifact contents, hashes and historical scope. Never simulate independent acceptance. Follow WORKFLOW.md. Report only changed evidence with exact source head/base/proposed merge/actual merge, installed version, UTC and local timestamp, classification, positives and negatives, one next action and unavailable tools. No new conversation or separate agent. Stop after one bounded operation or blocker. Do not infer release authorization.

## Release Control (0 */4 * * *)

Read live canonical OWNER/REPO. Reconcile release gates, permanent versions, closure, owner decisions, independent trial evidence, and current release status. Stop only after verified completion. Follow WORKFLOW.md. Report only changed evidence with exact source head/base/proposed merge/actual merge, installed version, UTC and local timestamp, classification, positives and negatives, one next action and unavailable tools. No new conversation or separate agent. Stop after one bounded operation or blocker. Do not infer release authorization.
