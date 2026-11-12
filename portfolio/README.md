# Data Quest public portfolio

This directory contains the public, read-only presentation layer for Data Quest.
It does not replace or recompute the authoritative Databricks implementation.

## Product boundary

- Databricks remains authoritative for ingestion, Bronze/Silver/Gold processing,
  expectations, access control, observability, and PySpark/SQL reconciliation.
- The Streamlit application reads versioned snapshots and evidence already
  validated by the project.
- Public presentation logic must not create new analytical claims.
- Missing exports remain visibly unavailable rather than being reconstructed
  from screenshots or partial evidence.

## Run locally

```bash
python -m pip install -r portfolio/requirements.txt
streamlit run portfolio/app.py
```

## Snapshot workflow

`portfolio/data/evidence_manifest.json` records the reviewed validation facts
currently available in Git. Full Gold exports will be added separately from the
authoritative Databricks tables:

- `gold_population_summary_2013_2018.csv` - 1 row
- `gold_bls_best_year_by_series.csv` - 282 rows
- `gold_bls_q01_population.csv` - 39 rows

Each export must be accompanied by a snapshot manifest containing its source
table, row count, export time, validated revision, and SHA-256 digest.

