from __future__ import annotations

import json
import hashlib
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO = Path(__file__).resolve().parent
MANIFEST = PORTFOLIO / "data" / "evidence_manifest.json"
GOLD_SNAPSHOT = PORTFOLIO / "data" / "gold_snapshot"
ARCHITECTURE = ROOT / "docs" / "architecture" / "data-quest-architecture.png"
SCREENSHOTS = ROOT / "docs" / "screenshots"


@st.cache_data
def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@st.cache_data
def load_gold_snapshot() -> tuple[dict, dict[str, pd.DataFrame]]:
    snapshot = json.loads(
        (GOLD_SNAPSHOT / "snapshot_manifest.json").read_text(encoding="utf-8")
    )
    frames = {}
    for contract, details in snapshot["contracts"].items():
        path = GOLD_SNAPSHOT / details["file"]
        observed_digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed_digest != details["sha256"]:
            raise ValueError(f"Snapshot digest mismatch for {contract}")
        frame = pd.read_csv(path)
        if len(frame) != details["row_count"]:
            raise ValueError(f"Snapshot row-count mismatch for {contract}")
        frames[contract] = frame
    return snapshot, frames


def inject_styles() -> None:
    st.markdown(
        """
        <style>
          :root { --dq-navy: #102a43; --dq-blue: #2f80c1; --dq-mint: #dff6ec;
                  --dq-border: #b8c9da; --dq-muted: #52677d; }
          .stApp { background: #f7f9fc; color: #102a43; }
          .block-container { max-width: 1180px; padding-top: 3.75rem; }
          .dq-kicker { color: #2f80c1; font-size: .82rem; font-weight: 750;
                       letter-spacing: .12em; text-transform: uppercase; }
          .dq-hero { color: #102a43; font-size: clamp(2.4rem, 6vw, 5rem);
                     line-height: .98; font-weight: 850; margin: .25rem 0 1rem; }
          .dq-subtitle { color: #52677d; font-size: 1.18rem; max-width: 780px; }
          .dq-boundary { border-left: 4px solid #2f80c1; background: #eef6fc;
                         padding: 1rem 1.1rem; border-radius: 0 .65rem .65rem 0; }
          .dq-stack { display: flex; flex-wrap: wrap; gap: .55rem; margin: .8rem 0 1rem; }
          .dq-stack span { background: #102a43; border: 1px solid #102a43;
                           border-radius: 999px; color: #ffffff; font-size: .9rem;
                           font-weight: 720; padding: .38rem .72rem; }
          .dq-links { display: flex; flex-wrap: wrap; gap: .7rem; margin: .35rem 0 1.3rem; }
          .dq-links a { background: #ffffff; border: 2px solid #2f80c1;
                        border-radius: .58rem; color: #155f91 !important;
                        font-weight: 750; padding: .58rem .82rem; text-decoration: none; }
          .dq-links a:hover { background: #e9f4fc; border-color: #155f91; }
          .dq-pass { color: #176b49; font-weight: 750; }
          [data-testid="stMetric"] { background: white; border: 1px solid #dbe5ef;
                                     padding: .8rem; border-radius: .8rem; }
          [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {
            color: #102a43;
          }
          .dq-callout { border: 1px solid var(--dq-border); border-left-width: 6px;
                        border-radius: .72rem; color: var(--dq-navy);
                        margin: .75rem 0 1rem; padding: .9rem 1rem; }
          .dq-callout strong { color: var(--dq-navy); display: block;
                               font-size: 1.02rem; margin-bottom: .22rem; }
          .dq-callout p { color: #263f58; margin: 0; }
          .dq-callout-info { background: #e9f4fc; border-color: #2f80c1; }
          .dq-callout-success { background: #e8f7ef; border-color: #23845d; }

          /* Keep tabs readable in light and dark browser themes. */
          [data-baseweb="tab-list"], [role="tablist"] { gap: .45rem; }
          [data-baseweb="tab"], [role="tab"],
          [data-testid="stTabs"] button, button[id*="-tab-"] {
            background: #e8eef5 !important; border: 1px solid #b8c9da !important;
            border-radius: .55rem .55rem 0 0 !important;
            min-height: 2.85rem; padding: .55rem .9rem !important;
          }
          [data-baseweb="tab"] p, [data-baseweb="tab"] span,
          [role="tab"], [role="tab"] p, [role="tab"] span,
          [data-testid="stTabs"] button, [data-testid="stTabs"] button p,
          [data-testid="stTabs"] button span, button[id*="-tab-"],
          button[id*="-tab-"] p, button[id*="-tab-"] span {
            color: #17324d !important; font-weight: 720 !important;
          }
          [data-baseweb="tab"][aria-selected="true"],
          [role="tab"][aria-selected="true"],
          [data-testid="stTabs"] button[aria-selected="true"],
          button[id*="-tab-"][aria-selected="true"] {
            background: #102a43 !important; border-color: #102a43 !important;
          }
          [data-baseweb="tab"][aria-selected="true"] p,
          [data-baseweb="tab"][aria-selected="true"] span,
          [role="tab"][aria-selected="true"],
          [role="tab"][aria-selected="true"] p,
          [role="tab"][aria-selected="true"] span,
          [data-testid="stTabs"] button[aria-selected="true"],
          [data-testid="stTabs"] button[aria-selected="true"] p,
          [data-testid="stTabs"] button[aria-selected="true"] span,
          button[id*="-tab-"][aria-selected="true"],
          button[id*="-tab-"][aria-selected="true"] p,
          button[id*="-tab-"][aria-selected="true"] span { color: #ffffff !important; }

          /* Make text inputs look unmistakably interactive. */
          [data-testid="stTextInput"] label p { color: #17324d !important;
                                                font-size: 1rem !important;
                                                font-weight: 760 !important; }
          [data-testid="stTextInput"] [data-baseweb="input"] {
            background: #ffffff !important; border: 2px solid #537a9e !important;
            border-radius: .62rem !important; box-shadow: 0 1px 2px rgba(16,42,67,.08);
          }
          [data-testid="stTextInput"] input { color: #102a43 !important;
                                               background: #ffffff !important; }
          [data-testid="stTextInput"] input::placeholder { color: #65798d !important;
                                                            opacity: 1; }
          [data-testid="stTextInput"] [data-baseweb="input"]:focus-within {
            border-color: #176da8 !important; box-shadow: 0 0 0 3px rgba(47,128,193,.18);
          }
          [data-testid="stSelectbox"] label p { color: #17324d !important;
                                                font-size: 1rem !important;
                                                font-weight: 760 !important; }
          [data-testid="stCaptionContainer"] p { color: #40566c !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero() -> None:
    st.markdown('<div class="dq-kicker">Governed public-data engineering</div>', unsafe_allow_html=True)
    st.markdown('<div class="dq-hero">Data Quest</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="dq-subtitle">A production-style Databricks data engineering project built with Python, PySpark, and Spark SQL—turning public labor and population data into validated, observable, and access-controlled analytical results.</div>',
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


def implementation_paths() -> None:
    st.markdown("### Databricks implementation")
    st.markdown(
        """
        <div class="dq-stack">
          <span>Databricks</span><span>Python</span><span>PySpark</span>
          <span>Spark SQL</span><span>Unity Catalog</span>
          <span>Bronze · Silver · Gold</span>
        </div>
        <div class="dq-links">
          <a href="https://github.com/Hgaines88/data-quest/tree/codex/public-portfolio/notebooks" target="_blank">Landing notebooks</a>
          <a href="https://github.com/Hgaines88/data-quest/tree/codex/public-portfolio/pipelines" target="_blank">PySpark pipelines</a>
          <a href="https://github.com/Hgaines88/data-quest/tree/codex/public-portfolio/sql" target="_blank">Spark SQL and validation</a>
          <a href="https://github.com/Hgaines88/data-quest/tree/codex/public-portfolio/docs/evidence" target="_blank">Databricks execution evidence</a>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "The Databricks workspace is authenticated. These version-controlled notebooks, "
        "pipelines, SQL contracts, and captured execution records provide the public review path."
    )


def overview(data: dict) -> None:
    hero()
    st.write("")
    boundary_note()
    st.write("")
    implementation_paths()
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
    snapshot, frames = load_gold_snapshot()

    st.subheader("Question 1 · Population, 2013–2018")
    q1 = frames["gold_population_summary_2013_2018"].iloc[0]
    cols = st.columns(3)
    cols[0].metric("Mean population", f"{q1['mean_population'] / 1_000_000:.1f}M")
    cols[1].metric("Population std. deviation", f"{q1['population_stddev'] / 1_000_000:.1f}M")
    cols[2].metric("Complete annual values", int(q1["year_count"]))
    st.caption("Population standard deviation is used because the six requested annual values form the complete finite range, not a sample.")

    st.subheader("Question 2 · Best year for every BLS series")
    q2_contract = contracts["best_year_by_series"]
    q2 = frames["gold_bls_best_year_by_series"]
    sample = q2.loc[q2["series_id"] == q2_contract["representative_result"]["series_id"]].iloc[0]
    cols = st.columns(3)
    cols[0].metric("Published series", f"{len(q2):,}")
    cols[1].metric("Selected year", int(sample["best_year"]))
    cols[2].metric("Q01–Q04 sum", sample["annual_quarterly_sum"])
    st.caption(f"Representative validated series: `{sample['series_id']}`")
    st.markdown(
        '<div class="dq-callout dq-callout-info"><strong>Annual-sum rule</strong>'
        '<p>Q05 is excluded because BLS defines it as an annual average, not a fifth quarter. '
        'Equal maxima resolve to the earliest year.</p></div>',
        unsafe_allow_html=True,
    )
    query = st.text_input(
        "Filter the 282 governed series",
        placeholder="Type a series ID or description…",
        help="Enter any portion of a BLS series ID or its readable label.",
    ).strip()
    visible_q2 = q2
    if query:
        mask = q2["series_id"].str.contains(query, case=False, na=False) | q2[
            "series_label"
        ].str.contains(query, case=False, na=False)
        visible_q2 = q2.loc[mask]
    st.dataframe(
        visible_q2[
            [
                "series_id",
                "series_label",
                "best_year",
                "annual_quarterly_sum",
                "quarterly_observation_count",
            ]
        ],
        hide_index=True,
        width="stretch",
        height=330,
    )
    st.caption(f"Showing {len(visible_q2):,} of {len(q2):,} authoritative Gold rows.")

    st.subheader("Question 3 · Q01 history with population context")
    q3_contract = contracts["q01_population"]
    q3 = frames["gold_bls_q01_population"]
    matched = int(q3["population_match_found"].sum())
    cols = st.columns(3)
    cols[0].metric("BLS observations retained", len(q3))
    cols[1].metric("Population matches", matched)
    cols[2].metric("Visible null matches", len(q3) - matched)
    st.caption(f"`{q3_contract['series_id']}` · {q3_contract['series_label']}")

    q01_chart = (
        alt.Chart(q3)
        .mark_line(point=True, color="#2f80c1")
        .encode(
            x=alt.X("year:O", title="Year"),
            y=alt.Y("q01_value:Q", title="Q01 value"),
            tooltip=["year:O", "q01_value:Q"],
        )
        .properties(height=300)
    )
    st.altair_chart(q01_chart, use_container_width=True)
    st.dataframe(
        q3[["year", "q01_value", "population", "population_match_found"]],
        hide_index=True,
        width="stretch",
        height=330,
    )
    st.caption("All 39 Gold rows are shown. Missing population remains NULL and never removes a valid BLS observation.")
    st.caption(f"Verified export snapshot: `{snapshot['snapshot_id']}`")


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
    st.subheader("Failure laboratory: What happens when something goes wrong?")
    st.write(
        "Choose a condition to see the contract-driven response. These scenarios explain "
        "implemented behavior without mutating the published evidence."
    )
    scenarios = {
        "Unchanged source digest": ("Discard staged bytes", "Record the successful run, publish no redundant manifest transition, and retain the existing immutable object."),
        "Duplicate business key": ("Block publication", "A uniqueness violation can fan out joins or misstate aggregates. The prior materialized result remains authoritative."),
        "Missing population match": ("Preserve the BLS row", "Population stays NULL and the explicit match indicator is false. Absence of context does not erase a valid observation."),
        "Incomplete quarterly year": ("Do not invent a complete annual result", "Only the defined Q01-Q04 contract can support the requested annual sum; incompleteness remains visible."),
        "Landing failure before publication": ("Keep last-good state", "Staging is cleaned, the sanitized failure is audited, and no partial manifest transition becomes current."),
        "Changed digest": ("Create a new immutable version", "Advance the candidate through validation while retaining prior source versions and provenance."),
    }
    selected = st.selectbox("Choose a failure condition", list(scenarios))
    outcome, explanation = scenarios[selected]
    st.markdown(
        f'<div class="dq-callout dq-callout-success"><strong>{outcome}</strong>'
        f'<p>{explanation}</p></div>',
        unsafe_allow_html=True,
    )


def evidence(data: dict) -> None:
    st.title("Evidence room")
    st.write(data["snapshot_label"])
    snapshot, _ = load_gold_snapshot()
    st.markdown(
        '<div class="dq-callout dq-callout-success">'
        '<strong>Complete governed Gold snapshot verified</strong>'
        f'<p>Snapshot {snapshot["snapshot_id"]} · 1 / 282 / 39 rows</p></div>',
        unsafe_allow_html=True,
    )
    with st.expander("Gold snapshot provenance and SHA-256 digests"):
        st.json(snapshot)
    st.markdown("Every public claim maps back to committed validation records and curated screenshots.")
    for source in data["evidence_sources"]:
        st.code(source, language=None)

    st.divider()
    failure_lab()

    st.divider()
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
        ["Overview", "Explore results", "Engineering", "Evidence room"],
    )
    st.sidebar.caption(data["snapshot_label"])
    st.sidebar.markdown("[View source repository](https://github.com/Hgaines88/data-quest)")

    if page == "Overview":
        overview(data)
    elif page == "Explore results":
        results(data)
    elif page == "Engineering":
        engineering(data)
    else:
        evidence(data)


if __name__ == "__main__":
    main()
