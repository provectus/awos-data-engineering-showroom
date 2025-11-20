# Task List: Demand Forecasting Engine - Station Rebalancing Predictions

## Vertical Slices (Incremental, Runnable Tasks)

- [ ] **Slice 1: Create station clusters using dbt Python model**
  - [ ] Create `dbt/models/core/dim_station_clusters.py` (Python model file)
  - [ ] Add model configuration at top:
    ```python
    def model(dbt, session):
        dbt.config(
            materialized='table',
            packages=['scikit-learn', 'pandas', 'numpy']
        )
    ```
  - [ ] Load dim_stations reference: `stations_df = dbt.ref('dim_stations').df()`
  - [ ] Filter stations with valid coordinates:
    ```python
    stations_df = stations_df[
        stations_df['latitude'].notna() &
        stations_df['longitude'].notna()
    ].copy()
    ```
  - [ ] Extract coordinates array: `coords = stations_df[['latitude', 'longitude']].values`
  - [ ] Import and run k-means clustering:
    ```python
    from sklearn.cluster import KMeans
    kmeans = KMeans(n_clusters=30, random_state=42, n_init=10)
    stations_df['cluster_id'] = kmeans.fit_predict(coords)
    ```
  - [ ] Calculate cluster centroids from k-means:
    ```python
    import pandas as pd
    centroids = pd.DataFrame(
        kmeans.cluster_centers_,
        columns=['centroid_lat', 'centroid_lon']
    )
    centroids['cluster_id'] = range(30)
    ```
  - [ ] Merge stations with centroids: `result_df = stations_df.merge(centroids, on='cluster_id', how='left')`
  - [ ] Calculate Haversine distance (vectorized):
    ```python
    import numpy as np

    lat1, lon1 = np.radians(result_df['latitude']), np.radians(result_df['longitude'])
    lat2, lon2 = np.radians(result_df['centroid_lat']), np.radians(result_df['centroid_lon'])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    result_df['distance_from_centroid_km'] = 6371 * c  # Earth radius in km
    ```
  - [ ] Select and order final columns:
    ```python
    final_columns = [
        'station_id', 'station_name', 'latitude', 'longitude',
        'cluster_id', 'centroid_lat', 'centroid_lon', 'distance_from_centroid_km'
    ]
    return result_df[final_columns].sort_values(['cluster_id', 'distance_from_centroid_km'])
    ```
  - [ ] Add schema tests in `dbt/models/core/schema.yml`:
    ```yaml
    - name: dim_station_clusters
      description: "K-means cluster assignments for bike stations (k=30)"
      columns:
        - name: station_id
          tests:
            - unique
            - not_null
        - name: cluster_id
          tests:
            - not_null
            - dbt_utils.accepted_range:
                min_value: 0
                max_value: 29
        - name: distance_from_centroid_km
          tests:
            - not_null
            - dbt_utils.accepted_range:
                min_value: 0
                max_value: 5
    ```
  - [ ] **Verification:** Run `cd dbt && uv run dbt run --select dim_station_clusters && uv run dbt test --select dim_station_clusters`, verify all tests pass, query cluster distribution to confirm balanced assignments (50-100 stations per cluster)

- [ ] **Slice 2: Create baseline net flow mart (cluster + day + hour only, no weather/holiday)**
  - [ ] Create `dbt/models/marts/mart_baseline_net_flow.sql` with `materialized='table'`
  - [ ] Add model docstring at top:
    ```sql
    -- Historical Net Flow Baseline for Demand Forecasting
    -- Pre-aggregates hourly patterns by cluster and day-of-week only
    -- Weather and holiday adjustments applied via factor multiplication in dashboard
    ```
  - [ ] CTE `trips_with_context`: Join trips with clusters and extract temporal dimensions
    ```sql
    select
        t.ride_id,
        t.ride_date,
        extract(hour from t.started_at) as hour,
        dayofweek(t.ride_date) as day_of_week,
        t.start_station_id,
        t.end_station_id,
        sc_start.cluster_id as start_cluster_id,
        sc_end.cluster_id as end_cluster_id
    from {{ ref('stg_bike_trips') }} t
    left join {{ ref('dim_station_clusters') }} sc_start
        on t.start_station_id = sc_start.station_id
    left join {{ ref('dim_station_clusters') }} sc_end
        on t.end_station_id = sc_end.station_id
    ```
  - [ ] CTE `hourly_trips`: UNION ALL to count trips started and ended separately
    ```sql
    select
        start_cluster_id as cluster_id,
        ride_date, hour, day_of_week,
        1 as trips_started,
        0 as trips_ended
    from trips_with_context
    where start_cluster_id is not null

    union all

    select
        end_cluster_id as cluster_id,
        ride_date, hour, day_of_week,
        0 as trips_started,
        1 as trips_ended
    from trips_with_context
    where end_cluster_id is not null
    ```
  - [ ] CTE `net_flow_by_day_hour`: Calculate daily net flow
    ```sql
    select
        cluster_id, ride_date, day_of_week, hour,
        sum(trips_ended) - sum(trips_started) as net_flow
    from hourly_trips
    group by cluster_id, ride_date, day_of_week, hour
    ```
  - [ ] Final SELECT: Aggregate across days (no weather/holiday dimensions)
    ```sql
    select
        cluster_id,
        day_of_week,
        hour,
        round(avg(net_flow), 2) as avg_net_flow,
        round(stddev(net_flow), 2) as stddev_net_flow,
        count(*) as sample_size,
        min(net_flow) as min_net_flow,
        max(net_flow) as max_net_flow
    from net_flow_by_day_hour
    group by cluster_id, day_of_week, hour
    order by cluster_id, day_of_week, hour
    ```
  - [ ] Add schema tests in `dbt/models/marts/schema.yml`:
    ```yaml
    - name: mart_baseline_net_flow
      description: "Baseline hourly net flow patterns by cluster and day-of-week (no weather/holiday adjustments)"
      columns:
        - name: cluster_id
          tests:
            - not_null
            - dbt_utils.accepted_range:
                min_value: 0
                max_value: 29
        - name: day_of_week
          tests:
            - not_null
            - dbt_utils.accepted_range:
                min_value: 0
                max_value: 6
        - name: hour
          tests:
            - not_null
            - dbt_utils.accepted_range:
                min_value: 0
                max_value: 23
        - name: sample_size
          tests:
            - not_null
            - dbt_utils.expression_is_true:
                expression: "> 0"
    ```
  - [ ] **Verification:** Run `cd dbt && uv run dbt build --select mart_baseline_net_flow`, verify tests pass, query results to confirm ~5,040 rows (30 clusters × 7 days × 24 hours)

- [ ] **Slice 3: Calculate historical adjustment factors (weather, holiday, wind impacts)**
  - [ ] Create `dbt/models/marts/mart_adjustment_factors.sql` with `materialized='table'`
  - [ ] Add model docstring:
    ```sql
    -- Historical Impact Factors for Demand Forecasting
    -- Calculates percentage impact of weather and holidays on bike demand
    -- Used to adjust baseline forecasts multiplicatively
    ```
  - [ ] CTE `trips_with_factors`: Join trips with weather and holidays
    ```sql
    select
        t.ride_date,
        t.ride_id,
        w.tmax,
        w.precip,
        w.wind_max,
        h.is_major as is_major_holiday,
        case when h.date is not null and h.is_major = false then true else false end as is_minor_holiday
    from {{ ref('stg_bike_trips') }} t
    left join {{ ref('stg_weather') }} w on t.ride_date = w.date
    left join {{ ref('stg_holidays') }} h on t.ride_date = h.date
    ```
  - [ ] CTE `daily_totals`: Aggregate trips per day with conditions
    ```sql
    select
        ride_date,
        count(*) as total_trips,
        avg(tmax) as avg_temp,
        max(precip) as max_precip,
        max(wind_max) as max_wind,
        bool_or(is_major_holiday) as is_major_holiday,
        bool_or(is_minor_holiday) as is_minor_holiday
    from trips_with_factors
    group by ride_date
    ```
  - [ ] CTE `baseline_metrics`: Calculate baseline (normal days: no rain, no holiday, moderate temp)
    ```sql
    select
        avg(total_trips) as baseline_trips
    from daily_totals
    where max_precip <= 1  -- No significant rain
      and not is_major_holiday
      and not is_minor_holiday
      and avg_temp between 15 and 25  -- Moderate temperature
    ```
  - [ ] Final SELECT: Calculate impact factors as percentage changes
    ```sql
    select
        'hot_weather' as factor_name,
        'Temperature > 25°C' as description,
        round((avg(case when avg_temp > 25 then total_trips end) / baseline_trips - 1) * 100, 1) as impact_pct
    from daily_totals, baseline_metrics
    where avg_temp > 25

    union all

    select
        'warm_weather',
        'Temperature 20-25°C',
        round((avg(case when avg_temp between 20 and 25 then total_trips end) / baseline_trips - 1) * 100, 1)
    from daily_totals, baseline_metrics
    where avg_temp between 20 and 25

    union all

    select
        'cold_weather',
        'Temperature < 15°C',
        round((avg(case when avg_temp < 15 then total_trips end) / baseline_trips - 1) * 100, 1)
    from daily_totals, baseline_metrics
    where avg_temp < 15

    union all

    select
        'rainy_weather',
        'Precipitation > 5mm',
        round((avg(case when max_precip > 5 then total_trips end) / baseline_trips - 1) * 100, 1)
    from daily_totals, baseline_metrics
    where max_precip > 5

    union all

    select
        'windy_weather',
        'Wind > 30 km/h',
        round((avg(case when max_wind > 30 then total_trips end) / baseline_trips - 1) * 100, 1)
    from daily_totals, baseline_metrics
    where max_wind > 30

    union all

    select
        'major_holiday',
        'Major holidays (Memorial Day, etc.)',
        round((avg(case when is_major_holiday then total_trips end) / baseline_trips - 1) * 100, 1)
    from daily_totals, baseline_metrics
    where is_major_holiday

    union all

    select
        'minor_holiday',
        'Minor holidays',
        round((avg(case when is_minor_holiday then total_trips end) / baseline_metrics.baseline_trips - 1) * 100, 1)
    from daily_totals, baseline_metrics
    where is_minor_holiday
    ```
  - [ ] Add schema tests:
    ```yaml
    - name: mart_adjustment_factors
      description: "Impact factors for weather and holidays (as percentage changes)"
      columns:
        - name: factor_name
          tests:
            - unique
            - not_null
        - name: impact_pct
          tests:
            - not_null
    ```
  - [ ] **Verification:** Run `uv run dbt build --select mart_adjustment_factors`, query results, expect 7 rows with factors like: hot=+15%, cold=-10%, rain=-12%, major_holiday=-20%, etc.

- [ ] **Slice 4: Create basic Streamlit forecast page with input controls**
  - [ ] Create `streamlit_app/pages/Demand_Forecast.py`
  - [ ] Add imports: `streamlit as st`, `duckdb`, `plotly.graph_objects as go`, `pandas as pd`
  - [ ] Set page config:
    ```python
    st.set_page_config(
        page_title="Demand Forecast Simulator",
        page_icon="🔮",
        layout="wide"
    )
    ```
  - [ ] Add DuckDB connection helper:
    ```python
    @st.cache_resource
    def get_db_connection():
        return duckdb.connect("duckdb/warehouse.duckdb", read_only=True)
    ```
  - [ ] Add page header:
    ```python
    st.title("🔮 Demand Forecast Simulator")
    st.markdown("""
    Select scenario parameters to predict hourly bike rebalancing needs.
    Forecast = Baseline × Weather Factor × Holiday Factor
    """)
    ```
  - [ ] Add sidebar with scenario inputs:
    ```python
    st.sidebar.header("Scenario Configuration")

    # Day of week selector
    day_of_week = st.sidebar.selectbox(
        "Day of Week",
        options=[0, 1, 2, 3, 4, 5, 6],
        format_func=lambda x: ['Sunday', 'Monday', 'Tuesday', 'Wednesday',
                               'Thursday', 'Friday', 'Saturday'][x],
        index=1  # Default to Monday
    )

    # Weather temperature category
    temp_category = st.sidebar.selectbox(
        "Temperature",
        options=['normal', 'warm', 'hot', 'cold'],
        format_func=lambda x: {
            'normal': '🌤️ Normal (15-20°C)',
            'warm': '☀️ Warm (20-25°C)',
            'hot': '🔥 Hot (>25°C)',
            'cold': '❄️ Cold (<15°C)'
        }[x]
    )

    # Rain toggle
    is_rainy = st.sidebar.checkbox("🌧️ Rainy (>5mm precipitation)")

    # Wind toggle
    is_windy = st.sidebar.checkbox("💨 Windy (>30 km/h)")

    # Holiday type selector
    holiday_type = st.sidebar.selectbox(
        "Holiday Type",
        options=['none', 'major', 'minor'],
        format_func=lambda x: {
            'none': 'Regular Day',
            'major': '🎉 Major Holiday',
            'minor': '📅 Minor Holiday'
        }[x]
    )
    ```
  - [ ] Add temporary cluster selector:
    ```python
    st.header("Select Area")
    selected_cluster = st.selectbox(
        "Cluster ID (map will be added in next slice):",
        options=list(range(30)),
        index=0
    )
    ```
  - [ ] Add placeholder for chart:
    ```python
    st.header("📊 24-Hour Forecast")
    st.info("Chart will be added in Slice 5")
    ```
  - [ ] **Verification:** Run `uv run streamlit run streamlit_app/pages/Demand_Forecast.py`, verify all input controls render correctly

- [ ] **Slice 5: Add 24-hour forecast chart with factor-based adjustments**
  - [ ] Add data loading function for baseline:
    ```python
    @st.cache_data(ttl=600)
    def load_baseline(cluster_id, day):
        con = get_db_connection()
        query = """
            SELECT hour, avg_net_flow, sample_size
            FROM main_marts.mart_baseline_net_flow
            WHERE cluster_id = ? AND day_of_week = ?
            ORDER BY hour
        """
        return con.execute(query, [cluster_id, day]).df()
    ```
  - [ ] Add data loading function for adjustment factors:
    ```python
    @st.cache_data(ttl=3600)
    def load_adjustment_factors():
        con = get_db_connection()
        query = """
            SELECT factor_name, impact_pct
            FROM main_marts.mart_adjustment_factors
        """
        df = con.execute(query).df()
        return dict(zip(df['factor_name'], df['impact_pct']))
    ```
  - [ ] Load data and calculate adjustments:
    ```python
    baseline = load_baseline(selected_cluster, day_of_week)
    factors = load_adjustment_factors()

    if baseline.empty:
        st.warning("⚠️ No baseline data for this cluster/day combination.")
    else:
        # Calculate total adjustment factor
        adjustment = 1.0
        applied_adjustments = []

        # Temperature adjustment
        if temp_category == 'hot':
            temp_factor = 1 + (factors.get('hot_weather', 0) / 100)
            adjustment *= temp_factor
            applied_adjustments.append(f"Hot: {factors.get('hot_weather', 0):+.0f}%")
        elif temp_category == 'warm':
            temp_factor = 1 + (factors.get('warm_weather', 0) / 100)
            adjustment *= temp_factor
            applied_adjustments.append(f"Warm: {factors.get('warm_weather', 0):+.0f}%")
        elif temp_category == 'cold':
            temp_factor = 1 + (factors.get('cold_weather', 0) / 100)
            adjustment *= temp_factor
            applied_adjustments.append(f"Cold: {factors.get('cold_weather', 0):+.0f}%")

        # Rain adjustment
        if is_rainy:
            rain_factor = 1 + (factors.get('rainy_weather', 0) / 100)
            adjustment *= rain_factor
            applied_adjustments.append(f"Rain: {factors.get('rainy_weather', 0):+.0f}%")

        # Wind adjustment
        if is_windy:
            wind_factor = 1 + (factors.get('windy_weather', 0) / 100)
            adjustment *= wind_factor
            applied_adjustments.append(f"Wind: {factors.get('windy_weather', 0):+.0f}%")

        # Holiday adjustment
        if holiday_type == 'major':
            holiday_factor = 1 + (factors.get('major_holiday', 0) / 100)
            adjustment *= holiday_factor
            applied_adjustments.append(f"Major Holiday: {factors.get('major_holiday', 0):+.0f}%")
        elif holiday_type == 'minor':
            holiday_factor = 1 + (factors.get('minor_holiday', 0) / 100)
            adjustment *= holiday_factor
            applied_adjustments.append(f"Minor Holiday: {factors.get('minor_holiday', 0):+.0f}%")

        # Apply adjustment to baseline
        baseline['forecast_net_flow'] = baseline['avg_net_flow'] * adjustment
    ```
  - [ ] Display adjustment info:
    ```python
    if applied_adjustments:
        st.info(f"**Adjustments applied:** {', '.join(applied_adjustments)} | **Total:** {(adjustment - 1) * 100:+.0f}%")
    else:
        st.info("**No adjustments** - showing baseline forecast")
    ```
  - [ ] Create Plotly bar chart:
    ```python
    fig = go.Figure(go.Bar(
        x=baseline['hour'],
        y=baseline['forecast_net_flow'],
        marker_color=baseline['forecast_net_flow'].apply(
            lambda x: '#FF6B6B' if x < 0 else '#4ECDC4'  # Red=add bikes, Teal=remove bikes
        ),
        text=baseline['forecast_net_flow'].round(1),
        textposition='outside',
        hovertemplate='Hour %{x}:00<br>Forecast: %{y:.1f} bikes<br>Baseline: %{customdata[0]:.1f}<br>Sample Size: %{customdata[1]}<extra></extra>',
        customdata=baseline[['avg_net_flow', 'sample_size']].values
    ))

    fig.update_layout(
        title="Bikes to Add (+) or Remove (-) by Hour",
        xaxis_title="Hour of Day",
        yaxis_title="Net Flow (bikes)",
        xaxis=dict(tickmode='linear', tick0=0, dtick=1),
        height=400,
        hovermode='x unified'
    )

    # Add zero reference line
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

    st.plotly_chart(fig, use_container_width=True)
    ```
  - [ ] Add summary metrics:
    ```python
    col1, col2, col3 = st.columns(3)
    with col1:
        peak_add = baseline['forecast_net_flow'].max()
        st.metric("Peak Addition", f"+{peak_add:.0f} bikes" if peak_add > 0 else "None")
    with col2:
        peak_remove = baseline['forecast_net_flow'].min()
        st.metric("Peak Removal", f"{peak_remove:.0f} bikes" if peak_remove < 0 else "None")
    with col3:
        avg_sample = baseline['sample_size'].mean()
        st.metric("Avg Data Points/Hour", f"{avg_sample:.0f}")
    ```
  - [ ] **Verification:** Select Monday, Hot, Rainy, Major Holiday → Verify adjustments compound correctly, chart shows adjusted forecast

- [ ] **Slice 6: Add cluster selection map visualization**
  - [ ] Add data loading function for cluster centroids:
    ```python
    @st.cache_data
    def load_clusters():
        con = get_db_connection()
        query = """
            SELECT DISTINCT
                cluster_id,
                centroid_lat,
                centroid_lon,
                COUNT(*) as station_count
            FROM main_core.dim_station_clusters
            GROUP BY cluster_id, centroid_lat, centroid_lon
        """
        return con.execute(query).df()
    ```
  - [ ] Replace temporary cluster selector with map section:
    ```python
    st.header("Select Area on Map")
    clusters = load_clusters()
    ```
  - [ ] Create Plotly scattermapbox:
    ```python
    fig_map = go.Figure(go.Scattermapbox(
        lat=clusters['centroid_lat'],
        lon=clusters['centroid_lon'],
        mode='markers',
        marker=dict(
            size=15,
            color=clusters['cluster_id'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="Cluster ID")
        ),
        text=clusters['cluster_id'],
        customdata=clusters[['cluster_id', 'station_count']],
        hovertemplate='<b>Cluster %{text}</b><br>%{customdata[1]} stations<extra></extra>',
    ))

    fig_map.update_layout(
        mapbox=dict(
            style='open-street-map',
            center=dict(lat=40.73, lon=-73.98),  # NYC center
            zoom=11
        ),
        height=500,
        margin=dict(l=0, r=0, t=0, b=0)
    )

    st.plotly_chart(fig_map, use_container_width=True)
    ```
  - [ ] Add dropdown selector below map:
    ```python
    selected_cluster = st.selectbox(
        "Select Cluster:",
        options=clusters['cluster_id'].tolist(),
        index=0
    )

    st.caption("💡 Map shows cluster locations. Use dropdown to select.")
    ```
  - [ ] **Verification:** Map renders with 30 clusters, selecting different clusters updates chart

- [ ] **Slice 7: Add station list for selected cluster**
  - [ ] Add data loading function:
    ```python
    @st.cache_data
    def load_cluster_stations(cluster_id):
        con = get_db_connection()
        query = """
            SELECT
                station_id,
                station_name,
                latitude,
                longitude,
                round(distance_from_centroid_km, 3) as distance_km
            FROM main_core.dim_station_clusters
            WHERE cluster_id = ?
            ORDER BY distance_from_centroid_km
        """
        return con.execute(query, [cluster_id]).df()
    ```
  - [ ] Add section after forecast chart:
    ```python
    st.header(f"🚲 Stations in Cluster {selected_cluster}")
    stations = load_cluster_stations(selected_cluster)
    ```
  - [ ] Display formatted dataframe:
    ```python
    st.dataframe(
        stations,
        column_config={
            "station_id": "ID",
            "station_name": "Station Name",
            "latitude": st.column_config.NumberColumn("Lat", format="%.4f"),
            "longitude": st.column_config.NumberColumn("Lon", format="%.4f"),
            "distance_km": st.column_config.NumberColumn("Distance from Center (km)", format="%.3f")
        },
        hide_index=True,
        use_container_width=True,
        height=400
    )

    st.caption(f"**{len(stations)} stations** in this cluster")
    ```
  - [ ] **Verification:** Station list updates when cluster changes, sorted by distance

- [ ] **Slice 8: Integration testing and data quality validation**
  - [ ] Run complete pipeline end-to-end:
    ```bash
    cd dbt
    uv run dbt build
    cd ..
    ```
  - [ ] Verify all models build successfully (dim_station_clusters, mart_baseline_net_flow, mart_adjustment_factors)
  - [ ] Run data quality validation queries:
    ```sql
    -- Query 1: Check cluster distribution
    SELECT cluster_id, COUNT(*) as station_count
    FROM main_core.dim_station_clusters
    GROUP BY cluster_id ORDER BY cluster_id;
    -- Expected: 30 rows, ~50-100 stations each

    -- Query 2: Check baseline mart (should have no sparse data issues)
    SELECT day_of_week, COUNT(DISTINCT cluster_id) as clusters, COUNT(*) as total_hours
    FROM main_marts.mart_baseline_net_flow
    GROUP BY day_of_week ORDER BY day_of_week;
    -- Expected: 7 rows, each day should have data for most clusters

    -- Query 3: Check adjustment factors
    SELECT * FROM main_marts.mart_adjustment_factors ORDER BY factor_name;
    -- Expected: 7 rows with reasonable percentages (hot=+10-20%, cold=-5-15%, rain=-10-20%, etc.)

    -- Query 4: Validate Monday baseline pattern
    SELECT hour, avg_net_flow, sample_size
    FROM main_marts.mart_baseline_net_flow
    WHERE cluster_id = 0 AND day_of_week = 1
    ORDER BY hour;
    -- Expected: 24 rows, morning negative, evening positive
    ```
  - [ ] Test dashboard scenarios:
    - [ ] **Normal weekday:** Monday, Normal temp, No rain/wind, Regular → Verify typical commute pattern
    - [ ] **Hot weekend:** Saturday, Hot, No rain/wind, Regular → Verify positive adjustment (more rides)
    - [ ] **Rainy holiday:** Memorial Day, Normal temp, Rainy, Major holiday → Verify compound negative adjustment
    - [ ] **All adjustments:** Hot + Rainy + Windy + Major holiday → Verify all factors multiply correctly
    - [ ] **Financial District cluster:** Find lower Manhattan cluster → Strong commute pattern
    - [ ] **All clusters:** Cycle through 0-29 → All work without errors
  - [ ] Verify adjustment factor display:
    - [ ] Info banner shows all applied adjustments
    - [ ] Percentages match mart_adjustment_factors table
    - [ ] Total percentage calculates correctly (compound multiplication)
  - [ ] Test edge cases:
    - [ ] Cluster with sparse data → Still works (fewer sample points but no errors)
    - [ ] No adjustments selected → Shows baseline only
    - [ ] Maximum adjustments → All 7 factors applied correctly
  - [ ] **Verification:** All acceptance criteria met, application works end-to-end

- [ ] **Slice 9: Update documentation and roadmap**
  - [ ] Update `CLAUDE.md`:
    ```markdown
    ### Demand Forecasting (dbt only - no data ingestion)

    # Build station clusters and baseline mart
    cd dbt
    uv run dbt run --select dim_station_clusters mart_baseline_net_flow mart_adjustment_factors

    # Run forecast dashboard
    uv run streamlit run streamlit_app/pages/Demand_Forecast.py
    # Opens at http://localhost:8501
    ```
  - [ ] Add notes about factor-based approach:
    ```markdown
    **Forecasting Approach:**
    - Baseline: Historical net flow by cluster + day + hour
    - Adjustments: Multiplicative factors from historical analysis
    - Formula: Forecast = Baseline × (1 + temp%) × (1 + rain%) × (1 + wind%) × (1 + holiday%)
    - Example: Hot (+15%) + Rainy (-12%) = Baseline × 1.15 × 0.88 = Baseline × 1.012 (+1.2%)
    ```
  - [ ] Update `context/product/roadmap.md`:
    ```markdown
    ### Phase 2: Predictive Intelligence

    - [x] **Demand Forecasting Engine** ✅ **COMPLETED**
      - [x] Station Clustering: 30 k-means clusters
      - [x] Baseline Patterns: Cluster + day + hour
      - [x] Historical Impact Factors: Temperature, rain, wind, holidays
      - [x] Scenario Simulator: Interactive dashboard with adjustable conditions
      - [x] Factor-based Adjustments: Multiplicative model (simple, explainable)

    **Implementation Notes:**
    - Weather factors: Hot (+15%), Warm (+5%), Cold (-10%), Rain (-12%), Wind (-8%)
    - Holiday factors: Major (-20%), Minor (-5%)
    - Factors calculated from May-June 2024 historical data
    - Baseline has ~5,000 scenario combinations (no sparse data)
    ```
  - [ ] **Verification:** Commands work as documented, roadmap accurate

---

## Notes

- **Total Clusters:** 30 (k-means, random_state=42)
- **Expected Stations:** ~2,000 with coordinates
- **Baseline Mart Size:** ~5,040 rows (30 clusters × 7 days × 24 hours) - NO SPARSE DATA
- **Adjustment Factors:** 7 rows (hot, warm, cold, rain, wind, major_holiday, minor_holiday)
- **Forecasting Formula:** `forecast = baseline × (1 + temp_factor) × (1 + rain_factor) × (1 + wind_factor) × (1 + holiday_factor)`
- **Example Calculation:** Hot weather (+15%) on rainy Memorial Day (-12%, -20%):
  - `forecast = baseline × 1.15 × 0.88 × 0.80 = baseline × 0.811` (-18.9% total)
- **dbt Python Model:** dim_station_clusters uses scikit-learn
- **Schema:** DuckDB uses `main_core`, `main_marts` prefixes
- **No External APIs:** All factors derived from existing historical data
- **Map:** Visual reference only (not clickable in MVP)

---

## Success Criteria Checklist

- [ ] 30 balanced clusters created (50-100 stations each)
- [ ] Baseline mart contains all cluster+day+hour combinations (no missing data)
- [ ] Adjustment factors calculated from historical analysis (7 factors total)
- [ ] Dashboard filters: Day, Temperature, Rain toggle, Wind toggle, Holiday, Cluster
- [ ] Factor-based forecast: Baseline × multiplicative adjustments
- [ ] Chart displays adjusted forecast with color coding (red=add, teal=remove)
- [ ] Adjustment info banner shows all applied factors and total percentage
- [ ] Map displays 30 cluster markers across NYC
- [ ] Station list shows all stations in selected cluster
- [ ] All dbt tests pass
- [ ] Documentation updated with accurate commands and formula explanation
