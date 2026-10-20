# Platform extension decision

## Decision

Stop with Databricks for this assessment. Do not add Snowflake or Power BI.

The implemented Databricks product already satisfies the current stakeholder,
governance, deployment, observability, and analytical requirements. Adding a
second platform would duplicate working capabilities without serving a named
consumer or closing a demonstrated requirement gap.

This decision does not claim that Snowflake or Power BI would never be useful.
It requires a specific user, unmet need, and proportionate operating model
before either platform is introduced.

## What Databricks already provides

| Need | Implemented response |
| --- | --- |
| Reproducible ingestion | Verified, content-addressed landing for BLS and Data USA with append-only manifests and idempotent reruns |
| Governed transformation | Bronze, Silver, and Gold Spark Declarative Pipelines with explicit contracts and lineage |
| Analytical answers | Three required Gold outputs with independent Spark SQL alternatives and cross-implementation reconciliation |
| Stakeholder consumption | Published Databricks dashboard datasets and a bounded Genie experience over governed Gold tables |
| Security | Unity Catalog read-only Gold access with positive and negative validation procedures |
| Deployment | A Databricks Asset Bundle for the three pipelines and their ordered refresh job |
| Operations | Source freshness, update health, contract counts, expectation metrics, controlled-failure evidence, and recovery guidance |
| Auditability | Source provenance, manifests, named expectations, validation SQL, automated tests, and curated evidence |

## Remaining gaps

No current assessment requirement is materially unsatisfied by Databricks.
The remaining work is final submission review and explanation, not an external
platform capability.

Possible future needs that could justify an extension include:

- an organization whose governed reporting standard requires Power BI;
- a consumer who cannot access the Databricks dashboard or Genie experience;
- an existing Snowflake estate that requires a supported interoperability path;
- a reusable enterprise semantic model owned outside Databricks; or
- a measured scale, concurrency, or governance constraint that the current
  architecture cannot address.

None of those conditions has been demonstrated for this project.

## Options considered

### Continue with Databricks only — selected

- Preserves one governed source of truth and the validated Gold contracts.
- Avoids another credential, storage, compute, deployment, and monitoring
  boundary.
- Keeps the architecture proportional to the assignment and explainable in an
  interview.
- Requires no new build or regression-validation cycle.

### Add Power BI — not selected

Power BI could be appropriate for a Microsoft-centered reporting audience or a
required enterprise semantic model. Here it would reproduce an existing
dashboard experience without a named consumer requirement. A credible build
would also require desktop authoring access (normally Windows), connectivity
and credential configuration, semantic-model and refresh design, publication
permissions, access testing, screenshots, and maintenance ownership.

Estimated incremental effort: at least one to two focused working days for a
small defensible implementation, excluding delays for Windows access,
credentials, licensing, or tenant approval.

### Add Snowflake — not selected

Snowflake could be appropriate when an existing Snowflake consumer or governed
data-sharing requirement exists. Here it would duplicate storage and compute,
introduce cross-platform transfer and reconciliation, and create additional
security, cost, deployment, freshness, and recovery responsibilities without
changing the required analytical result.

Estimated incremental effort: at least two to four focused working days for a
credible ingestion or sharing path, transformations or governed views,
security, reconciliation, operations, documentation, and review. Account,
network, credential, or cost approvals could extend that timeline.

## Cost and risk comparison

| Dimension | Databricks only | Add Power BI | Add Snowflake |
| --- | --- | --- | --- |
| New user value demonstrated | Yes | No | No |
| Additional credentials or permissions | None | Likely | Yes |
| Duplicated storage or compute | None | Possible import model and refresh | Yes unless a governed sharing pattern is available |
| Additional reconciliation boundary | None | Dashboard/model values and refresh | Transfer, transformation, and published values |
| Additional operational ownership | None | Dataset refresh and workspace access | Loads/shares, warehouse cost, freshness, and recovery |
| Regression and review burden | None | Moderate | High |

## Reuse boundary

The BLS and Data USA inputs are public sources, but that does not automatically
authorize reuse of assessment-specific repository content, screenshots,
workspace identifiers, credentials, or employer-provided material. This
submission remains within its authorized assessment context. Any later public
adaptation should be rebuilt from public source data, remove assessment- or
workspace-specific material, and proceed only after the applicable Rearc terms
have been confirmed.

## Reconsideration trigger

Reopen this decision only when a named consumer and a concrete requirement
cannot be served adequately by the validated Databricks product. The proposal
must identify the owner, user value, data boundary, security model, expected
cost, deployment path, operating responsibility, and acceptance test before
implementation begins.

