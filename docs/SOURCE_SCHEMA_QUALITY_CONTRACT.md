# Source schema and data-quality contract

## Purpose and evidence

This contract closes DQ-10 before Spark Declarative Pipeline implementation. It
uses the observed source profile in `docs/BLS_SOURCE_PROFILE.md`, the landed Data
USA response evidence, the BLS data dictionary, and the required Gold contracts.

Authoritative provider references:

- BLS PR data dictionary: <https://download.bls.gov/pub/time.series/pr/pr.txt>
- BLS PR source directory: <https://download.bls.gov/pub/time.series/pr/>
- Data USA API documentation: <https://datausa.io/about/api/>

The raw files in the managed Volume remain the byte-faithful system of record.
Bronze tables are source-shaped and provenance-bearing. Silver tables own
normalization, intentional types, deduplication, and semantic relationships.

## Quality-action vocabulary

| Action | Meaning in this project | Use |
| --- | --- | --- |
| Retain and measure | Keep the row and expose an expectation metric | Advisory conditions that do not make the row unusable |
| Drop and measure | Exclude the row from the published table and expose the rejected count | A row cannot safely satisfy the table grain or required key |
| Fail the update | Stop publication and preserve the previous successful table version | Schema incompatibility, conflicting or duplicate business keys, or another condition that could silently corrupt required results |

Dropping is acceptable only because the immutable raw artifact remains available
for diagnosis and the expectation count is visible. A row is never silently
coerced into a plausible replacement value.

## Bronze contracts

Every Bronze row adds `_source_file`, `_source_path`, and `_ingested_at_utc`.
The pipeline reads only the active manifest versions, never an unscoped wildcard
that could mix historical content-addressed versions.

Before projecting named BLS columns, the reader captures parser-level malformed
records and verifies the physical field count against the declared header. Any
malformed record or width mismatch fails the update rather than risking shifted
columns. This structural gate applies to both observation files, `pr.series`,
and every analytical lookup file. The immutable raw artifact remains available
for diagnosis, and the failed-record count is surfaced with the pipeline
evidence.

### `bronze_bls_observation_all`

Source: `pr.data.1.AllData`. `pr.data.0.Current` is modeled separately as a
subset-consistency signal and is never appended to this table.

| Source field | Bronze type | Required |
| --- | --- | --- |
| `series_id` | string | yes |
| `year` | string | yes |
| `period` | string | yes |
| `value` | string | yes |
| `footnote_codes` | string | no |

Grain candidate: one raw record per `series_id + year + period`. Bronze preserves
provider whitespace and value text; normalization occurs in Silver.

Expectations:

- Trim header names for comparison, then fail the update when the ordered header
  is not exactly the five declared fields. Provider padding is formatting, not
  schema drift.
- Drop and measure rows whose trimmed `series_id`, `year`, `period`, or `value`
  is empty.
- Retain and measure period text outside `Q01`–`Q05`; Silver rejects it after
  normalization so an unexpected provider code is visible before exclusion.

`bronze_bls_observation_current` uses the same schema and expectations for
`pr.data.0.Current`.

### `bronze_bls_series`

| Source field | Bronze type | Required |
| --- | --- | --- |
| `series_id` | string | yes |
| `sector_code` | string | yes |
| `class_code` | string | yes |
| `measure_code` | string | yes |
| `duration_code` | string | yes |
| `seasonal` | string | yes |
| `base_year` | string | yes; `-` is a documented sentinel |
| `footnote_codes` | string | no |
| `begin_year` | string | yes |
| `begin_period` | string | yes |
| `end_year` | string | yes |
| `end_period` | string | yes |

Expectations:

- Trim header names for comparison, then fail the update when the ordered header
  differs from the declared 12 fields.
- Drop and measure rows with a blank trimmed `series_id` or any blank required
  component code.
- Retain and measure unexpected period or base-year formats for Silver handling.

### BLS lookup Bronze tables

All code fields remain strings so leading zeroes survive.

| Table | Exact source fields | Candidate key |
| --- | --- | --- |
| `bronze_bls_class` | `class_code`, `class_text`, `display_level`, `selectable`, `sort_sequence` | `class_code` |
| `bronze_bls_duration` | `duration_code`, `duration_text`, `display_level`, `selectable`, `sort_sequence` | `duration_code` |
| `bronze_bls_measure` | `measure_code`, `measure_text`, `display_level`, `selectable`, `sort_sequence` | `measure_code` |
| `bronze_bls_sector` | `sector_code`, `sector_name`, `display_level`, `selectable`, `sort_sequence` | `sector_code` |
| `bronze_bls_footnote` | `footnote_code`, `footnote_text` | `footnote_code` |
| `bronze_bls_period` | `period`, `period_abbr`, `period_name` | `period` |
| `bronze_bls_seasonal` | `seasonal_code`, `seasonal_text` | `seasonal_code` |

Every source field is a nullable string at read time. The pipeline compares the
ordered header after trimming header names and fails on a mismatch, then drops
and measures rows with blank trimmed candidate keys or descriptions. Display and
ordering fields are typed in Silver.

`pr.contacts` and `pr.txt` remain governed raw artifacts but do not become
analytical Bronze tables because no required result consumes them.

### `bronze_datausa_population`

The JSON reader uses this explicit envelope:

```text
annotations  MAP<STRING, STRING>
columns      ARRAY<STRING>
data         ARRAY<STRUCT<
               `Nation ID`: STRING,
               Nation: STRING,
               Year: BIGINT,
               Population: DOUBLE
             >>
page         STRUCT<limit: BIGINT, offset: BIGINT, total: BIGINT>
```

The source is already validated before promotion, but the pipeline independently
checks the committed object before typed projection. The top-level keys must be
exactly `annotations`, `columns`, `data`, and `page`; the pagination keys must be
exactly `limit`, `offset`, and `total`; and `columns` must equal the ordered list
`Nation ID`, `Nation`, `Year`, `Population`. Every record must have exactly that
declared key set. Annotation-map keys remain provider-defined because they are
metadata rather than analytical columns.

The update fails when these envelope, pagination, column-set, record-key, or
parser checks fail, or when pagination indicates an incomplete response. This
detects both missing and additive schema drift instead of allowing an explicit
reader schema to silently discard new fields. After exploding `data`, the
pipeline drops and measures rows with blank `Nation ID` or `Nation`, null `Year`,
null `Population`, or a non-finite or negative population. Landing validation
parses JSON decimals losslessly and rejects exponent values that would overflow
to infinity or underflow to zero when projected into Bronze's double type.

## Silver contracts

### `silver_bls_observation`

Source: `bronze_bls_observation_all` only.

| Field | Silver type | Rule |
| --- | --- | --- |
| `series_id` | string, non-null | trim provider padding |
| `year` | integer, non-null | explicit cast; positive four-digit year |
| `period_code` | string, non-null | trim; one of `Q01`–`Q05` |
| `value` | decimal(20, 6), non-null | explicit cast; no default substitution |
| `footnote_codes` | string, nullable | trim; blank becomes null |
| `source_file` | string, non-null | provenance from Bronze |
| `ingested_at_utc` | timestamp, non-null | provenance from active manifest |

Business key: `series_id + year + period_code`.

- Drop and measure failed casts, invalid periods, and null business-key fields.
- Fail the update if the normalized business key is duplicated. The profiled
  source contains no duplicates, and selecting an arbitrary duplicate could
  change a required annual sum.
- Retain `Q05` in Silver because it is valid provider data. Required Question 2
  excludes it explicitly because it is an annual average, not a quarter.
- Treat `bronze_bls_observation_current` as validation input only: every current
  row must match exactly one row in the AllData-derived Silver table on the
  normalized business key and value. Fail the update when a Current row is
  absent from AllData or has a different value. Surface mismatch counts and
  bounded examples as evidence; do not publish a snapshot assembled from
  internally inconsistent provider files.

### `silver_bls_series`

| Field | Silver type | Rule |
| --- | --- | --- |
| `series_id` | string, non-null | trimmed primary key |
| component codes | string, non-null | trimmed; leading zeroes preserved |
| `base_year` | integer, nullable | `-` becomes null; otherwise explicit cast |
| `footnote_codes` | string, nullable | trimmed; blank becomes null |
| `begin_year`, `end_year` | integer, non-null | explicit cast |
| `begin_period`, `end_period` | string, non-null | `Q01`–`Q05` |
| `series_label` | string, non-null | provider-grounded lookup descriptions |

Business key: `series_id`.

- Drop and measure rows with invalid required casts or fields.
- Fail the update on duplicate `series_id` values.
- Fail the enriched publication when any component code lacks a lookup match;
  the required output needs a readable label and must not invent one.
- Before enriched observation or Gold publication, require every retained
  observation `series_id` to match exactly one valid `silver_bls_series` row.
  Fail the update on missing or ambiguous series metadata rather than silently
  omitting the observation or publishing it without the required readable
  label. Surface orphan and ambiguity counts with bounded examples.
- Build labels from sector, class, measure, duration, and seasonal descriptions.
  Period and footnote descriptions remain observation provenance, not stable
  label components.

### Silver lookup tables

Each lookup trims its code and description, casts `display_level` and
`sort_sequence` to integers where present, and interprets `selectable` as a
boolean from `T` or `F`. Invalid keys or casts are dropped and measured. A
duplicate normalized code fails the update because lookup ambiguity would make
series labels nondeterministic.

### `silver_population`

| Field | Silver type | Rule |
| --- | --- | --- |
| `nation_id` | string, non-null | trimmed from `Nation ID` |
| `nation` | string, non-null | trimmed |
| `year` | integer, non-null | exact cast from integral source value |
| `population` | long, non-null | source value must be finite, nonnegative, and integral |
| `source_file` | string, non-null | `population.json` |
| `ingested_at_utc` | timestamp, non-null | provenance from active manifest |

Business key: `nation_id + year`.

- Limit the analytical population table to the documented US national record
  (`nation_id = '01000US'`, `nation = 'United States'`). Retain other records in
  Bronze if the API expands, but measure and exclude them from this Silver
  contract until their grain is intentionally modeled.
- Drop and measure invalid or nonintegral values and null key fields.
- Fail the update on duplicate normalized business keys.
- Fail the DQ-16 precondition when any year from 2013 through 2018 is missing;
  this range completeness rule belongs at the required analytical boundary, not
  as a permanent restriction on the reusable Silver table.

## Schema drift and recovery

Additive or incompatible provider schema drift is not accepted automatically.
The explicit reader schema and header/envelope checks fail the update, preserve
the previous successful pipeline state, and leave the immutable raw artifact
available for inspection. I would review and version an intentional schema
change rather than silently discarding or coercing new fields.

Expectation metrics, rejected counts, duplicate checks, lookup coverage, the
Current-to-AllData subset check, and population year coverage must be exposed in
pipeline evidence. DQ-11 through DQ-15 will implement and reconcile these rules;
this document defines their contract but does not claim they are already live.
