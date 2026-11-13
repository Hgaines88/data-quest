# Cache reuse comparison

**Status:** Live validated on Databricks serverless on November 12, 2026.

This is a post-submission Spark extension. It uses generated records and does
not read or mutate the submitted landing, Bronze, Silver, Gold, manifest, or
audit state.

## Question

When does repeated deterministic computation justify caching, and what evidence
distinguishes actual reuse from merely adding a `persist` call?

## Controlled experiment

The notebook runs the same deterministic computation through two paths:

1. Build a filtered input and execute its aggregation twice uncached.
2. Build the identical filtered input and persist it at `MEMORY_AND_DISK`.
3. Use `count()` as the explicit materialization action.
4. Execute the identical aggregation twice against the cached input.
5. Reconcile every result with an independent expected object and with the
   uncached result.
6. Call blocking `unpersist` in a `finally` block so cleanup occurs even if a
   validation fails.

The aggregation itself is intentionally repeated. The persisted object is its
filtered input, making the reuse boundary explicit rather than implying that
every downstream operation is cached.

## Evidence to inspect during live validation

Capture and compare:

- the uncached extended logical and physical plan;
- the cached extended plan after materialization;
- a cache-reuse operator such as `InMemoryTableScan`, or the Databricks
  serverless equivalent actually shown by the executed plan and query profile;
- both uncached and cached runtime observations;
- exact result parity across all four actions;
- the selected storage level and successful cleanup.

The runtime values are descriptive observations from one controlled run. They
are not a statistically valid benchmark. Query plans and the Databricks query
profile are stronger evidence of reuse than elapsed time alone.

## Live Databricks evidence — November 12, 2026

The controlled notebook completed successfully on Databricks serverless with
Photon. It materialized 60 filtered rows, produced exact result parity between
the cached and uncached paths, and reported the requested persisted DataFrame
as `Disk Serialized 1x Replicated`.

The uncached physical plan read from the generated `Range`, applied the filter,
and then performed the keyed aggregation. The cached physical plan instead read
a managed Parquet relation through `PhotonScan parquet`; its internal location
was represented by `PreparedDeltaFileIndex`. This is evidence that Databricks
serverless materialized and reused the persisted relation through a
serverless-specific disk-backed path. It is not evidence of a classic
`InMemoryTableScan`, and it should not be generalized to every Databricks or
dedicated-cluster runtime.

Both captured plans reported `AdaptiveSparkPlan isFinalPlan=false`. They are
therefore useful initial-plan evidence, not a claim about every final decision
Adaptive Query Execution may make while the query runs.

| Execution path | First observation | Second observation |
| --- | ---: | ---: |
| Uncached | 2.531449 seconds | 0.742856 seconds |
| Cached | 0.989433 seconds | 1.034268 seconds |

These four single-run observations are not a benchmark. The second uncached
execution was the fastest individual observation, so this small controlled
experiment does not establish that caching is faster. The timings demonstrate
why cache decisions require repeated measurement with representative workloads
rather than intuition alone.

The notebook completed its validation with result parity and then released the
persisted relation with `unpersist(blocking=True)`.

## Cache lifecycle and engineering trade-offs

Persistence is lazy: `persist` declares intent, while the materialization action
causes Spark to compute and store partitions. `MEMORY_AND_DISK` permits
partitions that do not fit in memory to spill to disk rather than requiring all
cached data to remain resident.

Caching is not an automatic optimization. It is most defensible when the same
expensive intermediate result is reused enough to offset computation, storage,
serialization, and cleanup costs. Important risks include:

- memory pressure competing with execution memory and other workloads;
- eviction, which can force Spark to recompute missing cached partitions;
- storage overhead for data that is cheap or rarely reused;
- stale cached results when upstream data changes but an old cache remains;
- operational ambiguity when ownership and `unpersist` behavior are unclear.

For production work, the reuse frequency, intermediate cost, dataset size,
cluster pressure, freshness contract, and cleanup owner should be explicit.

## What this proves

The live experiment proves that:

- the cached and uncached paths return identical deterministic results;
- the chosen runtime materialized and reused the persisted input when the
  executed evidence shows a cache operator;
- the notebook records bounded runtime observations and releases the cache.

## What this does not prove

This experiment does not prove that caching is always faster, that the same
benefit will appear at production scale, or that `MEMORY_AND_DISK` is the best
storage level for every workload. Local contract tests validate the notebook's
controls and documentation; they do not substitute for live validation of
Spark execution behavior in Databricks.

## Practice explanation

“I ran the same deterministic aggregation twice without persistence, then
persisted its filtered input at `MEMORY_AND_DISK`, explicitly materialized it,
and ran the same aggregation twice again. I reconciled all results and inspected
the executed plan and query profile for reuse. Databricks serverless represented
the persisted relation as a disk-serialized internal Parquet source. The timings
are observations, not proof that cache is automatically faster. Cache consumes
resources, may be evicted or become stale, and needs an explicit cleanup owner.”
