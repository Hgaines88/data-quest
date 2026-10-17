# UML-style system design

This document records the intended system before the remaining implementation decisions are made. Solid relationships are planned product responsibilities. Dashed relationships are validation, governance, or optional interactions. Exact Databricks resource names remain subject to verified platform behavior.

## Component view

```mermaid
flowchart LR
    bls["BLS Major Sector Productivity<br/>directory and metadata"]
    datausa["Data USA<br/>population API"]

    subgraph dbx["Databricks workspace"]
        discover["Compliant source discovery<br/>and HTTP client"]
        manifest["Ingestion manifest<br/>state and provenance"]
        volume[("Unity Catalog Volume<br/>raw provider artifacts")]

        subgraph sdp["Spark Declarative Pipeline"]
            bronze[("Bronze<br/>source-faithful records")]
            silver[("Silver<br/>typed, keyed, labeled data")]
            gold[("Gold<br/>stakeholder-ready results")]
        end

        quality["Quality and reconciliation<br/>expectations, tests, metrics"]
        dashboard["Databricks dashboard"]
        genie["Genie space"]
        uc["Unity Catalog governance<br/>read-only analyst access"]
        obs["Operational evidence<br/>freshness, failures, recovery"]
        dab["Databricks Asset Bundle<br/>repeatable deployment"]
    end

    stakeholder["Economic Strategy Director"]
    analyst["Labor-market / policy analyst"]
    platform["Platform / governance lead"]

    bls --> discover
    datausa --> discover
    discover --> manifest
    discover --> volume
    manifest -. verifies .-> volume
    volume --> bronze
    bronze --> silver
    silver --> gold

    quality -. checks .-> manifest
    quality -. checks .-> bronze
    quality -. checks .-> silver
    quality -. reconciles .-> gold

    gold --> dashboard
    gold --> genie
    uc -. governs .-> gold
    uc -. governs .-> dashboard
    uc -. governs .-> genie
    obs -. observes .-> manifest
    obs -. observes .-> sdp
    dab -. deploys .-> sdp
    dab -. configures .-> uc

    dashboard --> stakeholder
    genie --> stakeholder
    gold --> analyst
    obs --> platform
```

## Ingestion and publication sequence

```mermaid
sequenceDiagram
    autonumber
    participant Job as Ingestion job
    participant BLS as BLS directory
    participant USA as Data USA API
    participant M as Manifest
    participant V as UC Volume
    participant P as Declarative Pipeline
    participant G as Gold tables/views
    participant X as Dashboard / Genie
    participant A as Read-only analyst

    Job->>BLS: Discover files with identifying User-Agent
    BLS-->>Job: Current provider inventory
    Job->>USA: Request assigned population response
    USA-->>Job: Raw JSON response
    Job->>M: Compare URL, size, metadata, digest, and active state
    Job->>V: Land new or changed raw bytes
    Job->>M: Commit success only after verified write
    Job-->>M: Mark missing provider objects according to removal policy

    P->>V: Read immutable raw artifacts
    P->>P: Build and check Bronze
    P->>P: Type, deduplicate, and enrich Silver
    P->>G: Publish validated stakeholder results
    P-->>G: Record expectations and reconciliation evidence

    X->>G: Query governed Gold surface
    G-->>X: Verified results and definitions
    A->>X: Explore dashboard or ask bounded question
    X-->>A: Plain-language result with context
```

## Responsibility boundaries

| Component | Responsible for | Not responsible for |
| --- | --- | --- |
| Discovery and ingestion | Policy-compliant requests, inventory, verified raw landing, rerun state | Interpreting economic meaning |
| Bronze | Source fidelity, provenance, initial structural expectations | Deduplicated stakeholder semantics |
| Silver | Types, keys, deduplication, metadata joins, readable labels | Final business presentation |
| Gold | Stable grains and verified analytical outputs | Raw-provider reconstruction |
| Dashboard and Genie | Accessible exploration of approved Gold results | Inventing causal explanations |
| Unity Catalog controls | Least-privilege access to intended objects | Proving analytical correctness |
| Quality and observability | Detecting incomplete, inconsistent, stale, or failed processing | Silently correcting provider data |
| Asset Bundle | Repeatable resource configuration and deployment | Replacing runtime validation |

