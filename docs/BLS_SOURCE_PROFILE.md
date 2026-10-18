# BLS productivity source profile

## Scope

I profiled the live BLS Major Sector Productivity `pr` directory on 2026-10-16 before implementing ingestion. The source snapshot was downloaded to temporary local storage with an identifying `User-Agent`; raw source files were not added to Git.

Source directory: <https://download.bls.gov/pub/time.series/pr/>

## Source inventory

| File | Role | Observed data rows | Observed size |
|---|---|---:|---:|
| `pr.class` | Worker-class lookup | 2 | 102 bytes |
| `pr.contacts` | Human-readable program contacts | 15 lines | 562 bytes |
| `pr.data.0.Current` | Recent-history observation subset | 38,469 | 1,615,931 bytes |
| `pr.data.1.AllData` | Complete historical observations | 77,126 | 3,239,525 bytes |
| `pr.duration` | Calculation or presentation type lookup | 3 | 176 bytes |
| `pr.footnote` | Footnote lookup | 1 | 40 bytes |
| `pr.measure` | Economic measure lookup | 22 | 745 bytes |
| `pr.period` | Quarter and annual-average lookup | 5 | 146 bytes |
| `pr.seasonal` | Seasonal-adjustment lookup | 2 | 79 bytes |
| `pr.sector` | Major-sector lookup | 6 | 263 bytes |
| `pr.series` | Series definitions and date coverage | 282 | 15,657 bytes |
| `pr.txt` | Provider documentation and data dictionary | 411 lines | 18,343 bytes |

Counts and sizes describe this snapshot and may change in later BLS releases.

## File format observations

- Structured files are ASCII text with CRLF line endings.
- Columns are tab-delimited and the first nonblank record is a header.
- `series_id` is right-padded with spaces in both the series and observation files and must be trimmed before key comparison.
- Blank trailing lines may occur and must not be interpreted as records.
- Codes must remain strings so leading zeroes in values such as measure code `03` are preserved.
- Empty footnote fields represent no published footnote.
- `base_year` uses `-` for measures without an index base year; it should be normalized separately from a genuine year.

## Core schemas and intended types

### `pr.data.0.Current` and `pr.data.1.AllData`

| Field | Intended type | Meaning |
|---|---|---|
| `series_id` | string | Statistical-series key after trimming |
| `year` | integer | Observation year |
| `period` | string | `Q01` through `Q05`; `Q05` is annual average |
| `value` | `decimal(20, 6)` | Published observation value; DQ-10 fixed the Silver precision |
| `footnote_codes` | nullable string | Provider footnote code, currently blank or `R` |

The observed business key is `series_id + year + period`. Neither observation file contained duplicate business keys in this snapshot, and none of the five fields other than `footnote_codes` was empty.

### `pr.series`

| Field | Intended type | Meaning |
|---|---|---|
| `series_id` | string | Unique series key after trimming |
| `sector_code` | string | Joins to `pr.sector` |
| `class_code` | string | Joins to `pr.class` |
| `measure_code` | string | Joins to `pr.measure` |
| `duration_code` | string | Joins to `pr.duration` |
| `seasonal` | string | Joins to `pr.seasonal` |
| `base_year` | nullable integer | Index base year; `-` means not applicable |
| `footnote_codes` | nullable string | Series-level footnotes |
| `begin_year` | integer | First published observation year |
| `begin_period` | string | First published period |
| `end_year` | integer | Latest published observation year |
| `end_period` | string | Latest published period |

The file contained 282 rows and 282 distinct trimmed `series_id` values. All 282 series were present in `pr.data.1.AllData`.

## Current and historical file relationship

The provider documentation describes `pr.data.0.Current` as current data, but its observed contents span 1995 through 2026 rather than only the current calendar year. `pr.data.1.AllData` spans 1947 through 2026.

In the profiled snapshot:

- all 38,469 `Current` rows appeared exactly in `AllData`;
- no `Current` row was absent from `AllData`;
- 38,657 older `AllData` rows were absent from `Current`; and
- neither file contained duplicate `series_id + year + period` keys.

The ingestion layer will mirror both provider artifacts, but the analytical observation model will use `AllData` as the complete source. It will not append `Current` to `AllData`. A subset-consistency check can use `Current` as an additional validation signal.

## Metadata relationships

Every code used by `pr.series` resolved to its corresponding lookup in this snapshot:

| Relationship | Lookup codes | Codes used by `pr.series` | Missing matches |
|---|---:|---:|---:|
| sector | 6 | 6 | 0 |
| class | 2 | 2 | 0 |
| measure | 22 | 22 | 0 |
| duration | 3 | 3 | 0 |
| seasonal | 2 | 1 | 0 |

All five period codes used by `AllData` resolved through `pr.period`. The only nonblank observation footnote code was `R`, which resolved to `revised` through `pr.footnote`.

A human-readable label therefore requires, at minimum:

1. `pr.series` as the bridge from `series_id` to component codes;
2. `pr.sector` for the economic sector;
3. `pr.class` for the worker class;
4. `pr.measure` for the measured concept;
5. `pr.duration` for the calculation or presentation type; and
6. `pr.seasonal` for adjustment status.

Period descriptions belong to observations rather than the stable series label. Footnotes should remain available as provenance but are not part of the normal label.

For example, `PRS30006032` resolves to:

> Manufacturing · All workers · Hours worked · % Change from previous quarter · Seasonal Adjusted

## Modeling implications

- Preserve all 12 raw artifacts because the assignment requires the complete directory.
- Treat raw files as versioned provider artifacts, not as tables to concatenate indiscriminately.
- Trim identifier fields and remove CRLF artifacts before enforcing keys.
- Preserve codes as strings through Bronze and use explicit typed columns in Silver.
- Use `AllData` for the complete observation history.
- Retain source filename and ingestion metadata so records remain auditable.
- Validate lookup coverage rather than silently inventing labels for unmatched codes.
- Account for revised observations and changing source files in the ingestion manifest.

