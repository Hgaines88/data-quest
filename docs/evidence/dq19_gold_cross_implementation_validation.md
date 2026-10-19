# DQ-19 Gold cross-implementation validation

## Validation identity

- Git revision: `e9170cf116d86b5da75657a54e048b1b2471d436`
- Branch: `codex/dq-19-cross-validation`
- Query: `sql/quality/validate_gold_cross_implementation.sql`
- Validated on: October 19, 2026

The operator switched the Databricks Git folder to the reviewed DQ-19 branch
before opening and running the tracked validation query. The screenshots show
the branch context, query name, successful execution, and result rows. They do
not independently prove the remote commit identity.

## Live validation outcome

The read-only query completed successfully at 4:32 PM EDT in 31.036 seconds,
returned exactly 17 checks, and displayed `passed = true` for every check. The
performance panel recorded 85 of 85 tasks completed with a green execution
status and no displayed query error.

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
3 preservation check reports matching `39,39,1988,2026` actual and expected
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
| `dq19_validation_checks_overview.png` | `787c3f2ae35495e340e754bce8d9aa24d53a8e341e695e6209a6fca953a7f3a4` |
| `dq19_validation_performance.png` | `20f44f01fa4443a18791663d5fca9847e09254fef2d93be85bcb1655eea96ded` |
| `dq19_validation_passed.png` | `a46337a0cfd36df032160a3aa3933d42ef488881f69ed89003370dfd0f35b696` |
| `dq19_validation_checks_complete.png` | `b92926d2fbcc60f2fe2953a233d3fdd4ad066696ff4ae796d46a2bca35aae453` |
| `dq19_validation_passed_complete.png` | `b33c91492e249b0f13d2d1dcf5e17b15b8fb53e647d995035b673d857f79359e` |

## Contract gate

The live 17-check result confirms that the three contracts in
`docs/REQUIRED_GOLD_CONTRACTS.md` are complete and mutually reconciled for the
validated snapshot. This satisfies the Gold validation gate before dashboard
or Genie implementation. It validates data contracts and implementation
equivalence; it does not make causal claims or validate future presentation
layers.
