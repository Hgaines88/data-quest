# UML-style system design

This document combines the implemented raw-ingestion boundary with the planned
Bronze, Silver, Gold, and stakeholder layers. Solid relationships are product
responsibilities; the landing notebooks and separate source manifests exist
today, while pipeline and presentation components remain planned. Dashed
relationships are validation, governance, or optional interactions.

## Component view

```mermaid
flowchart LR
    bls["BLS Major Sector Productivity<br/>directory and metadata"]
    datausa["Data USA<br/>population API"]

    subgraph dbx["Databricks workspace"]
        discover["Compliant source discovery<br/>and HTTP client"]
        bls_job["BLS landing notebook"]
        datausa_job["Data USA landing notebook"]
        bls_manifest["BLS manifest<br/>state and provenance"]
        datausa_manifest["Data USA manifest<br/>state and provenance"]
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
    discover --> bls_job
    datausa --> datausa_job
    bls_job --> bls_manifest
    datausa_job --> datausa_manifest
    bls_job --> volume
    datausa_job --> volume
    bls_manifest -. verifies .-> volume
    datausa_manifest -. verifies .-> volume
    volume --> bronze
    bronze --> silver
    silver --> gold

    quality -. checks .-> bls_manifest
    quality -. checks .-> datausa_manifest
    quality -. checks .-> bronze
    quality -. checks .-> silver
    quality -. reconciles .-> gold

    gold --> dashboard
    gold --> genie
    uc -. governs .-> gold
    uc -. governs .-> dashboard
    uc -. governs .-> genie
    obs -. observes .-> bls_manifest
    obs -. observes .-> datausa_manifest
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
    participant BLSJob as BLS landing notebook
    participant USAJob as Data USA landing notebook
    participant BLS as BLS directory
    participant USA as Data USA API
    participant BM as BLS manifest
    participant UM as Data USA manifest
    participant V as UC Volume
    participant P as Declarative Pipeline
    participant G as Gold tables/views
    participant X as Dashboard / Genie
    participant A as Read-only analyst

    BLSJob->>BLS: Discover files with identifying User-Agent
    BLS-->>BLSJob: Current provider inventory
    BLSJob->>BM: Compare path, size, digest, and current state
    BLSJob->>V: Land new or changed raw bytes
    BLSJob->>BM: Append transitions after verified promotion
    USAJob->>USA: Request assigned population response
    USA-->>USAJob: Raw JSON response
    USAJob->>UM: Compare path, size, digest, and current state
    USAJob->>V: Land validated raw response bytes
    USAJob->>UM: Append transition after verified promotion

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

