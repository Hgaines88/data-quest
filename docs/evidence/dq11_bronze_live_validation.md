# DQ-11 Bronze live-validation evidence

## Validated revision and runtime

- Git revision: `0b2c7f3cfb12ccc8c0ccbe0a1b352ba666ed7993`
- Databricks pipeline: `data-quest-bronze`
- Pipeline ID: `4de1f2d5-b749-4995-bec7-24ffa7cb8db0`
- Triggered update start: 2026-10-18 5:46 PM EDT
- Final update status: `Completed`
- Reported update issues: 0 errors, 0 warnings

The completion screen is preserved as
[`dq11_bronze_run_completed.png`](../screenshots/dq11_bronze_run_completed.png).
Its SHA-256 digest is
`1e06e0e4f8680d3cafbc6c1b73ba018cbe88dd2d8a26358df65fcb70f1e42a7a`.

## Published tables and expectations

The update-details screen is preserved as
[`dq11_bronze_tables_expectations.png`](../screenshots/dq11_bronze_tables_expectations.png).
Its SHA-256 digest is
`84f999ca179c6e7560999467ea03a2f33495d25b592603a298b712aaddde4bc4`.

| Materialized view | Displayed output records | Expectations |
| --- | ---: | ---: |
| `bronze_bls_class` | 2 | 5 met |
| `bronze_bls_duration` | 3 | 5 met |
| `bronze_bls_footnote` | 1 | 5 met |
| `bronze_bls_measure` | 22 | 5 met |
| `bronze_bls_observation_all` | 77K | 7 met |
| `bronze_bls_observation_current` | 38K | 7 met |
| `bronze_bls_period` | 5 | 5 met |
| `bronze_bls_seasonal` | 2 | 5 met |
| `bronze_bls_sector` | 6 | 5 met |
| `bronze_bls_series` | 282 | 14 met |
| `bronze_datausa_population` | 11 | 7 met |
| `bronze_source_contract_audit` | 11 | not applicable |

`77K` and `38K` are the abbreviated counts displayed by the Databricks UI; this
record does not claim more precise counts than the captured evidence. The two
temporary verification views display three defined expectations each and do
not publish output tables themselves.

## What this proves

The captured update proves that the target Databricks runtime compiled the
pipeline graph, resolved the Unity Catalog source paths, enforced the displayed
expectations, and published every required DQ-11 Bronze materialized view. In
particular, both observation views completed after the line-oriented reader
replaced the whole-file array/explode path that had exhausted executor memory.

This evidence closes DQ-11 only. It does not prove the typed, deduplicated
Silver behavior assigned to DQ-12 and later work.
