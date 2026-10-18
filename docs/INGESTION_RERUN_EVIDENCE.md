# Ingestion rerun evidence

This document maps DQ-09's rerun and failure-safety requirements to repeatable
tests and observed Databricks evidence. I use controlled fixtures for provider
change scenarios rather than altering BLS or Data USA resources.

## Meaning of skipped

An unchanged source is fetched and verified again so the ingestion can detect
provider changes. After its byte count and SHA-256 digest match the active
manifest entry, the workflow verifies the canonical immutable object. If that
object is valid, it does not promote another raw object, rewrite the committed
object, or append another manifest event. If it is missing, the workflow
restores it from the freshly verified staged bytes without changing manifest
state. A corrupt existing object fails visibly and is never overwritten.

## Acceptance evidence

| Required behavior | Repeatable evidence | What it establishes |
| --- | --- | --- |
| Immediate no-change rerun | `ExecuteLandingPlanTests.test_unchanged_run_verifies_but_does_not_publish_or_promote`; `PopulationLandingPreparationTests.test_same_verified_response_is_unchanged_on_rerun`; live BLS and Data USA reruns recorded in `PROCESS.md` | Verified identical bytes retain committed state with zero promotion and publication. |
| New source object | `PrepareBlsLandingTests.test_stages_complete_inventory_and_plans_all_change_types` | A newly observed path is classified as `NEW` and staged for immutable promotion. |
| Modified source object | `PrepareBlsLandingTests.test_stages_complete_inventory_and_plans_all_change_types`; `PlanManifestChangesTests.test_same_digest_but_different_size_is_changed` | Changed content evidence is classified as `CHANGED`; size and digest jointly define identity. |
| Removed source object | `PrepareBlsLandingTests.test_stages_complete_inventory_and_plans_all_change_types`; `PlanManifestChangesTests.test_empty_complete_inventory_marks_all_active_files_removed` | A missing path in a complete inventory produces a deterministic removal tombstone. |
| Interrupted or failed download | `PrepareBlsLandingTests.test_failed_download_cleans_the_run_and_produces_no_plan`; `PlanManifestChangesTests.test_partial_download_run_cannot_publish_a_plan` | An incomplete download run cleans staging and cannot produce a publishable manifest plan. |
| Failed promotion | `ExecuteLandingPlanTests.test_promotion_failure_prevents_manifest_publication` | Manifest publication is not attempted when immutable promotion fails. |
| Verification before publication | `ExecuteLandingPlanTests.test_verifies_all_objects_before_publishing_transitions` | New bytes are promoted and unchanged destinations are verified before any manifest transition is published. |
| Missing or corrupt immutable object | `ExecuteLandingPlanTests.test_missing_unchanged_object_is_recovered_without_publication`; `test_valid_unchanged_object_is_verified_without_rewrite`; `test_corrupt_unchanged_object_fails_without_overwrite` | Missing bytes are restored from verified staging without a manifest event; valid bytes are retained; corrupt bytes fail without overwrite. |

## Live no-change demonstrations

The BLS first run landed 12 objects under run ID
`20261017T194929Z-b3618da4`. The immediate rerun
`20261017T195437Z-5c5229ba` classified all 12 as unchanged, promoted zero
objects, published zero transitions, and retained the original run ID for every
active object.

The Data USA first run landed `population.json` under run ID
`20261017T223018Z-29527a8b`. The immediate rerun
`20261017T223605Z-09cb497b` classified it as unchanged, promoted zero objects,
published zero transitions, and retained the original run ID, 1,401-byte size,
and digest.

The corresponding screenshots are indexed in `docs/screenshots/README.md`, and
the Data USA result exports are indexed in `docs/evidence/README.md`.

## Claim boundaries

The controlled tests cover new, changed, removed, and failed inputs without
modifying an external provider. The live runs prove no-change behavior for the
observed BLS and Data USA responses in the authorized workspace. They do not
prove concurrent-writer safety or demonstrate a real provider mutation. This
assessment workflow remains explicitly single-writer; production scheduling
would require run-level mutual exclusion.
