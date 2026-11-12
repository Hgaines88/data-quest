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

Run `notebooks/04_export_public_gold_snapshots.py` in the project Databricks
Git folder. Download the four generated files from the displayed Volume path,
keep them together in one snapshot directory, and verify them locally before
use:

```bash
python portfolio/tools/verify_gold_snapshots.py /path/to/snapshot-directory
```

The verifier fails closed on schema order, contract counts, duplicate business
keys, Question 1 bounds, Question 3 match totals, or SHA-256 disagreement.

The committed `portfolio/data/gold_snapshot/` directory contains the verified
public presentation snapshot exported on November 12, 2026. The Streamlit app
checks each CSV against its recorded SHA-256 digest and row count before showing
the complete Question 1, Question 2, and Question 3 results. Databricks remains
the authoritative system; the committed files are a versioned read-only export.

