# Conceptual and logical data model

This model separates provider artifacts, normalized economic entities, and stakeholder-facing analytical results. It is a design contract, not a claim that every table has already been implemented. DQ-10 finalized the source schemas, selected data types, keys, and expectation actions in `docs/SOURCE_SCHEMA_QUALITY_CONTRACT.md`.

## Layered model

```mermaid
erDiagram
    INGESTION_RUN ||--o{ SOURCE_OBJECT : observes
    SOURCE_OBJECT ||--o{ RAW_ARTIFACT_VERSION : produces
    RAW_ARTIFACT_VERSION ||--o{ BRONZE_BLS_OBSERVATION : parsed_into
    RAW_ARTIFACT_VERSION ||--o{ BRONZE_BLS_SERIES : parsed_into
    RAW_ARTIFACT_VERSION ||--o{ BRONZE_BLS_LOOKUP : parsed_into
    RAW_ARTIFACT_VERSION ||--o{ BRONZE_POPULATION : parsed_into

    SILVER_BLS_SERIES ||--o{ SILVER_BLS_OBSERVATION : describes
    SILVER_BLS_SECTOR ||--o{ SILVER_BLS_SERIES : categorizes
    SILVER_BLS_CLASS ||--o{ SILVER_BLS_SERIES : categorizes
    SILVER_BLS_MEASURE ||--o{ SILVER_BLS_SERIES : categorizes
    SILVER_BLS_DURATION ||--o{ SILVER_BLS_SERIES : categorizes
    SILVER_BLS_SEASONAL ||--o{ SILVER_BLS_SERIES : categorizes
    SILVER_BLS_PERIOD ||--o{ SILVER_BLS_OBSERVATION : defines

    SILVER_BLS_OBSERVATION ||--o{ GOLD_SERIES_ANNUAL_RESULT : aggregates_to
    SILVER_BLS_SERIES ||--o{ GOLD_SERIES_ANNUAL_RESULT : labels
    SILVER_POPULATION ||--o{ GOLD_POPULATION_SUMMARY : summarizes
    SILVER_BLS_OBSERVATION ||--o{ GOLD_SERIES_POPULATION_CONTEXT : contributes
    SILVER_POPULATION ||--o{ GOLD_SERIES_POPULATION_CONTEXT : contributes

    INGESTION_RUN {
        string ingestion_run_id PK
        timestamp started_at
        timestamp completed_at
        string status
        int discovered_count
        int landed_count
        int skipped_count
        int failed_count
    }

    SOURCE_OBJECT {
        string source_object_id PK
        string provider
        string source_url UK
        string relative_path
        boolean is_active
        timestamp first_seen_at
        timestamp last_seen_at
    }

    RAW_ARTIFACT_VERSION {
        string artifact_version_id PK
        string source_object_id FK
        string ingestion_run_id FK
        string volume_path
        long content_size
        string sha256_digest
        timestamp source_last_modified
        timestamp ingested_at
        string status
    }

    SILVER_BLS_SERIES {
        string series_id PK
        string sector_code FK
        string class_code FK
        string measure_code FK
        string duration_code FK
        string seasonal_code FK
        int base_year
        int begin_year
        string begin_period
        int end_year
        string end_period
        string series_label
    }

    SILVER_BLS_OBSERVATION {
        string series_id PK,FK
        int year PK
        string period_code PK,FK
        decimal(20,6) value
        string footnote_code
        string source_file
        timestamp ingested_at
    }

    SILVER_POPULATION {
        string nation_id PK
        string nation
        int year PK
        long population
        string source_url
        timestamp ingested_at
    }

    GOLD_SERIES_ANNUAL_RESULT {
        string series_id PK,FK
        int year PK
        decimal annual_value
        string series_label
        string aggregation_method
    }

    GOLD_POPULATION_SUMMARY {
        int start_year PK
        int end_year PK
        double mean_population
        double population_stddev
        string stddev_semantics
    }

    GOLD_SERIES_POPULATION_CONTEXT {
        string series_id PK,FK
        int year PK
        decimal q01_value
        long population
        boolean population_match_found
        string series_label
    }
```

## Planned grains and keys

| Object | Intended grain | Candidate key | Primary use |
| --- | --- | --- | --- |
| `ingestion_run` | One execution of the ingestion workflow | `ingestion_run_id` | Operational audit and rerun evidence |
| `source_object` | One stable provider URL or relative path | `source_object_id`; unique source URL | Current inventory and removal state |
| `raw_artifact_version` | One observed content version of one source object | `artifact_version_id`; source plus digest | Provenance, change detection, and reproducibility |
| `silver_bls_series` | One BLS statistical series | `series_id` | Meaning, coverage, and readable labels |
| `silver_bls_observation` | One series, year, and published period | `series_id + year + period_code` | Historical productivity observations |
| `silver_population` | One nation and year | `nation + year` | Annual population context |
| `gold_series_annual_result` | One series and selected annual result year | `series_id + year` | Question 2 and trend exploration |
| `gold_population_summary` | One requested inclusive year range | `start_year + end_year` | Question 1 |
| `gold_series_population_context` | One selected series and year | `series_id + year` | Question 3 and population-context view |

## BLS semantic relationships

The series label is derived from provider metadata rather than guessed from the encoded identifier:

```text
series
  ├── sector_code   → sector
  ├── class_code    → class
  ├── measure_code  → measure
  ├── duration_code → duration
  └── seasonal      → seasonal

observation.period → period
observation.footnote_codes → footnote
```

The period description belongs to an observation. It is not part of the stable series label. Footnotes remain provenance and should not be discarded simply because they are often empty.

## Current source rules supported by evidence

- `pr.data.1.AllData` is the complete analytical observation source.
- `pr.data.0.Current` is preserved as a raw provider artifact and used as a subset-consistency signal; it is not appended to `AllData`.
- Identifier and code fields are trimmed but retained as strings so leading zeroes survive.
- `series_id + year + period` is the observed BLS business key.
- Population is expected at one US national record per year after normalization.
- A population left join must preserve a BLS year even when no population record exists.
- Missing lookup matches, duplicate keys, failed casts, and rejected records must be counted and surfaced.

## Gold contracts and stakeholder use

Gold objects should be narrow, documented, and stable enough to function as the dashboard and Genie semantic contract.

The binding calculation and validation rules are maintained in
`docs/REQUIRED_GOLD_CONTRACTS.md`. In particular, Question 2 uses `Q01` through
`Q04` and excludes the `Q05` annual average.

| Gold contract | Required interpretation | Stakeholder use |
| --- | --- | --- |
| Population summary | Mean and population standard deviation for the complete 2013–2018 range | Understand the assigned population range and variability |
| Series annual result | Deterministically selected largest `Q01`–`Q04` annual sum, with earliest-year tie handling and readable provider label | Identify the year associated with each series' highest annual quarterly sum |
| Series-population context | Q01 observation for `PRS30006032` with population where available and unmatched years preserved | Explore parallel historical context without claiming causality |

## Data-model decisions still open

- Whether raw artifact history is retained as full versions, current state plus audit history, or both.
- Whether removed source objects use tombstones, `is_active`, or a separate event history.
- Decimal precision for BLS values and tolerances used for cross-implementation comparisons.
- Whether BLS lookup entities remain separate Silver tables or are additionally exposed through a denormalized series dimension.
- Whether an additional dashboard-only trend view stores every annual `Q01`–`Q04` sum; the required best-year Gold object stores only the deterministic selected result.
- Which time-series and indexed-comparison Gold views the stakeholder dashboard requires beyond the three assigned questions.
- Whether Data USA's response supplies additional geographic attributes worth preserving outside the current national grain.
- Which objects become physical tables versus governed views.
- Which quality failures cause warning, row quarantine, row drop, or pipeline failure.
- Which dashboard and Genie objects are supported in the authorized Databricks edition.

These decisions will be closed only after source landing, schema inspection, quality profiling, and verified stakeholder need provide evidence.

