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
