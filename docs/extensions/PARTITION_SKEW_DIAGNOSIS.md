# Partition Skew Diagnosis and Mitigation

## Evidence boundary

This is a **post-submission** learning experiment. It does not read or modify the
submitted assessment's landing, Bronze, Silver, Gold, manifest, or audit state.
It uses controlled in-memory records so the cause of each execution shape is
known before Spark runs.

The controlled notebook was live validated on Databricks serverless compute on
November 12, 2026. Runtime-specific claims below are limited to the captured
partition profiles, extended plans, and reconciliation output from that run.

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

## Observed Databricks evidence

The live run reconciled the controlled inputs exactly:

- balanced key counts were `30 / 30 / 30 / 30`;
- the unsalted skewed partition profile was `4 / 4 / 4 / 108`; and
- the hot key divided into four equal 27-record salt buckets.

After salting, the non-empty physical partitions held 54, 58, and 8 records;
one of the four requested partitions was empty. The maximum observed partition
occupancy therefore fell from 108 to 58, a reduction of about 46 percent. This
is a meaningful improvement, but the salt buckets' downstream hash placement
did not guarantee equal physical partition occupancy. Salting increases the
number of partitioning keys; it does not promise that each salted key lands in
a different physical partition.

The unsalted physical plan contained a shuffle exchange using
`hashpartitioning(group_key, 4)`. The mitigated path first used
`hashpartitioning(group_key, salt_bucket, 4)` for partial aggregation and then
used `hashpartitioning(group_key, 16)` to recombine the partials. This confirms
the expected trade-off: lower concentrated pressure in exchange for an extra
shuffle and aggregation phase. Both plans were fully supported by Photon.

The observed plan was an adaptive initial plan (`isFinalPlan=false`), so it is
evidence of the planned execution shape rather than a claim that Adaptive Query
Execution could not revise the final runtime plan. The notebook's independent
assertions passed, `result_parity` was `True`, and both paths returned the same
counts and sums for every key.

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
- It does not establish how the same mitigation will behave at production scale
  or under a different Databricks runtime, partition count, or key distribution.

## Live validation record

1. `notebooks/extensions/07_partition_skew_diagnosis.py` completed on
   Databricks serverless compute.
2. Every assertion passed and `result_parity` was `True`.
3. Balanced, skewed, and salted partition occupancy was recorded above.
4. Extended plans confirmed the exchanges and partial/final aggregation phases.
5. The Spark performance profiles were exposed for follow-up task-level review.
6. Environment-specific qualifications and the adaptive-plan boundary are
   preserved in this guide.
