# DQ-28 end-to-end validation record

## Status

**Pending live Databricks validation.** This file records completed local gates
and the evidence still required. It must not be cited as a completed end-to-end
run until every applicable live row below is replaced with an observed result.

## Scope and claim boundary

The DQ-28 procedure is defined in `docs/END_TO_END_VALIDATION.md`. The bundle
manages the three pipelines and ordered Bronze-to-Gold refresh job. Landing,
the shared dashboard, warehouse, analyst identity, Unity Catalog grants, and
notification destinations remain externally governed. Validation must exercise
both paths without claiming that the bundle created or owns the external
resources.

## Exact revision

- Branch: `codex/dq-28-end-to-end-validation`
- Commit: pending final reviewed commit
- Validation date: pending
- Databricks environment: pending

## Quality gates

| Gate | Method | Current result | Evidence or limitation |
| --- | --- | --- | --- |
| Requirements | DQ-28 acceptance criteria mapped in the end-to-end runbook | Pass | Every criterion has an explicit local, live, reconciliation, security, operations, or documentation step. |
| Local tests | `PYTHONPATH=src python -m pytest -q` | Pass | 202 tests and 106 subtests passed on 2026-10-20 before documentation edits. |
| Compilation | `python -m compileall -q src tests notebooks pipelines` | Pass | Completed without output before documentation edits. |
| Whitespace | `git diff --check` | Pass | Completed before documentation edits; rerun required on the final diff. |
| Bundle validation and deployment | Authenticated `validate`, reviewed `plan`, `deploy`, ordered run, convergence `plan` | Pending | The local machine has no Databricks CLI; use the authorized environment and record only observed output. |
| Landing | Serial BLS and Data USA notebook rerun | Pending | Keep mass removal and controlled failure disabled. Reconcile provider changes if the rerun is not a no-op. |
| Pipeline and data | Bronze-to-Gold run plus layer and Gold reconciliation | Pending | Require exact contract counts and all pass flags. |
| Stakeholder | Dashboard refresh, acceptance query, and representative Genie questions | Pending | Reconcile against the shared governed Gold contracts; do not claim custom Genie instruction deployment. |
| Access control | Separate-principal positive and prohibited-operation checks | Pending | Preserve the distinction between authorization denials and the structural Gold-view write block. |
| Observability | Starting and final health and expectation queries | Pending | Null expectation metrics mean unavailable evidence, not zero rejected records. |
| Security and privacy | Tracked-file, history, screenshot, and identifier review | Pending | Do not retain contact email, workspace URL, identity, tokens, or raw errors. |
| Explainability | Owner walkthrough of boundaries, flow, failure, recovery, cost, and limitations | Pending | Must be completed in the project owner's own words. |

## Live results

Record the observed starting health, landing outcomes, bundle plan and run,
contract counts, dashboard and Genie reconciliation, access-control results,
final health, runtime, cleanup decision, and screenshot digests here after the
exact revision completes review.

## Known limitations to retain

- The assessment validates Free Edition behavior, not a production SLA.
- The bundle does not own landing, the existing dashboard, warehouse, identity
  groups, Unity Catalog grants, or notification destinations.
- Production is not deployed.
- The custom Genie instruction editor was not available in the observed Free
  Edition interface, so only reconciled generated answers are claimed.
