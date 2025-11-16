"""Streamlit dashboard for holiday impact analysis.

This page shows how holidays affect bike demand patterns compared to regular weekdays.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.cluster import KMeans

import duckdb


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


@st.cache_data(ttl=600)
def load_holiday_by_station(holiday_date):
    """Load station-level holiday impact data for a specific holiday."""
    con = get_db_connection()
    query = """
        SELECT *
        FROM main_marts.mart_holiday_impact_by_station
        WHERE holiday_date = ?
        ORDER BY trips_pct_change DESC
    """
    try:
        df = con.execute(query, [holiday_date]).df()
        return df
    except Exception as e:
        st.error(f"Error loading station data: {e}")
        return pd.DataFrame()


def get_rebalancing_flag(pct_change):
    """Determine rebalancing action based on percentage change."""
    if pct_change > 30:
        return 'Add bikes'
    elif pct_change < -30:
        return 'Remove bikes'
    else:
        return 'No action'


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

    # Section 3: Station-Level Demand Changes (Clustered)
    st.markdown("---")
    st.subheader("🗺️ Neighborhood-Level Demand Changes")

    # Add cluster count slider
    n_clusters = st.slider(
        "Number of Neighborhoods to Display",
        min_value=10,
        max_value=50,
        value=30,
        step=5,
        help="Adjust to show more or fewer neighborhood clusters"
    )

    # Load station data
    station_data = load_holiday_by_station(holiday_data['holiday_date'])

    if not station_data.empty:
        # Perform K-Means clustering
        coords = station_data[['latitude', 'longitude']].values
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        station_data['cluster'] = kmeans.fit_predict(coords)

        # Aggregate by cluster
        cluster_agg = station_data.groupby('cluster').agg({
            'trips_holiday': 'sum',
            'trips_baseline': 'sum',
            'trips_abs_change': 'sum',
            'latitude': 'mean',  # Cluster centroid
            'longitude': 'mean',
            'station_id': 'count',  # Number of stations in cluster
            'area': lambda x: x.mode()[0] if len(x.mode()) > 0 else 'Mixed'  # Most common area
        }).reset_index()

        # Calculate percentage change for clusters
        cluster_agg['trips_pct_change'] = (
            (cluster_agg['trips_holiday'] - cluster_agg['trips_baseline']) /
            cluster_agg['trips_baseline'].replace(0, np.nan)
        ) * 100

        # Apply rebalancing flag
        cluster_agg['rebalancing_flag'] = cluster_agg['trips_pct_change'].apply(get_rebalancing_flag)

        # Create map
        fig = px.scatter_mapbox(
            cluster_agg,
            lat="latitude",
            lon="longitude",
            color="trips_pct_change",
            size=abs(cluster_agg["trips_abs_change"]),
            color_continuous_scale=["red", "yellow", "green"],
            color_continuous_midpoint=0,
            hover_data={
                "area": True,
                "trips_pct_change": ":.1f",
                "trips_holiday": ":,.0f",
                "trips_baseline": ":.1f",
                "rebalancing_flag": True,
                "station_id": True,  # Show number of stations in cluster
                "latitude": False,
                "longitude": False
            },
            zoom=10,
            center={"lat": 40.73, "lon": -73.94},
            mapbox_style="open-street-map",
            height=600,
            title=f"Neighborhood Demand Changes: {selected_holiday} ({n_clusters} Clusters)"
        )

        fig.update_layout(
            coloraxis_colorbar=dict(
                title="% Change",
                ticksuffix="%"
            )
        )

        st.plotly_chart(fig, use_container_width=True)

        # Add legend/interpretation
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🔴 Red Clusters", "Decreased Demand", "Remove bikes")
        with col2:
            st.metric("🟡 Yellow Clusters", "Stable Demand", "No action")
        with col3:
            st.metric("🟢 Green Clusters", "Increased Demand", "Add bikes")

        st.caption(
            f"💡 **Interpretation:** Map shows {n_clusters} neighborhood clusters aggregated from {len(station_data)} stations. "
            "Larger circles indicate bigger absolute changes. Hover to see cluster details including number of stations. "
            "Adjust slider above to show more or fewer neighborhoods."
        )
    else:
        st.warning("No station data available for this holiday.")

    # Footer
    st.markdown("---")
    st.markdown(
        "*Holiday Data: Nager.Date API | Bike Data: NYC Citi Bike | "
        "Baseline: ±15 day weekdays*"
    )


if __name__ == "__main__":
    main()
