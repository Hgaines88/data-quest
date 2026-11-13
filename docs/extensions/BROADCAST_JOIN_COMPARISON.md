# Broadcast Join Comparison

## Status and boundary

**Status: Live validated in Databricks serverless on November 12, 2026.**

This is a post-submission portfolio extension. It does not modify the submitted
assessment, its governed tables, or its recorded claims. The notebook uses two
controlled DataFrames and does not read or mutate landing, Bronze, Silver,
Gold, manifest, or ingestion-audit state.

## The comparison

The notebook builds a 120-row fact input in four requested partitions and a
three-row dimension input in two requested partitions. It evaluates two paths:

1. **Ordinary optimizer selection:** call `join` and allow Spark to select a
   physical strategy from its statistics and runtime rules.
2. **Explicit broadcast:** wrap the dimension with `broadcast()` to state that
   it is small enough to replicate to workers.

Both paths use the same left-join keys, inputs, and independently calculated
expected summaries. The final assertions require each path to match the literal
expectation and require parity between the paths.

## Why broadcast can help

A conventional distributed join may need to repartition both inputs by their
join key so matching records reach the same workers. If one side is reliably
small, broadcasting can copy that side to every participating executor and
avoid shuffling the larger input. That can reduce network transfer and remove a
large shuffle boundary.

Spark may choose a broadcast join automatically when its statistics indicate
that an input is sufficiently small. Therefore, ordinary optimizer selection
and explicit broadcast may produce the same observed physical strategy in this
controlled example. The explicit hint communicates engineering intent; the
physical plans reveal what this environment actually selected. Strategy choice
is environment-specific rather than a portable promise.

## Why broadcast can hurt

Every participating executor needs memory for the broadcast relation. A table
that is larger than expected, badly estimated, or multiplied across many
concurrent workloads can create executor memory pressure or failure. Broadcast
is not a universal speed switch. The decision should be supported by measured
size, reliable statistics, expected growth, executor capacity, and concurrency.

## How to run it

1. Pull the `codex/spark-extension` branch into the Databricks Git folder.
2. Open `notebooks/extensions/06_broadcast_join_comparison.py`.
3. Attach Databricks serverless notebook compute—not a SQL warehouse.
4. Run all cells.
5. Confirm both summaries match the independent expected results and
   `result_parity` is `True`.
6. Compare the standard and explicit physical-plan sections.
7. Record the selected join operator, exchange nodes, partition profiles, and
   evidence available through each command's **See performance** link.

## Evidence to capture

| Evidence | Expected boundary | Live result on Databricks serverless |
| --- | --- | --- |
| Runtime | Record the environment used for the observation | Spark 4.2.0 with Photon; both queries were fully supported by Photon |
| Fact input | 120 rows; four requested partitions | 120 rows; four observed partitions with 30 rows each |
| Dimension input | Three rows; two requested partitions | Three rows; observed partition occupancy of one and two rows |
| Standard strategy | Selected by this runtime | `PhotonBroadcastHashJoin`, left outer, `BuildRight`; Spark automatically broadcast the dimension |
| Broadcast strategy | Inspect the effect of the explicit hint | The analyzed plan contained `ResolvedHint (strategy=broadcast)` and the optimized plan contained `rightHint=(strategy=broadcast)`; the physical operator was the same `PhotonBroadcastHashJoin` |
| Exchanges | Identify which side moved | The right side used `EXECUTOR_BROADCAST` and a `SinglePartition` exchange; the four-way fact range remained the streamed side |
| Result parity | Both paths match the literal expected summaries | Passed: A = 40 / 2380.0, B = 40 / 2420.0, C = 40 / 2460.0 for both paths |
| Adaptive plan state | Distinguish initial evidence from a final adaptive plan | Both captures reported `AdaptiveSparkPlan isFinalPlan=false`; these are initial physical plans |

## Reading the live plans

The standard join is the most important observation. Although the code supplied
no broadcast hint, Spark recognized that the three-row dimension was small and
selected a right-side `PhotonBroadcastHashJoin`. Its physical plan prepared the
dimension through an `EXECUTOR_BROADCAST` stage and a `SinglePartition`
exchange. The 120-row fact input remained the streamed side with four range
splits; the plan did not repartition that larger side by the join key.

The explicit path made the request visible earlier in planning. Its parsed plan
contained an unresolved broadcast hint, the analyzed plan resolved that hint,
and the optimized plan retained it as a right-side strategy hint. The final
physical operator was nevertheless the same one Spark had already chosen for
the ordinary path.

This is not evidence that the hint made the query faster. It shows that the
optimizer already made the appropriate decision for these controlled sizes,
while the explicit call documented an engineering choice. Both plan captures
reported `isFinalPlan=false`, so they record the initial adaptive plan rather
than claiming what every future execution will finalize.

## What this proves

The experiment proves that both observed join paths preserve the required
results for these controlled inputs. In this Databricks runtime, both paths used
a right-side Photon broadcast hash join, and only the explicit path carried a
broadcast hint through logical optimization. The evidence also shows the input
partition occupancy and the exchange used to prepare the small relation.

## What this does not prove

The experiment does not prove that broadcast is always faster, that a fixed
size threshold is safe for every cluster, or that the same ordinary strategy
will be selected in another environment. It is not a production benchmark.
Those claims require representative data volumes, concurrency, memory, network,
and repeated timing measurements.

## Practice aloud

> I use identical controlled inputs and reconcile both outputs against a
> separate literal expectation. The standard path lets Spark choose, while the
> second path explicitly broadcasts the three-row dimension. Broadcasting can
> avoid shuffling the larger fact input, but every executor must hold a copy of
> the smaller side. That makes measured size and growth part of the correctness
> decision, not merely performance tuning. I inspect both plans because the
> ordinary path may already broadcast in this environment.
