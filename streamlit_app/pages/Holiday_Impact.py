"""Streamlit dashboard for holiday impact analysis.

This page shows how holidays affect bike demand patterns compared to regular weekdays.
"""

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# Page configuration
st.set_page_config(
    page_title="Holiday Impact Analysis",
    page_icon="🎉",
    layout="wide",
)


@st.cache_resource
def get_db_connection():
    """Create and cache DuckDB connection."""
    return duckdb.connect("duckdb/warehouse.duckdb", read_only=True)


@st.cache_data(ttl=600)
def load_holiday_summary():
    """Load holiday impact summary mart."""
    con = get_db_connection()
    query = """
        SELECT *
        FROM main_marts.mart_holiday_impact_summary
        ORDER BY holiday_date
    """
    try:
        df = con.execute(query).df()
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()


def main():
    """Main Streamlit app for holiday impact analysis."""
    st.title("🎉 Holiday Impact Analysis")
    st.markdown("Analyze bike demand patterns on holidays vs regular weekdays")
    st.markdown("---")

    # Load data
    holiday_summary = load_holiday_summary()

    # Check if data exists
    if holiday_summary.empty:
        st.error(
            "No holiday data available. Please run:\n\n"
            "1. Holiday data ingestion: `uv run python dlt_pipeline/holidays.py`\n"
            "2. dbt transformations: `cd dbt && uv run dbt build`"
        )
        st.stop()

    # Holiday selector
    selected_holiday = st.selectbox(
        "Select Holiday",
        options=holiday_summary['holiday_name'].unique(),
        help="Choose a holiday to analyze its impact on bike demand"
    )

    # Filter to selected holiday
    holiday_data = holiday_summary[
        holiday_summary['holiday_name'] == selected_holiday
    ].iloc[0]

    # Section 1: KPI Cards
    st.subheader("📊 Key Metrics")

    col1, col2, col3 = st.columns(3)

    with col1:
        trips_pct = holiday_data['trips_pct_change']
        trips_abs = holiday_data['trips_abs_change']
        st.metric(
            label="Total Trips Change",
            value=f"{trips_pct:.1f}%",
            delta=f"{int(trips_abs):,} trips",
            help="Percentage change in total trips compared to baseline weekdays"
        )

    with col2:
        duration_pct = holiday_data['duration_pct_change']
        duration_abs = holiday_data['duration_abs_change']
        st.metric(
            label="Avg Duration Change",
            value=f"{duration_pct:.1f}%",
            delta=f"{duration_abs:.1f} mins",
            help="Percentage change in average trip duration"
        )

    with col3:
        # Placeholder for statistical significance (will be implemented in Slice 11)
        st.metric(
            label="Statistical Significance",
            value="Pending",
            delta="p-value TBD",
            help="Statistical significance of the observed changes (to be implemented)"
        )

    # Display baseline info
    st.markdown("---")
    st.caption(
        f"**Baseline Period:** {holiday_data['baseline_start_date']} to "
        f"{holiday_data['baseline_end_date']} "
        f"({int(holiday_data['baseline_days_count'])} weekdays)"
    )
    st.caption(
        f"**Holiday Type:** "
        f"{'Major Holiday' if holiday_data['is_major'] else 'Minor Holiday'} | "
        f"{'Non-Working Day' if not holiday_data['is_working_day'] else 'Working Day'}"
    )

    # Footer
    st.markdown("---")
    st.markdown(
        "*Holiday Data: Nager.Date API | Bike Data: NYC Citi Bike | "
        "Baseline: ±15 day weekdays*"
    )


if __name__ == "__main__":
    main()
