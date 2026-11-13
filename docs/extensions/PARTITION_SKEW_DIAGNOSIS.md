# Partition Skew Diagnosis and Mitigation

## Evidence boundary

This is a **post-submission** learning experiment. It does not read or modify the
submitted assessment's landing, Bronze, Silver, Gold, manifest, or audit state.
It uses controlled in-memory records so the cause of each execution shape is
known before Spark runs.

Live validation is still required in Databricks before runtime-specific claims
are promoted from expected behavior to observed evidence.

## Controlled distributions

The notebook builds two 120-row inputs:

- **Balanced:** four keys with 30 records each.
- **Skewed:** one hot key with 108 records while three cold keys receive four
  records each.

The notebook first reconciles exact key counts. It then repartitions by the
grouping key and records **partition occupancy** with
`spark_partition_id()`. The Databricks **Spark performance profile** provides
the task-level equivalent for the serverless environment: partition occupancy,
query duration, and the physical plan can be inspected together without direct
`SparkContext` access.

## Why skew is an execution risk

A shuffle must bring identical keys together. When one key owns most records,
one downstream partition can receive most of the work. That creates
**concentrated executor pressure** even when **total cluster capacity** appears
adequate. Adding memory everywhere may not fix a task whose individual
partition remains disproportionately large.

This experiment is deliberately small, so it demonstrates execution shape—not
an out-of-memory failure. Runtime, spill, and task-duration effects are
environment-specific and must be observed at representative scale.

## Mitigation: deterministic salting

The mitigation adds a deterministic `salt_bucket` to the hot key, repartitions
by key and salt, calculates partial aggregates, and then recombines those
partials by the original key. Assertions prove that:

1. the 108 hot-key records divide evenly across four salt buckets;
2. the unsalted result matches an independent expected result; and
3. the mitigated result is exactly equal to the unsalted result.

Salting trades a more even first aggregation for an **extra shuffle**, another
aggregation stage, higher intermediate key **cardinality**, and additional code
and operational **complexity**. It should be applied to measured hot keys—not
used as a universal default.

## Connection to the Data Quest correction

Data Quest previously exposed a related concentration problem in a different
form. **Whole-file parsing** placed an oversized unit of work behind one task,
producing a pathological memory shape. The correction used
**distributed line-oriented reading**, allowing Spark to divide the input instead of forcing
one task to hold the entire file. Both cases illustrate the same principle:
cluster-wide resources do not protect a single oversized task from concentrated
pressure.

## What this proves

- The balanced and skewed distributions are deterministic and reconciled.
- Repartitioning by a hot key produces measurable partition imbalance.
- Deterministic salting can distribute the hot key and preserve exact results.
- Logical and physical plans plus partition evidence provide a repeatable basis
  for diagnosis.

## What this does not prove

- It does not establish a universal partition-count or salting rule.
- It does not reproduce production volume, spilling, executor loss, or an
  out-of-memory event.
- It does not prove that salting is preferable to Adaptive Query Execution,
  source-side correction, different partitioning, or isolating hot keys in
  every workload.
- It does not turn local expectations into observed Databricks evidence until
  the notebook completes live validation and its performance output is reviewed.

## Live validation checklist

1. Run `notebooks/extensions/07_partition_skew_diagnosis.py` on Databricks
   serverless compute.
2. Confirm every assertion passes and `result_parity` is `True`.
3. Record balanced, skewed, and salted partition occupancy.
4. Inspect the physical plans for exchanges and partial/final aggregation.
5. Open each **Spark performance profile** and compare task-level evidence.
6. Add the observed runtime version and evidence to this guide; preserve any
   environment-specific qualification.
