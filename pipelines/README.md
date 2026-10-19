# Spark Declarative Pipelines

`bronze.py` defines the source-shaped Bronze layer with the current
`pyspark.pipelines` API. It publishes ten analytical BLS materialized views and
one Data USA population materialized view.

Only content-addressed objects selected by the latest active manifest state
reach Bronze. The binary reader may physically enumerate additional objects
before the manifest join, as described below. All source fields remain
source-shaped strings except Data USA `Year` and `Population`, whose JSON number
types are retained. Every output adds source file, physical path, ingestion
timestamp, run ID, and content digest provenance. Structural contract
violations fail an update; unusable required records are dropped and counted by
named expectations.

Shared temporary verification views join provider object bytes to latest-active
manifest paths, validate source presence and shape, and then feed every
published Bronze view. This explicit dependency prevents an empty or invalid
source from independently replacing a Bronze table.

BLS publication reads each artifact as distributed text lines after its exact
immutable path has passed the binary size, SHA-256, header, and nonempty-content
gates. It does not split a complete observation file into one in-row array.
This keeps the two observation datasets line-oriented during projection while
preserving ordered provider-header validation (with surrounding field whitespace
trimmed) and normalized Bronze column names.

The binary reader enumerates each provider's static content-addressed object
glob before the manifest join. The join prevents historical or unreferenced
bytes from reaching Bronze, but the execution engine can still read those bytes
and can reevaluate a temporary view for separate downstream flows. Dynamically
constructing reader paths would require collecting manifest rows while the
pipeline graph is planned, which this implementation deliberately avoids. Raw
history is bounded by content changes because unchanged landing reruns do not
create new objects; physical-read pruning can be revisited if that history
becomes operationally significant.

Configure these pipeline properties when deployment identifiers differ from
the defaults:

| Property | Default |
| --- | --- |
| `data_quest.catalog` | `workspace` |
| `data_quest.schema` | `rearc_data_quest` |
| `data_quest.volume` | `raw_landing` |

The pipeline requires the BLS and Data USA landing notebooks to have populated
their Delta manifest tables and immutable Volume objects. Run it as a triggered
batch update. Expectation metrics are available in the pipeline event log and
the update details in the Databricks UI.

## Silver observations

`silver.py` is a separate pipeline source so Silver development cannot alter the
validated Bronze graph. It reads the published AllData and Current observation
tables, trims provider formatting, casts `year` to integer and `value` to
`decimal(20,6)`, retains `Q01` through `Q05`, and converts blank footnotes to
null.

Invalid required rows are dropped and counted by named expectations. Duplicate
`series_id + year + period_code` keys fail the update rather than being resolved
arbitrarily. A second fail-fast gate requires every normalized Current row to
match the AllData-derived candidate on the complete business key and value. The
published `silver_bls_observation` depends on both gates.

The triggered target-runtime update completed successfully with zero errors and
warnings and approximately 77,000 published rows. See the
[DQ-12 live validation record](../docs/evidence/dq12_silver_live_validation.md)
for the completed-run, graph, performance, and pipeline-association evidence.

`silver_bls_series` left-joins the provider's series inventory to the sector,
class, measure, duration, and seasonal lookup tables. Its label concatenates
only provider descriptions. A fail-fast expectation requires every lookup to
match and every `series_id` to remain one row after the joins, so missing labels
or duplicate lookup keys cannot be hidden by a fallback description. Coverage
years are integers, coverage periods must be `Q01` through `Q05`, and the
provider's `-` base-year sentinel is published as a nullable integer.

The DQ-13 target-runtime update published 282 series rows with zero errors or
warnings while leaving the observation output unchanged. See the
[Silver series live-validation record](../docs/evidence/dq13_silver_series_live_validation.md).

`silver_population` normalizes the Bronze Data USA response to the documented
United States national grain. It publishes integer years and long population
values, drops and measures non-US, fractional, negative, or malformed records,
and fails rather than choosing an arbitrary row when `nation_id + year` is not
unique. The reusable Silver table retains every valid available year; the
required 2013–2018 completeness gate belongs to the Gold summary boundary.
See the
[Silver population live-validation record](../docs/evidence/dq14_silver_population_live_validation.md)
for the completed update, 11-row output, graph, performance, and explicit
year-coverage evidence boundary.
