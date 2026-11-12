from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO = Path(__file__).resolve().parent
MANIFEST = PORTFOLIO / "data" / "evidence_manifest.json"
ARCHITECTURE = ROOT / "docs" / "architecture" / "data-quest-architecture.png"
SCREENSHOTS = ROOT / "docs" / "screenshots"


@st.cache_data
def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def inject_styles() -> None:
    st.markdown(
        """
        <style>
          :root { --dq-navy: #102a43; --dq-blue: #2f80c1; --dq-mint: #dff6ec; }
          .stApp { background: #f7f9fc; color: #102a43; }
          .block-container { max-width: 1180px; padding-top: 3.75rem; }
          .dq-kicker { color: #2f80c1; font-size: .82rem; font-weight: 750;
                       letter-spacing: .12em; text-transform: uppercase; }
          .dq-hero { color: #102a43; font-size: clamp(2.4rem, 6vw, 5rem);
                     line-height: .98; font-weight: 850; margin: .25rem 0 1rem; }
          .dq-subtitle { color: #52677d; font-size: 1.18rem; max-width: 780px; }
          .dq-boundary { border-left: 4px solid #2f80c1; background: #eef6fc;
                         padding: 1rem 1.1rem; border-radius: 0 .65rem .65rem 0; }
          .dq-pass { color: #176b49; font-weight: 750; }
          [data-testid="stMetric"] { background: white; border: 1px solid #dbe5ef;
                                     padding: .8rem; border-radius: .8rem; }
          [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {
            color: #102a43;
          }
          [data-testid="stAlert"] p { color: #102a43; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero() -> None:
    st.markdown('<div class="dq-kicker">Governed public-data engineering</div>', unsafe_allow_html=True)
    st.markdown('<div class="dq-hero">Data Quest</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="dq-subtitle">A Databricks data product that turns public labor and population data into validated, observable, and access-controlled analytical results.</div>',
        unsafe_allow_html=True,
    )


def boundary_note() -> None:
    st.markdown(
        """
        <div class="dq-boundary"><strong>Public presentation boundary.</strong>
        This application is a read-only portfolio view generated from versioned
        Data Quest evidence and Gold outputs. Databricks remains authoritative
        for ingestion, transformation, governance, reconciliation, and operational state.</div>
        """,
        unsafe_allow_html=True,
    )


def overview(data: dict) -> None:
    hero()
    st.write("")
    boundary_note()
    st.write("")
    inventory = data["source_inventory"]
    cols = st.columns(4)
    cols[0].metric("BLS source files", f"{inventory['bls_files']:,}")
    cols[1].metric("Historical observations", f"{inventory['bls_observations']:,}")
    cols[2].metric("Statistical series", f"{inventory['bls_series']:,}")
    cols[3].metric("Population years", f"{inventory['population_rows']:,}")

    st.subheader("What the product answers")
    q1, q2, q3 = st.columns(3)
    q1.markdown("**01 — Population summary**\n\nMean and population standard deviation for annual US population from 2013 through 2018.")
    q2.markdown("**02 — Best year by series**\n\nThe highest Q01-Q04 annual sum for every governed BLS series, with deterministic tie handling.")
    q3.markdown("**03 — Population context**\n\nQ01 history for one assigned BLS series, preserving years with no population match.")

    st.subheader("Architecture at a glance")
    st.image(str(ARCHITECTURE), width="stretch")


def results(data: dict) -> None:
    st.title("Explore the validated results")
    contracts = data["gold_contracts"]

    st.subheader("Question 1 · Population, 2013–2018")
    q1 = contracts["population_summary"]
    cols = st.columns(3)
    cols[0].metric("Mean population", f"{q1['mean_population'] / 1_000_000:.1f}M")
    cols[1].metric("Population std. deviation", f"{q1['population_stddev'] / 1_000_000:.1f}M")
    cols[2].metric("Complete annual values", q1["year_count"])
    st.caption("Population standard deviation is used because the six requested annual values form the complete finite range, not a sample.")

    st.subheader("Question 2 · Best year for every BLS series")
    q2 = contracts["best_year_by_series"]
    sample = q2["representative_result"]
    cols = st.columns(3)
    cols[0].metric("Published series", q2["row_count"])
    cols[1].metric("Selected year", sample["best_year"])
    cols[2].metric("Q01–Q04 sum", sample["annual_quarterly_sum"])
    st.caption(f"Representative validated series: `{sample['series_id']}`")
    st.info("Q05 is excluded because BLS defines it as an annual average, not a fifth quarter. Equal maxima resolve to the earliest year.")
    if not q2["full_export_available"]:
        st.warning("The complete 282-row Gold export has not yet been added to the public snapshot. This view shows only validated aggregate and representative evidence.")

    st.subheader("Question 3 · Q01 history with population context")
    q3 = contracts["q01_population"]
    cols = st.columns(3)
    cols[0].metric("BLS observations retained", q3["row_count"])
    cols[1].metric("Population matches", q3["matched_population_rows"])
    cols[2].metric("Visible null matches", q3["unmatched_population_rows"])
    sample_rows = pd.DataFrame(q3["representative_rows"])
    st.dataframe(sample_rows, hide_index=True, width="stretch")
    st.caption("Representative source-level checks only. Missing population remains NULL and never removes a valid BLS observation.")


def engineering(data: dict) -> None:
    st.title("Inspect the engineering")
    st.markdown("The public interface is downstream of the evidence. The architecture, contracts, and failure behavior remain reviewable.")
    st.image(str(ARCHITECTURE), width="stretch")

    tabs = st.tabs(["Contracts", "Reliability", "Quality", "Governance", "Trade-offs"])
    with tabs[0]:
        st.markdown(
            """
            - **Landing:** immutable, content-addressed objects and append-only manifests
            - **Bronze:** source-shaped records, provenance, schema and row-shape validation
            - **Silver:** typed observations, series metadata, normalized population, business keys
            - **Gold:** three exact analytical contracts with fail-fast input checks
            """
        )
    with tabs[1]:
        st.markdown(
            """
            - SHA-256 digests are authoritative when provider ETags are unreliable.
            - Unchanged reruns discard temporary bytes and publish no redundant transition.
            - A failed landing or pipeline does not displace the last-good state.
            - Landing remains a separately governed single-writer prerequisite.
            """
        )
    with tabs[2]:
        quality = data["quality"]
        cols = st.columns(4)
        cols[0].metric("Bronze expectation rows", quality["bronze_expectation_rows"])
        cols[1].metric("Silver expectation rows", quality["silver_expectation_rows"])
        cols[2].metric("Gold expectation rows", quality["gold_expectation_rows"])
        cols[3].metric("Cross-implementation checks", f"{quality['gold_cross_implementation_passed']}/{quality['gold_cross_implementation_checks']}")
        st.markdown('<p class="dq-pass">All documented checks passed for the validated snapshot.</p>', unsafe_allow_html=True)
    with tabs[3]:
        st.markdown(
            """
            The demonstrated analyst receives only `USE CATALOG`, `USE SCHEMA`,
            and `SELECT` on the three exact Gold contracts, plus dashboard and
            warehouse consumption rights. Bronze, Silver, raw Volume, object
            creation, pipeline authority, ownership, and management remain denied.
            """
        )
    with tabs[4]:
        st.markdown(
            """
            - `AllData` is authoritative; misleadingly named `Current` remains a consistency check.
            - Whole-file parsing was replaced after live testing exposed a single oversized task and poor memory shape.
            - Landing stays outside the Asset Bundle because a job concurrency limit cannot coordinate every external writer.
            - A second analytics platform was rejected without a named consumer or unmet requirement.
            """
        )


def failure_lab() -> None:
    st.title("Failure laboratory")
    st.write("Choose a condition to see the contract-driven response. These are explanations of implemented behavior, not live mutations.")
    scenarios = {
        "Unchanged source digest": ("Discard staged bytes", "Record the successful run, publish no redundant manifest transition, and retain the existing immutable object."),
        "Duplicate business key": ("Block publication", "A uniqueness violation can fan out joins or misstate aggregates. The prior materialized result remains authoritative."),
        "Missing population match": ("Preserve the BLS row", "Population stays NULL and the explicit match indicator is false. Absence of context does not erase a valid observation."),
        "Incomplete quarterly year": ("Do not invent a complete annual result", "Only the defined Q01-Q04 contract can support the requested annual sum; incompleteness remains visible."),
        "Landing failure before publication": ("Keep last-good state", "Staging is cleaned, the sanitized failure is audited, and no partial manifest transition becomes current."),
        "Changed digest": ("Create a new immutable version", "Advance the candidate through validation while retaining prior source versions and provenance."),
    }
    selected = st.selectbox("Scenario", list(scenarios))
    outcome, explanation = scenarios[selected]
    st.success(outcome)
    st.write(explanation)


def evidence(data: dict) -> None:
    st.title("Evidence room")
    st.write(data["snapshot_label"])
    st.markdown("Every public claim maps back to committed validation records and curated screenshots.")
    for source in data["evidence_sources"]:
        st.code(source, language=None)

    st.subheader("Selected Databricks evidence")
    gallery = [
        ("Published dashboard", "dq25_published_dashboard_overview.png"),
        ("Gold pipeline graph", "dq17_gold_pipeline_graph.png"),
        ("Cross-implementation parity", "dq18_sql_pyspark_parity_outcome.png"),
        ("Least-privilege analyst", "dq26_analyst_dashboard_overview.png"),
    ]
    for title, filename in gallery:
        path = SCREENSHOTS / filename
        if path.exists():
            st.markdown(f"**{title}**")
            st.image(str(path), width="stretch")


def main() -> None:
    st.set_page_config(page_title="Data Quest", page_icon="DQ", layout="wide")
    inject_styles()
    data = load_manifest()
    page = st.sidebar.radio(
        "Data Quest",
        ["Overview", "Explore results", "Engineering", "Failure laboratory", "Evidence room"],
    )
    st.sidebar.caption(data["snapshot_label"])
    st.sidebar.markdown("[View source repository](https://github.com/Hgaines88/data-quest)")

    if page == "Overview":
        overview(data)
    elif page == "Explore results":
        results(data)
    elif page == "Engineering":
        engineering(data)
    elif page == "Failure laboratory":
        failure_lab()
    else:
        evidence(data)


if __name__ == "__main__":
    main()
