"""Streamlit dashboard for bike demand analytics - Home page.

This is the main page showing bike trip demand trends and key metrics.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import duckdb


# Page configuration
st.set_page_config(
    page_title="Bike Demand Dashboard",
    page_icon="🚲",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def get_db_connection():
    """Create and cache DuckDB connection."""
    return duckdb.connect("duckdb/warehouse.duckdb", read_only=True)


@st.cache_data(ttl=600)
def load_demand_data():
    """Load daily demand data from the marts."""
    con = get_db_connection()
    query = """
        SELECT *
        FROM main_marts.mart_demand_daily
        ORDER BY ride_date
    """
    try:
        df = con.execute(query).df()
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=600)
def load_station_stats():
    """Load station usage statistics from the marts layer."""
    con = get_db_connection()
    query = """
        SELECT
            station_name,
            start_trip_count as trip_count
        FROM main_marts.mart_station_stats
        ORDER BY start_trip_count DESC
        LIMIT 10
    """
    try:
        df = con.execute(query).df()
        return df
    except Exception as e:
        st.error(f"Error loading station stats: {e}")
        return pd.DataFrame()


def main():
    """Main Streamlit app."""
    st.title("🚲 NYC Bike Demand Dashboard")
    st.markdown("### Analyzing bike-share trip patterns and demand trends")

    # Load data
    df = load_demand_data()

    if df.empty:
        st.warning(
            "No data available. Please run the data pipeline first:\n\n"
            "1. Run bike data ingestion: `uv run python dlt_pipeline/bike.py`\n"
            "2. Run dbt transformations: `cd dbt && dbt build`"
        )
        return

    # Key Metrics Row
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)

    total_trips = df["trips_total"].sum()
    avg_daily_trips = df["trips_total"].mean()
    avg_duration = df["avg_duration_mins"].mean()
    member_pct = (df["member_trips"].sum() / total_trips * 100) if total_trips > 0 else 0

    with col1:
        st.metric("Total Trips", f"{total_trips:,.0f}")

    with col2:
        st.metric("Avg Daily Trips", f"{avg_daily_trips:,.0f}")

    with col3:
        st.metric("Avg Duration", f"{avg_duration:.1f} min")

    with col4:
        st.metric("Member %", f"{member_pct:.1f}%")

    # Daily Trips Trend
    st.markdown("---")
    st.subheader("📈 Daily Trip Trends")

    fig_trips = px.line(
        df,
        x="ride_date",
        y="trips_total",
        title="Total Trips Over Time",
        labels={"ride_date": "Date", "trips_total": "Number of Trips"},
        color_discrete_sequence=["#1f77b4"],
    )
    fig_trips.update_layout(hovermode="x unified", height=400)
    st.plotly_chart(fig_trips, use_container_width=True)

    # Member vs Casual Breakdown
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("👥 Member vs Casual Split")
        fig_pie = go.Figure(
            data=[
                go.Pie(
                    labels=["Member", "Casual"],
                    values=[df["member_trips"].sum(), df["casual_trips"].sum()],
                    hole=0.3,
                    marker_colors=["#2ca02c", "#ff7f0e"],
                )
            ]
        )
        fig_pie.update_layout(height=350)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.subheader("📅 Weekday vs Weekend")
        weekday_data = df.groupby("day_type")["trips_total"].sum().reset_index()
        fig_bar = px.bar(
            weekday_data,
            x="day_type",
            y="trips_total",
            title="Trips by Day Type",
            labels={"day_type": "Day Type", "trips_total": "Total Trips"},
            color="day_type",
            color_discrete_map={"Weekday": "#1f77b4", "Weekend": "#ff7f0e"},
        )
        fig_bar.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)

    # Top Stations
    st.markdown("---")
    st.subheader("🏆 Top 10 Start Stations")
    station_df = load_station_stats()

    if not station_df.empty:
        # Show most popular stations on top
        station_df_sorted = station_df.sort_values("trip_count", ascending=False)
        fig_stations = px.bar(
            station_df_sorted,
            x="trip_count",
            y="station_name",
            orientation="h",
            title="Most Popular Starting Stations",
            labels={"trip_count": "Number of Trips", "station_name": "Station"},
            color="trip_count",
            color_continuous_scale="Blues",
        )
        fig_stations.update_layout(height=500, showlegend=False)
        st.plotly_chart(fig_stations, use_container_width=True)

    # Data Preview
    st.markdown("---")
    with st.expander("📊 View Raw Data"):
        st.dataframe(df, use_container_width=True)

    # Footer
    st.markdown("---")
    st.markdown("*Data Source: NYC Citi Bike | Last Updated: Check pipeline run logs*")


if __name__ == "__main__":
    main()
