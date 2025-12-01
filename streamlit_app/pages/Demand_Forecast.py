import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Demand Forecast", page_icon="🔮", layout="wide")

@st.cache_resource
def get_db_connection():
    return duckdb.connect('duckdb/warehouse.duckdb', read_only=True)

@st.cache_data
def load_clusters():
    conn = get_db_connection()
    return conn.execute('''
        SELECT
            cluster_id,
            station_id,
            station_name,
            latitude,
            longitude,
            centroid_lat,
            centroid_lon
        FROM main_core.dim_station_clusters
        ORDER BY cluster_id, station_id
    ''').fetchdf()

@st.cache_data
def load_baseline_net_flow():
    conn = get_db_connection()
    return conn.execute('''
        SELECT * FROM main_marts.mart_baseline_net_flow
    ''').fetchdf()

@st.cache_data
def load_adjustment_factors():
    conn = get_db_connection()
    return conn.execute('''
        SELECT
            factor_name,
            description,
            impact_pct,
            adjustment_multiplier
        FROM main_marts.mart_adjustment_factors
    ''').fetchdf()

# Load data
clusters_df = load_clusters()
baseline_df = load_baseline_net_flow()
factors_df = load_adjustment_factors()

# Create factor lookup dictionary
factor_lookup = dict(zip(factors_df['factor_name'], factors_df['adjustment_multiplier']))

# Page title
st.title("🔮 Bike Demand Forecast Engine")
st.markdown("Predict hourly net flow and get rebalancing recommendations for the next 24 hours")

# Sidebar controls
st.sidebar.header("Forecast Inputs")

# Day of week selector
day_mapping = {
    'Monday': ('monday', 1),
    'Tuesday': ('tuesday', 2),
    'Wednesday': ('wednesday', 3),
    'Thursday': ('thursday', 4),
    'Friday': ('friday', 5),
    'Saturday': ('saturday', 6),
    'Sunday': ('sunday', 0)
}
selected_day_name = st.sidebar.selectbox(
    "Day of Week",
    options=list(day_mapping.keys()),
    index=2  # Default to Wednesday
)
day_factor_name, day_of_week_num = day_mapping[selected_day_name]
day_factor = factor_lookup.get(day_factor_name, 1.0)

# Temperature selector
temp_mapping = {
    'Cold (<15°C)': 'cold_weather',
    'Neutral (15-19°C)': 'neutral_weather',
    'Warm (20-28°C)': 'warm_weather',
    'Hot (>28°C)': 'hot_weather'
}
selected_temp = st.sidebar.selectbox(
    "Temperature",
    options=list(temp_mapping.keys()),
    index=2  # Default to Warm
)
temp_factor = factor_lookup.get(temp_mapping[selected_temp], 1.0)

# Wind selector
wind_mapping = {
    'Weak (≤15 km/h)': 'weak_wind',
    'Strong (>15 km/h)': 'strong_wind'
}
selected_wind = st.sidebar.selectbox(
    "Wind",
    options=list(wind_mapping.keys()),
    index=0  # Default to Weak
)
wind_factor = factor_lookup.get(wind_mapping[selected_wind], 1.0)

# Rain selector
rain_mapping = {
    'None': 1.0,  # No adjustment
    'Light (≤5 mm)': 'light_rain',
    'Heavy (>5 mm)': 'heavy_rain'
}
selected_rain = st.sidebar.selectbox(
    "Rain",
    options=list(rain_mapping.keys()),
    index=0  # Default to None
)
rain_factor = factor_lookup.get(rain_mapping[selected_rain], 1.0) if selected_rain != 'None' else 1.0

# Holiday selector
holiday_mapping = {
    'None': 1.0,  # No adjustment
    'Minor Holiday (Local)': 'minor_holiday',
    'Major Holiday (Federal)': 'major_holiday'
}
selected_holiday = st.sidebar.selectbox(
    "Holiday",
    options=list(holiday_mapping.keys()),
    index=0  # Default to None
)
holiday_factor = factor_lookup.get(holiday_mapping[selected_holiday], 1.0) if selected_holiday != 'None' else 1.0

# Cluster selector
unique_clusters = sorted(clusters_df['cluster_id'].unique())
selected_cluster = st.sidebar.selectbox(
    "Cluster / Area",
    options=unique_clusters,
    index=0
)

# Calculate combined adjustment factor
combined_factor = day_factor * temp_factor * wind_factor * rain_factor * holiday_factor

# Display selected conditions
st.subheader("📋 Selected Forecast Conditions")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Day", selected_day_name, f"{(day_factor-1)*100:+.1f}%")
    st.metric("Temperature", selected_temp.split('(')[0].strip(), f"{(temp_factor-1)*100:+.1f}%")
with col2:
    st.metric("Wind", selected_wind.split('(')[0].strip(), f"{(wind_factor-1)*100:+.1f}%")
    st.metric("Rain", selected_rain, f"{(rain_factor-1)*100:+.1f}%" if selected_rain != 'None' else "0.0%")
with col3:
    st.metric("Holiday", selected_holiday.split('(')[0].strip(), f"{(holiday_factor-1)*100:+.1f}%" if selected_holiday != 'None' else "0.0%")
    st.metric("Cluster", f"Area {selected_cluster}")
with col4:
    st.metric("Combined Factor", f"{combined_factor:.3f}", f"{(combined_factor-1)*100:+.1f}%", delta_color="normal")

# Filter baseline for selected cluster and day
forecast_data = baseline_df[
    (baseline_df['cluster_id'] == selected_cluster) &
    (baseline_df['day_of_week'] == day_of_week_num)
].copy()

# Apply adjustment factors
forecast_data['adjusted_net_flow'] = forecast_data['net_flow'] * combined_factor
forecast_data['bikes_to_add_or_remove'] = forecast_data['adjusted_net_flow'].apply(
    lambda x: round(abs(x)) if x < -3 else (-1 * round(x) if x > 3 else 0)
)
forecast_data['recommendation'] = forecast_data['adjusted_net_flow'].apply(
    lambda x: f"Add {round(abs(x))} bikes" if x < -3 else (f"Remove {round(x)} bikes" if x > 3 else "No action needed")
)

# Section 2: 24-Hour Forecast Chart
st.subheader("📈 24-Hour Net Flow Forecast")
fig_forecast = px.line(
    forecast_data,
    x='hour',
    y='adjusted_net_flow',
    title=f"Predicted Net Flow for Cluster {selected_cluster} on {selected_day_name}",
    labels={'hour': 'Hour of Day', 'adjusted_net_flow': 'Net Flow (bikes)'},
    markers=True
)
fig_forecast.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Balance Point")
fig_forecast.add_hline(y=3, line_dash="dot", line_color="blue", annotation_text="Remove Threshold")
fig_forecast.add_hline(y=-3, line_dash="dot", line_color="red", annotation_text="Add Threshold")
fig_forecast.update_layout(height=400)
st.plotly_chart(fig_forecast, use_container_width=True)

# Section 3: Rebalancing Recommendations
st.subheader("🔧 Rebalancing Recommendations")
recs_df = forecast_data[['hour_label', 'adjusted_net_flow', 'bikes_to_add_or_remove', 'recommendation']].copy()
recs_df.columns = ['Hour', 'Net Flow', 'Bikes to Add/Remove', 'Recommendation']
recs_df['Net Flow'] = recs_df['Net Flow'].round(1)

# Highlight actionable rows
def highlight_action(row):
    if 'Add' in row['Recommendation']:
        return ['background-color: #ffcccc'] * len(row)
    elif 'Remove' in row['Recommendation']:
        return ['background-color: #cce5ff'] * len(row)
    else:
        return [''] * len(row)

st.dataframe(recs_df.style.apply(highlight_action, axis=1), use_container_width=True, height=400)

# Section 4: Cluster Map
st.subheader("🗺️ Cluster Location Map")
cluster_stations = clusters_df[clusters_df['cluster_id'] == selected_cluster]
centroid = cluster_stations.iloc[0]

fig_map = px.scatter_mapbox(
    cluster_stations,
    lat='latitude',
    lon='longitude',
    hover_name='station_name',
    hover_data={'station_id': True, 'latitude': False, 'longitude': False},
    zoom=12,
    height=400
)
fig_map.add_scattermapbox(
    lat=[centroid['centroid_lat']],
    lon=[centroid['centroid_lon']],
    mode='markers',
    marker=dict(size=20, color='red', symbol='star'),
    name='Cluster Center',
    hovertext=f'Cluster {selected_cluster} Center'
)
fig_map.update_layout(mapbox_style="open-street-map")
st.plotly_chart(fig_map, use_container_width=True)

# Section 5: Station List
st.subheader("📍 Stations in Cluster")
stations_display = cluster_stations[['station_id', 'station_name', 'latitude', 'longitude']].copy()
stations_display.columns = ['Station ID', 'Station Name', 'Latitude', 'Longitude']
st.dataframe(stations_display, use_container_width=True, height=300)

st.caption(f"Total stations in cluster {selected_cluster}: {len(cluster_stations)}")
