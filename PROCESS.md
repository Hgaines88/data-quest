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
inventory or partial download run. The implemented Databricks workflow stages
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

### Layered data flow

The implemented flow is a governed medallion pipeline with an immutable raw
boundary:

1. The landing notebooks discover BLS files and fetch the assigned Data USA
   response, validate the downloaded bytes, and promote changed content to
   immutable, content-addressed Volume paths. Append-only Delta manifests
   identify the current version of every source object.
2. Bronze pipeline views publish rows only from objects authorized by the
   latest active manifest state. Their static binary and text source readers
   can still physically enumerate or read historical and unreferenced landing
   objects before the manifest join removes them. Published rows preserve
   source-shaped strings and provenance, validate headers and row widths, and
   expose rejected-row metrics before publishing reusable Bronze tables.
3. Silver pipeline views parse intentional types, normalize provider
   sentinels, enforce business keys and cross-file metadata coverage, and
   publish separate observation, series, and population tables. Silver retains
   reusable history such as `Q05`; question-specific filters belong in Gold.
4. Gold pipeline views implement the three requested analytical contracts.
   Candidate and input-validation views fail closed on incomplete or ambiguous
   inputs before the final materialized views are published.
5. Tracked Spark SQL alternatives independently recompute each result from
   Silver. A final read-only report compares SQL and PySpark schemas, counts,
   keys, values, invariants, and representative source calculations.

Bronze therefore answers “what valid source-shaped records arrived?”, Silver
answers “what normalized entities and observations are safe to reuse?”, and
Gold answers the three bounded stakeholder questions. The live evidence for
each boundary is indexed under `docs/evidence/`; a successful downstream layer
does not retroactively prove an upstream contract that was not tested.

### Primary analytical implementations

PySpark is the primary implementation for all three Gold outputs. It integrates
directly with the declarative pipeline graph, supports named fail-fast
expectations and DataFrame-level transformations, and publishes governed
materialized views that downstream consumers can reference consistently. The
Spark SQL versions remain tracked, executable alternatives rather than pipeline
sources. Keeping them outside source discovery prevents duplicate publication
and preserves their value as an independently readable reconciliation path.

- **Question 1:** PySpark publishes the six-year population summary only after
  exact range and cardinality checks. SQL independently expresses the same
  aggregate and makes the population-standard-deviation choice easy to review.
- **Question 2:** PySpark makes the inventory-preserving left join and
  deterministic window ranking explicit in the pipeline. SQL provides a terse
  independent statement of the `Q01`–`Q04` sum and earliest-year tie break.
- **Question 3:** PySpark publishes the left-join result and visible population
  match flag behind input and output expectations. SQL independently confirms
  that BLS history remains the driving side of the join.

The choice is operational, not a claim that one API is intrinsically more
correct. DQ-19 compares both implementations and requires agreement before the
PySpark views are treated as the stakeholder contract.

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
response contained 11 records with minimum year 2013 and maximum year 2024.
Those bounds do not imply that every intermediate year was present. The
declared columns were `Nation ID`, `Nation`, `Year`, and `Population`.

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

The assessment is deliberately small, but a real client deployment would need
to make the following operating decisions explicit:

| Concern | Assessment choice | Production extension or trade-off |
| --- | --- | --- |
| Schema drift | Bronze fails closed on header and row-shape changes; Silver uses explicit casts and domain gates. | Alert on quarantined drift, version contracts, and provide a reviewed migration path instead of silently accepting new columns or meanings. |
| Scale | Complete small files and tables are practical here, and clarity is favored over premature optimization. | Partition or cluster by useful access keys, compact small files, incrementally process manifest changes, and benchmark shuffles, joins, and state growth before selecting a strategy. |
| Cost | Triggered Free Edition pipelines and bounded validations minimize idle compute. | Set workload budgets and tags, select job/serverless policies deliberately, schedule around freshness needs, and monitor cost per successful update rather than optimizing only runtime. |
| Security | Secrets and personal contact data are excluded from tracked files; raw data is stored in Unity Catalog objects rather than local workspace paths. | Use service principals, secret scopes, private networking where required, encryption controls, and separate development, test, and production identities. |
| Access control | The assessment uses one writable project catalog/schema and a single operator. | Grant least privilege by layer: ingestion may write manifests and raw objects, pipelines may read upstream/write owned schemas, and analysts should normally receive Gold-only access. Add row or column controls if the data becomes sensitive. |
| Monitoring | Pipeline expectations, manifest reconciliation, automated tests, and evidence files provide explicit pass/fail signals. | Send alerts for failed freshness, drift, rejected rows, anomalous volumes, provider errors, and cost; retain run-level lineage and define ownership, escalation, and recovery objectives. |
| Provider reliability | Requests use identifying clients, timeouts, bounded retries, redirect restrictions, exact-byte validation, and last-known-good manifests. | Add provider-specific service expectations, backoff with jitter, outage playbooks, cached replay, change notifications where available, and a policy for how long stale data may remain publishable. |

Content-addressed raw storage improves auditability and recovery but consumes
more storage than overwriting files. Full re-downloads make content identity
independent of weak ETags but cost more network and provider capacity. The
single-writer rule avoids races in this assessment; production concurrency
would require orchestration locks or a transactional run-control protocol.
The Bronze manifest join governs publication, not physical source discovery:
static reader globs may scan historical or unreferenced immutable objects.
That is acceptable for this bounded assessment history, but a larger deployment
should monitor bytes scanned and consider a manifest-driven pruning design if
the extra read cost becomes operationally significant.

## Quality assurance protocol

Beginning with DQ-05, every pull request follows `docs/QUALITY_ASSURANCE_PROTOCOL.md`. The protocol defines a repeatable set of requirements, tests, static checks, adversarial review, integration evidence, data reconciliation, security and operational review, documentation, and explainability gates.

The applicable depth depends on the risk of the change. Documentation changes still require accuracy and claim-boundary review. Integration, data movement, analytics, security, and deployment changes require progressively stronger live evidence and reconciliation. A gate may be marked not applicable only with a reason.

The protocol does not treat AI review, unit tests, or a successful Databricks run as sufficient on its own. Each tool provides one kind of evidence. Merge approval depends on the combined evidence and my ability to explain the implementation and its limitations.

## AI usage

AI assistance was used throughout as a drafting, test-design, review, and
diagnostic aid. It proposed decompositions, code and SQL changes, adversarial
cases, documentation structure, and interpretations of platform errors. I made
the implementation decisions, inspected the resulting diffs, ran the tests,
executed the Databricks steps, and retained evidence only for observed results.
AI output was never treated as execution proof.

Several corrections materially changed the project. Source profiling disproved
the assumption that the BLS `Current` file represented only the current year.
Live Bronze failures exposed a header-contract mismatch, a whole-file
array/explode design that exhausted executor memory, and an incorrect
regular-expression argument. Replacing the whole-file design with Spark's
distributed line-oriented reader removed the pathological memory shape.
Population validation was strengthened against floating-point overflow,
underflow, and
integer-rounding ambiguity. Reviews added mass-removal protection, immutable
object recovery, redirect-origin checks, strict JSON constants, metadata
cardinality gates, complete sample coverage, and analyzed schema comparison.
The first independent variance formula also suffered catastrophic cancellation
and was replaced with a two-pass calculation. Each accepted correction was
covered by focused tests or structural assertions and, where it crossed the
platform boundary, rerun in Databricks before its evidence was considered
final.

### 2026-10-16: Requirements decomposition and repository foundation

I reviewed and approved the plan before it was converted into GitHub issues. I validated the resulting foundation through a focused pull request, secret-safe ignore checks, Python package compilation, and a documented definition of done. The checklist remains subject to revision when source profiling or Databricks behavior provides new evidence.

### 2026-10-16: Databricks environment verification

I executed each probe in the Databricks notebook and recorded the actual outputs. I progressed one operation at a time: inspect, create schema, verify schema, create Volume, verify Volume, write and read a probe, then remove it. The verified outputs, rather than the proposed commands alone, support the environment claims recorded above.

### 2026-10-16: BLS source profiling

I reviewed the provider documentation, inspected the raw files, and checked record counts, field counts, whitespace, missing-value conventions, business-key uniqueness, lookup coverage, and the relationship between the two observation files.

The profile corrected an initial assumption that `pr.data.0.Current` contained only the current calendar year. The observed file instead covered 1995 through 2026 and was an exact 38,469-row subset of `pr.data.1.AllData` in this snapshot. I therefore kept the decision to mirror both raw artifacts but selected `AllData` as the complete analytical source. I also corrected and reran a diagnostic after a trailing blank line and a syntax error distorted its first result. The verified source profile is recorded in `docs/BLS_SOURCE_PROFILE.md`.

### 2026-10-17: Product vision, stakeholder personas, and conceptual design

I selected a consulting Economic Strategy Director as the primary stakeholder and defined the product around the decisions that person needs to make. I retained secondary personas for analytical depth, client conversations, and platform governance without attempting to make one dashboard satisfy every audience equally. I also required the design to distinguish observation from interpretation and recommendation, preserve missing or revised data, and prevent population context from being presented as causal evidence.

The diagrams and logical objects are plans rather than proof of implementation. I will validate and revise them as ingestion, schema profiling, Databricks capabilities, and stakeholder-facing Gold requirements produce new evidence.

### 2026-10-17: Repository-wide quality assurance protocol

I established a review protocol incorporating requirements traceability, risk classification, normal and failure-path testing, automated checks, adversarial diff review, live integration evidence, data reconciliation, security and operational review, documentation, and an explainability gate.

I adopted the protocol because correctness must be supported by multiple independent forms of evidence. I will apply it to DQ-05 and every remaining issue, document why any gate is not applicable, and retest the exact commit after rebases or conflict resolution.

### 2026-10-17: Required Gold semantics and dashboard boundary

An audit of the product vision and issue plan against the three analytical
questions in the assessment found that the overall
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

I implemented and reviewed HTML-directory discovery in two layers: a pure parser that rejects links outside the exact configured directory, and a request function that sends an identifying `User-Agent`, applies a timeout, uses bounded retries for transient failures, and fails immediately with policy guidance for HTTP 403 or 429 responses.

The tests were written before the HTTP implementation and initially failed because the new request API did not exist. After implementation and self-review, 13 controlled tests passed without network access. A separate live integration check then discovered the 12 files observed during source profiling. The live check listed files only; it did not download them or write to Databricks. The code contains no hardcoded BLS filenames, and the committed configuration retains a placeholder rather than personal contact information.

### 2026-10-17: Manifest and change-detection contract

I challenged the manifest design against partial downloads, interrupted runs,
ambiguous source identities, source removals, and
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

I implemented streamed BLS downloads, run-scoped staging, immutable promotion,
Delta manifest publication, and Databricks reconciliation. I retained the architecture from the approved
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

I inspected the current assigned response shape, wrote failure-oriented tests,
and adapted the verified raw-landing contract for the single Data USA API
artifact. I reviewed the provider documentation and made one
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

I audited DQ-09 against the already merged manifest, landing, download, and
Data USA tests. I chose not to add duplicate
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

I reconciled the observed BLS and Data USA structures, the official BLS data
dictionary, the logical model, and the three required Gold contracts. I reviewed
the proposed fields, keys, types, normalization boundaries,
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

Pull-request review identified four documentation gaps before
merge. I corrected an invalid Mermaid precision annotation, aligned the
population candidate key with the `nation_id + year` contract, added an explicit
fail-update gate for malformed or wrong-width BLS records before projection, and
made the Data USA envelope, pagination, ordered columns, and record-key checks
exact so additive drift cannot be silently discarded. I reviewed each suggestion
against the source evidence and project quality policy before accepting it.

Re-review found two additional quality actions that the first revision
left implicit. I made both fail-update invariants: every normalized Current row
must match the AllData snapshot on business key and value, and every retained
observation must resolve to exactly one valid series-metadata row before enriched
or Gold publication. These checks prevent an internally inconsistent provider
snapshot or an unlabeled series from producing apparently complete results.

### 2026-10-18: Independent audit and inventory-safety remediation

I completed a repository-wide audit after the raw landing and schema-contract
phases, then independently reviewed the findings before accepting changes. The
accepted high-severity finding showed that a BLS
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
immutable bytes. Review then exposed a lifecycle distinction in the
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

Review found three remaining identity edge cases in the first revision.
I accepted all three after reproducing them: an encoded base directory was
decoded before relative-link resolution, path normalization could hide an
encoded separator in the original final component, and two encoded aliases
could produce duplicate manifest names. The corrected parser preserves the
encoded base, validates the decoded original component before normalization,
and deduplicates by decoded name. When aliases exist, it deterministically
prefers the spelling with fewer percent escapes and then lexical URL order. The
regressions reverse alias order to prove the result does not depend on listing
order.

### 2026-10-18: Redirect-origin and request-identity privacy

The audit showed that checking `response.geturl()` after `urllib` returned was
too late to protect an identifying header: the standard redirect handler had
already sent the redirected request. Discovery also lacked the post-response
check, and the Data USA notebook reused the BLS contact-bearing `User-Agent`
without a documented provider requirement.

I moved the boundary to a custom `HTTPRedirectHandler`. It compares normalized
scheme, hostname, and effective port before constructing a redirected request,
allowing same-origin HTTPS redirects while refusing cross-origin and HTTPS-to-
HTTP redirects. The existing response-origin checks remain as defense in depth
for injected or custom openers. BLS retains its required non-placeholder contact
validation by default. Data USA now uses a distinct product-only identity and
explicitly opts out of the contact-email requirement.

Failing-first tests cover cross-origin and downgrade refusal at the handler
level, safe same-origin behavior, discovery's injected-opener boundary, default
BLS contact enforcement, and the explicit Data USA opt-out. These controlled
tests prove redirect decisions before a follow-up request is created; the live
notebook check can confirm normal provider operation but cannot manufacture a
real provider redirect.

### 2026-10-18: Strict Data USA JSON syntax

Python's default JSON parser accepts `NaN`, `Infinity`, and `-Infinity` even
though the JSON grammar does not. I reproduced that gap with a failing-first
subtest for each constant, then supplied a `parse_constant` callback that raises
before envelope or record validation and before any raw promotion.

This change enforces valid JSON syntax at landing. It deliberately does not
claim the exact Bronze envelope or the finite, integral, unique Silver business
contract; those independent pipeline rules remain assigned to DQ-11 through
DQ-15 in the source-quality contract.

### 2026-10-18: Interrupted HTTP and staging-failure normalization

The independent audit found two failure paths that bypassed the ingestion
contract. `http.client.IncompleteRead` and related protocol exceptions could
escape without retry or partial-file cleanup, while a local directory or file
creation failure could surface as an unclassified `OSError`. `InvalidURL` also
needed to remain a hard failure rather than consume the retry budget.

I established the boundaries with failing-first tests at both network entry
points. Directory discovery and streaming downloads now retry bounded HTTP
protocol interruptions. Downloads remove bytes from every failed attempt before
retrying or returning, so a later successful attempt replaces rather than
appends to partial content. An invalid request target is wrapped as a typed
`SourceRequestError` and is not retried. Local staging setup and write failures
are wrapped as `StagingWriteError` and likewise do not repeat a provider
request.

The controlled tests include an interruption after partial bytes have reached
disk, repeated interruption exhaustion, recovery on the next attempt, invalid
URL behavior, and a filesystem path whose parent is a regular file. These tests
exercise failure states that a normal live provider run cannot safely or
deterministically manufacture.

Review identified that cleanup itself remained outside the typed local
storage boundary. I reproduced it with a destination that was an existing
directory: the initial unlink raised raw `IsADirectoryError` before any network
request. Cleanup now ignores only genuinely absent paths and wraps every other
filesystem error as non-retryable `StagingWriteError`; the regression also
proves that the provider opener is never called. I retained an additional
permission-denied unlink regression because it covers a distinct cleanup path,
and removed its duplicate existing-directory case.

Exact-head re-review then identified the parallel discovery case for
connection resets: `response.read()` can raise `ConnectionResetError`, an
`OSError` rather than an `HTTPException`. I added failing-first recovery and
retry-exhaustion regressions and included read-side `OSError` in discovery's
bounded network retry set. The earlier `HTTPError` and `InvalidURL` handlers
still take precedence, preserving their policy and hard-failure semantics.

### 2026-10-18: Test-evidence fidelity and Spark validation

The audit correctly distinguished controlled adapter tests from executed Spark
evidence. The fake-backed manifest tests validate emitted DDL text, typed row
mapping, DataFrame construction, writer calls, and identifier rejection; they
do not execute a window function or Delta write. I renamed the three broadest
tests so their names state those actual claims.

For landing orchestration, I added a real-filesystem regression around the real
immutable promoter. It proves that successful promotion followed by publisher
failure leaves verified bytes unreferenced, and that a later run against the
still-empty committed manifest reuses the exact immutable object before
publishing one transition. This complements the existing real-promoter tests
for missing, valid, and corrupt unchanged objects.

For the platform boundary, I added a dedicated Databricks validation notebook.
It creates a uniquely named temporary Delta manifest, proves idempotent DDL,
appends four synthetic transitions, and executes the latest-state window with
both timestamp and lexical run-ID ordering. It always attempts to drop only its
generated validation table. The live result remains a required DQ-41 gate and
unit tests alone do not satisfy that claim.

Review found that the first synthetic ordering fixture could not
distinguish timestamp-first ordering from run-ID-first ordering, and that early
dictionary construction could hide duplicate current rows. I reversed the old
event's lexical run-ID relationship to conflict with its timestamp and now
validate the uncollapsed ordered result list before dictionary lookup. The live
gate therefore fails both incorrect precedence and missing latest-row filtering.

The second review also noted that one write into an empty table could not prove
append semantics. The notebook now establishes two historical rows in its first
write and adds two later transitions in a second write. Its four-row assertion
therefore fails if the adapter overwrites instead of preserving prior history.

A later review correctly noted that the fake-backed writer test recorded append
mode and destination but did not count writer invocations. I removed the word
`one` from its name so it claims only the append request that it actually
observes; the two-write live notebook supplies the append-history evidence.

I then ran every cell of the validation notebook in Databricks from commit
`3c153c7` on 2026-10-18. All cells completed with green checks. The observed
result preserved four transitions across the two writes, returned two current
paths, selected `20261018T010000Z-b` as the removed `ranked.txt` winner, and
reported all 11 manifest columns. The exact exported row is preserved as
`docs/evidence/dq41_spark_manifest_validation.csv`. This closes the live DDL,
append-history, and latest-state ranking gate for the observed runtime while
retaining the documented concurrency and version claim boundaries.

### 2026-10-18: Documentation reconciliation after ingestion remediation

I re-evaluated all 15 documentation contradictions from the independent audit
against the repository after DQ-35 through DQ-41. I did not rewrite the audit's
historical snapshot. Instead, I corrected current contracts, diagrams, evidence
indexes, checklist state, and planned-versus-implemented wording, and recorded
an explicit disposition for every item in
`docs/DOCUMENTATION_RECONCILIATION.md`.

The review preserved the boundary that raw landing is implemented while Bronze,
Silver, Gold, stakeholder interfaces, deployment, and production concurrency
controls remain future work. No Databricks execution was required because these
changes describe behavior already proved by the merged code, controlled tests,
and recorded live evidence; they do not introduce a new platform claim.

### 2026-10-18: Bronze live-validation fault decomposition

The first triggered Bronze update discovered the complete 12-node graph but
failed with 11 flow errors and one executor out-of-memory warning. I treated
those counts as symptoms rather than 12 independent defects. The event log
showed two different failure classes: repeated
`ordered_header_matches_contract` expectation violations and executor/JVM heap
loss. Increasing compute or immediately rerunning would have mixed those causes
and weakened the evidence, so neither action was taken.

The expectation payload identified `pr.seasonal` as the deterministic contract
failure. Its immutable object existed, matched the manifest byte count and
SHA-256 digest, and contained data, but the provider header was
`Seasonal_code` / `Seasonal_text` while the contract reused normalized Bronze
names `seasonal_code` / `seasonal_text`. Those are two legitimate naming layers,
not corrupt source data. The contract now stores an optional exact provider
header separately from projected Bronze columns. A regression asserts both
representations. Local tests, compilation, repository CI, and focused review
passed before the next platform run.

The second triggered update supplied the necessary isolation evidence. The
seasonal table published two rows with all five expectations met; the other
small BLS tables and Data USA population also completed. Only
`bronze_bls_observation_current` and `bronze_bls_observation_all` failed. Both
had met all seven expectations before failing at approximately five minutes.
Databricks reported executor exit code 52 and `JVM_OUT_OF_MEMORY` in
`UnsafeRow.copy`, while the larger AllData flow lost its executor. This ruled
out source absence, checksum mismatch, header drift, row-width failure, and the
earlier seasonal defect as explanations for the remaining failures.

The common implementation shape explained why only the observation files were
affected: the binary verifier decoded each complete file, split it into one
array-valued row, and downstream publication exploded that array. The design
therefore concentrated every observation line and its intermediate copies in a
single row before distribution. The corrective design retains the immutable
binary size/SHA-256 gate and ordered first-line header check (trimming
surrounding field whitespace), but avoids building
the complete line array. Once verified, each BLS artifact is read through
Spark's distributed text reader at its static content-addressed filename path;
physical paths are joined back to the latest-active verified manifest row,
headers and blank lines are removed, and individual lines retain the existing
field-count, required-value, and provenance rules.

Two tempting shortcuts were rejected. Raising executor memory would make
correctness depend on a larger runtime and leave future provider growth exposed;
disabling expectations would conceal evidence that had already distinguished
valid source from execution failure. The line-oriented change instead removes
the pathological memory shape without weakening governance. It remains subject
to fresh pull-request review and a third Databricks triggered update before
DQ-11 can be considered complete.

The third triggered update failed during graph analysis rather than execution.
Two primary errors reported the regular-expression text
`(?s)^[^\\n]*\\n[^\\n]+` as an unresolved column at the shared BLS verifier;
the other eleven messages only reported that downstream flows could not resolve
`verified_bls_sources`. I therefore treated the downstream count as dependency
fan-out, not eleven new defects. The PySpark `regexp_like` function accepts its
pattern as a column expression in this Databricks runtime, so passing a Python
string caused Spark to interpret the regex as a column name. The correction
wraps the pattern with `F.lit`, preserving the intended content-nonempty rule
without changing its semantics. A source-shape regression now protects this
runtime-specific API boundary.

The fourth triggered update compiled the shared verifier but Unity Catalog
rejected `input_file_name()` in the line-oriented reader. Databricks emitted
the same line-127 error once for each of the ten BLS publications, so the ten
red entries again represented one shared helper failure rather than ten data
defects. The supported Unity Catalog metadata column, `_metadata.file_path`,
provides the same physical-path value needed for the manifest join without an
extra abstraction or behavioral change. The reader now selects that column
directly, and a regression prohibits reintroducing `input_file_name()`.

The next normal triggered update, started at 5:46 PM EDT on 2026-10-18,
completed successfully with zero errors and zero warnings. All ten BLS
materialized views, the Data USA population view, and the source-contract audit
were green. Most importantly, the two flows that had isolated the original
memory defect completed after the line-oriented correction:
`bronze_bls_observation_all` published approximately 77,000 rows with all seven
expectations met, and `bronze_bls_observation_current` published approximately
38,000 rows with all seven expectations met. `bronze_datausa_population`
published 11 rows, and the audit published one passing result for each of the
11 required sources.

This sequence closed the live-validation loop without increasing compute or
weakening quality controls. The successive error counts were decomposed by
shared dependency: provider-header evidence corrected one contract boundary;
table-specific runtime evidence isolated the whole-file memory shape; and
graph-analysis messages identified two Databricks API compatibility boundaries.
Each correction was made at the shared cause, covered by a focused regression,
reviewed at the exact commit, and validated again on the target runtime. DQ-11
is therefore complete at the Bronze scope; Silver behavior remains separate
work.

### DQ-12: isolate typed BLS observations behind explicit Silver gates

Silver observation work began from the validated DQ-11 commit on a dedicated
branch and in a separate `pipelines/silver.py` source file. This boundary is
deliberate: a Silver deployment can be reviewed and validated without changing
the live Bronze graph that already passed its target-runtime run.

The implementation keeps one normalization path for both provider observation
files. It trims provider padding, casts `year` to integer and `value` to
`decimal(20,6)`, maps `period` to `period_code`, converts blank footnotes to
null, and retains the Bronze provenance needed to trace any Silver row. Named
drop expectations measure invalid required casts, keys, periods, and provenance.
`Q05` remains valid Silver data because it is the provider's annual-average
period; the quarterly analytical question will exclude it at query time.

I did not silently deduplicate the source. A window count on
`series_id + year + period_code` feeds a fail-fast expectation, because choosing
an arbitrary duplicate could change an annual total. The published table also
depends on a separate Current-file consistency gate. That gate normalizes
`bronze_bls_observation_current` with the same rules and requires every row to
match the unique AllData-derived candidate on the complete business key and
value. This makes AllData the sole publication source while still using Current
as independent provider consistency evidence.

The design publishes only `silver_bls_observation`; candidate, uniqueness, and
consistency datasets are temporary pipeline views. This keeps the public model
small while leaving each quality decision visible in the pipeline graph and
event log. Local source-contract tests, the full repository test suite, Python
compilation, and diff checks must pass before deployment. DQ-12 will not be
marked complete until a triggered Databricks update provides table counts and
expectation evidence on the target runtime.

The first review identified an important ANSI-mode boundary before live
deployment. Ordinary integer and decimal casts can throw on malformed or
overflowing provider text, which would abort evaluation before the named drop
expectations could count and exclude those rows. The normalization therefore
uses SQL `try_cast` for both numeric fields. Failed conversions become null and
reach the existing validity rules, preserving the documented behavior without
adding another processing stage.

The target-runtime update then completed successfully on October 18, 2026 at
7:21 PM EDT. Databricks reported zero errors and zero warnings, and published
approximately 77,000 `silver_bls_observation` rows in 5 seconds. Because the
published table depends on both fail-fast gates, completion also establishes
that no normalized duplicate business key or unmatched Current record reached
publication. The captured table screen lists the expectation definitions but
does not expose a per-rule `met` count, so the evidence makes no stronger claim
than the UI supports. The completed update, graph, performance view, and editor
pipeline-selector interpretation are preserved in
[`docs/evidence/dq12_silver_live_validation.md`](docs/evidence/dq12_silver_live_validation.md).

The runtime workflow reinforced a useful deployment lesson for later Silver
and Gold work: keep each medallion pipeline separate while allowing both to use
one versioned Git folder. Databricks consequently shows a `2 pipelines` editor
selector; that selector names `data-quest-silver` as current and
`data-quest-bronze` as the other associated pipeline. It is navigation context,
not duplicate source execution or cross-pipeline contamination.

### DQ-13: build labels from provider metadata without inventing meaning

The series dimension extends the existing Silver pipeline without changing the
validated observation path. It starts from `bronze_bls_series` and left-joins
the five provider lookups referenced by that file: sector, class, measure,
duration, and seasonal adjustment. Keeping the joins left-sided makes a missing
description observable instead of silently removing the series.

One fail-fast gate enforces the two risks that matter at this boundary. Every
provider description must match, and the joined result must contain exactly one
row per `series_id`. The latter also detects a duplicated lookup code because a
many-to-many join would increase the per-series window count. The readable
label is a simple concatenation of the five provider descriptions; there is no
guessed fallback such as `Unknown series`. This produces one public
`silver_bls_series` table while keeping the quality decision visible in the
temporary candidate view.

Review caught two contract boundaries before deployment. The provider
uses `-` when a series has no base year, so Silver now converts that sentinel to
null and uses ANSI-safe `try_cast` to publish an integer. The coverage gate also
checks both begin and end periods against `Q01` through `Q05`; a non-null but
unsupported code can no longer pass merely because Bronze preserved it.

The target-runtime update completed successfully on October 18, 2026 at 7:55
PM EDT with zero errors and zero warnings. `silver_bls_series` published 282
rows in 7 seconds, exactly matching the previously recorded Bronze series
inventory. Its dependency graph shows all five lookups feeding the candidate
gate, and the existing observation table remained green with `No change`.
Because the published series table depends on the fail-fast completeness and
one-row-per-series condition, successful publication establishes full lookup
coverage and stable cardinality for this snapshot. The completed update, table
result, graph, and performance evidence are preserved in
[`docs/evidence/dq13_silver_series_live_validation.md`](docs/evidence/dq13_silver_series_live_validation.md).

### DQ-14: normalize population without narrowing reusable history

The population transform reads only `bronze_datausa_population` and retains the
documented United States national record (`01000US`, `United States`). Bronze
requires the parsed numeric text to represent a whole number, including when
Databricks normalizes it to scientific notation, then verifies that the
projected double preserves its value. This avoids a fixed decimal scale and
prevents a fraction from rounding into an apparently valid population count.
ANSI-safe Silver casts then produce integer years and long population values,
while named drop expectations measure malformed, negative, non-US, or
incomplete-provenance rows.

A separate fail-fast window enforces one row per `nation_id + year`; the
pipeline never chooses an arbitrary duplicate. The final `silver_population`
table keeps every valid available year. The required 2013–2018 completeness
check is intentionally deferred to the Gold Question 1 boundary so this
reusable history is not shaped around one analytical request.

After the final numeric-form correction, fresh target-runtime Bronze and Silver
updates completed successfully on October 18, 2026. Bronze published all 11
population rows with all 10 expectations met. The 11:00 PM EDT Silver update
reported zero errors and zero warnings and published 11 population rows, 282
series rows, and approximately 77,000 observation rows. The graph confirms the
intended isolated population dependency chain and the intact BLS paths. The
completed updates, table results, graph, and performance evidence are preserved in
[`docs/evidence/dq14_silver_population_live_validation.md`](docs/evidence/dq14_silver_population_live_validation.md).

A separate read-only SQL query returned exactly six ordered records for 2013
through 2018, with one population value for each year. Engineering judgment
keeps this confirmation distinct from the 11-row pipeline count: the pipeline
run proves typed, quality-gated, uniquely keyed publication, while the query
directly proves the requested year coverage. The later Gold pipeline will
still enforce the six-year analytical range at its own publication boundary.

Final review exposed numeric range edge cases outside the normal provider
snapshot. Python's default JSON float parser converts valid exponent notation
such as `1e400` to infinity and `1e-400` to zero before validation. Rejecting
only JSON's nonstandard `Infinity` token was therefore insufficient. Landing
now parses decimals losslessly, then rejects values that would overflow or
underflow or change integer value when projected into Bronze's double type.
Bronze retains the original numeric text and independently checks the finite
range, positive-to-zero underflow, and integer round trip before retaining a
row. Regression tests cover both range edges, the greater-than-53-bit integer
case, and the pipeline rules. Silver already rejected overflow because its
ANSI-safe long cast becomes null, but the earlier checks are needed to prevent
underflow or double rounding from becoming a plausible publishable count.

The live runtime then exposed a different boundary: Spark normalized the valid
provider counts to scientific notation such as `3.16128839E8`. The initial
lexical expectation understood only plain integer notation and therefore
dropped all 11 rows. This was a safe failure—the pipeline published no
population data and identified the single failing expectation—but it revealed
that representation and value semantics had been conflated. The final rule
accepts scientific notation only when its exponent shifts every significant
fractional digit into the integer portion. The exact-decimal, range, underflow,
and double-projection checks remain separate. This small correction supports
Databricks' actual representation without broadly relaxing the contract.

An attempted fresh read-only SQL verification after both corrected pipeline
runs could not start because the free-edition serverless compute allowance was
exhausted. The earlier six-row SQL result remains direct year-coverage evidence,
while the fresh Bronze and Silver table counts prove successful publication on
the reviewed commit. Recording this infrastructure limitation separately avoids
mistaking unavailable compute for either successful query execution or a data
defect.

### DQ-16: publish and independently reconcile the population summary

Question 1 is implemented twice from the same governed Silver source. The
primary PySpark pipeline filters the normalized United States record to 2013
through 2018, then uses a fail-fast candidate view to require six rows, six
distinct years, and the requested inclusive bounds before publication. This
prevents a partial interval from producing a plausible but unsupported average.
The published materialized view carries the bounds, year count, mean,
population standard deviation, and an explicit `population` semantic label.

The separate Spark SQL implementation is a read-only analytical alternative,
not another pipeline source. It applies the same filters and returns no row
unless the same completeness conditions hold. Keeping it outside the Gold
pipeline avoids duplicate publication while providing an independent API path
for numerical reconciliation.

On October 19, 2026, the `data-quest-gold` triggered update completed in the
target Databricks workspace with zero displayed errors or warnings and one
published result. The candidate expectation panel reported action `FAIL`, zero
percent failures, and zero failed records. The tracked SQL alternative then
read six rows and returned
the same bounds, count, mean, semantic label, and population standard deviation
within a manually applied `1e-6` comparison tolerance. The structural tests do
not execute that live numerical comparison. A simple independent calculation
from the six annual source values produced the same mean and standard
deviation. The completed update, graph, exact outputs, SQL execution,
screenshot digests, and evidence limits are preserved in
[`docs/evidence/dq16_gold_population_summary_validation.md`](docs/evidence/dq16_gold_population_summary_validation.md).

### DQ-17: publish deterministic BLS best-year results

Question 2 is implemented in both PySpark and Spark SQL from the governed
Silver observation and series tables. Both versions include only `Q01` through
`Q04`, sum values by series and year, rank the largest annual sum first, and
select the earliest year when sums tie. The PySpark materialized view is the
primary governed output. It starts from the complete 282-series metadata
inventory so series without quarterly history remain visible with an explicit
false status rather than disappearing.

Review identified a cross-table integrity boundary that the original
inventory-first joins could hide: a quarterly observation whose `series_id`
did not resolve to metadata would be silently omitted. The final PySpark graph
therefore contains a fail-fast metadata-validation view, and the standalone SQL
alternative uses an equivalent `RAISE_ERROR` guard. Both require exactly one
metadata row for every retained quarterly series before returning results.

On October 19, 2026, the final `data-quest-gold` update completed in the target
Databricks workspace with zero displayed errors or warnings. The metadata gate
and both result expectations passed, and the published best-year table retained
282 series. The guarded SQL alternative then completed with 282 rows. The
earlier null-safe full-outer comparison found 282 SQL rows, 282 PySpark rows,
and zero field-level mismatches; the guard changes failure behavior without
changing valid calculations. An independent Silver query also reconciled
`PRS30006032` year 1994 from four quarterly values to `14.600000`. The exact
outputs, screenshots, digests, attribution boundary, and claim limits are in
[`docs/evidence/dq17_gold_bls_best_year_validation.md`](docs/evidence/dq17_gold_bls_best_year_validation.md).

### DQ-18: preserve BLS history while adding nullable population context

Question 3 is implemented in both PySpark and Spark SQL from the governed
Silver tables. Both implementations filter exactly `PRS30006032` and `Q01`,
then use those BLS observations as the left side of the annual United States
population join. This direction is intentional: population is optional context,
so a missing population year must not erase a valid BLS observation. The
published table exposes both nullable `population` and the explicit
`population_match_found` flag and makes no causal claim.

The PySpark version is the primary Gold materialized view. A fail-fast input
view requires a nonempty, uniquely keyed Q01 history and exactly one provider
metadata row. The candidate view separately requires one joined result per BLS
year and agreement between population nullability and the visible match flag.
The standalone SQL alternative contains equivalent input-cardinality checks and
remains excluded from pipeline source discovery so it can be run independently.

On October 19, 2026, the `data-quest-gold` update completed with zero displayed
errors or warnings and published 39 ordered rows covering 1988 through 2026.
Eleven rows matched available population records and 28 retained BLS years with
null population. Both input expectations and both result expectations reported
zero failed records. The SQL alternative also returned 39 rows. A null-safe
full-outer comparison found 39 distinct keys in each implementation, identical
28-row missing-population counts, and zero field-level mismatches.

A separate direct Silver-to-Gold spot check sampled 2012, 2013, 2020, 2024,
and 2026. This selection tests a pre-coverage year, the first match, an internal
population gap, a later match, and a post-coverage BLS year. Source Q01 values,
nullable population values, and match flags all reconciled. Exact outputs,
screenshots, digests, attribution limits, and the non-causal scope boundary are
preserved in
[`docs/evidence/dq18_gold_bls_q01_population_validation.md`](docs/evidence/dq18_gold_bls_q01_population_validation.md).

### DQ-19: reconcile every Gold SQL and PySpark implementation

The final Gold quality query independently recomputes all three SQL alternatives
from the governed Silver tables and compares them with the primary PySpark
materialized views. It emits machine-readable checks for ordered schemas, row
counts, unique keys, values, year bounds, join preservation, deterministic
tie-breaking, and representative source calculations. Full-outer comparisons
make missing rows visible in either direction instead of allowing an inner join
to hide them.

Question 1 DOUBLE aggregates use an explicit absolute `1e-6` tolerance and
one-sided-null detection. Question 2 DECIMAL results and Question 3 DECIMAL,
nullable population, and boolean values use exact null-safe equality. The SQL
alternatives are ephemeral reviewer calculations while the PySpark results are
governed materialized views. Storage order is intentionally excluded from the
data contract; key uniqueness and the Question 2 earliest-year tie-break are
validated, and reviewer-facing queries may order their output explicitly.

On October 19, 2026, the final post-review validation query completed in
Databricks in 35.092 seconds with a green execution status and 111 of 111 tasks
completed. It returned 17 checks—five for Question 1 and six each for Questions
2 and 3—and every row reported `passed = true`. The output confirmed analyzed
SQL and published Gold schema agreement, one Question 1 summary, the complete
282-series Question 2 inventory with zero metadata violations, and all 39
Question 3 history rows. All value and independent source-check discrepancy
counts were zero, and all five documented Question 3 sample years were present
in both inputs. This closes the three-contract Gold gate before dashboard or
Genie work. The exact outputs, screenshots, SHA-256 digests, and claim
boundaries are preserved in
[`docs/evidence/dq19_gold_cross_implementation_validation.md`](docs/evidence/dq19_gold_cross_implementation_validation.md).

### DQ-21: curate privacy-reviewed submission screenshots

The implementation cards already produced live Databricks evidence for the
pipeline, layer tables, and all three analytical outputs. For the final
submission I selected the minimum authoritative views and created nine
losslessly cropped copies. The crops remove browser chrome, the workspace
hostname, operator identity, pipeline identifiers, and account email; they do
not alter the displayed execution state, table names, row counts, labels, or
result values. SHA-256 digests and direct links are recorded in the
[`docs/screenshots/` index](docs/screenshots/README.md#dq-21-curated-submission-set).
The original implementation evidence remains available for the chronological
audit trail, while reviewers can verify the required deliverables from the
privacy-reviewed set without live workspace access.

### DQ-22: replace the assignment brief with a reviewer-facing guide

The root README now leads with the implemented solution rather than repeating
the prompt. It gives a reviewer one ordered path through the medallion
architecture, non-secret configuration, landing notebooks, separate Bronze,
Silver, and Gold pipeline sources, three published Gold outputs, independent
SQL alternatives, local QA, and live evidence. Runtime-only BLS contact data is
documented as a notebook widget and is never supplied as an example credential.
The original acceptance criteria remain traceable in
[`REQUIREMENTS_CHECKLIST.md`](REQUIREMENTS_CHECKLIST.md), while the README links
directly to this process record and the curated screenshot set.

## Retrospective

The hardest problem was not any single transformation. It was preserving a
credible chain of evidence across unreliable external inputs, immutable raw
storage, declarative pipeline semantics, two analytical APIs, and a constrained
Databricks environment. Many defects initially appeared downstream from their
cause: one shared Bronze helper produced multiple failed nodes, an incomplete
inventory could have looked like mass deletion, an inner comparison could have
hidden missing rows, and a numerically plausible variance formula was unstable
for large population values. Solving these required decomposing failures at the
earliest boundary that could explain them and distinguishing “the code looks
right” from “the target runtime demonstrated the contract.”

The main lessons are:

- Profile provider data before encoding semantic assumptions. Filenames,
  headers, sentinel values, and period codes need evidence, not intuition.
- Make absence visible. Tombstones, null-preserving joins, inventory-first
  publication, full-outer comparisons, and explicit match flags prevent silent
  data loss.
- Fail closed before publication, but keep failures diagnosable through named
  expectations, rejected-row metrics, stable validation rows, and clear claim
  boundaries.
- Separate reusable data quality from question-specific semantics. Silver
  retains valid provider history; Gold applies the requested filters and tie
  rules.
- Use independent implementations only when their independence is real.
  Comparing two expressions that share the same constants or joins can repeat
  the same mistake; source calculations and analyzed schemas provide stronger
  evidence.
- Treat tests, reviews, and live runs as complementary. Local tests exercise
  controlled failure paths, review challenges assumptions, and Databricks
  proves target-runtime behavior. None is sufficient alone.
- Record corrections honestly. The review trail is more useful when it explains
  why an apparently reasonable first approach was changed and what now prevents
  recurrence.

The resulting project is still an assessment implementation: it is
single-writer, uses a small public dataset, and does not claim production
scheduling, service-level objectives, or causal inference. Within that scope,
the ingestion, Bronze, Silver, and three Gold contracts are implemented,
rerunnable, reconciled, and supported by traceable evidence.

### 2026-10-19: DQ-25 governed stakeholder exploration contract

I converted the earlier stakeholder boundary into a buildable AI/BI dashboard
contract for the Economic Strategy Director. Three explicit-column datasets
read the three required Gold outputs at their published grains; the dashboard
does not reach back into Silver or Bronze, silently remove unavailable series,
replace missing population with zero, or place unlike BLS and population units
on a shared axis. The design also states that historical context is not causal
evidence.

The checked-in acceptance query produces four named, machine-readable checks
covering the population range and values, a representative BLS best-year row,
and five boundary, matched, and internal-gap Q01 rows. The expected values are
accepted 2026-10-19 regression anchors. They make provider revisions visible
rather than authorizing an unexplained expectation change.

### 2026-10-19: DQ-25 live dashboard and reconciliation

I built and published the **US Productivity Insight Workspace** in Databricks
Free Edition from the three governed stakeholder SQL datasets. The published
page contains the four specified filters, two population KPI cards, coverage
and best-year tables, nullable Q01 population context, the non-causality
boundary, and an operator-verification source note. Population cards use the
actual Gold values rather than row counts.

The four-row acceptance query passed for population bounds, population values,
the representative BLS best-year result, and Q01 nullable-context behavior.
Two representative Genie answers reconciled to the Gold-backed datasets. The
Free Edition surface exposed generated dashboard Genie behavior but no verified
custom instruction editor, so I do not claim that the proposed custom Genie
instructions were deployed.

The first published revision failed with `No warehouse selected to run query`.
I explicitly selected and started the Serverless Starter Warehouse, reran the
dataset, and republished with shared data permissions. The published widgets
then rendered successfully. A published-mode `2026` filter test preserved
`q01_value = 0.00`, null population, and `population_match_found = false`, after
which the filter was reset to its default. Privacy-safe screenshots and exact
digests are indexed in
[`docs/evidence/dq25_stakeholder_exploration_validation.md`](docs/evidence/dq25_stakeholder_exploration_validation.md).

### 2026-10-19: DQ-26 least-privilege implementation and validation

I defined `data_quest_readonly_analysts` as a non-admin interactive analyst
group. Its data path is limited to `USE CATALOG` on `workspace`, `USE SCHEMA`
on `workspace.rearc_data_quest`, and `SELECT` on the three governed Gold
contracts used by the dashboard. Because Bronze, Silver, Gold, quality, and
helper objects share one schema, schema-wide `SELECT` would violate the stated
Gold-only boundary; the policy therefore names each Gold table explicitly.
It grants no ownership, management, modification, creation, or Volume access.

The workspace-object path is also explicit: the group requires **Can use** on
the Serverless Starter Warehouse and **Can view** on the published dashboard.
The dashboard must be republished with **Individual data permission** for the
access-control validation. Shared data permission executes with the
publisher's authority and can demonstrate dashboard availability, but cannot
prove that the analyst's Unity Catalog grants are sufficient.

Checked-in apply, inspection, positive, negative, and revocation SQL makes the
intended data grants reviewable and reversible. Repository tests enforce exact
Gold-table symmetry and reject elevated or schema-wide grants.

I then completed the live test with a separate non-admin user in the analyst
group. Databricks SQL access was enabled while Consumer, Workspace, and Admin
access remained disabled. The group received **Can use** on the Serverless
Starter Warehouse and **Can view** on the dashboard, which was republished with
**Individual data permission**. All three Gold reads and the dashboard worked;
the Series and Observation year filters also worked and were reset.

The lower-layer tests produced authorization denials for Bronze `SELECT`,
Silver `SELECT`, raw-Volume `LIST`, and schema `CREATE TABLE`. The Gold
`UPDATE` also failed, but because the deployed Gold object is a view
(`EXPECT_TABLE_NOT_VIEW`), not because an authorization check denied DML. I
record this distinction instead of overstating the result. The admin audit
returned exactly five direct group grants: catalog use, schema use, and
`SELECT` on the three named Gold contracts. No lower-layer, Volume, creation,
or management grant appeared in that grant inventory. Subsequent review identified
that the initial audit did not enumerate grants inherited through other groups.
I strengthened the inspection SQL to cover every project-schema securable and
reran it for both the inherited workspace `users` group and the validation
identity directly; each returned zero rows. The operator then inspected the
validation identity's complete workspace membership field, which listed exactly
the analyst group and `users`, with no additional direct or inherited groups.
This inspection followed the behavioral tests in one continuous validation
session spanning midnight; no membership change occurred between the tests and
the inspection.
A later review correctly separated
those grant results from ownership metadata and job/pipeline workspace ACLs;
those controls require their own inventories and are not claimed by the SQL
grant result. On 2026-10-20, the ownership inventory covered 44 objects and
returned zero matches when filtered independently for the analyst group,
`users`, and the validation identity. The workspace inventory found the Bronze,
Silver, and Gold pipelines and no separate jobs; only the operator and inherited
`Admins` management authority appeared on each pipeline ACL. The privacy-safe
evidence and exact
digests are indexed in
[`docs/evidence/dq26_gold_access_control_validation.md`](docs/evidence/dq26_gold_access_control_validation.md).

### 2026-10-20: DQ-24 bundle resource model and pre-deployment gate

I modeled the deployable Databricks portion of the verified solution as three
triggered serverless pipelines and one ordered downstream refresh job. The job
orchestrates Bronze, Silver, and Gold only. BLS and Data USA landing remain a
separately governed single-authorized-writer prerequisite because job-level
concurrency cannot serialize shared manifest and Volume writes across users or
deployment targets. The development target uses both a current-user bundle root
and a current-user output schema, while production uses an explicit shared root
and cannot be deployed safely until its plan and any existing-resource binding
decision are reviewed.

The ownership boundary is intentionally narrower than the complete product.
The pre-existing catalog, schema, managed Volume, warehouse, dashboard,
identity groups, and Unity Catalog grants remain externally governed. Importing
those shared objects merely to maximize bundle coverage would let bundle state
or teardown affect validated data and access policy. The existing dashboard
also lacks a privacy-reviewed serialized source export, so I document it as a
manual Free Edition resource instead of inventing a deployable definition.
DQ-26 remains the authority for its data and workspace access controls.

Databricks CLI 1.21.0 parsed and resolved the development target, bundle name,
and isolated workspace path without reporting a configuration-schema finding.
It then stopped at the expected authentication boundary because this local
worktree has no configured Databricks credentials. The repository's 185 local
tests, including four bundle contract checks, pass. I do not treat either result
as deployment evidence: authenticated validation, a reviewed plan, isolated
development deployment, the ordered downstream live run, and post-deployment quality
checks remain required before DQ-24 can close.

The first isolated development deploy exposed a runtime API constraint that
static validation did not report: serverless pipelines cannot explicitly set
`photon: false`. All three pipeline creates were rejected with
`INVALID_PARAMETER_VALUE`, their dependent job was not created, and the only
completed action was synchronizing files beneath the isolated user bundle
path. I removed the invalid Photon override and required a fresh validation and
plan before retrying instead of changing compute mode or bypassing the failure.

The corrected deploy created all four development resources, but I stopped
before running them when a post-deploy review found that resource-name
isolation alone did not isolate pipeline output tables. I split the existing
source schema from the pipeline output schema: Bronze continues to read the
verified manifests and raw Volume in `rearc_data_quest`, while the development
Bronze, Silver, and Gold outputs target a schema derived from the current user's
Databricks short name. Production
retains `rearc_data_quest` as its output only after a separate binding and plan
review. This prevents a development update from contending with tables owned by
the manually verified pipelines.

The first intermediate five-task run then failed before notebook execution because the job
environment used deprecated `client: "1"`, which Free Edition rejected as an
unsupported `Client-1` REPL channel. All downstream tasks were skipped and no
data update ran. Current Databricks bundle guidance permits serverless notebook
tasks to omit both a cluster definition and an explicit environment; only
non-notebook serverless tasks require `environment_key`. I removed the
deprecated environment rather than guessing another client channel and again
required validation and plan review before deployment.

After that correction, an intermediate plan changed only the refresh job and
deleted nothing, and the five-task trial succeeded. A final review then
identified two valid deployment-isolation gaps: the fixed development schema
was shared by all developers, and `max_concurrent_runs: 1` did not serialize
landing writes across independently deployed jobs. I corrected the development
schema to include `workspace.current_user.short_name` and removed both landing
notebooks and their runtime parameters from the bundle job. Landing remains
governed by its existing single-writer runbooks; the bundle now begins at Bronze
and cannot mutate shared landing state. Final authenticated validation, a
zero-delete plan, deployment, and the three-stage run all succeeded. The Gold
contracts returned 1, 282, and 39 rows with zero invalid rows, and the
convergence plan reported four unchanged resources with no additions, changes,
or deletions. The full claim boundaries and failure/recovery trail are recorded in
[`docs/evidence/dq24_bundle_deployment_validation.md`](docs/evidence/dq24_bundle_deployment_validation.md).

### 2026-10-20: DQ-28 end-to-end validation plan

I mapped the DQ-28 acceptance criteria to one bounded integration procedure
after DQ-24 through DQ-27 closed. I retained the existing
ownership boundaries instead of adding a wrapper or claiming that the bundle
manages landing, the dashboard, warehouse, identities, grants, or notification
destinations. The resulting runbook validates the isolated bundle outputs and
the externally governed shared stakeholder surface as explicit, separate paths
over the same source and Gold contracts.

Before documentation changes, the local baseline passed 202 tests and 106
subtests, Python compilation, and `git diff --check`. The exact reviewed
revision subsequently completed the live bundle, landing, reconciliation,
stakeholder, authorization, observability, privacy, cost, and explainability
gates in the authorized Databricks environment. The observed results and claim
boundaries are recorded in
[`docs/evidence/dq28_end_to_end_validation.md`](docs/evidence/dq28_end_to_end_validation.md).

### 2026-10-20: DQ-23 final submission audit

I performed the final audit against the merged submission tree after every
implementation and platform-decision card had closed. The existing DQ-28 record
supplies the complete workflow, ordered Bronze-to-Gold execution, and immediate
no-change landing reruns; I did not repeat those live operations merely to
produce duplicate evidence.

The final local suite passed 202 tests and 106 subtests, Python compilation,
and the whitespace check. All three required PySpark Gold outputs and their
Spark SQL alternatives are present. Ninety-three PNG evidence files are valid
images, and all local targets referenced by the 38 submitted Markdown files
resolve. A tracked-tree and Git-history scan found no credential, personal-email,
private-key, Databricks-host, or access-token pattern outside deliberate test
fixtures. The repository is public, its default branch is `main`, and an
unauthenticated request returned HTTP 200.

The submission contains the required code, architecture and trade-off record,
honest AI-usage and correction summary, retrospective, pipeline and table
screenshots, and outputs for all three analytical questions. Internal planning
and interview-preparation artifacts are not part of the submitted tree. Within
the assessment's documented Free Edition and single-writer boundaries, the
repository is reproducible, reviewable, explainable, and ready for Rearc review.
