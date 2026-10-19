# DQ-15 Bronze-to-Silver quality validation

## Result

After pulling reviewed branch head `300c345`, the complete read-only
`sql/quality/validate_bronze_to_silver.sql` report ran successfully in
Databricks on October 19, 2026 at 11:08 AM EDT. All 14 named checks returned
`passed = true`.

The report reconciled 77,126 Bronze and Silver observation rows, 282 Bronze and
Silver series rows, and 11 US population rows. Conversion mismatches,
duplicate keys, required-field or domain failures, observation-series orphans,
and missing required population years all returned zero.

The commit association is operator-recorded because the Databricks file result
does not display a Git SHA. The file header displayed the
`codex/dq-15-silver-quality` branch, and the operator pulled the branch before
running the report.

## Evidence

- [All 14 checks passed](../screenshots/dq15_bronze_to_silver_all_checks_passed.png)
  shows the complete ordered result, all `passed` values as `true`, the exact
  reconciled row counts, and the successful query status.
- [Successful performance result](../screenshots/dq15_bronze_to_silver_performance.png)
  shows the completed statement and all 41 tasks finishing successfully.

The committed screenshot SHA-256 digests are:

| Screenshot | SHA-256 |
|---|---|
| `dq15_bronze_to_silver_all_checks_passed.png` | `a8c1c14c655de00aaaa1298998b2ea1b47f49e3bde13616b67f64ac3e1340887` |
| `dq15_bronze_to_silver_performance.png` | `a3859b96e4f5a6a9dfd30a7cbf59d8acd6690f45bee17502ce15fbe815d92ca0` |

## Quality interpretation

The equal layer counts show that this snapshot produced no rejected Silver
rows. The three bidirectional, null-safe conversion checks independently show
that normalized analytical values were neither added, omitted, nor changed
during publication. Separate checks establish unique business keys, required
and valid fields, the provider-composed series labels, complete observation
metadata coverage, and population coverage for every required year from 2013
through 2018.

Together, the successful live report and its repeatable SQL satisfy DQ-15's
Bronze-to-Silver reconciliation requirement without adding another stateful
pipeline.
