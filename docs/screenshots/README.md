# Reviewer Evidence

Required screenshots of the Databricks pipeline, representative tables, and all three analytical outputs will be stored here. Images must be descriptively named and reviewed for sensitive information before they are committed.

## DQ-07 BLS landing evidence

- `dq07_first_run_reconciliation.png`: 12 first-run active objects with byte
  counts, original run ID, and shortened digest evidence.
- `dq07_no_change_counts_publication.png`: second-run discovery, new, promoted,
  and published-transition counts.
- `dq07_no_change_counts_unchanged.png`: second-run removed, reused-version, and
  unchanged counts.
- `dq07_no_change_reconciliation.png`: post-rerun reconciliation retaining the
  original first-run manifest ID for all 12 objects.

Digest prefixes are displayed for safe, readable evidence. The notebook
recomputed and compared each complete 64-character SHA-256 digest.

## DQ-08 Data USA landing evidence

- `dq08_no_change_counts.png`: immediate rerun showing one unchanged response,
  zero promotions, and zero published transitions.
- `dq08_reconciliation_identity.png`: final active-object reconciliation showing
  the original run ID, shortened digest, path, and status.
- `dq08_reconciliation_schema.png`: complementary reconciliation view showing
  declared columns, byte size, record count, and year bounds.

The request-contact widget was excluded from committed evidence. Digest prefixes
are displayed for readability; the notebook compared the complete digest.

