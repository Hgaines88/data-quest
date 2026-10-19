# DQ-14 Silver population live validation

## Result

After pulling reviewed branch head `ad3927b`, fresh triggered updates of both
medallion pipelines completed successfully in Databricks on October 18, 2026.
The Bronze population output published 11 rows with all 10 expectations met.
The subsequent `data-quest-silver` update completed at 11:00 PM EDT with zero
errors and zero warnings: `silver_bls_observation` published approximately
77,000 rows, `silver_bls_series` published 282 rows, and `silver_population`
published 11 rows.

The commit association is operator-recorded because the Databricks update
screen does not display a Git SHA. The operator pulled the branch immediately
before the recorded runs.

## Evidence

- [Fail-closed Bronze result](../screenshots/dq14_bronze_scientific_notation_fail_closed.png)
  shows the diagnostic run in which all 11 otherwise-valid provider records
  were dropped only by `population_has_integral_numeric_form`.
- [Corrected Bronze result](../screenshots/dq14_bronze_population_corrected_success.png)
  shows 11 published population rows, all 10 population expectations met, and
  the remaining Bronze outputs green.
- [Completed Silver update](../screenshots/dq14_silver_corrected_completed.png)
  shows the explicit 11:00 PM `Completed` status, zero errors and warnings, the
  pipeline ID, and all three Silver paths in the graph.
- [Corrected Silver table results](../screenshots/dq14_silver_corrected_tables.png)
  show approximately 77,000 observation rows, 282 series rows, and 11
  population rows after full recompute.
- [Corrected pipeline graph](../screenshots/dq14_silver_corrected_graph.png)
  shows the population candidate, uniqueness, and publication chain alongside
  the intact BLS paths.
- [Corrected performance summary](../screenshots/dq14_silver_corrected_performance.png)
  shows three materialized-view refresh statements finishing successfully.
- [2013–2018 coverage query](../screenshots/dq14_silver_population_2013_2018_coverage.png)
  is the earlier successful read-only query returning exactly six ordered rows:
  one each for 2013, 2014, 2015, 2016, 2017, and 2018.
- [Fresh SQL retry limitation](../screenshots/dq14_sql_warehouse_capacity_limit.png)
  records the environmental `RESOURCE_EXHAUSTED` failure when the free-edition
  serverless warehouse could not allocate additional compute after the fresh
  pipeline runs.

The committed screenshot SHA-256 digests are:

| Screenshot | SHA-256 |
|---|---|
| `dq14_bronze_scientific_notation_fail_closed.png` | `1005150b610dd143323232a42fc5485318e9c81be00ae636520bc6a7c327ca08` |
| `dq14_bronze_population_corrected_success.png` | `5e1814dd8ea10811e46ad381de45e48329dd07a28d12823c7b3aa9ad1076b77b` |
| `dq14_silver_corrected_completed.png` | `53d6110062aeb880f478b132dc33f86a0fb0a220b358097453bd85a0287958b2` |
| `dq14_silver_corrected_tables.png` | `c26371a2def436bd48811c13fcc758e31e2dc893ef8712ac113f0dcce8cb188e` |
| `dq14_silver_corrected_graph.png` | `fdbfd1364e34e059c472a3dc5ce033197c1df14721b287b9673ee84199ee718b` |
| `dq14_silver_corrected_performance.png` | `0cf8f476161f18e72652bebeabcda4d0399063015552ebd62bf5ecaec1e1a335` |
| `dq14_sql_warehouse_capacity_limit.png` | `151ce538a7b50642ac7a083054ca2711f532a67c1cc97161ceb94bd8873a78ff` |
| `dq14_silver_population_run_completed.png` | `53129f6a7f694e88dd1de9c9633bd2a9cc7d133b57dc1d6c45a321aa0b7eb6e0` |
| `dq14_silver_population_tables.png` | `c429412d45ef8490a25bf3fa6a7536f4e55ff63a387d436ac669bef501facbd8` |
| `dq14_silver_population_graph.png` | `0e6175bf9bd471462a4f4ef0be99ef31fd08567137eb8bb49a86909ab960d9d2` |
| `dq14_silver_population_performance.png` | `bc4df36e8bbed868a75866a45525e17a20368cc7580d304d523386268f6e8533` |
| `dq14_silver_population_2013_2018_coverage.png` | `4b4598b4736ad1738da143b13b21c149836bfda8c3fce2c8fd82429ed627edde` |

## Quality interpretation

### Fail-closed correction

The first post-review Bronze validation failed closed: Spark represented the
provider values in scientific notation such as `3.16128839E8`, while the
original lexical rule recognized only plain integer notation. The pipeline
published zero population rows and attributed all 11 drops to the integral-form
expectation. This made the faulty assumption observable without weakening any
unrelated rule.

The correction recognizes a scientific value as integral only when its
nonnegative exponent is at least the count of significant fractional digits.
For example, `3.16128839E8` is integral, while `1.25E1` is not. Plain integer
notation remains supported. Exact decimal comparison, finite-range checks, and
underflow protection remain independent gates, so this targeted change does
not substitute permissive floating-point rounding for validation. Regression
tests cover normalized provider notation and the previously identified
overflow, underflow, precision, and fractional edge cases.

### Published contract

The candidate view drops and measures records that violate the exact US
national grain, integer-year rule, nonnegative exact-integral population rule,
or provenance rule. Its downstream fail-fast expectation requires exactly one
row for each `nation_id + year`; the pipeline never chooses an arbitrary
duplicate. Successful publication therefore establishes that all 11 published
rows passed those gates and have unique business keys for this snapshot.

The earlier SQL result capture directly shows exactly one published row for
every requested year from 2013 through 2018. It establishes DQ-14's coverage
requirement while leaving the later Gold pipeline responsible for enforcing the
six-year analytical range at its own publication boundary.

A fresh SQL retry after the corrected pipeline runs remained queued because
the free-edition serverless compute allowance was exhausted, then was
cancelled. The warehouse reported `RESOURCE_EXHAUSTED`, not a query, schema, or
data error. This limitation is recorded rather than represented as a fresh
query success. The corrected pipeline evidence independently proves that both
current population tables contain 11 rows; the earlier query remains the
direct six-year value-level evidence.
