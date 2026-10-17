# Engineering quality assurance protocol

## Purpose

This protocol defines the evidence required before work is merged into the Rearc Data Quest repository. It is designed to make correctness depend on explicit contracts, repeatable checks, verified execution, and engineering judgment rather than on any single paid tool or AI reviewer.

The protocol applies to DQ-05 and every remaining issue. Not every gate applies to every change, but an omitted gate must be marked **not applicable** with a reason. Silence is not evidence.

## Core principles

1. **Requirements become checks.** Each issue must map its acceptance criteria to tests, inspection, or executable evidence.
2. **Test the risk, not only the happy path.** Failure, retry, partial-state, malformed-input, and rerun behavior receive explicit attention.
3. **Independent evidence beats confidence.** Row counts, keys, digests, schemas, expectations, and source comparisons support claims about data.
4. **Small changes are easier to trust.** One issue should normally produce one focused pull request.
5. **No silent corruption.** A visible failure is preferable to a plausible but unsupported result.
6. **Generated code remains my responsibility.** I must understand, test, and be able to explain every submitted line.
7. **Tool findings are inputs, not verdicts.** AI review, static analysis, and automated tests can find problems but cannot replace judgment.
8. **Claims stay within the evidence.** Documentation must state what a check proves and what it does not prove.

## Change-risk classes

Each pull request declares the highest applicable risk class.

| Class | Typical work | Minimum review depth |
| --- | --- | --- |
| A: Documentation | Narrative, diagrams, planning records | Accuracy, consistency, link, secret, and claim-boundary review |
| B: Local logic | Pure parsing, transformations, helpers | Unit tests, boundary cases, static checks, and adversarial diff review |
| C: Integration or data movement | HTTP, Volume writes, manifests, pipeline reads | Class B plus contract tests, controlled failures, reruns, and integration evidence |
| D: Published analytics, security, or deployment | Gold results, dashboard, Genie, access controls, Asset Bundles | Class C plus reconciliation, authorization tests, operational evidence, and stakeholder validation |

## Required pull-request gates

### Gate 1: Requirements and risk

- [ ] Link the GitHub issue and state the change-risk class.
- [ ] Map every applicable acceptance criterion to a validation method.
- [ ] Identify the most damaging plausible failure, including any silent-corruption risk.
- [ ] State assumptions and dependencies that remain outside the change.

**Pass condition:** The reviewer can tell what success means and how it will be demonstrated.

### Gate 2: Test design

- [ ] Cover normal behavior.
- [ ] Cover empty, missing, malformed, boundary, and duplicate inputs where relevant.
- [ ] Cover retry, timeout, partial-write, rerun, and interrupted-state behavior where relevant.
- [ ] Use controlled fixtures or dependency injection rather than manipulating external providers.
- [ ] Ensure tests can fail for the defect they claim to detect.

**Pass condition:** Applicable failure modes are exercised rather than merely described.

### Gate 3: Automated local checks

- [ ] Run the full available unit and contract test suite.
- [ ] Run formatting, linting, and type checks configured for the repository.
- [ ] Run `git diff --check`.
- [ ] Compile or import Python modules where relevant.
- [ ] Scan tracked changes for credentials, tokens, private workspace identifiers, and unintended data.
- [ ] Record exact commands and summarized results in the pull request.

**Pass condition:** All configured checks pass, or an exception is documented and justified.

### Gate 4: Manual and adversarial review

- [ ] Read the complete diff line by line.
- [ ] Compare the implementation directly with the issue acceptance criteria.
- [ ] Look for hardcoded source assumptions, unsafe defaults, broad exception handling, nondeterminism, and misleading success states.
- [ ] Ask how the code behaves when the provider, schema, network, or prior state differs from expectations.
- [ ] Review naming, separation of responsibilities, and maintainability.
- [ ] Record findings and their resolution, including a clear statement when no findings remain.

**Pass condition:** The change has been challenged from the perspective of failure and silent corruption.

### Gate 5: Integration and platform evidence

Required for Classes C and D.

- [ ] Exercise the relevant behavior against the authorized external service or Databricks environment.
- [ ] Capture the environment, date, command or notebook cell, and observed result.
- [ ] Confirm that the integration proves only the behavior claimed.
- [ ] Avoid committing credentials, personal identifiers, private URLs, or raw downloaded data.

**Pass condition:** The real environment confirms the critical integration behavior without overstating its scope.

### Gate 6: Data reconciliation

Required when a change reads, moves, transforms, joins, aggregates, or publishes data.

- [ ] Reconcile expected and observed file inventories.
- [ ] Compare source and stored content size and SHA-256 digest where raw fidelity is claimed.
- [ ] Reconcile row counts and explain intentional differences between layers.
- [ ] Check key uniqueness, required non-null fields, parse failures, rejected rows, and metadata coverage.
- [ ] Test join cardinality and preserve unmatched records when required.
- [ ] Compare independent SQL and PySpark implementations using appropriate numeric tolerance.
- [ ] Spot-check representative results against source records or a simple independent calculation.

**Pass condition:** Completeness and correctness are supported by repeatable evidence, not visual plausibility.

### Gate 7: Security, privacy, reliability, and cost

- [ ] Confirm secrets and contact information are configured rather than committed.
- [ ] Restrict network and storage operations to intended locations.
- [ ] Apply least privilege to published data and stakeholder interfaces.
- [ ] Confirm retries are bounded and do not bypass provider policy.
- [ ] Consider compute size, repeated work, cleanup, and likely cost.
- [ ] Define recovery, rollback, or safe rerun behavior for state-changing work.

**Pass condition:** The change does not create an unjustified security, privacy, operational, or cost risk.

### Gate 8: Documentation and AI-use record

- [ ] Update architecture, contracts, commands, screenshots, or process notes affected by the change.
- [ ] Record material AI assistance, what I accepted or changed, and how I checked it.
- [ ] State known limitations and unresolved decisions.
- [ ] Distinguish verified behavior from proposed design.

**Pass condition:** Repository documentation accurately matches the implemented and verified state.

### Gate 9: Explainability

- [ ] Explain the purpose and control flow without reading an AI-generated summary.
- [ ] Explain keys, schemas, state transitions, and failure behavior relevant to the change.
- [ ] Explain why the selected approach was preferable to reasonable alternatives.
- [ ] Identify what the validation proves and what it does not prove.

**Pass condition:** I can defend the implementation and its limits in an interview.

### Gate 10: Merge decision

- [ ] All applicable gates pass.
- [ ] All review findings are resolved or explicitly accepted with rationale.
- [ ] The branch is current with `main` and the final diff is reviewed after conflict resolution.
- [ ] CI or local evidence is current for the exact commit being merged.
- [ ] The issue and project card reflect the true state of the work.

**Pass condition:** The pull request is reproducible, reviewable, explainable, and safe to merge.

## Evidence format

Each pull request should record applicable evidence in this form:

| Gate | Method | Result | Evidence or limitation |
| --- | --- | --- | --- |
| Requirements | Acceptance-criteria trace | Pass/Fail/N/A | Link or concise explanation |
| Tests | Exact command | Pass/Fail/N/A | Test count and relevant cases |
| Static checks | Exact command | Pass/Fail/N/A | Tool output summary |
| Adversarial review | Manual review | Pass/Fail/N/A | Findings and resolutions |
| Integration | Live or controlled execution | Pass/Fail/N/A | Date, environment, and observed result |
| Reconciliation | Counts, keys, digests, comparison | Pass/Fail/N/A | Metrics and explained differences |
| Security and operations | Review and tests | Pass/Fail/N/A | Risks, controls, and limitations |
| Documentation and AI | Diff review | Pass/Fail/N/A | Updated artifacts and AI-use note |
| Explainability | Walkthrough | Pass/Fail/N/A | Concepts rehearsed and remaining questions |

## Stop conditions

Do not merge when any of the following remains true:

- An acceptance criterion lacks a validation method.
- A failing check is dismissed only because output appears plausible.
- A partial write or failed request can be recorded as successful.
- Data is silently dropped, duplicated, relabeled, or coerced without an explicit rule.
- A credential, token, personal identifier, or private workspace value is exposed.
- The final commit has not been tested after a rebase or conflict resolution.
- I cannot explain a submitted line or architectural decision.
- Documentation claims more than the recorded evidence proves.

## Application to the remaining project

This protocol is applied beginning with DQ-05. Later issues add domain-specific evidence:

- DQ-06 through DQ-09 emphasize state transitions, raw fidelity, idempotency, and failure recovery.
- DQ-10 through DQ-15 emphasize schemas, keys, duplicate handling, lookup coverage, and layer reconciliation.
- DQ-16 through DQ-19 emphasize deterministic analytics, independent SQL/PySpark agreement, and numerical semantics.
- DQ-20 through DQ-23 emphasize documentation accuracy, evidence quality, reproducibility, and final audit.
- Bonus work emphasizes stakeholder reconciliation, least privilege, deployment reproducibility, observability, and operational recovery.

