# Repartition and coalesce comparison

**Status:** Awaiting live validation in Databricks.

This is a post-submission Spark extension. It uses generated records and does
not read or mutate the submitted landing, Bronze, Silver, Gold, manifest, or
audit state.

## Question

How do `repartition()` and `coalesce()` differ when reducing partitions, and
what evidence distinguishes reducing partitions from rebalancing data?

## Controlled experiment

Both operations run from the same controlled baseline: 120 deterministic rows
created across four input partitions. The experiment derives two paths:

1. `repartition(2, "group_key")` requests two partitions organized by key.
2. `coalesce(2)` requests two partitions by collapsing existing partitions.

For the source and both derived paths, the notebook captures non-empty
partition occupancy with `spark_partition_id()`. It prints extended plans,
calculates the same grouped counts and sums, and reconciles all three outputs
against one independent expected object. Exact result parity protects the
comparison from confusing a physical-layout change with a business-result
change.

## Expected execution behavior

`repartition()` introduces a full shuffle because records must be redistributed
to satisfy a new partitioning requirement. When a key is provided, records with
the same key are brought together, but the requested partition count does not
guarantee balanced partition occupancy when keys are skewed or hash placement
is uneven.

`coalesce()` is normally a narrow reduction: it combines existing partitions
without redistributing every record through a full shuffle. That makes it less
expensive for modest reductions, but it also preserves more of the prior data
shape. It is not a rebalancing operation and can leave uneven or oversized
partitions.

The live run should confirm these expectations from the actual physical plans.
The plan evidence is authoritative for that runtime; the prose is not a
substitute for inspection.

## Operational guidance

Use `coalesce()` when reducing partitions after filtering or before writing a
smaller result and the existing distribution is already acceptable. It can help
reduce small files without paying for a full shuffle. It becomes unsafe or
inefficient when the reduction collapses too much work onto too few executors,
preserves skew, creates oversized output files, or removes useful parallelism.

Use `repartition()` when the workload needs rebalancing, a different partition
count, or key-aligned distribution before a wide operation or write. Its full
shuffle has network, serialization, and spill costs, so it is inefficient when
the existing layout is already suitable or the downstream work is too small to
recover that cost.

Neither operation should be selected from row count alone. Data volume, key
cardinality, skew, target file size, available parallelism, downstream access
patterns, and observed task behavior all belong in the decision.

## Evidence to capture during live validation

- source, repartitioned, and coalesced partition occupancy;
- the shuffle exchange in the repartition physical plan;
- the narrow coalesce operator without a corresponding full shuffle;
- exact row-count and value parity across all three paths;
- Photon and Adaptive Query Execution details shown by the runtime;
- any difference between requested partitions and observed non-empty ones.

## What this proves

After live validation, this experiment can prove how one Databricks runtime
executed these two controlled partition changes and that both preserved the
expected analytical result.

## What this does not prove

It does not prove that either operation is universally faster, that two
requested partitions will be evenly occupied, or that this tiny generated
dataset predicts production performance. Local contract tests validate the
experiment's controls and documentation; they do not replace live Spark plan
and task evidence.

## Practice explanation

“I compared `repartition` and `coalesce` from the same four-partition baseline.
Both produced the same verified result, but they solve different physical
problems. Repartition performs a full shuffle to redistribute data and is the
choice when I need rebalancing or key-based organization. Coalesce narrowly
reduces partitions with less movement, which is useful for reducing small files
when the existing shape is acceptable. It can preserve skew and reduce
parallelism, so I inspect partition occupancy and the physical plan rather than
assuming the requested count created a balanced layout.”
