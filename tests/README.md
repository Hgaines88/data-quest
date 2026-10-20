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
