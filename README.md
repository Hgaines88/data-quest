# Rearc Data Quest: Databricks Medallion Pipeline

This repository implements the Rearc Data Quest as an idempotent Databricks
landing workflow and a Spark Declarative Pipeline. It ingests the complete BLS
productivity time-series directory plus the assigned Data USA population
response, publishes governed Bronze and typed Silver tables, and answers all
three analytical questions in Gold. Each Gold result has a primary PySpark
implementation and an independently runnable Spark SQL alternative.

For implementation decisions, corrections, trade-offs, AI usage, and the
retrospective, read [`PROCESS.md`](PROCESS.md). For a quick visual review, open
the [curated screenshot index](docs/screenshots/README.md#dq-21-curated-submission-set).
The remaining work and the rule that reserves DQ-23 for the final audit are
recorded in the [project completion roadmap](docs/PROJECT_ROADMAP.md).

## Architecture

```text
BLS directory ─────────────┐
                          ├─ landing notebooks ─ immutable Volume objects
Data USA population API ──┘                     + append-only manifests
                                                     │
                                                     ▼
                    Bronze source-shaped tables + provenance + expectations
                                                     │
                                                     ▼
                    Silver typed observations, series metadata, population
                                                     │
                                                     ▼
                    Gold answers (PySpark) ⇄ SQL alternatives and parity checks
```

- **Landing:** content-addressed raw objects and provider-specific Delta
  manifests make unchanged reruns no-ops while retaining an audit trail.
- **Bronze:** [`pipelines/bronze.py`](pipelines/bronze.py) validates manifest
  state and source shape before publishing provider-shaped records with
  provenance.
- **Silver:** [`pipelines/silver.py`](pipelines/silver.py) applies intentional
  types, business keys, provider-grounded labels, uniqueness gates, and
  population normalization.
- **Gold:** [`pipelines/gold.py`](pipelines/gold.py) publishes the three required
  analytical contracts with fail-fast input checks.

The detailed table grain, keys, and quality rules are documented in the
[logical data model](docs/LOGICAL_DATA_MODEL.md), [source quality contract](docs/SOURCE_SCHEMA_QUALITY_CONTRACT.md),
and [Gold contracts](docs/REQUIRED_GOLD_CONTRACTS.md).

The optional DQ-25 stakeholder layer is specified in the
[stakeholder exploration guide](docs/STAKEHOLDER_EXPLORATION.md). Its three
[dashboard dataset queries](sql/stakeholder/README.md) read only governed Gold
tables, and its acceptance query keeps the live Databricks build and evidence
as an explicit manual completion gate.

The DQ-26 [Gold access-control runbook](docs/GOLD_ACCESS_CONTROL.md) defines the
read-only analyst persona, exact Unity Catalog table grants, warehouse and
dashboard ACLs, positive reads, prohibited operations, teardown, and the live
separate-principal evidence gate. Its [security SQL](sql/security/README.md)
never grants schema-wide data access.

DQ-24 packages the three triggered pipelines and their ordered Bronze-to-Gold
refresh job as a version-controlled Databricks bundle. Landing remains a
separately governed single-writer prerequisite because independently deployed
jobs cannot safely serialize writes to the shared manifests and raw Volume. The
[bundle deployment runbook](docs/BUNDLE_DEPLOYMENT.md) records its external
governance prerequisites, isolated development target, authenticated validation
gate, reviewed plan requirement, landing prerequisite, update path, and guarded
teardown procedure. The [DQ-24 validation record](docs/evidence/dq24_bundle_deployment_validation.md)
captures the isolated deployment, review-driven isolation corrections, and
post-deployment Gold checks without claiming production deployment.

## Prerequisites

- A Databricks workspace with Spark Declarative Pipelines, Unity Catalog, and a
  writable managed Volume. Databricks Free Edition is sufficient.
- Permission to create a schema, Volume, manifest tables, and pipeline tables.
- A Databricks Git folder containing this repository.
- Outbound HTTPS access to the BLS and Data USA public endpoints.
- A valid contact email for the BLS request `User-Agent`. Enter it only in the
  notebook widget; do not commit it or any token, profile, or workspace URL.
- Python 3 for optional local contract tests; they use the standard-library
  `unittest` runner and require no third-party test package. Runtime pipeline
  modules require Databricks' `pyspark.pipelines` API and are not executed
  locally.

No Databricks access token is required by the checked-in code. The
[`.env.example`](.env.example) file contains public URLs, placeholder contact
text, and non-secret object-name defaults only.

## Configuration

The verified defaults are:

| Setting | Default | Where to set it |
| --- | --- | --- |
| Catalog | `workspace` | Landing notebook `catalog` widget; Bronze/Silver property `data_quest.catalog`; Gold target catalog |
| Schema | `rearc_data_quest` | Landing notebook `schema` widget; Bronze/Silver property `data_quest.schema`; every pipeline target schema |
| Managed Volume | `raw_landing` | Landing notebook `volume` widget; Bronze/Silver property `data_quest.volume` |
| BLS contact | none | `contact_email` widget in `notebooks/01_land_bls.py` |

Use simple Unity Catalog identifiers consisting of letters, numbers, and
underscores. If the defaults change, use the same object names in both landing
notebooks and the corresponding Bronze/Silver properties, and target every
pipeline at the configured catalog and schema. Keep the BLS
`allow_mass_removal` widget at `false` unless a confirmed provider-side removal
has been reviewed according to the [BLS landing runbook](docs/BLS_LANDING_RUNBOOK.md).

## Run the solution

Run the following from the repository's Databricks Git folder. The ingestion
workflow is deliberately single-writer, so do not execute two copies of one
landing notebook concurrently.

1. **Land BLS:** run all cells in
   [`notebooks/01_land_bls.py`](notebooks/01_land_bls.py). Supply the runtime
   `contact_email` widget and the configured catalog, schema, and Volume. The
   notebook discovers the complete directory, stages and verifies every object,
   promotes content-addressed bytes, and commits manifest transitions only
   after successful validation.
2. **Land population:** run all cells in
   [`notebooks/02_land_datausa_population.py`](notebooks/02_land_datausa_population.py)
   with the same object-name widgets. It validates and preserves the assigned
   JSON response and updates its independent manifest.
3. **Demonstrate idempotency:** immediately rerun both notebooks. With unchanged
   upstream content, expect zero promotions and zero new manifest transitions.
   See the [BLS](docs/BLS_LANDING_RUNBOOK.md) and
   [Data USA](docs/DATAUSA_LANDING_RUNBOOK.md) runbooks for exact evidence.
4. **Run Bronze:** configure a triggered Spark Declarative Pipeline whose source
   is [`pipelines/bronze.py`](pipelines/bronze.py), set the three
   `data_quest.*` properties above, and run an update.
5. **Run Silver:** configure or select the triggered pipeline whose source is
   [`pipelines/silver.py`](pipelines/silver.py), set the same three
   `data_quest.*` properties, and run it after Bronze succeeds.
6. **Run Gold:** configure or select the triggered pipeline whose source is
   [`pipelines/gold.py`](pipelines/gold.py), target the same catalog and schema,
   and run it after Silver succeeds. Confirm every update completes and inspect
   named expectation metrics in the pipeline UI.
7. **Validate parity:** run
   [`sql/quality/validate_bronze_to_silver.sql`](sql/quality/validate_bronze_to_silver.sql)
   and [`sql/quality/validate_gold_cross_implementation.sql`](sql/quality/validate_gold_cross_implementation.sql)
   in Databricks SQL. Every Gold validation row must report `passed = true`.

   For a non-default deployment, retarget every
   `workspace.rearc_data_quest` reference in the validation scripts and the
   three SQL alternatives to the configured catalog and schema. In the Gold
   validator, also replace `workspace.information_schema.columns` with the
   target catalog's `information_schema.columns` and each
   `table_schema = 'rearc_data_quest'` predicate with the deployed schema. Keep
   these substitutions aligned so schema checks and value checks inspect the
   same tables. The [quality SQL guide](sql/quality/README.md) records the full
   rule.

The pipeline implementation details and expected table counts are collected in
[`pipelines/README.md`](pipelines/README.md).

## Gold outputs and alternatives

| Question | Published Gold output | Primary | Independent alternative | Live evidence |
| --- | --- | --- | --- | --- |
| 1. US population mean and population standard deviation, 2013–2018 | `gold_population_summary_2013_2018` | [PySpark Gold](pipelines/gold.py) | [Spark SQL](sql/alternatives/question_1_population_summary.sql) | [DQ-16 validation](docs/evidence/dq16_gold_population_summary_validation.md) |
| 2. Best Q01–Q04 summed year for every BLS series, with readable labels | `gold_bls_best_year_by_series` | [PySpark Gold](pipelines/gold.py) | [Spark SQL](sql/alternatives/question_2_bls_best_year.sql) | [DQ-17 validation](docs/evidence/dq17_gold_bls_best_year_validation.md) |
| 3. `PRS30006032` Q01 history with nullable annual population | `gold_bls_q01_population` | [PySpark Gold](pipelines/gold.py) | [Spark SQL](sql/alternatives/question_3_bls_q01_population.sql) | [DQ-18 validation](docs/evidence/dq18_gold_bls_q01_population_validation.md) |

Question 2 deliberately excludes BLS `Q05`, which is an annual average rather
than a quarter, and resolves equal maxima to the earliest year. Question 3 uses
BLS history as the left side of the join so missing population context never
removes a valid observation. Cross-implementation reconciliation is preserved
in the [DQ-19 validation record](docs/evidence/dq19_gold_cross_implementation_validation.md).

## Verification and reviewer map

Run the local deterministic checks from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v
python -m compileall -q src pipelines notebooks tests
git diff --check
```

The local suite uses controlled fixtures and does not contact either provider.
Databricks runtime claims are supported separately by captured live evidence.

| Review need | Location |
| --- | --- |
| Curated pipeline, table, and Question 1–3 screenshots | [`docs/screenshots/README.md`](docs/screenshots/README.md#dq-21-curated-submission-set) |
| Detailed live-validation records and exported rows | [`docs/evidence/README.md`](docs/evidence/README.md) |
| Architecture, trade-offs, AI usage, corrections, retrospective | [`PROCESS.md`](PROCESS.md) |
| Acceptance-criteria traceability | [`REQUIREMENTS_CHECKLIST.md`](REQUIREMENTS_CHECKLIST.md) |
| Ingestion manifest semantics | [`docs/INGESTION_MANIFEST_CONTRACT.md`](docs/INGESTION_MANIFEST_CONTRACT.md) |
| Test scope | [`tests/README.md`](tests/README.md) |

The repository contains no credentials. Screenshot files intended for review
are cropped to exclude workspace hostnames, account email, operator identity,
and pipeline identifiers; their SHA-256 digests are recorded in the screenshot
index.
