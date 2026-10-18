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

## Observed validation evidence

On 2026-10-17, the first live run (`20261017T223018Z-29527a8b`) published one
new `population.json` object. It contained 1,401 bytes, 11 records spanning
2013–2024, and the four expected columns. Its displayed SHA-256 prefix was
`daa4d0576778`.

The immediate rerun (`20261017T223605Z-09cb497b`) classified the response as
unchanged, promoted zero objects, and published zero manifest transitions. The
final reconciliation retained the original run ID. Screenshots are indexed in
`docs/screenshots/README.md`, and the exported result rows are indexed in
`docs/evidence/README.md`.
