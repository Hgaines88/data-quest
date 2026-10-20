# DQ-28 end-to-end validation record

## Status

**Complete.** The reviewed revision passed the local gates, isolated bundle
deployment and convergence checks, serial landing reruns, development and
shared pipeline refreshes, expectation inspection, and layer reconciliation on
2026-10-20. Existing stakeholder and access-control evidence remained
applicable because DQ-28 did not change those external resources or contracts.

## Scope and claim boundary

The DQ-28 procedure is defined in `docs/END_TO_END_VALIDATION.md`. The bundle
manages the three pipelines and ordered Bronze-to-Gold refresh job. Landing,
the shared dashboard, warehouse, analyst identity, Unity Catalog grants, and
notification destinations remain externally governed. Validation must exercise
both paths without claiming that the bundle created or owns the external
resources.

## Exact revision

- Branch: `codex/dq-28-end-to-end-validation`
- Commit: `a81645fd68d34fa586b4834455d5de49f894eb7d`
- Validation date: 2026-10-20
- Databricks environment: Free Edition workspace, serverless SQL warehouse,
  isolated bundle development target, and separately governed shared pipelines

## Quality gates

| Gate | Method | Current result | Evidence or limitation |
| --- | --- | --- | --- |
| Requirements | DQ-28 acceptance criteria mapped in the end-to-end runbook | Pass | Every criterion has an explicit local, live, reconciliation, security, operations, or documentation step. |
| Local tests | `PYTHONPATH=src python -m pytest -q` | Pass | 202 tests and 106 subtests passed on 2026-10-20 before documentation edits. |
| Compilation | `python -m compileall -q src tests notebooks pipelines` | Pass | Completed without output before documentation edits. |
| Whitespace | `git diff --check` | Pass | Passed on the reviewed final diff. |
| Bundle validation and deployment | Authenticated `validate`, reviewed `plan`, `deploy`, ordered run, convergence `plan` | Pass | Initial plan: 0 add, 3 change, 0 delete, 1 unchanged. The ordered refresh completed Bronze through Gold; the final plan converged to 0 add, 0 change, 0 delete, 4 unchanged. |
| Landing | Serial BLS and Data USA notebook rerun | Pass | BLS run `20261020T164038Z-43cb75a2` found 12 unchanged files; Data USA run `20261020T165548Z-c9665d89` found one unchanged object. Both had zero changes, removals, failures, and publication transitions. |
| Development pipeline and data | Bundle Bronze-to-Gold run plus retargeted layer, Gold, health, and expectation queries | Pass | Bronze, Silver, and Gold completed in order. Pipeline update identifiers are omitted from the submission. All 79 Bronze, 13 Silver, and 8 Gold expectation rows passed. Gold counts were 282, 39, and 1. |
| Shared pipeline and data | Separately governed shared Bronze-to-Gold run plus checked-in reconciliation and operational queries | Pass | Bronze, Silver, and Gold completed in order. Pipeline update identifiers are omitted from the submission. All expectation rows passed with zero rejected or blocking records. All 14 Bronze-to-Silver reconciliation checks passed. |
| Stakeholder | Published dashboard, acceptance query, and representative Genie evidence | Pass | DQ-25 evidence reconciles the external stakeholder surface to the unchanged shared Gold contracts. DQ-28 introduced no dashboard or Genie configuration change. |
| Access control | Separate-principal positive and prohibited-operation checks | Pass | DQ-26 evidence validates the unchanged external grants and preserves the distinction between authorization denials and structural view write protection. |
| Observability | Starting and final health and expectation queries | Pass | BLS, Data USA, and Gold reported healthy current states; the intentional DQ-27 controlled failure remained visible and was followed by success. Current expectation results contained explicit zero rejected or blocking counts rather than unavailable null metrics. |
| Security and privacy | Tracked-file, screenshot, and identifier review | Pass | The reviewed changes introduced no credential or raw-error material. Existing curated evidence retains its documented privacy boundary. |
| Explainability | Owner review of boundaries, flow, failure, recovery, cost, and limitations | Pass | The owner reviewed the integrated workflow and accepted the accumulated validation evidence as sufficient without repeating redundant queries. |

## Live results

- Starting health showed successful BLS and Data USA source runs and a healthy
  Gold refresh.
- The isolated development deployment used a per-user development schema;
  shared resources remained in `workspace.rearc_data_quest`.
- Both landing reruns were no-ops, demonstrating idempotency without publishing
  new manifest transitions.
- Development and shared Bronze, Silver, and Gold updates completed in order.
- Development expectations passed 79 Bronze, 13 Silver, and 8 Gold rows. Shared
  expectations passed the same 79, 13, and 8 rows with zero rejected or
  blocking records.
- The shared Bronze-to-Silver validator passed all 14 checks, including 77,126
  observation rows, 282 series rows, 11 US population rows, and zero conversion
  mismatches, duplicate keys, required-value failures, or orphans.
- The isolated bundle plan converged after deployment and execution. Production
  was not deployed, and no external stakeholder or access resource was claimed
  as bundle-owned.

## Known limitations to retain

- The assessment validates Free Edition behavior, not a production SLA.
- The bundle does not own landing, the existing dashboard, warehouse, identity
  groups, Unity Catalog grants, or notification destinations.
- Production is not deployed.
- The custom Genie instruction editor was not available in the observed Free
  Edition interface, so only reconciled generated answers are claimed.
