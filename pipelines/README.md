# Spark Declarative Pipelines

`bronze.py` defines the source-shaped Bronze layer with the current
`pyspark.pipelines` API. It publishes ten analytical BLS materialized views and
one Data USA population materialized view.

The pipeline reads only content-addressed objects selected by the latest active
manifest state. All source fields remain source-shaped strings except Data USA
`Year` and `Population`, whose JSON number types are retained. Every output adds
source file, physical path, ingestion timestamp, run ID, and content digest
provenance. Structural contract violations fail an update; unusable required
records are dropped and counted by named expectations.

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

