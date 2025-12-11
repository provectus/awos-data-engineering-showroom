"""Streamlit dashboard for data quality monitoring.

This page shows test results and data freshness status.
"""

from datetime import datetime

import pandas as pd
import streamlit as st

import duckdb


# Page configuration
st.set_page_config(
    page_title="Data Quality Monitor",
    page_icon="✅",
    layout="wide",
)

# Freshness thresholds (days)
FRESHNESS_WARN_DAYS = 10
FRESHNESS_ERROR_DAYS = 15


@st.cache_resource
def get_db_connection():
    """Create and cache DuckDB connection."""
    return duckdb.connect("duckdb/warehouse.duckdb", read_only=True)


@st.cache_data(ttl=300)
def load_latest_results() -> pd.DataFrame:
    """Load latest test results from data_quality.test_results."""
    conn = get_db_connection()
    query = """
        WITH latest_run AS (
            SELECT MAX(run_timestamp) as max_ts
            FROM data_quality.test_results
        )
        SELECT
            run_id,
            run_timestamp,
            test_type,
            test_name,
            status,
            failure_message,
            source_name
        FROM data_quality.test_results
        WHERE run_timestamp = (SELECT max_ts FROM latest_run)
        ORDER BY test_type, test_name
    """
    try:
        return conn.execute(query).df()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_freshness_data() -> pd.DataFrame:
    """Load freshness data for all raw sources."""
    conn = get_db_connection()

    sources = [
        ("bike_trips", "raw_bike.bike_trips", "started_at"),
        ("weather", "raw_weather.daily_weather", "CAST(date AS DATE)"),
        ("holidays", "raw_holidays.us_holidays", "CAST(date AS DATE)"),
        ("games", "raw_games.mlb_games", "CAST(game_date AS DATE)"),
    ]

    freshness_data = []
    for name, table, date_col in sources:
        try:
            result = conn.execute(f"SELECT MAX({date_col}) FROM {table}").fetchone()
            last_date = result[0] if result else None
            freshness_data.append({"source": name, "last_date": last_date})
        except Exception:
            freshness_data.append({"source": name, "last_date": None})

    return pd.DataFrame(freshness_data)


def get_freshness_status(last_date, today) -> tuple[str, str]:
    """Determine freshness status and color based on age."""
    if last_date is None:
        return "NO DATA", "red"

    if hasattr(last_date, "date"):
        last_date = last_date.date()

    days_old = (today - last_date).days

    if days_old > FRESHNESS_ERROR_DAYS:
        return f"STALE ({days_old}d)", "red"
    elif days_old > FRESHNESS_WARN_DAYS:
        return f"WARN ({days_old}d)", "orange"
    else:
        return f"OK ({days_old}d)", "green"


def main():
    """Main Streamlit app for data quality monitoring."""
    st.title("✅ Data Quality Monitor")
    st.markdown("### Automated data quality checks and freshness monitoring")

    # Load data
    results_df = load_latest_results()
    freshness_df = load_freshness_data()

    if results_df.empty:
        st.warning(
            "No test results found. Please run the data quality DAG first:\n\n"
            "```bash\n"
            "uv run python -c \"from data_quality.validate_all import main; main()\"\n"
            "```\n\n"
            "Or trigger via Airflow: `uv run airflow dags trigger data_quality_dag`"
        )
        # Still show freshness even without test results
        if not freshness_df.empty:
            st.subheader("📅 Data Freshness")
            display_freshness_section(freshness_df)
        return

    # Show last run timestamp
    last_run = results_df["run_timestamp"].iloc[0]
    st.caption(f"Last validation run: {last_run}")

    # KPI Cards Section
    st.subheader("📊 Test Summary")
    display_kpi_cards(results_df)

    # Data Freshness Section
    st.subheader("📅 Data Freshness")
    display_freshness_section(freshness_df)

    # Failed Tests Section
    st.subheader("❌ Failed Tests")
    display_failed_tests(results_df)

    # All Results Section
    with st.expander("📋 View All Test Results"):
        st.dataframe(
            results_df[["test_type", "test_name", "status", "source_name", "failure_message"]],
            use_container_width=True,
            hide_index=True,
        )


def display_kpi_cards(results_df: pd.DataFrame):
    """Display KPI cards for test summary."""
    total = len(results_df)
    passed = len(results_df[results_df["status"] == "pass"])
    failed = total - passed
    pass_rate = (passed / total * 100) if total > 0 else 0

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Tests", total)

    with col2:
        st.metric("Passed", passed, delta=None)

    with col3:
        st.metric("Failed", failed, delta=None, delta_color="inverse" if failed > 0 else "off")

    with col4:
        st.metric("Pass Rate", f"{pass_rate:.0f}%")


def display_freshness_section(freshness_df: pd.DataFrame):
    """Display data freshness status for each source."""
    today = datetime.now().date()

    cols = st.columns(len(freshness_df))

    for idx, row in freshness_df.iterrows():
        source = row["source"]
        last_date = row["last_date"]
        status, color = get_freshness_status(last_date, today)

        with cols[idx]:
            st.markdown(f"**{source.replace('_', ' ').title()}**")

            if last_date is not None:
                if hasattr(last_date, "strftime"):
                    date_str = last_date.strftime("%Y-%m-%d")
                else:
                    date_str = str(last_date)
                st.markdown(f"Last data: `{date_str}`")
            else:
                st.markdown("Last data: `N/A`")

            if color == "green":
                st.success(status)
            elif color == "orange":
                st.warning(status)
            else:
                st.error(status)


def display_failed_tests(results_df: pd.DataFrame):
    """Display failed tests with details."""
    failed_df = results_df[results_df["status"] == "fail"]

    if failed_df.empty:
        st.success("All tests passed!")
        return

    st.error(f"{len(failed_df)} test(s) failed")

    for _, row in failed_df.iterrows():
        with st.expander(f"❌ {row['test_name']} ({row['test_type'].upper()})"):
            st.markdown(f"**Source:** {row['source_name']}")
            st.markdown(f"**Type:** {row['test_type']}")
            if row["failure_message"]:
                st.markdown(f"**Details:** {row['failure_message']}")
            else:
                st.markdown("**Details:** No additional details available")


if __name__ == "__main__":
    main()
else:
    main()
