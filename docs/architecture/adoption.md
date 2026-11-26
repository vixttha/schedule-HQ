# Adopt Schedule HQ (read-only first)

Use Python 3.12 and Git. Clone this project at an approved exact SHA and clone the authorized target repository separately. Create a dedicated target branch named schedule-hq. Verify the numeric target repository ID in authenticated GitHub metadata. No license or permission is implied by the installer. Use credential-free HTTPS origin (no token embedded in URL). The checkout must be clean and exclusively controlled locally.

From the Schedule HQ source checkout, run:

```sh
python tools/adopt.py install --checkout /path/to/target --repository OWNER/REPO --repository-id 123 --timezone Etc/UTC
python tools/adopt.py verify --checkout /path/to/target --repository OWNER/REPO --repository-id 123 --timezone Etc/UTC
```

Replace placeholders with verified target values. The installer writes only .schedule-hq/ on the dedicated local branch, without commits, network calls, activation or GitHub workflow files. All five standalone prompts are explicitly read-only in this pilot. No automatic task creation. Inspect the prompts and UTC schedule, then manually bind authorized tasks to the existing conversation. The reporting timezone is separate from nominal UTC slots; custom cadence is only a proposed host schedule, not a change to the frozen v1 reconciliation engine. Use --minutes with a JSON map of all five offsets and --release-hours (2,3,4,6,8,12,24) to generate alternative cadence; reconciliation of custom slots remains unqualified. Windows may require trusted IANA timezone data for non-UTC reporting; UTC needs no external dependency.

Before uninstall, pause/remove any live host tasks manually. Re-run the same source SHA and configuration with action uninstall (dry run), then uninstall --apply to rename the verified directory to .schedule-hq-removed. Modified or extra files, wrong branch/origin, symlinks, junctions and existing backup block removal. No automatic deletion or Git reset. Restore by moving the verified backup back after review. Never commit private receipts, credentials, conversation IDs or task IDs. This local cooperative checkout procedure is not hostile filesystem protection or authenticated remote identity verification. The host cannot be inferred from a generated prompt.

## Qualification boundary

The public-runner pilot installs into a separate local clone of this exact public repository revision, verifies origin locator and branch, checks dry-run rollback and moves the verified bundle to a backup without changing tracked files or pushing a ref. This is an isolated checkout, not an independently adopted second remote repository. No host-side credential scope, delivery, or independent review is inferred from these tests.
