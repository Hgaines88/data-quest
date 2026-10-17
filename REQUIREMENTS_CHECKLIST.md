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

- [ ] Choose clear locations for ingestion code, pipeline code, SQL alternatives, tests or validation helpers, documentation, and screenshots.
- [ ] Add a `.gitignore` that excludes local secrets, downloaded data, Databricks state, and generated artifacts that should not be committed.
- [ ] Document required configuration through environment variables or Databricks configuration, without committing secret values.
- [ ] Decide on naming conventions for catalog, schema, Volume, and Bronze/Silver/Gold tables.

**Done when:** A reviewer can understand the intended repository layout and no secret material is tracked.

### DQ-02: Confirm the Databricks execution environment

**Priority:** Required  
**Depends on:** DQ-01

- [ ] Confirm access to Databricks Free Edition or another authorized workspace.
- [ ] Confirm that a catalog or metastore, schema, Volume, and Spark Declarative Pipelines are available.
- [ ] Record runtime and relevant platform assumptions in `PROCESS.md`.
- [ ] Prove a small file can be written to and read from the target Volume.

**Done when:** The workspace can execute a minimal read/write test using the planned storage location.

### DQ-03: Create the documentation and AI-usage log scaffold

**Priority:** Required  
**Depends on:** DQ-01

- [ ] Create `PROCESS.md` with sections for architecture, trade-offs, AI usage, validation or corrections, and retrospective.
- [ ] Record AI use incrementally, including what was requested, what was accepted or changed, and how the result was checked.
- [ ] Add a source-notes section referencing the BLS data-access policy and Data USA API documentation.

**Done when:** The required narrative exists before implementation and can be updated throughout the project.

## Epic 1: Raw-source ingestion

### DQ-04: Profile the BLS directory and metadata relationships

**Priority:** Required  
**Depends on:** DQ-03

- [ ] Inspect the complete BLS `pr` directory rather than only the primary data file.
- [ ] Identify the data, series, measure, sector, duration, seasonal, period, class, footnote, contact, and documentation files currently present.
- [ ] Determine which metadata files are required to create a human-readable series label.
- [ ] Record delimiter, headers, data types, key fields, and any whitespace or null conventions.

**Done when:** The ingestion and modeling design is based on provider documentation and observed file structure.

### DQ-05: Implement compliant dynamic BLS discovery

**Priority:** Required  
**Depends on:** DQ-04

- [ ] Fetch the BLS folder listing programmatically.
- [ ] Send a descriptive `User-Agent` containing valid owner contact information, as required by the BLS automated-retrieval policy.
- [ ] Discover file links dynamically without hardcoded filenames.
- [ ] Restrict discovered downloads to the intended BLS directory and reject parent or unrelated links.
- [ ] Use timeouts, bounded retries or backoff, and clear error reporting without attempting to bypass access controls.

**Done when:** The program discovers the current source inventory and handles a BLS `403` in the documented, policy-compliant manner.

### DQ-06: Design the ingestion manifest and change-detection contract

**Priority:** Required  
**Depends on:** DQ-05

- [ ] Define a manifest containing at least source URL, relative path, source metadata when available, content size, content digest, ingestion timestamp, and status.
- [ ] Define how new, changed, unchanged, and removed source objects are detected.
- [ ] Decide whether removals are represented by deletion, tombstone, or active/inactive status, and explain the choice.
- [ ] Define safe behavior for partial download failures and interrupted runs.

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

- [ ] Run ingestion twice with no source changes and show that unchanged files are skipped.
- [ ] Test new and modified files through a controlled fixture or dependency-injected source listing.
- [ ] Test removal handling through a controlled fixture rather than manipulating the provider.
- [ ] Test an interrupted or failed download and confirm the manifest does not falsely mark it successful.
- [ ] Record concise evidence for `PROCESS.md`.

**Done when:** Tests or controlled demonstrations cover new, changed, unchanged, removed, and failed inputs.

## Epic 2: Bronze and Silver pipeline

### DQ-10: Define explicit source schemas and data-quality rules

**Priority:** Required  
**Depends on:** DQ-04, DQ-08

- [ ] Define explicit schemas for the BLS observation data, required BLS metadata, and population records.
- [ ] Identify non-null business keys and acceptable value types.
- [ ] Decide how malformed, null-key, and duplicate records are handled.
- [ ] Define the pipeline expectations and their action: retain with metrics, drop, or fail.

**Done when:** Schema and expectation decisions are documented before table implementation.

### DQ-11: Build Bronze tables in a Spark Declarative Pipeline

**Priority:** Required  
**Depends on:** DQ-07, DQ-08, DQ-10

- [ ] Read raw BLS files and population JSON from the Volume.
- [ ] Preserve source fidelity while adding provenance fields such as source file and ingestion timestamp where useful.
- [ ] Apply expected-schema and non-null-key expectations.
- [ ] Ensure repeated pipeline execution is deterministic.
- [ ] Expose expectation results for screenshot evidence.

**Done when:** Bronze tables are pipeline-managed, queryable, traceable to raw sources, and visibly quality-checked.

### DQ-12: Build typed and deduplicated Silver BLS observations

**Priority:** Required  
**Depends on:** DQ-11

- [ ] Normalize column names and trim provider formatting artifacts.
- [ ] Cast year, value, and other fields to intentional types.
- [ ] Define and enforce the observation business key.
- [ ] Handle nulls and duplicates according to the documented rule.
- [ ] Preserve useful period information for quarterly analysis.

**Done when:** Silver observations have intentional types, stable uniqueness, and no unexpected null keys.

### DQ-13: Build Silver BLS series metadata and readable labels

**Priority:** Required  
**Depends on:** DQ-11, DQ-04

- [ ] Model the required BLS lookup files.
- [ ] Join series metadata to measure, sector, duration, seasonal, class, or other applicable descriptions.
- [ ] Construct a concise, human-readable series label from documented provider fields.
- [ ] Check for missing lookup matches and avoid silently inventing descriptions.

**Done when:** Every Gold result can display a provider-grounded label or an explicitly handled missing-label condition.

### DQ-14: Build typed and deduplicated Silver population data

**Priority:** Required  
**Depends on:** DQ-11

- [ ] Extract records from the Data USA response envelope.
- [ ] Normalize year, nation, and population fields with explicit types.
- [ ] Limit or validate the intended US national population grain.
- [ ] Enforce non-null keys and deterministic deduplication.
- [ ] Confirm the years needed for 2013 through 2018 are present.

**Done when:** Silver population contains one valid US population record per available year at the intended grain.

### DQ-15: Validate Bronze-to-Silver quality

**Priority:** Required  
**Depends on:** DQ-12, DQ-13, DQ-14

- [ ] Reconcile row counts and explain expected differences between layers.
- [ ] Check uniqueness and non-null keys.
- [ ] Check type conversions and rejected or quarantined rows.
- [ ] Check label coverage and population year coverage.
- [ ] Save compact validation queries or tests that can be rerun.

**Done when:** Each Silver table has repeatable quality checks and all discrepancies are explained.

## Epic 3: Gold analytical outputs in both APIs

### DQ-16: Answer Question 1 in Spark SQL and PySpark

**Priority:** Required  
**Depends on:** DQ-14

- [ ] Filter annual US population to 2013 through 2018 inclusive.
- [ ] Confirm exactly one normalized US population row exists for each of the six requested years.
- [ ] Compute mean and standard deviation in Spark SQL.
- [ ] Compute the same result with the PySpark DataFrame API.
- [ ] Use and document population standard deviation (`stddev_pop`) because the requested six-year range is the complete finite set being summarized.
- [ ] Publish the inclusive bounds, year count, mean, standard deviation, and standard-deviation semantics in `gold_population_summary_2013_2018`.
- [ ] Compare both implementations using an appropriate numeric tolerance.
- [ ] Select and document the primary implementation feeding the Gold table.

**Done when:** Both versions agree and the Gold output clearly identifies the range and statistic semantics.

### DQ-17: Answer Question 2 in Spark SQL and PySpark

**Priority:** Required  
**Depends on:** DQ-12, DQ-13

- [ ] Filter to quarterly periods `Q01` through `Q04`; explicitly exclude `Q05` because it is an annual average, not an additional quarter.
- [ ] Sum quarterly `value` by `series_id` and year.
- [ ] Select the largest annual sum for every series in Spark SQL.
- [ ] Implement the same logic with the PySpark DataFrame API.
- [ ] Break ties deterministically by selecting the earliest tied year.
- [ ] Include the human-readable series label.
- [ ] Reconcile the expected series inventory and visibly flag a series with no quarterly observations rather than silently omitting it.
- [ ] Compare both implementations and designate the primary Gold-table version.

**Done when:** Each series has a deterministic best year, annual sum, and readable label, with equivalent SQL and PySpark results.

### DQ-18: Answer Question 3 in Spark SQL and PySpark

**Priority:** Required  
**Depends on:** DQ-12, DQ-14

- [ ] Filter BLS observations to `series_id = PRS30006032` and `period = Q01`.
- [ ] Join population by year while preserving BLS years without a population match.
- [ ] Use the filtered BLS observations as the left side of the join and expose an explicit population-match indicator or equivalent visible missing-value behavior.
- [ ] Implement the result in Spark SQL.
- [ ] Implement the same result with the PySpark DataFrame API.
- [ ] Compare both implementations and designate the primary Gold-table version.
- [ ] Order output by year for readability.

**Done when:** The output shows annual Q01 values and population where available without silently dropping unmatched BLS years.

### DQ-19: Add cross-implementation and result validation

**Priority:** Required  
**Depends on:** DQ-16, DQ-17, DQ-18

- [ ] Compare SQL and PySpark schemas, row counts, keys, and values for all three questions.
- [ ] Use numeric tolerances where floating-point results require them.
- [ ] Add invariants for expected year bounds, uniqueness, ordering assumptions, and join cardinality.
- [ ] Independently spot-check representative results against source records or a simple calculation.
- [ ] Document any intentional representational differences.
- [ ] Confirm the three contracts in `docs/REQUIRED_GOLD_CONTRACTS.md` are complete before beginning dashboard or Genie implementation.

**Done when:** Equivalent implementations are demonstrated, not merely assumed.

## Epic 4: Documentation, evidence, and submission

### DQ-20: Complete `PROCESS.md`

**Priority:** Required  
**Depends on:** DQ-09, DQ-15, DQ-19

- [ ] Explain Bronze, Silver, and Gold responsibilities and data flow.
- [ ] Explain ingestion idempotency and handling of additions, changes, removals, and failures.
- [ ] Explain why SQL or PySpark was selected as primary for each question.
- [ ] Discuss real-client trade-offs: schema drift, scale, cost, security, access control, monitoring, and provider reliability.
- [ ] Document AI use, corrections, and validation honestly.
- [ ] Describe the hardest problem and what was learned.

**Done when:** The document answers every requested topic and accurately matches the implementation.

### DQ-21: Capture required screenshots

**Priority:** Required  
**Depends on:** DQ-11, DQ-15, DQ-19

- [ ] Capture the successful Spark Declarative Pipeline graph or run.
- [ ] Capture representative Bronze, Silver, and Gold tables.
- [ ] Capture the output of Question 1.
- [ ] Capture the output of Question 2 with readable labels.
- [ ] Capture the output of Question 3.
- [ ] Redact workspace identifiers, tokens, email addresses, or other unnecessary private information.
- [ ] Give screenshots descriptive filenames and reference them from the README or `PROCESS.md`.

**Done when:** A reviewer without workspace access can verify the pipeline and all three outputs.

### DQ-22: Write the reviewer-facing README

**Priority:** Required  
**Depends on:** DQ-20, DQ-21

- [ ] Summarize the solution and architecture.
- [ ] Provide configuration and execution instructions.
- [ ] Identify the pipeline entry point, ingestion entry point, Gold outputs, SQL alternatives, and evidence.
- [ ] Document prerequisites without exposing credentials.
- [ ] Link to `PROCESS.md` and screenshots.

**Done when:** A reviewer can navigate and understand the submission without verbal guidance.

### DQ-23: Perform final submission audit

**Priority:** Required  
**Depends on:** DQ-20, DQ-21, DQ-22

- [ ] Run the complete ingestion and pipeline workflow from a documented starting state.
- [ ] Re-run it to demonstrate idempotency.
- [ ] Confirm required outputs, SQL alternatives, and PySpark alternatives are present.
- [ ] Search tracked files and Git history for secrets or sensitive data.
- [ ] Confirm screenshots render and repository links work.
- [ ] Review every submitted line sufficiently to explain it in an interview.
- [ ] Confirm the repository is accessible to Rearc reviewers.

**Done when:** The solution is reproducible, reviewable, explainable, and contains every required deliverable.

## Epic 5: Optional enhancements

These begin only after DQ-23 is functionally complete.

### DQ-24: Deploy with Databricks Asset Bundles

- [ ] Define resources and environment configuration as code.
- [ ] Validate the bundle and document deployment commands.

### DQ-25: Add stakeholder exploration

- [ ] Create a focused dashboard or Genie space over the Gold layer.
- [ ] Use plain-language labels and questions relevant to a non-technical stakeholder.

### DQ-26: Add Gold-layer access controls

- [ ] Create an appropriate read-only analyst access pattern in Unity Catalog.
- [ ] Document the principle-of-least-privilege rationale.

### DQ-27: Add operational observability

- [ ] Surface freshness, file-processing, expectation, and pipeline-failure metrics.
- [ ] Describe alerting and recovery behavior suitable for a client environment.

## Recommended execution order

1. DQ-01 through DQ-04
2. DQ-05 and DQ-06
3. DQ-07 through DQ-10
4. DQ-11 through DQ-15
5. DQ-16 through DQ-19
6. DQ-20 through DQ-23
7. One carefully selected bonus card if time and quality permit

## Suggested first sprint

Move only these cards to **Ready** initially:

- DQ-01 Establish repository structure and development conventions
- DQ-02 Confirm the Databricks execution environment
- DQ-03 Create the documentation and AI-usage log scaffold
- DQ-04 Profile the BLS directory and metadata relationships

Keep all other cards in **Backlog** until their dependencies are satisfied.
