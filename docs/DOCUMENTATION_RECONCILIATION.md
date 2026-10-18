# Documentation reconciliation

This record closes the documentation-drift findings in section 8 of
`docs/COPILOT_CODEBASE_AUDIT.md`. That audit remains a historical assessment of
commit `8cf008b`; this disposition compares each finding with the repository
after DQ-35 through DQ-41.

| Finding | Current disposition | Evidence or correction |
| --- | --- | --- |
| D-1 | Landing gap resolved; downstream scope preserved | Data USA landing now rejects non-standard JSON constants before publication. Exact top-level and ordered-column checks, finite integral population, and normalized-key uniqueness remain binding Bronze and Silver work in `docs/SOURCE_SCHEMA_QUALITY_CONTRACT.md`; this reconciliation does not claim they are implemented. |
| D-2 | Corrected here | The manifest contract now describes `ingested_at_utc` as the attempt timestamp carried by successfully published transitions, matching the notebooks. |
| D-3 | Resolved by implementation | BLS removals require anchor files and an identical second discovery. When the removal fraction exceeds the configured threshold, publication also requires a reviewed mass-removal override. |
| D-4 | Corrected here | `PROCESS.md` now distinguishes implemented raw landing from planned Bronze, Silver, and Gold work. |
| D-5 | Resolved by implementation | Data USA uses a provider-specific product user agent without personal contact information; only BLS requires the contact widget. |
| D-6 | Corrected here | The logical model now uses the three binding names from `docs/REQUIRED_GOLD_CONTRACTS.md`. |
| D-7 | Corrected here | The logical model now represents the two append-only source manifests and aligns timestamp, provenance, and footnote field names with the implemented manifest and DQ-10 contracts. A separate ingestion-run table is not claimed. |
| D-8 | Corrected here | Decisions already fixed by the manifest and source-quality contracts were removed from the open-decision list. |
| D-9 | Corrected here | The system UML now shows separate BLS and Data USA landing notebooks and manifests. Downstream layers remain explicitly planned. |
| D-10 | Corrected here | The BLS source profile now records the binding `decimal(20, 6)` Silver value type. |
| D-11 | Clarified here | The QA protocol now states that unittest and compilation are configured, while formatter, linter, and type-checker gates are not yet configured and must not be implied. |
| D-12 | Clarified here | Project conventions now identify notebook-based ingestion reconciliation as current and reserve `src/data_quest/validation` for reusable downstream checks. |
| D-13 | Corrected here | Completed DQ-01 through DQ-06 checklist items are marked complete, consistent with their merged implementation and evidence. |
| D-14 | Clarified here | Data USA evidence now states minimum and maximum years without implying uninterrupted annual coverage. PROCESS trade-off and retrospective sections remain intentionally living sections for DQ-20. |
| D-15 | Corrected here | Evidence indexes explain that Databricks serialized the column-name sequence with `_1` through `_4` struct keys; the values are the validated provider names. |

## Claim boundary

This reconciliation corrects descriptions of implemented ingestion behavior and
current design contracts. It does not claim that Bronze, Silver, Gold, pipeline,
dashboard, Genie, deployment, concurrent-writer control, or production
observability work is complete.
