"""Streamlit dashboard for baseball game impact analysis.

This page shows how Yankees and Mets home games affect bike demand at nearby stations,
with actionable rebalancing recommendations for operations managers.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import duckdb


# Page configuration
st.set_page_config(
    page_title="Baseball Game Impact",
    page_icon="⚾",
    layout="wide",
)


@st.cache_resource
def get_db_connection():
    """Create and cache DuckDB connection."""
    return duckdb.connect("duckdb/warehouse.duckdb", read_only=True)


@st.cache_data(ttl=600)
def load_stadiums():
    """Load list of stadiums."""
    con = get_db_connection()
    query = """
        SELECT DISTINCT stadium_name
        FROM main_core.dim_stadiums
        ORDER BY stadium_name
    """
    try:
        df = con.execute(query).df()
        return df['stadium_name'].tolist()
    except Exception as e:
        st.error(f"Error loading stadiums: {e}")
        return []


@st.cache_data(ttl=600)
def load_games(stadium_name):
    """Load games for a specific stadium."""
    con = get_db_connection()
    query = """
        SELECT
            game_id,
            game_date,
            game_datetime_rounded as game_datetime,
            home_team_name || ' vs ' || away_team_name as matchup,
            DAYNAME(game_date) as day_of_week
        FROM main_staging.stg_games
        WHERE stadium_name = ?
          AND stadium_name IN ('Yankee Stadium', 'Citi Field')
        ORDER BY game_date
    """
    try:
        df = con.execute(query, [stadium_name]).df()
        return df
    except Exception as e:
        st.error(f"Error loading games: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=600)
def load_rebalancing_recommendations(stadium_name, hour_offset):
    """Load rebalancing recommendations for a specific stadium and hour offset."""
    con = get_db_connection()
    query = """
        SELECT
            r.station_name,
            r.hour_offset,
            ROUND(r.avg_net_flow, 2) as avg_net_flow,
            r.bikes_to_add_or_remove,
            r.rebalancing_recommendation,
            ROUND(r.avg_trips_started, 1) as avg_trips_started,
            ROUND(r.avg_trips_ended, 1) as avg_trips_ended,
            r.num_games,
            ROUND(r.pct_capacity_adjustment, 1) as pct_capacity_adjustment
        FROM main_marts.mart_game_rebalancing r
        WHERE r.stadium_name = ?
          AND r.hour_offset = ?
        ORDER BY ABS(r.avg_net_flow) DESC
    """
    try:
        df = con.execute(query, [stadium_name, hour_offset]).df()
        return df
    except Exception as e:
        st.error(f"Error loading rebalancing data: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=600)
def load_demand_comparison(stadium_name):
    """Load aggregated demand comparison for a stadium across all games."""
    con = get_db_connection()
    query = """
        SELECT
            hour_offset,
            AVG(trips_started_game_day) as avg_trips_started_game,
            AVG(trips_started_baseline) as avg_trips_started_baseline,
            AVG(trips_ended_game_day) as avg_trips_ended_game,
            AVG(trips_ended_baseline) as avg_trips_ended_baseline
        FROM main_marts.mart_game_day_demand
        WHERE stadium_name = ?
        GROUP BY hour_offset
        ORDER BY hour_offset
    """
    try:
        df = con.execute(query, [stadium_name]).df()
        return df
    except Exception as e:
        st.error(f"Error loading demand comparison: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=600)
def load_nearby_stations(stadium_name):
    """Load stations within 1km of a stadium."""
    con = get_db_connection()
    query = """
        SELECT
            p.station_name,
            s.latitude,
            s.longitude,
            ROUND(p.distance_km, 3) as distance_km
        FROM main_core.fct_station_proximity p
        JOIN main_core.dim_stations s ON p.station_id = s.station_id
        JOIN main_core.dim_stadiums st ON p.stadium_id = st.stadium_id
        WHERE st.stadium_name = ?
          AND p.within_1km = true
        ORDER BY p.distance_km
    """
    try:
        df = con.execute(query, [stadium_name]).df()
        # Also get stadium coordinates
        stadium_query = """
            SELECT latitude, longitude FROM main_core.dim_stadiums
            WHERE stadium_name = ?
        """
        stadium_df = con.execute(stadium_query, [stadium_name]).df()
        return df, stadium_df
    except Exception as e:
        st.error(f"Error loading station map data: {e}")
        return pd.DataFrame(), pd.DataFrame()


# Main dashboard
st.title("⚾ Baseball Game Impact Analysis")
st.markdown("""
Analyze how Yankees and Mets home games impact bike demand at nearby stations.
Use this dashboard to plan bike rebalancing operations before and after games.
""")

# Sidebar filters
st.sidebar.header("Filters")

# Stadium selector
stadiums = load_stadiums()
if not stadiums:
    st.error("No stadium data available")
    st.stop()

selected_stadium = st.sidebar.selectbox(
    "Select Stadium",
    stadiums,
    index=0 if stadiums else None
)

# Hour offset slider (30-minute intervals)
hour_offset = st.sidebar.slider(
    "Time Relative to Game Start (hours)",
    min_value=-3.0,
    max_value=3.0,
    value=-1.0,
    step=0.5,
    help="Negative values = before game, positive = after game. In 30-minute increments."
)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Analyzing:** {selected_stadium}")
st.sidebar.markdown(f"**Time:** {hour_offset:+.1f} hours from game start")

# Load games for context
games_df = load_games(selected_stadium)
if not games_df.empty:
    st.sidebar.markdown(f"**Total games analyzed:** {len(games_df)}")

# Main content tabs
tab1, tab2, tab3 = st.tabs(["🎯 Rebalancing Calculator", "📊 Demand Analysis", "🗺️ Station Map"])

with tab1:
    st.header("Rebalancing Calculator")
    st.markdown(f"""
    **Recommendations for {selected_stadium} at {hour_offset:+.1f} hours from game start**

    This table shows average bike flow patterns based on historical game data (30-minute intervals).
    Negative net flow = bikes depleting (recommend adding bikes).
    Positive net flow = bikes accumulating (recommend removing bikes).
    """)

    rebal_df = load_rebalancing_recommendations(selected_stadium, hour_offset)

    if rebal_df.empty:
        st.info(f"No rebalancing data available for {selected_stadium} at {hour_offset:+d}h offset. Try a different time.")
    else:
        # Display key metrics
        col1, col2, col3 = st.columns(3)

        with col1:
            total_stations = len(rebal_df)
            st.metric("Stations Analyzed", total_stations)

        with col2:
            max_depletion = rebal_df['avg_net_flow'].min()
            st.metric("Max Depletion", f"{max_depletion:.1f} bikes/game")

        with col3:
            max_accumulation = rebal_df['avg_net_flow'].max()
            st.metric("Max Accumulation", f"{max_accumulation:.1f} bikes/game")

        st.markdown("---")

        # Format and display the rebalancing table
        display_df = rebal_df[[
            'station_name',
            'avg_net_flow',
            'rebalancing_recommendation',
            'avg_trips_started',
            'avg_trips_ended',
            'num_games'
        ]].copy()

        display_df.columns = [
            'Station',
            'Avg Net Flow',
            'Recommendation',
            'Avg Trips Started',
            'Avg Trips Ended',
            'Games'
        ]

        # Add color highlighting based on net flow
        def highlight_flow(row):
            if row['Avg Net Flow'] < -2:
                return ['background-color: #ffe6e6'] * len(row)  # Light red for depletion
            elif row['Avg Net Flow'] > 2:
                return ['background-color: #e6f7ff'] * len(row)  # Light blue for accumulation
            else:
                return [''] * len(row)

        styled_df = display_df.style.apply(highlight_flow, axis=1).format({
            'Avg Net Flow': '{:.2f}',
            'Avg Trips Started': '{:.1f}',
            'Avg Trips Ended': '{:.1f}',
            'Games': '{:.0f}'
        })

        st.dataframe(styled_df, use_container_width=True, height=600)

        st.caption("💡 Stations are sorted by absolute net flow (highest impact first)")
        st.caption("Red highlight = bikes depleting | Blue highlight = bikes accumulating")

with tab2:
    st.header("Demand Analysis")
    st.markdown(f"**Comparing game day demand vs baseline for {selected_stadium}**")

    demand_df = load_demand_comparison(selected_stadium)

    if demand_df.empty:
        st.info("No demand data available")
    else:
        # Create line chart comparing game day vs baseline
        fig = go.Figure()

        # Add game day trips started
        fig.add_trace(go.Scatter(
            x=demand_df['hour_offset'],
            y=demand_df['avg_trips_started_game'],
            mode='lines+markers',
            name='Game Day (Started)',
            line=dict(color='#FF6B6B', width=3),
            marker=dict(size=8)
        ))

        # Add baseline trips started
        fig.add_trace(go.Scatter(
            x=demand_df['hour_offset'],
            y=demand_df['avg_trips_started_baseline'],
            mode='lines+markers',
            name='Baseline (Started)',
            line=dict(color='#FF6B6B', width=2, dash='dash'),
            marker=dict(size=6)
        ))

        # Add game day trips ended
        fig.add_trace(go.Scatter(
            x=demand_df['hour_offset'],
            y=demand_df['avg_trips_ended_game'],
            mode='lines+markers',
            name='Game Day (Ended)',
            line=dict(color='#4ECDC4', width=3),
            marker=dict(size=8)
        ))

        # Add baseline trips ended
        fig.add_trace(go.Scatter(
            x=demand_df['hour_offset'],
            y=demand_df['avg_trips_ended_baseline'],
            mode='lines+markers',
            name='Baseline (Ended)',
            line=dict(color='#4ECDC4', width=2, dash='dash'),
            marker=dict(size=6)
        ))

        fig.update_layout(
            title=f"Trip Patterns at {selected_stadium} (Game Day vs Baseline)",
            xaxis_title="Hours from Game Start",
            yaxis_title="Average Trips",
            hovermode='x unified',
            height=500
        )

        st.plotly_chart(fig, use_container_width=True)

        st.markdown("""
        **Reading the chart:**
        - Solid lines = game day demand
        - Dashed lines = baseline (same day of week, non-game days)
        - Red = trips started (people leaving stations)
        - Teal = trips ended (people arriving at stations)
        """)

with tab3:
    st.header("Station Map")
    st.markdown(f"**Bike stations within 1km of {selected_stadium}**")

    stations_df, stadium_df = load_nearby_stations(selected_stadium)

    if stations_df.empty or stadium_df.empty:
        st.info("No station map data available")
    else:
        # Create map
        fig = go.Figure()

        # Add stations
        fig.add_trace(go.Scattermapbox(
            lat=stations_df['latitude'],
            lon=stations_df['longitude'],
            mode='markers',
            marker=dict(
                size=10,
                color='blue',
            ),
            text=stations_df['station_name'],
            hovertemplate='<b>%{text}</b><br>Distance: %{customdata} km<extra></extra>',
            customdata=stations_df['distance_km'],
            name='Bike Stations'
        ))

        # Add stadium
        fig.add_trace(go.Scattermapbox(
            lat=stadium_df['latitude'],
            lon=stadium_df['longitude'],
            mode='markers',
            marker=dict(
                size=20,
                color='red',
                symbol='star'
            ),
            text=[selected_stadium],
            hovertemplate='<b>%{text}</b><extra></extra>',
            name='Stadium'
        ))

        # Update map layout
        center_lat = stadium_df['latitude'].iloc[0]
        center_lon = stadium_df['longitude'].iloc[0]

        fig.update_layout(
            mapbox=dict(
                style='open-street-map',
                center=dict(lat=center_lat, lon=center_lon),
                zoom=13
            ),
            height=600,
            margin=dict(l=0, r=0, t=0, b=0)
        )

        st.plotly_chart(fig, use_container_width=True)

        st.markdown(f"**{len(stations_df)} stations** within 1km walking distance")
