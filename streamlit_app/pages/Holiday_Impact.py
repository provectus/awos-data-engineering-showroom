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

    # Section 2: Demand Comparison Chart
    st.markdown("---")
    st.subheader("📊 Demand Comparison: Holiday vs Baseline")

    # Prepare data for the chart
    categories = ['Total Trips', 'Avg Duration', 'Member Trips', 'Casual Trips']
    baseline_values = [
        holiday_data['total_trips_baseline'],
        holiday_data['avg_duration_baseline'],
        holiday_data['member_trips_baseline'],
        holiday_data['casual_trips_baseline']
    ]
    holiday_values = [
        holiday_data['total_trips_holiday'],
        holiday_data['avg_duration_holiday'],
        holiday_data['member_trips_holiday'],
        holiday_data['casual_trips_holiday']
    ]

    # Create grouped bar chart
    fig = go.Figure()

    # Add baseline bars
    fig.add_trace(go.Bar(
        name='Baseline',
        x=categories,
        y=baseline_values,
        marker_color='lightblue',
        text=[f'{v:,.0f}' for v in baseline_values],
        textposition='outside'
    ))

    # Add holiday bars
    fig.add_trace(go.Bar(
        name='Holiday',
        x=categories,
        y=holiday_values,
        marker_color='darkblue',
        text=[f'{v:,.0f}' for v in holiday_values],
        textposition='outside'
    ))

    # Update layout
    fig.update_layout(
        barmode='group',
        height=400,
        title=f"{selected_holiday}: Demand Metrics Comparison",
        yaxis_title="Count / Duration (mins)",
        xaxis_title="Metric",
        hovermode='x unified',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    # Display chart
    st.plotly_chart(fig, use_container_width=True)

    # Add interpretation
    st.caption(
        "💡 **Interpretation:** Blue bars (Holiday) vs light blue bars (Baseline). "
        "Shorter holiday bars indicate decreased demand, taller bars indicate increased demand."
    )

    # Footer
    st.markdown("---")
    st.markdown(
        "*Holiday Data: Nager.Date API | Bike Data: NYC Citi Bike | "
        "Baseline: ±15 day weekdays*"
    )


if __name__ == "__main__":
    main()
