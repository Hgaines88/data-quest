# Product one-pager: US productivity insight workspace

## Product statement

I am building a governed economic-trends product for a consulting strategy director who needs to explore US productivity and labor-cost measures, identify notable historical periods, understand the provider definitions behind each series, and confidently use verified results in further analysis or client conversations.

The product begins with a reproducible Databricks pipeline and ends with a focused dashboard, a Genie space, or both. The experience is backed by curated Gold tables rather than direct access to raw provider files.

## Why this product exists

BLS Major Sector Productivity data is technically accessible but difficult for a non-technical stakeholder to interpret safely. Series identifiers are encoded, observations span different sectors and measurement types, revisions are possible, and population provides context without proving causation.

This product turns those sources into an auditable decision-support experience. It should help a stakeholder discover an important pattern, understand exactly what the measure represents, verify how current the evidence is, and decide whether deeper research or a client briefing is warranted.

## Primary stakeholder

### Director of Economic Strategy at a national consulting firm

This person advises clients or leadership but does not normally write Spark or SQL. They need concise evidence, plain-language definitions, relevant context, and enough provenance to use the result responsibly.

Typical questions include:

- Which productivity or labor-cost measures changed most significantly?
- When did each series reach its highest annual result?
- Are recent values unusual relative to their history?
- What does a selected series actually measure?
- How does a selected series move alongside population over the available period?
- Is the result current, complete, and trustworthy enough to investigate further?

## Supporting stakeholders

| Persona | Need | Product response |
| --- | --- | --- |
| Labor-market or policy analyst | Precise series comparisons and definitions | Detailed labels, periods, units, source metadata, and downloadable Gold results |
| Client-facing consultant | Fast answers to reasonable follow-up questions | A bounded Genie space using governed Gold tables and tested sample questions |
| Data governance or platform lead | Evidence that the product is reliable and appropriately secured | Lineage, quality metrics, freshness, least-privilege access, and operational documentation |

## Intended experience

### 1. Executive overview

- Data freshness and coverage
- Number of represented series
- Selected reporting period
- A small number of notable, verified observations
- Visible data-quality status

### 2. Productivity and labor-cost trends

- Selectable time-series views
- Provider-grounded, human-readable series labels
- Quarterly and annual results where analytically valid
- Highest annual result for each series with deterministic tie handling
- Carefully defined changes or indexes when the measure supports them

### 3. Population context

- The assigned BLS series and national population by year
- Preservation and disclosure of unmatched years
- Indexed comparison, such as a shared base year, when raw units would be misleading
- An explicit statement that co-movement does not establish causation

### 4. Definitions and methodology

- Sector, worker class, measure, duration, adjustment status, period, and units
- Source links and last successful ingestion time
- Missing-data, revision, aggregation, and standard-deviation conventions
- A concise explanation of how each displayed result was calculated

### 5. Ask-the-data experience

- Tested natural-language questions grounded in Gold tables
- Plain-language answers with relevant filters and definitions
- Guardrails against unsupported causal or policy claims
- A route from an answer to the underlying governed result

## Product success criteria

The product is successful when:

1. The complete assigned source inventory is landed reproducibly with provenance and content verification.
2. Bronze, Silver, and Gold layers have explicit contracts and repeatable quality checks.
3. Required analytical results agree across Spark SQL and PySpark implementations.
4. A representative dashboard value and Genie answer reconcile to the corresponding Gold query.
5. A read-only analyst can use the intended experience but cannot modify data or access unauthorized layers.
6. A reviewer can understand the architecture, reproduce the workflow, inspect the evidence, and explain the limits of every major claim.

## Design principles

1. **Evidence before presentation.** The pipeline and Gold results must be validated before dashboard design begins.
2. **Provider meaning over guessed labels.** Series descriptions come from BLS metadata relationships.
3. **Observation is not causation.** Population is context, not proof of an economic cause.
4. **Gold is the stakeholder contract.** Dashboards and Genie consume curated, documented Gold objects rather than raw or intermediate tables.
5. **Preserve disagreement and absence.** Missing joins, revisions, rejected records, and coverage gaps remain visible and explainable.
6. **Deterministic results.** Keys, deduplication, aggregation, ties, ordering, and numeric tolerances are defined explicitly.
7. **Least privilege by default.** Stakeholders receive only the access needed to consume approved results.
8. **Operational claims require evidence.** Freshness, recoverability, idempotency, and deployment claims are demonstrated, not inferred.
9. **AI assistance does not transfer responsibility.** I review, test, understand, and document assisted work before accepting it.
10. **Earn complexity.** Additional platforms or features require a user need and architectural justification.

## Explicit claim boundaries

The product may report observed values, comparisons, coverage, and calculated summaries. It may help a stakeholder form a hypothesis. It will not, from these sources alone:

- claim that population changes caused productivity changes;
- treat unlike units as directly comparable;
- convert a statistical high or low into a business recommendation automatically;
- imply that a successful pipeline run proves every analytical interpretation is correct; or
- hide missing, revised, rejected, or unmatched records to produce a cleaner visual.

## Decisions to make after profiling and modeling

- Which series merit headline placement for the primary stakeholder?
- Which measures can be summed, averaged, indexed, or compared responsibly?
- What constitutes a meaningful change for each measure and unit?
- Does population provide enough stakeholder value beyond the required analytical join?
- Should the stakeholder experience be a dashboard, Genie space, or both?
- Which Gold tables or governed views form the smallest useful semantic surface?
- What freshness and quality thresholds should trigger a warning or failure?
- Which features are available in the authorized Databricks edition?

## Later decision gate

The Databricks-native product will be completed and reassessed before adding Snowflake or Power BI. An external platform will be introduced only if it serves a defensible consumer, interoperability, semantic-modeling, or reporting requirement that justifies the additional time, credentials, compute, storage, and maintenance.

