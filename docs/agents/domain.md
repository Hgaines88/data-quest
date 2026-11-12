# Domain Docs

This repository uses a single-context domain layout. These rules describe how engineering agents should consume its domain documentation before modifying the project.

## Before Exploring

Read the following when they exist and are relevant to the task:

- `GLOSSARY.md` at the repository root
- Architecture decisions under `docs/adr/`
- Existing contracts, runbooks, logical models, conventions, and validation documents under `docs/`

If `GLOSSARY.md` or `docs/adr/` does not exist, proceed silently. Create domain documentation only when a real term or architectural decision has been resolved and needs a durable record.

## Use Established Vocabulary

Use the project's existing terms in issue titles, specifications, code, tests, and documentation. Important established concepts include:

- landing, Bronze, Silver, and Gold
- immutable source version
- append-only manifest
- last-good state
- Gold analytical contract
- ingestion run audit
- PySpark primary implementation
- Spark SQL independent reconciliation

Do not introduce synonyms that blur an existing contract. If a required concept lacks a stable name, record the gap for explicit domain modelling rather than inventing competing terminology silently.

## Respect Existing Decisions

Read the documents governing the area before proposing a change. If a proposal conflicts with an existing contract, runbook, convention, or architecture decision, surface that conflict explicitly and explain why the decision may need to be revisited.

Do not modify submitted assessment artifacts merely to simplify an extension. New Spark experiments and learning evidence must remain clearly identified as post-submission portfolio extensions.
