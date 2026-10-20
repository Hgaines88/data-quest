# Tests

This directory will contain local unit and contract tests for source discovery, manifest change detection, schema handling, deduplication, and result validation. Databricks-specific integration evidence will be documented separately.

Run the local tests from the repository root without writing bytecode into the checkout:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The source-discovery tests use controlled HTML and fake HTTP responses. They do not contact BLS or require credentials.

`test_bundle_config.py` statically protects the DQ-24 deployment contract: the
three triggered serverless pipelines, ordered downstream task chain, exclusion
of shared landing writes, per-user development outputs, and exclusion of shared
governance resources from bundle ownership. These checks complement, but do not replace,
authenticated `databricks bundle validate` and `databricks bundle plan`.

`test_observability.py` and `test_spark_observability.py` protect the DQ-27
terminal audit contract, UTC and nonnegative-count invariants, privacy-safe
failure categories, append-only Spark adapter, and best-effort failure logging
that cannot mask the primary exception. `test_operational_sql.py` requires the
freshness, file-processing, expectation, and threshold fields while rejecting
mutating SQL, committed identities, and workspace IDs.
