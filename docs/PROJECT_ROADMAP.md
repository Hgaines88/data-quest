# Project completion roadmap

This roadmap is the authoritative execution order for the remaining Data Quest
work. It supersedes the earlier plan that placed the final submission audit
before the optional product extensions.

## Governing rule

**DQ-23 is the final project-wide audit. Do not close it until DQ-24 through
DQ-29 are complete and no implementation card remains open. DQ-29 may conclude
that no external-platform extension should be built; that decision does not
waive or replace any preceding card.**

DQ-29 concluded that the validated Databricks product is the appropriate final
platform for this assessment. The rationale and reconsideration trigger are
recorded in the [platform extension decision](PLATFORM_EXTENSION_DECISION.md).

This ordering keeps the repository-accessibility check, secrets and privacy
scan, link and screenshot validation, reproducibility run, and explainability
review focused on the repository that will actually be submitted. Performing
those checks before the remaining work would make the audit immediately stale.

## Remaining execution order

| Sequence | Card | Purpose | Entry gate | Exit gate |
|---:|---|---|---|---|
| 1 | DQ-25 | Add stakeholder exploration over governed Gold outputs. | Required pipeline and Gold contracts are complete. | Representative dashboard or Genie answers reconcile to Gold and reviewer evidence is captured. |
| 2 | DQ-26 | Apply least-privilege Gold-layer access controls. | The stakeholder experience and its required objects are known. | Read-only use succeeds; prohibited reads and writes fail. |
| 3 | DQ-24 | Encode the verified solution as a Databricks Asset Bundle. | Resources and required permissions are known. | The bundle validates; supported resources deploy successfully; unsupported Free Edition resources have explicit constraint evidence and a documented equivalent validation path. |
| 4 | DQ-27 | Add operational observability and recovery guidance. | The deployable resource model is known. | Freshness, processing, quality, and failure signals are visible; a safe recovery path is evidenced. |
| 5 | DQ-28 | Validate the extended Databricks product end to end. | DQ-24 through DQ-27 are complete. | Supported bundle deployment, documented equivalents for unsupported resources, operation, governance, stakeholder use, and evidence reconcile as one product without overstating Free Edition capabilities. |
| 6 | DQ-29 | Decide whether Snowflake or Power BI adds defensible value. | The Databricks-native product has been fully evaluated. | A documented decision either ends the extension work or defines a narrowly scoped additional consumer. |
| 7 | DQ-23 | Perform the final submission audit. | DQ-29 is complete and no implementation card remains open. | The final repository is reproducible, reviewable, explainable, privacy-safe, and accessible to Rearc reviewers. |

DQ-24 retained its technical dependency on DQ-26 because the bundle should
encode the final access model. DQ-27 retains its dependency on DQ-24 because
deployment and recovery evidence should exercise the version-controlled
resource definition. DQ-28 remains the integration gate for DQ-24 through
DQ-27. Where Free Edition cannot deploy a modeled resource, DQ-28 validates
the bundle configuration and exercises the documented equivalent resource; it
must record the limitation and must not claim that the unsupported deployment
occurred. DQ-29 remains a decision gate, not an automatic commitment to
another platform.

## QA gate for every card

For each card:

1. Confirm the live issue acceptance criteria and dependencies before editing.
2. Implement on a card-specific branch and preserve unrelated work.
3. Run proportionate local, static, security, and live Databricks checks.
4. Reconcile documented claims to captured evidence.
5. Resolve review findings and rerun affected checks.
6. Merge only after all checks are complete and explicit authorization is
   given.
7. Update this roadmap, the requirements checklist, and `PROCESS.md` when the
   implementation changes the plan or establishes a limitation.

Live Databricks actions that cannot be performed safely through automation are
explicit human validation gates. Their evidence must be recorded before the
corresponding card is considered complete.

## Current status

DQ-01 through DQ-22, DQ-24 through DQ-29, and the engineering QA protocol are
complete. DQ-24 keeps
landing outside independently deployed jobs, isolates development outputs per
current user, and deploys only the ordered Bronze-through-Gold resources.
Production was not deployed, and shared landing state, dashboard, warehouse,
identity, and grant resources remain explicitly external. DQ-27 adds the
privacy-safe health, expectation, failure, and recovery controls. DQ-28 passed
its integrated live gates, and DQ-29 concluded that no external platform is
justified. DQ-23 remains intentionally deferred.
