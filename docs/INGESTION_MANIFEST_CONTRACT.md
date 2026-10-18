# Ingestion manifest and change-detection contract

## Purpose and scope

The ingestion manifest is the control record for the raw mirror. It answers
which source objects are current, which verified bytes were last accepted, and
which ingestion run produced each state transition. This contract is shared by
the BLS and Data USA ingestion paths, although each source maintains its own
relative-path namespace.

DQ-06 defines and tests the state model only. Network streaming, temporary-file
handling, Databricks Volume writes, and transactional persistence are implemented
and proven in DQ-07 through DQ-09.

## Record schema

Each current or historical manifest entry contains:

| Field | Meaning |
| --- | --- |
| `source_url` | Absolute HTTP(S) location from which the object was obtained |
| `relative_path` | Canonical, source-relative object identity; absolute paths and `.` or `..` segments are invalid |
| `landed_path` | Canonical absolute Volume path of the immutable verified raw object version |
| `source_etag` | Provider ETag when present; retained as advisory metadata |
| `source_last_modified` | Provider Last-Modified value when present; retained as advisory metadata |
| `source_content_length` | Provider-reported content length when present; retained as advisory metadata |
| `content_size_bytes` | Number of bytes actually read and verified |
| `content_sha256` | Lowercase SHA-256 digest of the exact downloaded bytes |
| `ingested_at_utc` | UTC-aware timestamp of the successful state transition |
| `run_id` | Nonblank identifier tying all transitions to one ingestion attempt |
| `status` | `active` for a current source object or `removed` for a tombstone |

Provider metadata can help issue conditional requests, but it does not prove
content equality. The verified byte count and SHA-256 digest are authoritative.

## Identity and deterministic comparison

Within one configured source root, `relative_path` is the stable business key.
The source URL is provenance, not identity, because a provider may alter URL
encoding or host details without changing the logical object. A complete run
must contain at most one observation and one current manifest record per key.
Duplicates fail visibly rather than being resolved by input order.

Planning evaluates the sorted union of observed and current paths, so output
order does not depend on directory-listing or storage order.

| Current state | Complete current observation | Classification | Published state |
| --- | --- | --- | --- |
| No record | Present | `new` | New `active` entry |
| `removed` tombstone | Present | `new` | New `active` entry; historical tombstone remains auditable |
| `active` record | Same verified size and digest | `unchanged` | Keep the prior entry; do not rewrite raw bytes |
| `active` record | Different verified size or digest | `changed` | New `active` entry for verified bytes |
| `active` record | Absent from a complete inventory | `removed` | New `removed` tombstone |
| `removed` tombstone | Absent | `unchanged` | Keep the existing tombstone |

An empty inventory is meaningful only when discovery itself completed
successfully. DQ-05 rejects a malformed directory page that yields no usable
links, which prevents that failure from being interpreted as mass removal.

A nonempty inventory is not automatically trusted as complete when it would
remove currently active BLS paths. The BLS workflow requires its semantic
anchor files (`pr.data.1.AllData` and `pr.series`), repeats discovery
independently when removals are proposed, and requires both inventories to
match exactly. It also blocks removal of more than half of the active inventory
unless an operator explicitly enables the reviewed mass-removal override. This
guard prevents a truncated but superficially valid directory page from
publishing widespread tombstones. It does not prove that a confirmed upstream
deletion was intentional; that remains an operator-review decision.

## Removal decision

Removals are represented by append-only tombstones rather than physical
deletion. The raw bytes and prior active record remain available for audit,
reconciliation, and recovery, while the current view excludes records whose
latest status is `removed`. If the same path later reappears, it is classified
as `new` in the current source lifecycle, with the prior history retained.

This costs modest additional storage, but the source is small and the audit and
recovery benefits outweigh that cost. Automatically deleting raw evidence would
make an upstream mistake or transient listing defect harder to investigate.

## Safe run and publication protocol

The manifest plan may be created only after both conditions are true:

1. Source discovery returned a complete, validated inventory. For BLS runs
   proposing removals, an independent second discovery matched it exactly and
   the mass-removal safety gate was satisfied.
2. Every object needed for the run was fully staged and its observed byte count
   and SHA-256 digest were computed successfully.

The implementation sequence for DQ-07 is:

1. Assign one `run_id` and UTC timestamp.
2. Discover and validate the complete source inventory.
3. Stream required objects to a run-scoped temporary path, computing byte count
   and SHA-256 while reading.
4. Compare verified observations with the current committed manifest.
5. Promote new and changed objects to immutable, versioned raw paths and verify
   every unchanged active destination. Retained removal tombstones require no
   staged or landed bytes. If an unchanged active destination is absent,
   restore it from its freshly verified staged copy. If it exists but fails
   evidence verification, stop without overwriting it. The path includes a digest or
   equivalent unique version component so an interrupted run cannot overwrite
   bytes referenced by the committed manifest.
6. Append the run's new, changed, and removed transitions in one Delta
   transaction. Unchanged entries are not rewritten.
7. Expose the latest committed transition per `relative_path` as current state.
8. Clean up the run-scoped temporary path.

If discovery, download, verification, promotion, or publication fails, the run
must fail visibly. Temporary artifacts are removed or quarantined, no removal
tombstones are inferred from the partial inventory, and the previously committed
manifest remains authoritative. A retry uses a new `run_id` and safely compares
against that unchanged committed state.

An interruption after raw-file promotion but before the manifest transaction
may leave an unreferenced immutable file version. It must not become current
implicitly; the next run may verify and reuse or clean it before publishing. An
interruption after the atomic manifest commit is a successful state transition
even if later temporary cleanup must be retried.

## Evidence and limits

The pure contract tests prove deterministic classification of new, changed,
unchanged, removed, and reappearing objects; rejection of duplicate or unsafe
keys; and refusal to produce a plan for incomplete inventory or downloads.

They do not yet prove HTTP streaming, Databricks Volume promotion, Delta
transaction atomicity, cleanup after interruption, or live rerun behavior. Those
integration claims require controlled and Databricks-backed evidence in DQ-07
through DQ-09.
