# DQ-19 Gold cross-implementation validation

## Validation identity

- Git revision: `eeaa0f522fe71a6c036024aa1f256358fce921f4`
- Branch: `codex/dq-19-cross-validation`
- Query: `sql/quality/validate_gold_cross_implementation.sql`
- Validated on: October 19, 2026

The operator switched the Databricks Git folder to the reviewed DQ-19 branch
before opening and running the tracked validation query. The screenshots show
the branch context, query name, successful execution, and result rows. They do
not independently prove the remote commit identity.

## Live validation outcome

After review hardening and a numerically stable source calculation, the
read-only query completed successfully at 4:55 PM EDT in 8.380 seconds,
returned exactly 17 checks, and displayed `passed = true` for every check. The
editor displayed a green execution status and no query error.

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
| `dq19_final_passed_rows_1_14.png` | `1b101322e36a906b32f1e2596620b88e2f6b34973f28ddc647f915a4a85fcaeb` |
| `dq19_final_values_rows_1_14.png` | `40079ac8bb0e4d567a7a176b4e23fc2544ba790522eec7a4b9ea7e43d83cda4e` |
| `dq19_final_values_rows_4_17.png` | `529ffe2eeb7aa3dbfaf2782eaa6dca2c791b969e3e71f235ca8ec653626034e6` |
| `dq19_final_passed_rows_4_17.png` | `449f4b5c54f9d4e0338d3183d3295d7c4f92222618c42c4fd30c3bb88bbf153f` |

The earlier `dq19_validation_*` captures are retained as review history for the
initial implementation. The `dq19_final_*` captures above are the authoritative
evidence for the corrected revision.

## Contract gate

The live 17-check result confirms that the three contracts in
`docs/REQUIRED_GOLD_CONTRACTS.md` are complete and mutually reconciled for the
validated snapshot. This satisfies the Gold validation gate before dashboard
or Genie implementation. It validates data contracts and implementation
equivalence; it does not make causal claims or validate future presentation
layers.
