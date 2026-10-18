# Project Conventions

This document records the working conventions for the Rearc Data Quest solution. Workspace-dependent values are recorded only after they are verified in the target Databricks environment.

## Repository layout

```text
.
├── docs/
│   └── screenshots/        # Reviewer evidence required by the assignment
├── notebooks/                  # Databricks orchestration and evidence notebooks
├── pipelines/              # Spark Declarative Pipeline definitions
├── sql/
│   └── alternatives/       # Spark SQL counterparts to PySpark logic
├── src/
│   └── data_quest/
│       ├── ingestion/      # Source discovery, downloads, and manifest logic
│       └── validation/     # Reusable reconciliation and contract checks
└── tests/                  # Local unit and contract tests
```

Reusable source-access and validation logic belongs under `src/data_quest` so it can be tested independently of Databricks. Current ingestion reconciliation is executed by the landing and manifest-validation notebooks; `src/data_quest/validation` is reserved for reusable Bronze, Silver, and Gold checks as those layers are implemented. Databricks pipeline definitions belong under `pipelines` so reviewers can find the platform entry points quickly. Required alternative Spark SQL implementations belong under `sql/alternatives`.

## Databricks object names

Initial names use lowercase `snake_case`:

- Schema: `rearc_data_quest`
- Raw Volume: `raw_landing`
- Raw BLS path: `/Volumes/<catalog>/rearc_data_quest/raw_landing/bls/productivity/`
- Raw population path: `/Volumes/<catalog>/rearc_data_quest/raw_landing/datausa/population/`

DQ-02 confirmed `workspace` as the writable Unity Catalog catalog in the target Free Edition environment. The catalog name remains configuration rather than being repeated throughout the code.

Because Free Edition capabilities may make multiple schemas unnecessary, the initial plan uses one schema and layer-prefixed tables:

- Bronze: `bronze_<source>_<entity>`
- Silver: `silver_<domain>_<entity>`
- Gold: `gold_<question_or_business_result>`

Candidate Gold table names are:

- `gold_population_summary_2013_2018`
- `gold_bls_best_year_by_series`
- `gold_bls_q01_population`

These names describe business results rather than implementation details. They may be refined after source profiling, but changes must be recorded in `PROCESS.md`.

## Configuration and secrets

- Public endpoint defaults may be committed in `.env.example`.
- Real email addresses, tokens, workspace hosts, profiles, and credentials stay in local environment variables or Databricks secrets and must never be committed.
- The BLS request `User-Agent` must identify the client and include valid owner contact information, but the committed example uses a placeholder.
- Databricks object names must be read from pipeline configuration or environment-specific settings rather than repeated throughout the code.

## Code and data conventions

- Python modules, functions, variables, columns, schemas, Volumes, and tables use lowercase `snake_case`.
- Constants use uppercase `SNAKE_CASE`.
- Raw files are preserved without content mutation; normalization begins in the Silver layer.
- Time values used for audit metadata are stored in UTC.
- Network operations use explicit timeouts, bounded retries, and status checking.
- Business keys, deduplication rules, null handling, and expectation actions must be documented before implementation.
- Gold outputs must be deterministic, including explicit tie behavior and stable ordering where appropriate.

## Git workflow

- One issue represents one reviewable outcome.
- Branch names use `codex/dq-<number>-<short-description>` while working with Codex.
- Commit messages describe the completed outcome, not the editing activity.
- A card moves to **Validate** only after its implementation is complete.
- A card moves to **Done** only after its acceptance criteria are checked and its work is committed.
- Required work takes priority over bonus enhancements.

## Evidence and AI usage

- Screenshots required for review belong in `docs/screenshots` with descriptive filenames.
- Screenshots must exclude tokens, private workspace identifiers, and unrelated personal information.
- Meaningful AI use is recorded incrementally in `PROCESS.md`, including the task, the resulting contribution, any correction, and the validation performed.
- Every submitted line must be understood well enough to explain during an interview.
