# BLS raw landing runbook

This runbook executes and validates DQ-07 in Databricks. The implementation is
single-writer: do not run two copies of the landing notebook concurrently.

## Preconditions

- Run `notebooks/01_land_bls.py` from this repository's Databricks Git folder.
- Use an identity that can create tables and write to the configured managed
  Volume.
- Enter a valid contact email in the `contact_email` widget. It is sent only in
  the BLS `User-Agent` and is not stored in the repository.
- Keep the verified defaults unless the target workspace requires different
  safe identifiers:
  - catalog: `workspace`
  - schema: `rearc_data_quest`
  - Volume: `raw_landing`
- Keep `allow_mass_removal` set to `false` for normal runs. Set it to `true`
  only after reviewing a confirmed provider-side change that legitimately
  removes more than half of the currently active source inventory.

## First-run evidence

Run every notebook cell in order and retain the following evidence:

1. The discovered-file count and current-manifest count printed before landing.
2. The `LandingExecutionResult` table. On an empty target, every discovered file
   should be `new`, every object should be promoted, and no object should be
   `changed`, `unchanged`, or `removed`.
3. The reconciliation table showing one active manifest row per discovered
   source path, its byte count, a 12-character digest prefix, status, and run ID.
4. A successful final assertion and a `Reconciled active files` count equal to
   the discovered-file count.

Do not mark DQ-07 complete if any discovered file is missing from the active
manifest, any unexpected active path appears, or any referenced object's size
or SHA-256 check fails.

## No-change rerun evidence

Without changing the source or configuration, run every cell again. The result
must show:

- the same discovered-file count;
- zero promoted objects;
- zero published transitions;
- every discovered object classified as `unchanged`;
- a successful full reconciliation of manifest paths and physical bytes.

The implementation re-downloads current provider bytes to compute independent
content evidence. A no-change rerun must not rewrite an immutable object or
append a duplicate manifest event. The result's `recovered_count` must normally
be zero. A positive value means an absent immutable object was restored from
freshly downloaded bytes that matched the committed size and SHA-256 evidence.

## Failure boundary

The notebook stages and verifies the complete inventory before publishing any
manifest change. Promotion failures prevent manifest publication. New and
changed bytes use content-addressed immutable paths, so an interrupted run may
leave an unreferenced object but cannot overwrite bytes referenced by the last
committed manifest. A retry with a new run ID reconciles against committed
manifest truth.

Before any proposed removal, the notebook performs a second independent BLS
directory discovery and requires the two inventories to match. Both discoveries
must include `pr.data.1.AllData` and `pr.series`. If more than half of the active
paths would be removed, publication fails unless `allow_mass_removal` was
explicitly enabled after operator review. Any failure occurs before downloads,
promotion, or manifest publication, so the existing active state remains
authoritative.

Every unchanged destination is verified before manifest publication. A missing
destination is restored from the verified staged copy and increments
`recovered_count` without creating a manifest transition. An existing object
that fails size or digest verification is preserved, never overwritten, and
fails the run for coordinated operator recovery.

## Cleanup and retention

Run-scoped `_staging` content is removed after success or failure. Historical
content-addressed objects and append-only manifest events are intentionally
retained for auditability. Garbage collection of unreferenced immutable objects
is outside DQ-07 and would require an age threshold plus a manifest-reference
check before deletion.
