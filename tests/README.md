# Tests

This directory will contain local unit and contract tests for source discovery, manifest change detection, schema handling, deduplication, and result validation. Databricks-specific integration evidence will be documented separately.

Run the local tests from the repository root without writing bytecode into the checkout:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The source-discovery tests use controlled HTML and fake HTTP responses. They do not contact BLS or require credentials.
