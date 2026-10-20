# DQ-19 Gold cross-implementation validation

## Validation identity

- Git revision: `8e9f91bb724029ef7fcbcb9bbb3cc68bac640e7e`
- Branch: `codex/dq-19-cross-validation`
- Query: `sql/quality/validate_gold_cross_implementation.sql`
- Validated on: October 19, 2026

The operator switched the Databricks Git folder to the reviewed DQ-19 branch
before opening and running the tracked validation query. The screenshots show
the branch context, query name, successful execution, and result rows. They do
not independently prove the remote commit identity.

## Live validation outcome

After the final review fixes, the read-only query completed
successfully at 5:15 PM EDT in 35.092 seconds, returned exactly 17 checks, and
displayed `passed = true` for every check. The editor displayed a green
execution status, no query error, and 111 of 111 completed execution tasks.

The checks cover all three required Gold questions:

- Question 1: ordered schema, one-row key/cardinality contract, inclusive
  2013–2018 bounds, population-standard-deviation semantics, independent
  six-row source calculation, and value equality using an absolute `1e-6`
  tolerance only for DOUBLE mean and standard deviation.
- Question 2: ordered schema, 282-row governed-series inventory, unique
  `series_id` keys, null-safe exact values, deterministic earliest-year
  tie-breaking, and an independent four-quarter source check for
  `PRS30006032` in 1994.
- Question 3: ordered schema, 39-row BLS history, unique `series_id + year`
  keys, exact nullable values and match flags, 1988–2026 source preservation,
  and an independent representative source check.

## Observed results

| Question | Check count | Result |
| --- | ---: | --- |
| Question 1 | 5 | All passed |
| Question 2 | 6 | All passed |
| Question 3 | 6 | All passed |
| **Total** | **17** | **All passed** |

Representative displayed values include one Question 1 result row, 282
Question 2 rows and unique keys, and 39 Question 3 rows and unique keys. All
value-mismatch and source-spot-check discrepancy counts are zero. The Question
2 inventory result `282,0` proves 282 published rows and zero series without
exactly one metadata record. The Question 3 sample result `5,5,0` proves all
five documented years exist in both inputs with zero mismatches, while its
preservation check reports matching `39,39,1988,2026` actual and expected
values.

The three schema checks display analyzed `struct<...>` signatures derived from
the SQL result CTEs and matching ordered signatures reconstructed from the
published Gold metadata. This directly validates the post-review change that
removed fixed SQL-side schema constants.

## Intentional representation differences

The primary outputs are governed PySpark materialized views, while the SQL
implementations are ephemeral reviewer-visible CTE calculations. Storage order
is not treated as data; deterministic keys and the explicit Question 2
tie-break rule are validated instead, and presentation queries may use
`ORDER BY`. Question 1 uses DOUBLE aggregates and therefore the documented
absolute tolerance of `1e-6`. Question 2 DECIMAL values and Question 3 DECIMAL,
nullable population, and boolean fields are compared exactly and null-safely.

## Evidence files

| Screenshot | SHA-256 |
| --- | --- |
| `dq19_post_review_passed_rows_1_14.png` | `ab85bc9a58da6c104b33fd9c983098a37817de8fa13e71626f835fa91936fdfb` |
| `dq19_post_review_passed_rows_4_17.png` | `78d41cfbc11c6ee1bac1b03fe4d8bf188b86667995393a6409e920c8afa0bec5` |
| `dq19_post_review_values_rows_1_14.png` | `02f400b2eaab6d3c03ea7f67388e1037656d3b827c1b327952d3a2efb6fbde31` |
| `dq19_post_review_values_rows_4_17.png` | `30c85a19310306b7242e9d828d9e846e9bee84a79602976c022430d16c140022` |
| `dq19_post_review_performance.png` | `8918d29c5204b5ab5bd7d33639fa8205c3818153e3a0246cfdc4f7297a9014b8` |

The earlier `dq19_validation_*` and `dq19_final_*` captures are retained as
review history for the pre-review and first corrected implementations. The
`dq19_post_review_*` captures above are the authoritative evidence for the
final reviewed revision.

## Contract gate

The live 17-check result confirms that the three contracts in
`docs/REQUIRED_GOLD_CONTRACTS.md` are complete and mutually reconciled for the
validated snapshot. This satisfies the Gold validation gate before dashboard
or Genie implementation. It validates data contracts and implementation
equivalence; it does not make causal claims or validate future presentation
layers.
