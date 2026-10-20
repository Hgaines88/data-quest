# DQ-24 Databricks bundle deployment validation

## Scope

This record covers the isolated `dev` target of the DQ-24 Databricks bundle.
It contains no workspace URL, user email, access token, BLS contact value,
resource identifier, or request identifier. Production was not deployed.

The validated bundle manages four workspace resources:

- one ordered refresh job;
- one triggered serverless Bronze pipeline;
- one triggered serverless Silver pipeline; and
- one triggered serverless Gold pipeline.

The existing catalog, source schema, raw Volume, warehouse, dashboard, identity
groups, grants, and manually verified pipelines remain outside bundle state.
Development pipeline outputs are isolated per deployer in a schema resolved
from `workspace.current_user.short_name`; no personal resolved name is retained
in this record.

## Local and authenticated gates

Validation used Databricks CLI 1.21.0 on 2026-10-20.

- `git diff --check`: passed.
- Python compilation: passed.
- Local unit and contract suite: 185 tests passed.
- `databricks bundle validate --target dev`: `Validation OK!`.
- Initial reviewed plan: four creates, zero changes, zero deletions.
- Isolation correction plan: three pipeline updates, zero deletions.
- Job compatibility correction plan: one job update, zero deletions.
- Final review correction plan: four updates, zero additions, zero deletions.
- Final convergence plan: four unchanged resources, zero pending changes or
  deletions.

The final deployed summary contained exactly the refresh job and the three
layer pipelines named above.

## Corrections established by live deployment

The first create attempt failed before resource creation because serverless
pipelines cannot explicitly disable Photon. Only bundle files were synchronized
to the isolated user bundle path. The `photon: false` overrides were removed,
validation and plan were repeated, and all four resources were then created.

Before running data work, a post-deploy review found that resource-name
isolation did not by itself isolate pipeline output tables. The pipeline target
schema was separated from the existing source schema, an empty dedicated
development schema was provisioned, and the three pipeline resources were
updated. No data run occurred against the shared output tables.

The first refresh run failed before notebook execution because Free Edition
rejected deprecated `client: "1"` as an unsupported REPL channel. Every
downstream task was skipped. The deprecated environment block was removed;
serverless notebook tasks now omit a cluster definition as supported by the
current Databricks bundle contract. Validation and plan were repeated before
the single job update.

## Superseded five-task trial

An intermediate refresh ran on 2026-10-20 with mass-removal protection disabled
and the BLS contact supplied only as a runtime parameter. The job and all five
tasks reported `TERMINATED/SUCCESS`:

1. `land_bls`;
2. `land_population`;
3. `refresh_bronze`;
4. `refresh_silver`; and
5. `refresh_gold`.

This historical run proved the then-deployed dependency chain could execute,
but it does not validate the final configuration. A later review correctly
found that `max_concurrent_runs: 1` serializes only one job and cannot prevent
another user's or target's deployment from writing the same manifests and raw
Volume. The final bundle therefore excludes both landing tasks and treats
landing as a separately governed, single-authorized-writer prerequisite.

The same review found that a fixed development schema isolated development from
production but not one developer from another. The final development target
derives its output schema from `workspace.current_user.short_name`.

## Final corrected run

The corrected configuration was authenticated, planned, and deployed on
2026-10-20. The deployment updated exactly the refresh job and three pipelines,
created and deleted no bundle resources, and deleted no synchronized files.
The refresh job contained only the following ordered tasks, each of which
reported `TERMINATED/SUCCESS`:

1. `refresh_bronze`;
2. `refresh_silver`; and
3. `refresh_gold`.

The development output schema resolved from the authenticated current user's
short name and was distinct from both the shared source schema and the prior
fixed development schema. No landing notebook was scheduled or executed by the
bundle. A post-run plan reported zero additions, zero changes, zero deletions,
and four unchanged resources.

## Isolated output validation

A read-only integrity query against the per-user development schema returned:

| Gold contract | Row count | Invalid rows |
| --- | ---: | ---: |
| `gold_population_summary_2013_2018` | 1 | 0 |
| `gold_bls_best_year_by_series` | 282 | 0 |
| `gold_bls_q01_population` | 39 | 0 |

The checks enforced the published population range and standard-deviation
semantics, complete-or-visibly-missing best-year contract, and exact Q01 series
identity with population match consistency. Successful fail-fast pipeline
updates provide the complementary expectation evidence.

## Unsupported or externally governed resources

The existing dashboard has no privacy-reviewed serialized dashboard source in
the repository, so bundle-managed dashboard deployment is not claimed. Its
manual build and Gold reconciliation remain evidenced by DQ-25. Warehouse and
dashboard ACLs, group membership, and Unity Catalog grants remain governed by
the DQ-26 runbook and were not imported into bundle state. DQ-28 must validate
these documented equivalents with the deployed data product rather than imply
that the bundle created them.
