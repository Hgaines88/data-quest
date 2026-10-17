# Data USA population landing runbook

This runbook executes and validates DQ-08 in Databricks. The notebook is
single-writer and preserves the assigned API response bytes unchanged.

## Preconditions

- Run `notebooks/02_land_datausa_population.py` from this repository's
  Databricks Git folder.
- Enter a valid contact email in the request-contact widget.
- Keep the verified defaults unless the authorized workspace differs:
  `workspace.rearc_data_quest.raw_landing`.

## First run

Run each cell in order. The first result should show one discovered and new
object, one promotion, one published transition, and zero changed, unchanged,
removed, or reused-version objects. The response summary must show a nonzero
record count, the declared columns, and a valid minimum and maximum year.

The final reconciliation must show one active `population.json` object. It
recomputes the complete file size and SHA-256 digest and reparses the committed
raw bytes against the envelope, pagination, column, and record contract.

## Immediate no-change rerun

Run the timestamp/manifest, landing, and reconciliation cells again without
changing configuration. The result must show one unchanged object, zero
promotions, and zero published transitions. The reconciled manifest entry must
retain the first-run ID.

## Failure boundary

Invalid UTF-8, malformed JSON, a missing envelope field or required column, an
invalid record, or a partial page fails before promotion and manifest
publication. Promotion failure also prevents manifest publication. The previous
committed state therefore remains authoritative.
