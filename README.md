# Veraphify

Code memory for each project version. Veraphify archives an evidence graph against the exact project commit and uses it to look up implementation citations for a selected version.

We use and support the open-source Graphify project. Veraphify is developed and maintained independently of Graphify Labs.

## Open the candidate

Clone the candidate and run its entry point with Node.js 24 and Git.

```sh
git clone --branch work/veraphifiy-v0.0.9 https://github.com/vixttha/Veraphify.git
cd Veraphify
node veraphifiy.mjs --help
```

The draft branch, CLI filename, and archive output field `veraphifiy_version` retain their existing spelling for compatibility.

## Build and verify two versions

Follow the [adopter walkthrough](docs/adopter-walkthrough.md) to build two maps with the pinned producer, import both versions, and verify their citations from a clean checkout.

## Archive and find evidence

Supply the paired `graph.json` and `receipt.json` produced by the existing pinned Graphify feature-evidence builder (Graphify `0.9.109`). The source checkout must contain the exact commit claimed by the receipt.

```sh
node veraphifiy.mjs import --archive ./archive --project owner/repo --version v1.2.3 \
  --source COMMIT_SHA --checkout ../project --evidence ../graph-output
node veraphifiy.mjs verify --archive ./archive --project owner/repo --version v1.2.3
node veraphifiy.mjs lookup --archive ./archive --project owner/repo --version v1.2.3 \
  --feature feature:export
```

The project name must match the receipt. Each archive entry preserves the graph, receipt and verified source blobs. Importing identical evidence is repeatable. An existing version can only be read or replayed. Record `source` and `archive_sha256` from a trusted import separately from the archive. To verify the exact approved entry, pass those values to `verify` or `lookup` as `--source` and `--archive-sha256`. The summary distinguishes the archived project version, archive format, Veraphify version and pinned producer version.

Lookup citations use one-based physical lines in the pinned Git blob. LF advances the line, including the LF in CRLF. If the producer uses a different line because of an embedded separator, `producer_line` records its original coordinate. Archived graph and receipt bytes are preserved.

Keep archives that contain private source on private storage. On POSIX systems, new archive directories request mode `0700` and new entries request `0600`, subject to the process umask. Existing directory and entry permissions are preserved. On Windows, choose a private archive location and check that its inherited access control lists restrict access to the intended users. Review permissions on existing archives before storing private source. The public Test Vault uploads only disposable fixture archives. [Test Vault](test-vault/README.md) · [v0.0.9 tracker](https://github.com/vixttha/Veraphify/issues/21)
