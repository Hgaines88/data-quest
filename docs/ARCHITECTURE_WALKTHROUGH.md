# Architecture and interview walkthrough

## Audit outcome

The pre-submission explainability audit found no refactor that would improve
reviewability enough to justify regression risk before submission. The
production flow is already separated at meaningful boundaries: provider-aware
landing, source-shaped Bronze, typed and keyed Silver, and stakeholder-ready
Gold. Reliability controls are intentionally explicit because they protect
observable behavior and recorded evidence.

This document is the concise entry point. It supplements, rather than repeats,
the detailed contracts and runbooks linked below.

## System in one pass

1. [`notebooks/01_land_bls.py`](../notebooks/01_land_bls.py) discovers the full
   BLS directory and [`notebooks/02_land_datausa_population.py`](../notebooks/02_land_datausa_population.py)
   requests the assigned population response.
2. The landing libraries under [`src/data_quest/ingestion/`](../src/data_quest/ingestion/)
   stage and validate bytes, promote immutable content-addressed objects, and
   append manifest transitions only after a successful promotion. An unchanged
   rerun therefore performs no new publication.
3. [`pipelines/bronze.py`](../pipelines/bronze.py) joins raw objects to the
   latest active manifest state, checks source shape, and publishes
   source-faithful rows with provenance.
4. [`pipelines/silver.py`](../pipelines/silver.py) applies types, business keys,
   deduplication, provider-grounded labels, and population normalization.
5. [`pipelines/gold.py`](../pipelines/gold.py) publishes the three required
   analytical answers after fail-fast input checks. Independent SQL versions
   under [`sql/alternatives/`](../sql/alternatives/) provide a second
   implementation for reconciliation.
6. The dashboard and Genie space consume governed Gold outputs. Read-only SQL
   checks expose freshness, update state, exact output counts, and expectation
   results without creating another writer.

## Why the design is trustworthy

- **Retry and idempotency:** immutable objects plus append-only manifest state
  distinguish new, changed, skipped, failed, and removed inputs.
- **Failure containment:** downloads are staged and verified before promotion;
  pipeline expectations block structurally invalid or ambiguous publication.
- **Reconciliation:** Bronze-to-Silver checks and independent Gold SQL
  alternatives confirm both record handling and final values.
- **Governance:** the analyst persona receives read-only access to the intended
  Gold surface, while landing remains a separately governed single writer.
- **Recovery:** operators diagnose the recorded layer state and rerun from the
  last trustworthy boundary instead of silently editing data.

## Complexity judgment

The audit distinguishes necessary complexity from optional cleanup:

| Area | Judgment | Reason |
| --- | --- | --- |
| Provider-specific landing and manifest transitions | Keep | BLS directory ingestion and Data USA JSON have different contracts, while shared helpers already isolate download, landing, manifest, and observability concerns. |
| Separate Bronze, Silver, and Gold pipeline modules | Keep | The files are long but preserve layer ownership, deployment boundaries, and an easy-to-follow execution order. Splitting individual table declarations into more modules would add navigation without changing responsibility. |
| Explicit expectations and recovery branches | Keep | The apparent repetition makes quality, failure, and publication rules visible in the Databricks graph and event log. |
| Repeated catalog and schema references in reviewer SQL | Defer | Explicit names make standalone queries easy to run and review. Parameterization is worthwhile only if another deployment target becomes a maintained product requirement. |
| Repeated notebook configuration setup | Defer | A shared wrapper could reduce lines, but it would hide runtime widgets and introduce another import boundary immediately before submission. |
| Repeated event-log query scaffolding | Defer | The operational statements are intentionally independent so one unavailable layer cannot hide evidence from the others. Consolidate only if Databricks exposes a stable shared operational abstraction. |

These deferred items are cleanup opportunities, not known correctness defects.
They should be reconsidered only with a narrow issue, a tested baseline, and a
specific maintenance or user benefit.

## Interview-ready explanation

> I built the solution as a single-writer landing workflow followed by separate
> Bronze, Silver, and Gold Databricks pipelines. Landing preserves immutable
> provider bytes and records state transitions, so retries are auditable and
> unchanged reruns are no-ops. Bronze verifies source shape and provenance;
> Silver establishes types, keys, labels, and uniqueness; Gold answers the
> three business questions behind fail-fast input checks. I implemented each
> Gold answer a second time in Spark SQL and reconciled the results. A governed
> dashboard and Genie space read only Gold, while operational queries expose
> freshness, failures, expectations, and recovery state. I kept the safety
> controls explicit because simplifying them away would make the system shorter
> but less trustworthy.

## Detailed references

| Question | Detailed source |
| --- | --- |
| What are the components and ownership boundaries? | [`SYSTEM_UML.md`](SYSTEM_UML.md) |
| What are the grains, keys, and relationships? | [`LOGICAL_DATA_MODEL.md`](LOGICAL_DATA_MODEL.md) |
| How does ingestion remain safe on rerun? | [`INGESTION_MANIFEST_CONTRACT.md`](INGESTION_MANIFEST_CONTRACT.md) |
| What does each layer accept and reject? | [`SOURCE_SCHEMA_QUALITY_CONTRACT.md`](SOURCE_SCHEMA_QUALITY_CONTRACT.md) |
| What are the three required outputs? | [`REQUIRED_GOLD_CONTRACTS.md`](REQUIRED_GOLD_CONTRACTS.md) |
| How is failure diagnosed and recovered? | [`OPERATIONAL_OBSERVABILITY.md`](OPERATIONAL_OBSERVABILITY.md) |
| What passed in the integrated validation? | [`END_TO_END_VALIDATION.md`](END_TO_END_VALIDATION.md) and [`evidence/dq28_end_to_end_validation.md`](evidence/dq28_end_to_end_validation.md) |
| What trade-offs and corrections were made? | [`../PROCESS.md`](../PROCESS.md) |

