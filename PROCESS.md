# Process

This is a living record of the architecture, validation, trade-offs, AI assistance, and lessons learned while completing the Rearc Data Quest. It is updated as decisions are made rather than reconstructed only at the end.

## Architecture

### Verified Databricks environment

Environment verification was performed in a Databricks Free Edition notebook before ingestion or pipeline implementation began.

| Capability | Verified result |
| --- | --- |
| Spark runtime | Apache Spark 4.2.0 |
| Unity Catalog | Available |
| Visible catalogs | `dbacademy`, `samples`, `system`, `workspace` |
| Project catalog | `workspace` |
| Project schema | `workspace.rearc_data_quest` |
| Raw managed Volume | `workspace.rearc_data_quest.raw_landing` |
| Raw Volume path | `/Volumes/workspace/rearc_data_quest/raw_landing/` |
| Pipeline interface | Pipeline creation controls are available under **Jobs & Pipelines** |

The `workspace` catalog was selected because it is the user-writable catalog in this Free Edition workspace. A dedicated `rearc_data_quest` schema isolates assessment objects from the catalog's default schema. The `raw_landing` Volume provides governed file storage for unmodified BLS and Data USA source artifacts before they are modeled as tables.

The setup statements use `IF NOT EXISTS` so environment initialization is safe to rerun. They create or confirm named containers without deleting or replacing existing data.

### Ingestion manifest and rerun contract

The raw mirror uses each source-relative path as its stable object identity. I
retain provider metadata when available, but I use the verified downloaded byte
count and SHA-256 digest to decide whether content is unchanged. This avoids
treating an unreliable or absent ETag as proof of equality.

New and changed objects produce active manifest entries. Missing objects produce
append-only removal tombstones only after a complete source inventory and all
required downloads have succeeded. Unchanged objects retain their prior entry
and are not rewritten. A previously removed path that reappears is new in the
current lifecycle while its historical tombstone remains auditable.

The planning layer refuses to return a publishable plan for an incomplete
inventory or partial download run. The planned Databricks implementation stages
and verifies all required bytes first, promotes changed content to an immutable
versioned path, then publishes the run's transitions in one Delta transaction.
Until that transaction commits, the previous manifest and the immutable bytes it
references remain authoritative. The complete contract and its current evidence
limits are recorded in `docs/INGESTION_MANIFEST_CONTRACT.md`.

The BLS landing implementation deliberately re-downloads every file in the
current source inventory so it can calculate its own byte count and SHA-256
digest. Provider ETags and modification timestamps are retained for provenance,
but I do not assume they are present or reliable enough to establish content
identity. On a no-change rerun, the temporary bytes are discarded: the immutable
raw object is not rewritten, no manifest event is appended, and downstream work
does not receive a new version to process.

I use content-addressed immutable paths so a failed run cannot overwrite bytes
referenced by the last committed manifest. The Databricks notebook stages and
verifies the complete inventory, promotes every new or changed object, verifies
the promoted bytes again, and appends all manifest transitions with one Delta
write. It then independently reconciles the active manifest paths against the
discovered inventory and recomputes the size and digest of every referenced
object.

This assessment implementation is intentionally single-writer. Concurrent runs
could race between checking and promoting the same content-addressed path or
publish competing manifest snapshots. In a production client environment I
would add orchestration-level mutual exclusion or a transactional run-control
table before permitting parallel schedules.

The assigned Data USA response uses the same immutable promotion and atomic
publication contract but has its own `datausa_ingestion_manifest`. I kept source
manifests separate because each ingestion run observes only one provider's
inventory. Combining provider paths in one unscoped manifest would allow a
BLS-only run to misclassify the Data USA artifact as removed, or the reverse.

Before a Data USA response becomes publishable, I require valid UTF-8 JSON; the
documented `annotations`, `columns`, `data`, and `page` envelope types; all four
assigned population columns; records that match the declared columns; valid
nation, year, and population values; and pagination evidence that the response
contains the complete first-page result. Validation reads the staged bytes but
does not serialize them again, so the promoted raw object remains exactly what
the provider returned.

### Planned data flow

The planned flow is:

1. Discover and land raw BLS and Data USA files in the managed Volume.
2. Read those source artifacts into Bronze tables with provenance and ingestion quality metrics.
3. Normalize types, keys, nulls, duplicates, and provider metadata in Silver tables.
4. Produce three deterministic Gold analytical outputs.
5. Implement and compare every required analytical result in both Spark SQL and PySpark.

This plan will be revised only when source profiling or verified platform behavior provides a concrete reason.

### Product vision and stakeholder contract

Before continuing ingestion implementation, I recorded the intended end product so that technical decisions can be evaluated against a stakeholder need rather than only against the minimum assignment requirements.

The primary stakeholder is a Director of Economic Strategy at a national consulting firm. The product is intended to help this person explore US productivity and labor-cost measures, identify notable historical periods, understand provider-grounded series definitions, and decide whether a result warrants deeper analysis or a client briefing. Labor-market analysts, client-facing consultants, and platform or governance leads are supporting personas with more detailed analytical, conversational, and operational needs.

The intended experience contains five sections: an executive overview, productivity and labor-cost trends, population context, definitions and methodology, and a bounded ask-the-data experience. Dashboards and Genie will consume governed Gold objects. They will not query raw provider artifacts directly or present population co-movement as evidence of causation.

The three required Gold outputs are a delivery gate before that broader
experience. I will use population standard deviation for the complete 2013–2018
range; sum only `Q01` through `Q04` for each series' annual result because `Q05`
is an annual average; select the earliest year when annual sums tie; and preserve
unmatched BLS years in the Q01 population left join. Every question will be
implemented in both Spark SQL and PySpark and reconciled before one version is
selected as the primary pipeline path. The full contract is recorded in
`docs/REQUIRED_GOLD_CONTRACTS.md`.

The product vision, UML-style component and sequence views, and conceptual data model are maintained in:

- `docs/PRODUCT_ONE_PAGER.md`
- `docs/SYSTEM_UML.md`
- `docs/LOGICAL_DATA_MODEL.md`

These are living design records. Open choices remain explicitly labeled rather than being presented as completed implementation.

## Validation log

### 2026-10-16: Workspace and Volume verification

The notebook reported Spark version `4.2.0`. `SHOW CATALOGS` confirmed Unity Catalog, and `SHOW SCHEMAS IN workspace` established the schema baseline before project objects were added.

The project schema was created idempotently and independently confirmed by filtering the schema listing for `rearc_data_quest`. The managed Volume was then created idempotently and independently confirmed with `SHOW VOLUMES IN workspace.rearc_data_quest`.

A temporary file containing `Rearc Data Quest Volume check\n` was written to the managed Volume, read back, and compared with the expected content using an assertion. The test file was removed, and the removal operation returned `True`. This proves that the current identity and serverless notebook environment can create, read, verify, and remove a file at the planned landing path. It does not yet prove that the external data sources can be reached or that the ingestion design is idempotent; those are separate cards.

The **Jobs & Pipelines** interface was inspected manually and exposed the expected pipeline creation controls. No pipeline was created during this environment check.

### 2026-10-17: BLS Volume landing and no-change rerun

I executed `notebooks/01_land_bls.py` from the Databricks Git folder at commit
`419c396`. The first live run used ID
`20261017T194929Z-b3618da4`, discovered 12 BLS files, and began with zero current
manifest objects. It classified all 12 as new, promoted all 12 verified objects,
and published 12 manifest transitions. The final reconciliation independently
matched the 12 active manifest paths to the 12 discovered paths and recomputed
the full byte count and SHA-256 digest of every referenced Volume object.

I then immediately repeated the discovery and landing with run ID
`20261017T195437Z-5c5229ba`. It again discovered 12 files and loaded 12 current
manifest objects. All 12 were classified as unchanged; the run promoted zero
objects and published zero manifest transitions. New, changed, removed, and
reused-version counts were also zero. The final reconciliation again verified
all 12 physical objects. Every active row retained the original first-run ID,
providing additional evidence that the no-change run did not replace manifest
state.

This proves the observed BLS inventory can be downloaded with the compliant
client, landed in the target managed Volume, described by the Delta manifest,
and rerun without rewriting or republishing unchanged content. It does not prove
concurrent-writer safety or behavior against a future real provider change;
those boundaries remain covered by the single-writer operating rule and
controlled change-contract tests.

Evidence is stored in `docs/screenshots/dq07_first_run_reconciliation.png`,
`docs/screenshots/dq07_no_change_counts_publication.png`,
`docs/screenshots/dq07_no_change_counts_unchanged.png`, and
`docs/screenshots/dq07_no_change_reconciliation.png`.

### 2026-10-17: Data USA Volume landing and no-change rerun

I executed `notebooks/02_land_datausa_population.py` from the Databricks Git
folder at commit `4b5d642`. The first live run used ID
`20261017T223018Z-29527a8b` and began with zero current Data USA manifest
objects. It downloaded and validated one response, classified it as new,
promoted `population.json`, and published one manifest transition. The parsed
response contained 11 records spanning 2013 through 2024 with the declared
columns `Nation ID`, `Nation`, `Year`, and `Population`.

The independent reconciliation reparsed the committed raw bytes and recomputed
their complete size and SHA-256 digest. It reported one active object of 1,401
bytes with digest prefix `daa4d0576778` and the original first-run ID.

I immediately repeated the manifest load and landing with run ID
`20261017T223605Z-09cb497b`. The response was again discovered and validated,
but it was classified as unchanged. The rerun promoted zero objects and
published zero manifest transitions; new, changed, removed, and reused-version
counts were also zero. Final reconciliation retained the original first-run ID,
size, digest, record count, and year bounds.

This proves that the observed assigned response can be fetched, validated,
preserved unchanged in the target managed Volume, described by a dedicated
Delta manifest, and checked again without rewriting or republishing identical
content. It does not prove concurrent-writer safety or behavior against a future
real provider change. Those boundaries remain addressed by the single-writer
operating rule and controlled change-contract tests.

Reviewer-friendly screenshots are stored in
`docs/screenshots/dq08_no_change_counts.png`,
`docs/screenshots/dq08_reconciliation_identity.png`, and
`docs/screenshots/dq08_reconciliation_schema.png`. Machine-readable exports are
stored under `docs/evidence/`.

## Source documentation notes

- BLS productivity time-series directory: <https://download.bls.gov/pub/time.series/pr/>
- BLS automated retrieval policy: <https://www.bls.gov/bls/pss.htm>
- Assigned Data USA population endpoint: <https://honolulu-api.datausa.io/tesseract/data.jsonrecords?cube=acs_yg_total_population_1&drilldowns=Year%2CNation&locale=en&measures=Population>
- Data USA API documentation: <https://datausa.io/about/api/>

The BLS policy states that automated clients may be blocked when their activity is excessive or when requests do not contain information that can be used to contact the owner. The ingestion client will therefore use a descriptive `User-Agent` containing valid contact information, along with timeouts and bounded retry behavior. This is compliance with the provider's published access policy, not an attempt to bypass an access restriction.

## Trade-offs

This section will be expanded as implementation decisions are made. Current constraints include Free Edition platform capabilities, small source volume, external-provider reliability, and the need to keep the submission reproducible without exposing credentials or workspace-specific identifiers.

## Quality assurance protocol

Beginning with DQ-05, every pull request follows `docs/QUALITY_ASSURANCE_PROTOCOL.md`. The protocol replaces dependence on any single paid reviewer with a repeatable set of requirements, tests, static checks, adversarial review, integration evidence, data reconciliation, security and operational review, documentation, and explainability gates.

The applicable depth depends on the risk of the change. Documentation changes still require accuracy and claim-boundary review. Integration, data movement, analytics, security, and deployment changes require progressively stronger live evidence and reconciliation. A gate may be marked not applicable only with a reason.

The protocol does not treat AI review, unit tests, or a successful Databricks run as sufficient on its own. Each tool provides one kind of evidence. Merge approval depends on the combined evidence and my ability to explain the implementation and its limitations.

## AI usage

### 2026-10-16: Requirements decomposition and repository foundation

AI assistance was used to translate the assessment README into a dependency-aware checklist, propose a conventional repository layout, and identify validation cases that were implied by the assignment, such as deterministic tie handling and preservation of unmatched years during joins.

I reviewed and approved the plan before it was converted into GitHub issues. I validated the resulting foundation through a focused pull request, secret-safe ignore checks, Python package compilation, and a documented definition of done. The checklist remains subject to revision when source profiling or Databricks behavior provides new evidence.

### 2026-10-16: Databricks environment verification

AI assistance was used to explain the Unity Catalog hierarchy and draft small, bounded notebook probes for catalog discovery, idempotent schema and Volume creation, and write/read/delete validation.

I executed each probe in the Databricks notebook and recorded the actual outputs. I progressed one operation at a time: inspect, create schema, verify schema, create Volume, verify Volume, write and read a probe, then remove it. The verified outputs, rather than the proposed commands alone, support the environment claims recorded above.

### 2026-10-16: BLS source profiling

AI assistance was used to organize a bounded source-profile procedure and draft shell diagnostics for the live BLS productivity directory. I reviewed the provider documentation, inspected the raw files, and checked record counts, field counts, whitespace, missing-value conventions, business-key uniqueness, lookup coverage, and the relationship between the two observation files.

The profile corrected an initial assumption that `pr.data.0.Current` contained only the current calendar year. The observed file instead covered 1995 through 2026 and was an exact 38,469-row subset of `pr.data.1.AllData` in this snapshot. I therefore kept the decision to mirror both raw artifacts but selected `AllData` as the complete analytical source. I also corrected and reran a diagnostic after a trailing blank line and a syntax error distorted its first result. The verified source profile is recorded in `docs/BLS_SOURCE_PROFILE.md`.

### 2026-10-17: Product vision, stakeholder personas, and conceptual design

AI assistance was used to organize my proposed stakeholder personas, product sections, design principles, UML-style views, and conceptual data model into reviewable repository documentation.

I selected a consulting Economic Strategy Director as the primary stakeholder and defined the product around the decisions that person needs to make. I retained secondary personas for analytical depth, client conversations, and platform governance without attempting to make one dashboard satisfy every audience equally. I also required the design to distinguish observation from interpretation and recommendation, preserve missing or revised data, and prevent population context from being presented as causal evidence.

The diagrams and logical objects are plans rather than proof of implementation. I will validate and revise them as ingestion, schema profiling, Databricks capabilities, and stakeholder-facing Gold requirements produce new evidence.

### 2026-10-17: Repository-wide quality assurance protocol

AI assistance was used to organize an enhanced review protocol after I decided not to make project quality dependent on a paid Copilot review subscription. The protocol incorporates requirements traceability, risk classification, normal and failure-path testing, automated checks, adversarial diff review, live integration evidence, data reconciliation, security and operational review, documentation, and an explainability gate.

I adopted the protocol because correctness must be supported by multiple independent forms of evidence. I will apply it to DQ-05 and every remaining issue, document why any gate is not applicable, and retest the exact commit after rebases or conflict resolution.

### 2026-10-17: Required Gold semantics and dashboard boundary

AI assistance was used to audit the product vision and issue plan against the
three analytical questions in the assessment. The audit found that the overall
Gold and evidence plan was complete but that the Question 2 wording did not yet
explicitly exclude `Q05`, which the source profile identifies as an annual
average.

I approved an explicit contract that uses `Q01` through `Q04`, population
standard deviation for the complete requested six-year range, earliest-year tie
handling, and a left join that preserves unmatched BLS years. I also required
both SQL and PySpark implementations, reconciliation, independent spot checks,
and dedicated screenshots before the optional dashboard or Genie work begins.
This is a documented implementation decision, not evidence that the Gold tables
have already been built or validated.

### 2026-10-16: Policy-compliant BLS discovery

AI assistance was used to draft tests and implementation for converting an HTML directory listing into a safe, deterministic source inventory. I reviewed the behavior in two layers: a pure parser that rejects links outside the exact configured directory, and a request function that sends an identifying `User-Agent`, applies a timeout, uses bounded retries for transient failures, and fails immediately with policy guidance for HTTP 403 or 429 responses.

The tests were written before the HTTP implementation and initially failed because the new request API did not exist. After implementation and self-review, 13 controlled tests passed without network access. A separate live integration check then discovered the 12 files observed during source profiling. The live check listed files only; it did not download them or write to Databricks. The code contains no hardcoded BLS filenames, and the committed configuration retains a placeholder rather than personal contact information.

### 2026-10-17: Manifest and change-detection contract

AI assistance was used to challenge the manifest design against partial
downloads, interrupted runs, ambiguous source identities, source removals, and
misleading provider metadata. I chose the source-relative path as the stable key,
verified size plus SHA-256 as the content identity, and append-only tombstones as
the removal representation. I also required a run identifier and deterministic
path ordering so transitions can be audited and reproduced.

I wrote the contract tests before the implementation; the first run failed
because the manifest module did not yet exist. I then implemented a pure planning
layer with no network, filesystem, or Databricks side effects. The full suite
passed 36 tests covering all four required change cases, reappearance, duplicate
keys, unsafe paths, invalid digests and timestamps, deterministic ordering, and
refusal to publish incomplete runs. These tests validate the state model, not the
future Volume and Delta integration, which remains to be proven in DQ-07 through
DQ-09.

### 2026-10-17: DQ-05 enhanced quality review

I rebased DQ-05 onto the product-design and quality-protocol changes on `main`, preserved both sides of the `PROCESS.md` conflict, and reviewed the final discovery implementation against `docs/QUALITY_ASSURANCE_PROTOCOL.md`.

The adversarial review found that the parser rejected relative and non-HTTP directory URLs, but the public network-fetch function did not perform the same validation before calling its opener. I added shared pre-request URL validation, including rejection of embedded credentials, queries, and fragments. I expanded the controlled suite from 13 to 19 tests to cover that boundary as well as HTTP 429, other client errors, decode failures, and invalid retry settings.

The final local suite passed all 19 tests, Python compilation succeeded, and `git diff --check` reported no whitespace errors. With explicit authorization, a live check used the contact email from local Git configuration only in the BLS `User-Agent`; it was not printed or committed. The reviewed code discovered the same 12 source files recorded in the source profile.

This evidence proves safe and deterministic directory discovery for the observed provider listing. It does not prove file download integrity, Volume landing, manifest state transitions, or ingestion idempotency; those remain DQ-06 through DQ-09 responsibilities.

### 2026-10-17: Verified BLS landing implementation

AI assistance was used to draft test cases and implementation for streamed BLS
downloads, run-scoped staging, immutable promotion, Delta manifest publication,
and Databricks reconciliation. I retained the architecture from the approved
manifest contract: complete discovery and download precede planning, all new or
changed bytes are promoted before one manifest write, and unchanged objects are
neither rewritten nor republished.

I strengthened the initial implementation by requiring a second size and
SHA-256 verification after promotion rather than treating a completed move as
proof that the landed object is correct. I also made the concurrency boundary
explicit: the assessment notebook is single-writer, and a production schedule
would need run-level mutual exclusion. The controlled suite currently passes 58
tests plus 11 subtests, including partial downloads, policy failures, redirect
boundaries, invalid content lengths, unsafe paths, promotion failures, no-change
runs, atomic Spark append behavior, and post-landing evidence checks.

The local tests prove deterministic contracts and controlled failure paths. I
then ran the exact committed notebook in Databricks and completed both the
first-run and immediate no-change rerun procedure in
`docs/BLS_LANDING_RUNBOOK.md`. The observed live results and their remaining
claim boundaries are recorded in the validation log above.

### 2026-10-17: Data USA raw-response validation and landing design

AI assistance was used to inspect the current assigned response shape, draft
failure-oriented tests, and adapt the verified raw-landing contract for the
single Data USA API artifact. I reviewed the provider documentation and made one
read-only request to the assigned endpoint. The observed response contained the
documented four-part envelope, 11 records, and the columns `Nation ID`, `Nation`,
`Year`, and `Population`.

I rejected a tempting shortcut of placing the Data USA object in the BLS
manifest. The two ingestions have independent inventories, so a shared unscoped
snapshot could produce false removal events. I also required explicit opt-in for
query-bearing download URLs so the BLS file downloader retains its stricter
default. The controlled suite currently passes 66 tests plus 11 subtests,
including malformed JSON, invalid UTF-8, missing columns, partial pagination,
validation cleanup, and a Data USA-specific no-change plan.

I then executed the exact committed notebook in the target Databricks workspace.
The first run and immediate no-change rerun passed the procedure in
`docs/DATAUSA_LANDING_RUNBOOK.md`; the observed results and bounded claims are
recorded in the validation log above. This completes DQ-08 without claiming
concurrent-writer safety or behavior against an as-yet-unobserved provider
change.

### 2026-10-17: Consolidated ingestion rerun evidence

AI assistance was used to audit DQ-09 against the already merged manifest,
landing, download, and Data USA tests. I chose not to add duplicate
implementation merely to create a new card-sized change. Instead, I mapped each
acceptance criterion to a named controlled test and the two completed live
no-change demonstrations in `docs/INGESTION_RERUN_EVIDENCE.md`.

The audit confirmed controlled coverage for new, changed, unchanged, removed,
failed-download, partial-run, and failed-promotion behavior. It also clarified
the term “skipped”: unchanged sources are fetched and verified again to detect
provider changes, but matching content is not promoted, rewritten, or
republished. This preserves currency checking without unnecessary state
transitions.

I retained the existing claim boundary. Controlled fixtures prove deterministic
change and failure behavior without manipulating external providers; the live
runs prove no-change behavior for the observed sources in the authorized
workspace. Neither form of evidence proves concurrent-writer safety, so the
assessment workflow remains explicitly single-writer.

### 2026-10-17: Source schemas and data-quality actions

AI assistance was used to reconcile the observed BLS and Data USA structures,
the official BLS data dictionary, the logical model, and the three required Gold
contracts. I reviewed the proposed fields, keys, types, normalization boundaries,
and expectation severity before recording them in
`docs/SOURCE_SCHEMA_QUALITY_CONTRACT.md`.

I chose source-shaped string columns for BLS Bronze tables so provider padding,
leading zeroes, sentinels, and malformed values remain observable before Silver
typing. Raw bytes remain immutable in the Volume. Silver uses explicit integer,
long, timestamp, and `decimal(20, 6)` types; the decimal preserves BLS published
values without introducing binary floating-point error into quarterly sums.

I checked the assigned Data USA endpoint once more before finalizing its nested
schema. The observed annotation values were strings; pagination fields were
integers; the declared columns were `Nation ID`, `Nation`, `Year`, and
`Population`; and the data records used string identifiers, integer years, and
numeric population values. I also corrected the BLS header rule to compare
ordered field names after trimming provider padding rather than treating harmless
header whitespace as schema drift.

Required-key and cast failures are dropped only with visible metrics because
they cannot safely satisfy the published grain. Duplicate normalized business
keys, missing series-label lookup matches, incompatible headers, and incomplete
JSON envelopes fail the update instead of selecting an arbitrary value or
publishing a plausible but corrupted result. The previous successful pipeline
state and immutable raw artifact remain available for recovery.

I retained `Q05` in Silver as valid annual-average provider data while requiring
Question 2 to filter explicitly to `Q01` through `Q04`. I also placed the
2013–2018 population completeness assertion at the Question 1 boundary rather
than restricting the reusable Silver population history. These rules are now
documented implementation contracts; DQ-11 through DQ-15 still need to build and
validate them in Databricks.

GitHub Copilot's pull-request review identified four documentation gaps before
merge. I corrected an invalid Mermaid precision annotation, aligned the
population candidate key with the `nation_id + year` contract, added an explicit
fail-update gate for malformed or wrong-width BLS records before projection, and
made the Data USA envelope, pagination, ordered columns, and record-key checks
exact so additive drift cannot be silently discarded. I reviewed each suggestion
against the source evidence and project quality policy before accepting it.

Copilot's re-review found two additional quality actions that the first revision
left implicit. I made both fail-update invariants: every normalized Current row
must match the AllData snapshot on business key and value, and every retained
observation must resolve to exactly one valid series-metadata row before enriched
or Gold publication. These checks prevent an internally inconsistent provider
snapshot or an unlabeled series from producing apparently complete results.

### 2026-10-18: Independent audit and inventory-safety remediation

I commissioned a repository-wide Copilot audit after completing the raw landing
and schema-contract phases, then independently reviewed and corrected the audit
report before merging it. The accepted high-severity finding showed that a BLS
directory response could remain nonempty yet be severely truncated. Without an
additional guard, that response could be treated as a complete inventory and
publish false removal tombstones for valid active files.

For DQ-35, I kept the generic landing planner reusable and placed the
provider-specific safety policy in the BLS wrapper. A BLS inventory must contain
the data and metadata anchors `pr.data.1.AllData` and `pr.series`. When any
currently active path appears removed, the notebook performs a second
independent discovery and both inventories must match exactly. A confirmed plan
that removes more than half of the active inventory is blocked unless I
explicitly enable the operator-reviewed `allow_mass_removal` override.

I used failing-first tests to establish each boundary before implementation:
missing anchors, absent confirmation, disagreement between discoveries,
severely truncated inventories, explicit override behavior, and a legitimate
confirmed single-file deletion. These controls prevent partial discovery from
silently mutating manifest truth while preserving an auditable path for real
upstream deletions. They do not prove that a stable provider deletion was
intentional; the mass-removal override deliberately remains a human judgment.

### 2026-10-18: Immutable raw-object recovery

The independent audit identified a recovery gap after manifest classification:
a freshly downloaded object could correctly classify as unchanged even when its
canonical immutable file had been deleted or damaged. The old execution path
discarded the staged copy and discovered the storage problem only during final
reconciliation, so every later rerun failed in the same way.

I chose to verify every unchanged destination during the promotion phase,
before any manifest transitions are published. When the destination is absent,
the existing immutable promoter restores it from freshly staged bytes whose
size and SHA-256 already match committed evidence. This increments a separate
`recovered_count`; it does not publish a manifest event because logical manifest
state did not change. When a destination exists but fails evidence verification,
the run stops without overwriting it. That case still requires coordinated
operator quarantine and recovery so corruption is never silently hidden.

I established the behavior with failing-first filesystem tests for missing,
valid, and corrupt unchanged destinations, plus ordering coverage proving all
object verification completes before publication. This design repairs absence
automatically while preserving the stronger safety boundary around conflicting
immutable bytes. Copilot review then exposed a lifecycle distinction in the
first revision: a retained removal tombstone is also classified as unchanged,
but correctly has neither an active immutable-object requirement nor staged
bytes. I added a failing regression with an unrelated new object and narrowed
verification to unchanged entries whose resulting status is `active`.

### 2026-10-18: Encoded discovery URL integrity

The independent audit found that discovery decoded each linked URL path before
rebuilding the request URL. That coupled a manifest-friendly display name to
network identity: `%20` became a literal space, while `%25` could be interpreted
again by a later URL layer and address a different object.

I separated those responsibilities. Discovery now preserves the provider's
encoded path in the canonical request URL and decodes only the local relative
name used by the manifest. Decoded percent signs, path separators, backslashes,
and control characters are rejected because they make that local identity
ambiguous; a safely encoded space remains supported and stays encoded on the
wire. Same-origin and exact-directory checks still operate on the decoded path
so an encoded separator cannot escape the configured directory.

I established the change with failing-first cases for `%20`, `%25`, `%2F`, and
literal and encoded backslashes, then reran the entire controlled suite. This
remediation prevents discovery from requesting a different path than the one
advertised. Redirect handling and network-exception normalization remain
separate audit findings and are not claimed here.

Copilot review found three remaining identity edge cases in the first revision.
I accepted all three after reproducing them: an encoded base directory was
decoded before relative-link resolution, path normalization could hide an
encoded separator in the original final component, and two encoded aliases
could produce duplicate manifest names. The corrected parser preserves the
encoded base, validates the decoded original component before normalization,
and deduplicates by decoded name. When aliases exist, it deterministically
prefers the spelling with fewer percent escapes and then lexical URL order. The
regressions reverse alias order to prove the result does not depend on listing
order.

## Retrospective

This section will be completed as the implementation develops. The environment phase reinforced the value of verifying platform capabilities and permissions before writing pipeline code.
