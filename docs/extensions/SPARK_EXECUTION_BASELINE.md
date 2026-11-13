# Spark Execution Baseline

## Status and boundary

**Status: Live validation passed on Databricks serverless on November 12, 2026.**

This is a post-submission portfolio extension. It does not modify the submitted assessment, its governed tables, or its recorded claims. The baseline notebook uses controlled in-memory records and does not read or mutate landing, Bronze, Silver, Gold, manifest, or ingestion-audit state.

The repository's local source and contract tests require Python 3.10 or newer.
The Spark workload itself must run in the authorized Databricks environment,
where PySpark, the cluster runtime, the physical plan, and the Spark UI are
available.

## The baseline question

What changes inside Spark when a DataFrame moves from a row-local filter to a
keyed `groupBy` aggregation, and what evidence can distinguish planning from
execution?

The notebook deliberately separates three moments:

1. Create a partitioned DataFrame from fixed records through `spark.range`.
2. Declare a filter and aggregation without requesting results.
3. Call `collect()` on the tiny aggregate result to trigger execution.

## Mental model

- The **driver** runs the application control flow, constructs the query plan,
  and coordinates work. Databricks serverless exposes the supported DataFrame
  session boundary without permitting direct `SparkContext` or RDD access.
- **Executors** are application processes that run tasks and can retain data in
  memory or on disk.
- Transformations are **lazy**: they describe a result without immediately
  computing it.
- An action such as `collect()` creates a **job**. In this controlled example,
  collecting two aggregate rows is safe; collecting an unbounded dataset would
  put unsafe pressure on the driver.
- Spark divides a job into one or more **stages** separated by dependencies that
  require data redistribution.
- Each **task** processes one partition for its stage on an executor.
- The filter is narrow because an output record depends only on its existing
  input partition.
- The keyed aggregation is wide because values for one `series_id` may begin in
  different partitions. Spark requires a **shuffle** to bring like keys
  together before producing the totals.

Apache Spark's official cluster overview defines the driver, executor, job,
stage, and task roles. Its programming guide documents lazy transformations,
actions, and shuffle behavior:

- [Apache Spark cluster overview](https://spark.apache.org/docs/latest/cluster-overview.html)
- [Apache Spark RDD programming guide](https://spark.apache.org/docs/latest/rdd-programming-guide.html)

## How to run it

1. Pull the `codex/spark-extension` branch into the Databricks Git folder.
2. Open `notebooks/extensions/05_spark_groupby_baseline.py`.
3. Attach the notebook to Databricks serverless compute.
4. Run all cells once.
5. Confirm the final validation reports `passed` and the actual result matches:
   - Series A: two retained observations, sum `3.0`
   - Series B: three retained observations, sum `20.0`
6. Save the extended plan output.
7. Open the query profile and locate the aggregate command by notebook name and
   execution timestamp. Serverless does not expose `SparkContext.setJobGroup`.
8. Record the observed jobs, stages, tasks, partition counts, shuffle exchange,
   and any visible Adaptive Query Execution changes. Do not query restricted
   serverless configuration keys to infer them.

The extended `explain()` output contains parsed, analyzed, optimized, and
physical plan sections. The **physical plan** is the primary pre-execution
evidence for locating exchanges and the selected operators. The Spark UI is the
runtime evidence for the work that actually ran. Spark's official Web UI guide
describes its Jobs, Stages, Executors, and SQL/DataFrame surfaces:

- [Apache Spark Web UI](https://spark.apache.org/docs/latest/web-ui.html)

## Evidence to capture

| Evidence | Expected observation | Live result |
| --- | --- | --- |
| Spark version and interface | Printed from the active serverless runtime | Spark 4.2.0 through the serverless DataFrame API |
| Source partitions | Four requested input partitions; record observed non-empty occupancy | Four: row counts `1, 2, 2, 2` |
| Filtered partitions | Record observed occupancy after the narrow filter | Four: row counts `1, 1, 2, 1` |
| Physical plan | Keyed aggregation includes an exchange | `PhotonShuffleExchangeSink hashpartitioning(series_id, 16)` |
| Final result | Matches the independent literal expectation | Passed: A = `(2, 3.0)`; B = `(3, 20.0)` |
| Query profile | Aggregate command identified by notebook and timestamp | Available from the command's **See performance** link |
| Stages and tasks | Record observed counts; do not predict them as facts | Exact counts intentionally not asserted across runtimes |
| AQE | Record only evidence visible in the plan or query profile | Initial plan reported `AdaptiveSparkPlan isFinalPlan=false` |

## Annotated live plan

The captured physical plan provides the following evidence:

- `PhotonRange ... splits=4` confirms the four requested source partitions.
- `PhotonFilter` performs the row-local nonnegative-value filter before any
  redistribution.
- `PhotonGroupingAgg` appears on both sides of the exchange: Spark performs a
  partial aggregation before the shuffle and a final aggregation afterward.
- `PhotonShuffleExchangeSink hashpartitioning(series_id, 16)` is the direct
  evidence that the keyed `groupBy` introduces a shuffle boundary.
- `AdaptiveSparkPlan isFinalPlan=false` identifies the captured output as the
  initial adaptive plan; it does not prove what the final runtime plan became.
- The Photon explanation reported that the full query was supported by Photon.

Adaptive Query Execution can use runtime statistics to revise a Spark SQL
physical plan while a query runs. It may coalesce post-shuffle partitions, but
the actual behavior depends on runtime configuration and observed data. The
baseline requires inspection rather than assuming an outcome. Free Edition
serverless may not expose the underlying configuration key through
`spark.conf.get`, so the notebook does not depend on that access:

- [Apache Spark SQL performance tuning](https://spark.apache.org/docs/latest/sql-performance-tuning.html#adaptive-query-execution)

## What this proves

The successful live validation proves that the controlled DataFrame produces
the expected aggregates, that the declared `groupBy` requires a keyed
redistribution in the observed physical plan, and that the run exposes
performance evidence through the Databricks serverless command interface.

## What this does not prove

The small experiment does not benchmark production performance, guarantee a
fixed number of stages or tasks across runtimes, reproduce Data Quest's earlier
out-of-memory failure, or prove that one partition strategy is universally
optimal. Those claims require the later controlled experiments and their own
recorded evidence.

## Serverless compatibility correction

The first live run exposed a platform boundary before the aggregation executed:
Databricks serverless rejected direct `SparkContext` access. The corrected
notebook uses `spark.range(..., numPartitions=4)` to create the controlled
source, `spark_partition_id()` to observe non-empty partition occupancy, and
the query profile to inspect execution. It contains no direct `SparkContext`,
RDD, JVM, or restricted configuration access. This correction preserves the
experiment while treating the live runtime as evidence instead of assuming
dedicated-compute APIs were available.

## Practice aloud

> I request four small input partitions through the serverless-compatible
> DataFrame API. The filter is lazy and narrow, so
> each existing partition can decide which of its own rows survive. The
> `groupBy` is also declared lazily, but it introduces a wide dependency because
> every value for a series must reach the same key group. `collect()` is the
> action that starts the job. Spark divides that job into stages around the
> shuffle and sends one task per participating partition to executors. I inspect
> the physical plan before execution and the serverless query profile afterward
> because those are different kinds of evidence. Separate partition-profile
> actions then record actual non-empty occupancy without using RDD internals.
