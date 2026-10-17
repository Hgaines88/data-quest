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

## Retrospective

This section will be completed as the implementation develops. The environment phase reinforced the value of verifying platform capabilities and permissions before writing pipeline code.
