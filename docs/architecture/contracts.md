# Offline architecture boundaries

Contracts parse and validate input. Policy consumes validated facts; no API calls or credentials. Evidence exposes only fixed public fields (free text, proof URLs, SHAs, identities and raw logs excluded). Adapters are capability declarations, not implementations. CLI and wrappers call contracts. Dashboard is generated, not authoritative.

Lease decision requires independently authenticated actor, owner authorization, matching issue/repository/head/fence, unexpired lease, no competing claim and atomic host enforcement. It is not a lease acquisition. Dedup keys exclude execution timestamps; durable cursor updates only after verified delivery in the associated conversation. Recovery never automatically retries; a verified unchanged head permits reauthorization only. UTC slots are bounded; local timestamps use observed offset, not inferred DST or timezone rules. NOT OBSERVED is not proof of a missed run. Actual host behavior remains unqualified. Schema files are structural; Python semantic validation is mandatory.

Historical pins identify frozen sources; never replace them with moving branch tips. No schema v2 until a breaking wire change is approved. No new live scheduler integrations in .2.
