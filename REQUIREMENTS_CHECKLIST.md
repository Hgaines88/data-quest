# Rearc Data Quest Requirements Checklist

This document translates the assignment into a Kanban-ready implementation plan. It distinguishes required work from optional enhancements and gives every card a verifiable definition of done.

## Working agreements

- Apply `docs/QUALITY_ASSURANCE_PROTOCOL.md` to every pull request beginning with DQ-05.
- Understand and be able to explain every submitted line of code.
- Record meaningful AI assistance, validation, and corrections as work proceeds.
- Prefer small, reviewable commits tied to one card.
- Do not expose credentials, tokens, workspace URLs, or private identifiers.
- Keep the assessment instructions and solution work within the authorized review context.

## Definition of done for required work

- [ ] The BLS productivity folder is discovered dynamically and fully mirrored into a Databricks Volume.
- [ ] The Data USA population response is stored as raw JSON in the same Volume.
- [ ] Re-running ingestion safely handles source additions, changes, removals, and unchanged files.
- [ ] Bronze, Silver, and Gold tables are built through a Spark Declarative Pipeline.
- [ ] Pipeline expectations enforce the expected schema and non-null keys.
- [ ] Each analytical question is implemented once in Spark SQL and once with the PySpark DataFrame API.
- [ ] One implementation per question is designated as the primary Gold-table path; the other is documented and validated as an equivalent alternative.
- [ ] Human-readable BLS series labels are derived from the provider's metadata files rather than guessed from the series code.
- [ ] `PROCESS.md` documents architecture, trade-offs, AI usage, validation, and the retrospective.
- [ ] Screenshots show the pipeline, tables, and output of all three questions.
- [ ] The submitted repository is shareable and contains all code needed to reproduce ingestion and transformation.

## Kanban columns

1. **Backlog**: defined but not yet ready or selected.
2. **Ready**: acceptance criteria and dependencies are satisfied.
3. **In Progress**: actively being implemented; limit to one or two cards.
4. **Validate**: implementation is complete and evidence is being checked.
5. **Done**: acceptance criteria are met and the work is committed.

Recommended labels: `setup`, `ingestion`, `bronze`, `silver`, `gold`, `sql`, `pyspark`, `quality`, `documentation`, `evidence`, `bonus`, `blocked`.

## Epic 0: Workspace and repository foundation

### DQ-01: Establish repository structure and development conventions

**Priority:** Required  
**Depends on:** None

- [x] Choose clear locations for ingestion code, pipeline code, SQL alternatives, tests or validation helpers, documentation, and screenshots.
- [x] Add a `.gitignore` that excludes local secrets, downloaded data, Databricks state, and generated artifacts that should not be committed.
- [x] Document required configuration through environment variables or Databricks configuration, without committing secret values.
- [x] Decide on naming conventions for catalog, schema, Volume, and Bronze/Silver/Gold tables.

**Done when:** A reviewer can understand the intended repository layout and no secret material is tracked.

### DQ-02: Confirm the Databricks execution environment

**Priority:** Required  
**Depends on:** DQ-01

- [x] Confirm access to Databricks Free Edition or another authorized workspace.
- [x] Confirm that a catalog or metastore, schema, Volume, and Spark Declarative Pipelines are available.
- [x] Record runtime and relevant platform assumptions in `PROCESS.md`.
- [x] Prove a small file can be written to and read from the target Volume.

**Done when:** The workspace can execute a minimal read/write test using the planned storage location.

### DQ-03: Create the documentation and AI-usage log scaffold

**Priority:** Required  
**Depends on:** DQ-01

- [x] Create `PROCESS.md` with sections for architecture, trade-offs, AI usage, validation or corrections, and retrospective.
- [x] Record AI use incrementally, including what was requested, what was accepted or changed, and how the result was checked.
- [x] Add a source-notes section referencing the BLS data-access policy and Data USA API documentation.

**Done when:** The required narrative exists before implementation and can be updated throughout the project.

## Epic 1: Raw-source ingestion

### DQ-04: Profile the BLS directory and metadata relationships

**Priority:** Required  
**Depends on:** DQ-03

- [x] Inspect the complete BLS `pr` directory rather than only the primary data file.
- [x] Identify the data, series, measure, sector, duration, seasonal, period, class, footnote, contact, and documentation files currently present.
- [x] Determine which metadata files are required to create a human-readable series label.
- [x] Record delimiter, headers, data types, key fields, and any whitespace or null conventions.

**Done when:** The ingestion and modeling design is based on provider documentation and observed file structure.

### DQ-05: Implement compliant dynamic BLS discovery

**Priority:** Required  
**Depends on:** DQ-04

- [x] Fetch the BLS folder listing programmatically.
- [x] Send a descriptive `User-Agent` containing valid owner contact information, as required by the BLS automated-retrieval policy.
- [x] Discover file links dynamically without hardcoded filenames.
- [x] Restrict discovered downloads to the intended BLS directory and reject parent or unrelated links.
- [x] Use timeouts, bounded retries or backoff, and clear error reporting without attempting to bypass access controls.

**Done when:** The program discovers the current source inventory and handles a BLS `403` in the documented, policy-compliant manner.

### DQ-06: Design the ingestion manifest and change-detection contract

**Priority:** Required  
**Depends on:** DQ-05

- [x] Define a manifest containing at least source URL, relative path, source metadata when available, content size, content digest, ingestion timestamp, and status.
- [x] Define how new, changed, unchanged, and removed source objects are detected.
- [x] Decide whether removals are represented by deletion, tombstone, or active/inactive status, and explain the choice.
- [x] Define safe behavior for partial download failures and interrupted runs.

**Done when:** The rerun behavior is explicit, deterministic, and capable of representing all four source-change cases.

### DQ-07: Land the complete BLS folder into the Volume

**Priority:** Required  
**Depends on:** DQ-02, DQ-05, DQ-06

- [x] Download every dynamically discovered file using the compliant request behavior.
- [x] Write raw bytes to a stable BLS path in the Databricks Volume.
- [x] Avoid rewriting or reprocessing unchanged content.
- [x] Update the manifest only after a file is landed successfully.
- [x] Preserve enough source metadata to audit what was ingested.

**Done when:** The Volume mirrors the current BLS source inventory and the manifest accurately describes the landed files.

### DQ-08: Land the Data USA population response as raw JSON

**Priority:** Required  
**Depends on:** DQ-02, DQ-06

- [x] Call the assigned Data USA endpoint with timeout and explicit status checking.
- [x] Validate that the response is JSON and contains the expected response envelope and data records.
- [x] Store the unmodified response as JSON in the same Volume under a separate source path.
- [x] Capture request URL, ingestion time, size, and digest in the ingestion manifest or equivalent metadata.
- [x] Make repeated runs idempotent.

**Done when:** A reproducible raw population artifact and its provenance are present in the Volume.

### DQ-09: Prove ingestion rerun behavior

**Priority:** Required  
**Depends on:** DQ-07, DQ-08

- [x] Run ingestion twice with no source changes and show that unchanged files are skipped.
- [x] Test new and modified files through a controlled fixture or dependency-injected source listing.
- [x] Test removal handling through a controlled fixture rather than manipulating the provider.
- [x] Test an interrupted or failed download and confirm the manifest does not falsely mark it successful.
- [x] Record concise evidence for `PROCESS.md`.

**Done when:** Tests or controlled demonstrations cover new, changed, unchanged, removed, and failed inputs.

## Epic 2: Bronze and Silver pipeline

### DQ-10: Define explicit source schemas and data-quality rules

**Priority:** Required  
**Depends on:** DQ-04, DQ-08

- [x] Define explicit schemas for the BLS observation data, required BLS metadata, and population records.
- [x] Identify non-null business keys and acceptable value types.
- [x] Decide how malformed, null-key, and duplicate records are handled.
- [x] Define the pipeline expectations and their action: retain with metrics, drop, or fail.

**Done when:** Schema and expectation decisions are documented before table implementation.

### DQ-11: Build Bronze tables in a Spark Declarative Pipeline

**Priority:** Required  
**Depends on:** DQ-07, DQ-08, DQ-10

- [x] Read raw BLS files and population JSON from the Volume.
- [x] Preserve source fidelity while adding provenance fields such as source file and ingestion timestamp where useful.
- [x] Apply expected-schema and non-null-key expectations.
- [x] Ensure repeated pipeline execution is deterministic.
- [x] Expose expectation results for screenshot evidence ([DQ-11 live evidence](docs/evidence/dq11_bronze_live_validation.md)).

**Done when:** Bronze tables are pipeline-managed, queryable, traceable to raw sources, and visibly quality-checked. See the [completed Databricks update and table evidence](docs/evidence/dq11_bronze_live_validation.md).

### DQ-12: Build typed and deduplicated Silver BLS observations

**Priority:** Required  
**Depends on:** DQ-11

- [x] Normalize column names and trim provider formatting artifacts.
- [x] Cast year, value, and other fields to intentional types.
- [x] Define and enforce the observation business key.
- [x] Handle nulls and duplicates according to the documented rule.
- [x] Preserve useful period information for quarterly analysis.

**Done when:** Silver observations have intentional types, stable uniqueness, and no unexpected null keys. See the [completed Silver update, graph, and performance evidence](docs/evidence/dq12_silver_live_validation.md).

### DQ-13: Build Silver BLS series metadata and readable labels

**Priority:** Required  
**Depends on:** DQ-11, DQ-04

- [x] Model the required BLS lookup files.
- [x] Join series metadata to measure, sector, duration, seasonal, class, or other applicable descriptions.
- [x] Construct a concise, human-readable series label from documented provider fields.
- [x] Check for missing lookup matches and avoid silently inventing descriptions.

**Done when:** Every Gold result can display a provider-grounded label or an explicitly handled missing-label condition. See the [completed Silver series update and graph evidence](docs/evidence/dq13_silver_series_live_validation.md).

### DQ-14: Build typed and deduplicated Silver population data

**Priority:** Required  
**Depends on:** DQ-11

- [x] Extract records from the Data USA response envelope.
- [x] Normalize year, nation, and population fields with explicit types.
- [x] Limit or validate the intended US national population grain.
- [x] Enforce non-null keys and deterministic deduplication.
- [x] Confirm the years needed for 2013 through 2018 are present.

**Done when:** Silver population contains one valid US population record per available year at the intended grain. The [completed Silver population update, graph, table, performance, and year-coverage evidence](docs/evidence/dq14_silver_population_live_validation.md) proves the published grain, runtime result, and one row for each requested year from 2013 through 2018.

### DQ-15: Validate Bronze-to-Silver quality

**Priority:** Required  
**Depends on:** DQ-12, DQ-13, DQ-14

- [x] Reconcile row counts and explain expected differences between layers.
- [x] Check uniqueness and non-null keys.
- [x] Check type conversions and rejected or quarantined rows.
- [x] Check label coverage and population year coverage.
- [x] Save compact validation queries or tests that can be rerun.

**Done when:** Each Silver table has repeatable quality checks and all
discrepancies are explained. The [completed 14-check Databricks
report](docs/evidence/dq15_bronze_to_silver_quality_validation.md) reconciles
77,126 observation rows, 282 series rows, and 11 population rows with every
check passing and no unexplained discrepancy.

## Epic 3: Gold analytical outputs in both APIs

### DQ-16: Answer Question 1 in Spark SQL and PySpark

**Priority:** Required  
**Depends on:** DQ-14

- [x] Filter annual US population to 2013 through 2018 inclusive.
- [x] Confirm exactly one normalized US population row exists for each of the six requested years.
- [x] Compute mean and standard deviation in Spark SQL.
- [x] Compute the same result with the PySpark DataFrame API.
- [x] Use and document population standard deviation (`stddev_pop`) because the requested six-year range is the complete finite set being summarized.
- [x] Publish the inclusive bounds, year count, mean, standard deviation, and standard-deviation semantics in `gold_population_summary_2013_2018`.
- [x] Compare both implementations using an appropriate numeric tolerance.
- [x] Select and document the primary implementation feeding the Gold table.

**Done when:** Both versions agree and the Gold output clearly identifies the range and statistic semantics. The [completed Gold pipeline and independent Spark SQL validation](docs/evidence/dq16_gold_population_summary_validation.md) show one matching summary row, explicit population-standard-deviation semantics, and numerical agreement within tolerance.

### DQ-17: Answer Question 2 in Spark SQL and PySpark

**Priority:** Required  
**Depends on:** DQ-12, DQ-13

- [x] Filter to quarterly periods `Q01` through `Q04`; explicitly exclude `Q05` because it is an annual average, not an additional quarter.
- [x] Sum quarterly `value` by `series_id` and year.
- [x] Select the largest annual sum for every series in Spark SQL.
- [x] Implement the same logic with the PySpark DataFrame API.
- [x] Break ties deterministically by selecting the earliest tied year.
- [x] Include the human-readable series label.
- [x] Reconcile the expected series inventory and visibly flag a series with no quarterly observations rather than silently omitting it.
- [x] Compare both implementations and designate the primary Gold-table version.

**Done when:** Each series has a deterministic best year, annual sum, and readable label, with equivalent SQL and PySpark results. The [completed Gold pipeline, metadata-resolution gate, SQL/PySpark parity comparison, and independent source calculation](docs/evidence/dq17_gold_bls_best_year_validation.md) establish the result for the validated snapshot.

### DQ-18: Answer Question 3 in Spark SQL and PySpark

**Priority:** Required  
**Depends on:** DQ-12, DQ-14

- [x] Filter BLS observations to `series_id = PRS30006032` and `period = Q01`.
- [x] Join population by year while preserving BLS years without a population match.
- [x] Use the filtered BLS observations as the left side of the join and expose an explicit population-match indicator or equivalent visible missing-value behavior.
- [x] Implement the result in Spark SQL.
- [x] Implement the same result with the PySpark DataFrame API.
- [x] Compare both implementations and designate the primary Gold-table version.
- [x] Order output by year for readability.

**Done when:** The output shows annual Q01 values and population where available without silently dropping unmatched BLS years. The [completed Gold pipeline, fail-fast expectations, SQL/PySpark parity comparison, and representative source checks](docs/evidence/dq18_gold_bls_q01_population_validation.md) validate all 39 BLS years while preserving 28 unmatched population rows.

### DQ-19: Add cross-implementation and result validation

**Priority:** Required  
**Depends on:** DQ-16, DQ-17, DQ-18

- [x] Compare SQL and PySpark schemas, row counts, keys, and values for all three questions.
- [x] Use numeric tolerances where floating-point results require them.
- [x] Add invariants for expected year bounds, uniqueness, ordering assumptions, and join cardinality.
- [x] Independently spot-check representative results against source records or a simple calculation.
- [x] Document any intentional representational differences.
- [x] Confirm the three contracts in `docs/REQUIRED_GOLD_CONTRACTS.md` are complete before beginning dashboard or Genie implementation.

**Done when:** Equivalent implementations are demonstrated, not merely assumed. The [live 17-check reconciliation](docs/evidence/dq19_gold_cross_implementation_validation.md) confirms all three schemas, cardinalities, keys, values, invariants, and independent source checks before presentation-layer work.

## Epic 4: Documentation, evidence, and submission

### DQ-20: Complete `PROCESS.md`

**Priority:** Required  
**Depends on:** DQ-09, DQ-15, DQ-19

- [x] Explain Bronze, Silver, and Gold responsibilities and data flow.
- [x] Explain ingestion idempotency and handling of additions, changes, removals, and failures.
- [x] Explain why SQL or PySpark was selected as primary for each question.
- [x] Discuss real-client trade-offs: schema drift, scale, cost, security, access control, monitoring, and provider reliability.
- [x] Document AI use, corrections, and validation honestly.
- [x] Describe the hardest problem and what was learned.

**Done when:** The document answers every requested topic and accurately matches the implementation. The completed [`PROCESS.md`](PROCESS.md) records the implemented medallion flow, rerun contract, analytical API choices, production trade-offs, AI-assisted corrections, validation approach, and retrospective.

### DQ-21: Capture required screenshots

**Priority:** Required  
**Depends on:** DQ-11, DQ-15, DQ-19

- [x] Capture the successful Spark Declarative Pipeline graph or run.
- [x] Capture representative Bronze, Silver, and Gold tables.
- [x] Capture the output of Question 1.
- [x] Capture the output of Question 2 with readable labels.
- [x] Capture the output of Question 3.
- [x] Redact workspace identifiers, tokens, email addresses, or other unnecessary private information.
- [x] Give screenshots descriptive filenames and reference them from the README or `PROCESS.md`.

**Done when:** A reviewer without workspace access can verify the pipeline and all three outputs. The [curated DQ-21 submission set](docs/screenshots/README.md#dq-21-curated-submission-set) provides nine descriptively named, privacy-reviewed screenshots covering the successful pipeline, representative Bronze/Silver/Gold tables, and all three required analytical outputs.

### DQ-22: Write the reviewer-facing README

**Priority:** Required  
**Depends on:** DQ-20, DQ-21

- [x] Summarize the solution and architecture.
- [x] Provide configuration and execution instructions.
- [x] Identify the pipeline entry point, ingestion entry point, Gold outputs, SQL alternatives, and evidence.
- [x] Document prerequisites without exposing credentials.
- [x] Link to `PROCESS.md` and screenshots.

**Done when:** A reviewer can navigate and understand the submission without verbal guidance. The reviewer path begins in the [repository README](README.md), which covers architecture, prerequisites, configuration, execution order, outputs, alternatives, QA, and evidence links.

### DQ-23: Perform final submission audit

**Priority:** Required  
**Depends on:** DQ-20, DQ-21, DQ-22, DQ-29
**Execution note:** This is the final project-wide gate. See the
[project completion roadmap](docs/PROJECT_ROADMAP.md); do not close DQ-23 while
an implementation card or the platform decision gate remains open.

- [ ] Run the complete ingestion and pipeline workflow from a documented starting state.
- [ ] Re-run it to demonstrate idempotency.
- [ ] Confirm required outputs, SQL alternatives, and PySpark alternatives are present.
- [ ] Search tracked files and Git history for secrets or sensitive data.
- [ ] Confirm screenshots render and repository links work.
- [ ] Review every submitted line sufficiently to explain it in an interview.
- [ ] Confirm the repository is accessible to Rearc reviewers.

**Done when:** The solution is reproducible, reviewable, explainable, and contains every required deliverable.

## Epic 5: Optional enhancements

These extend the completed required pipeline before DQ-23 certifies the final
repository. Their execution order and QA gates are defined in the
[project completion roadmap](docs/PROJECT_ROADMAP.md).

### DQ-24: Deploy with Databricks Asset Bundles

**Depends on:** DQ-26

- [ ] Define resources and environment configuration as code.
- [ ] Validate the bundle and document deployment commands.

### DQ-25: Add stakeholder exploration

**Depends on:** DQ-22

- [ ] Create a focused dashboard or Genie space over the Gold layer.
- [ ] Use plain-language labels and questions relevant to a non-technical stakeholder.

### DQ-26: Add Gold-layer access controls

**Depends on:** DQ-25

- [ ] Create an appropriate read-only analyst access pattern in Unity Catalog.
- [ ] Document the principle-of-least-privilege rationale.

### DQ-27: Add operational observability

**Depends on:** DQ-24

- [ ] Surface freshness, file-processing, expectation, and pipeline-failure metrics.
- [ ] Describe alerting and recovery behavior suitable for a client environment.

### DQ-28: Validate the extended Databricks product end to end

**Depends on:** DQ-24, DQ-25, DQ-26, DQ-27

- [ ] Deploy and run the documented solution from its starting state using the Asset Bundle where supported.
- [ ] For unsupported Free Edition resources, validate the bundle configuration, exercise the documented equivalent resource, and record the limitation without claiming deployment.
- [ ] Reconcile stakeholder answers to Gold and verify least-privilege access.
- [ ] Confirm operational signals and recovery evidence are visible.
- [ ] Reconcile the final documentation and evidence gallery to the implementation.

### DQ-29: Reassess before adding Snowflake or Power BI

**Depends on:** DQ-28

- [ ] Evaluate whether an external platform serves a defensible unmet need.
- [ ] Record cost, access, reuse, maintenance, and environment constraints.
- [ ] Decide to stop with Databricks, build a separate adaptation, or add a narrowly scoped consumer.
- [ ] Do not begin an external implementation before documenting the decision.

## Recommended execution order

1. DQ-01 through DQ-04
2. DQ-05 and DQ-06
3. DQ-07 through DQ-10
4. DQ-11 through DQ-15
5. DQ-16 through DQ-19
6. DQ-20 through DQ-22
7. DQ-25, DQ-26, DQ-24, and DQ-27
8. DQ-28 and DQ-29
9. DQ-23 as the final project-wide audit

## Suggested first sprint

Move only these cards to **Ready** initially:

- DQ-01 Establish repository structure and development conventions
- DQ-02 Confirm the Databricks execution environment
- DQ-03 Create the documentation and AI-usage log scaffold
- DQ-04 Profile the BLS directory and metadata relationships

Keep all other cards in **Backlog** until their dependencies are satisfied.
