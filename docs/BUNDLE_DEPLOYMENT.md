# Databricks bundle deployment

## Scope and ownership boundary

The DQ-24 bundle deploys versioned workspace code, three triggered serverless
pipelines, and one downstream refresh job. The job preserves the layer order:

1. refresh Bronze;
2. refresh Silver; and
3. refresh Gold.

The bundle deliberately does not schedule the two landing notebooks. Landing
writes shared manifests and immutable Volume objects under an explicit
single-writer contract, while independent bundle deployments create separate
jobs. A per-job concurrency limit cannot serialize those shared writes across
users or targets. Operators must complete the BLS and Data USA landing runbooks
through the one authorized landing writer before running this downstream job.

The bundle does **not** claim ownership of the existing `workspace` catalog,
`rearc_data_quest` schema, `raw_landing` managed Volume, Serverless Starter
Warehouse, published dashboard, identity groups, or Unity Catalog grants.
Those shared objects predate DQ-24 and are deliberately retained as external
prerequisites so `bundle destroy` cannot remove governed data or access policy.
The landing notebooks create the schema and Volume idempotently when the
deploying identity is authorized, but operators should provision and govern
them independently before a production run.

The existing dashboard was created in the Databricks UI and no privacy-safe
serialized dashboard source has yet been exported. It therefore remains an
explicitly documented manual resource rather than an invented bundle resource.
DQ-28 must either add and validate an exported dashboard definition or retain
this Free Edition limitation without claiming bundle-managed dashboard
deployment. DQ-26 remains the authoritative runbook for analyst group, table,
warehouse, and dashboard permissions.

## Configuration

The bundle pins Databricks CLI `>= 1.21.0` and exposes only non-secret object
names as bundle variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `catalog` | `workspace` | Unity Catalog catalog |
| `schema` | `rearc_data_quest` | Existing source schema containing manifests and the managed Volume |
| `output_schema` | `rearc_data_quest` | Pipeline output schema; overridden per user in development |
| `volume` | `raw_landing` | Managed landing Volume |

Do not place a Databricks host, token, personal workspace path, or BLS contact
email in tracked configuration. Authentication belongs in a Databricks CLI
profile or environment supported by the CLI. The BLS contact remains a
runtime-only input to the separately governed landing notebook.

The `dev` target is the default. Development mode isolates resource names and
stores synchronized files beneath the current user's bundle root. It also
publishes pipeline outputs to
`rearc_data_quest_dq24_${workspace.current_user.short_name}`. The resolved
short name also prefixes development resource names, so separate users do not
manage pipelines that publish the same tables. Bronze reads manifests and raw
objects from the existing `rearc_data_quest` source schema. Provision the
resolved user-specific development schema before the first pipeline update and
remove it separately only after its tables are no longer needed. The `prod`
target uses a shared bundle root and the governed project schema; it must not be
deployed until its plan has been reviewed and any intended binding to existing
resources has been decided.

## Validate and inspect

From the repository root with Databricks CLI 1.21.0 or newer:

```bash
databricks schemas get workspace.rearc_data_quest_dq24_<short-name>
# Create only when the preceding command confirms it is absent.
databricks schemas create rearc_data_quest_dq24_<short-name> workspace \
  --comment "Isolated DQ-24 development pipeline outputs"
databricks bundle validate --target dev
databricks bundle plan --target dev
```

Validation proves that the local configuration conforms to the CLI schema and
that substitutions resolve for the authenticated target. It does not create or
update workspace resources. Review the plan before every deployment; stop if it
would replace, delete, or take ownership of an existing shared object.

## Deploy and run

Deploy the isolated development target first:

```bash
databricks bundle deploy --target dev
databricks bundle summary --target dev
databricks bundle run --target dev refresh
```

Before this command, execute the BLS and Data USA landing runbooks through the
single authorized writer. Never run independent landing notebooks concurrently.
Keep `allow_mass_removal=false` unless the BLS removal procedure in
`docs/BLS_LANDING_RUNBOOK.md` has been explicitly authorized.

After a successful run, confirm all three job tasks succeed, the three pipeline
updates report no errors, named expectations are visible, and the existing SQL
reconciliation checks still pass. Record live results separately; checked-in
configuration alone is not deployment evidence.

## Update, recovery, and teardown

Use the same reviewed target to apply an update:

```bash
databricks bundle plan --target dev
databricks bundle deploy --target dev
```

Pipeline reruns are designed to be deterministic against the current committed
manifest state. Investigate a failed task before rerunning downstream work; do
not bypass the dependency chain. Landing recovery remains governed by the two
source-specific runbooks and their single-writer rule.

Destroy only an isolated bundle deployment after reviewing the plan and
confirming that no shared object was imported or bound into its state:

```bash
databricks bundle destroy --target dev
```

Bundle teardown intentionally leaves the externally provisioned development
schema in place. Inspect its contents first; delete it separately only when it
contains no evidence or output that must be retained:

```bash
databricks schemas get workspace.rearc_data_quest_dq24_<short-name>
databricks schemas delete workspace.rearc_data_quest_dq24_<short-name>
```

The externally managed catalog, schema, Volume, warehouse, dashboard, groups,
and grants are outside bundle state and must remain intact. Production teardown
requires a separate change review and must follow the DQ-26 revocation runbook
for access-policy changes.
