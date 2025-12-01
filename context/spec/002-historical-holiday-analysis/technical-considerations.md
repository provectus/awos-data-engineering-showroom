# Technical Specification: Historical Holiday Analysis

- **Functional Specification:** `context/spec/002-historical-holiday-analysis/functional-spec-lite.md`
- **Status:** ✅ Completed
- **Author(s):** Engineering Team
- **Implementation:** All 12 vertical slices completed (38/38 tests passing)

---

## 1. High-Level Technical Approach

This feature extends the existing dbt → DuckDB → Streamlit architecture without modifying working V1 code. We will:

1. **Enhance `dim_stations`** to include latitude, longitude, and area classification (using existing lat/lon from raw bike data)
2. **Create 4 new dbt mart models** at different granularities: summary (per holiday), by-station, by-hour, by-area
3. **Build new Streamlit dashboard page** (`pages/Holiday_Impact.py`) following the existing `Weather.py` pattern
4. **Calculate baselines inline** using SQL window functions (15 days before/after each holiday, excluding weekends and other holidays)
5. **Calculate statistics in Streamlit** (p-values using scipy, rebalancing flags using Python logic for flexibility)

**Systems Affected:**
- `dbt/models/core/dim_stations.sql` - Add lat/lon and area columns
- `dbt/models/marts/` - 4 new holiday mart models
- `streamlit_app/pages/Holiday_Impact.py` - New dashboard page

**No changes to existing working code:** dlt pipelines, existing marts, existing Streamlit pages remain unchanged.

---

## 2. Proposed Solution & Implementation Plan (The "How")

### Data Model / Database Changes

#### Enhancement: `dim_stations` (Core Layer)

**File:** `dbt/models/core/dim_stations.sql`

**Current state:** Has `station_id`, `station_name` only

**Changes:** Add 3 new columns:
- `latitude` (DOUBLE) - Extracted from `stg_bike_trips.start_lat` grouped by `start_station_id`
- `longitude` (DOUBLE) - Extracted from `stg_bike_trips.start_lng` grouped by `start_station_id`
- `area` (VARCHAR) - Derived from lat/lon using CASE statement with ranges

**Area Classification Logic:**
```sql
CASE
    WHEN latitude BETWEEN 40.700 AND 40.720 AND longitude BETWEEN -74.020 AND -73.980
        THEN 'Manhattan - Financial'
    WHEN latitude BETWEEN 40.740 AND 40.780 AND longitude BETWEEN -74.010 AND -73.970
        THEN 'Manhattan - Midtown'
    WHEN latitude BETWEEN 40.580 AND 40.740 AND longitude BETWEEN -74.050 AND -73.833
        THEN 'Brooklyn'
    -- Additional cases for other areas
    ELSE 'Other'
END as area
```

**Implementation:**
- Add CTE to join `stg_bike_trips` and extract first non-null lat/lon per station
- Apply area CASE logic in final SELECT
- Filter out NULL lat/lon values
- **No breaking changes** - existing queries continue to work (additive only)

---

#### New Model: `mart_holiday_impact_summary`

**File:** `dbt/models/marts/mart_holiday_impact_summary.sql`

**Grain:** One row per holiday occurrence

**Logic Flow:**
1. CTE `holidays`: Get all holidays from `stg_holidays`
2. CTE `baseline_days`: Cross join holidays with all ride dates, filter to 15 days before/after, exclude weekends (dayofweek IN (0,6)) and other holidays
3. CTE `holiday_metrics`: Aggregate bike trips on holiday dates (total trips, avg duration, member/casual splits)
4. CTE `baseline_metrics`: Aggregate bike trips on baseline dates, average across baseline period
5. Final SELECT: Join holiday and baseline metrics, calculate absolute and percentage changes

**Key Calculation - Percentage Change:**
```sql
((holiday_metric - baseline_metric) / NULLIF(baseline_metric, 0)) * 100 as metric_pct_change
```

**Columns:**
- Holiday identifiers: `holiday_date`, `holiday_name`, `is_major`, `is_working_day`
- Holiday metrics: `total_trips_holiday`, `avg_duration_holiday`, `member_trips_holiday`, `casual_trips_holiday`
- Baseline metrics: `total_trips_baseline`, `avg_duration_baseline`, etc.
- Comparisons: `trips_abs_change`, `trips_pct_change`, `duration_pct_change`, etc.
- Metadata: `baseline_start_date`, `baseline_end_date`, `baseline_days_count`

**Materialization:** `table` (like existing marts)

---

#### New Model: `mart_holiday_impact_by_station`

**File:** `dbt/models/marts/mart_holiday_impact_by_station.sql`

**Grain:** One row per holiday-station combination

**Logic:** Similar to summary mart, but group by `station_id` instead of aggregating citywide. Join with `dim_stations` to get station name, lat/lon, and area.

**Columns:**
- `holiday_date`, `holiday_name`, `station_id`, `station_name`, `area`, `latitude`, `longitude`
- `trips_holiday`, `trips_baseline`, `trips_abs_change`, `trips_pct_change`

**Note:** Rebalancing flag NOT included - calculated in Streamlit for flexibility

---

#### New Model: `mart_holiday_impact_by_hour`

**File:** `dbt/models/marts/mart_holiday_impact_by_hour.sql`

**Grain:** One row per holiday-hour combination (hours 0-23)

**Logic:** Extract hour from `started_at` using `EXTRACT(HOUR FROM started_at)`, group by holiday and hour, compare to baseline hours.

**Columns:**
- `holiday_date`, `holiday_name`, `hour_of_day` (0-23)
- `trips_holiday`, `trips_baseline`, `trips_pct_change`

---

#### New Model: `mart_holiday_impact_by_area`

**File:** `dbt/models/marts/mart_holiday_impact_by_area.sql`

**Grain:** One row per holiday-area combination

**Logic:** Join bike trips with `dim_stations` to get area, aggregate by area for holiday and baseline periods.

**Columns:**
- `holiday_date`, `holiday_name`, `area_name`
- `station_count`, `trips_holiday`, `trips_baseline`, `trips_pct_change`
- `avg_station_trips_holiday`, `avg_station_trips_baseline`

---

### Component Breakdown

#### Streamlit Dashboard: `streamlit_app/pages/Holiday_Impact.py`

**Structure:** Single scrollable page with 6 sections (following `Weather.py` pattern)

**Page Configuration:**
```python
st.set_page_config(
    page_title="Holiday Impact Analysis",
    page_icon="🎉",
    layout="wide"
)
```

**Data Loading Pattern:**
```python
@st.cache_resource
def get_db_connection():
    return duckdb.connect("duckdb/warehouse.duckdb", read_only=True)

@st.cache_data(ttl=600)  # 10-minute cache like Weather.py
def load_holiday_summary():
    con = get_db_connection()
    return con.execute("SELECT * FROM main_marts.mart_holiday_impact_summary").df()
```

**Section 1: Holiday Selector & KPI Cards**
- Dropdown to select holiday from `holiday_summary['holiday_name']`
- 3 metric cards: Total Trips Change %, Avg Duration Change %, Statistical Significance (Yes/No with p-value)
- Statistical test using `scipy.stats.ttest_ind()` on holiday vs baseline trip arrays

**Section 2: Demand Comparison Chart**
- Grouped bar chart (Plotly) comparing holiday vs baseline for: Total Trips, Avg Duration, Member Trips, Casual Trips

**Section 3: Neighborhood-Level Demand Map (K-Means Clustering)** ✅ Implemented
- User-adjustable slider for cluster count (10-50, default 30, step 5)
- K-Means clustering aggregates 2,000+ stations into neighborhoods:
```python
from sklearn.cluster import KMeans
kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
station_data['cluster'] = kmeans.fit_predict(coords)
```
- Cluster aggregation: sum trips, mean lat/lon, count stations, mode area
- Plotly Scattermapbox with clusters color-coded by `trips_pct_change`
- Color scale: Red (decreased) → Yellow (stable) → Green (increased), midpoint=0
- Circle size represents absolute change magnitude
- Hover data: area, trips_pct_change, trips_holiday, trips_baseline, rebalancing_flag, station_count
- Rebalancing flags calculated in Python:
```python
def get_rebalancing_flag(pct_change):
    if pct_change > 30: return 'Add bikes'
    elif pct_change < -30: return 'Remove bikes'
    else: return 'No action'
```

**Section 4: Hourly Demand Pattern**
- Line chart comparing hourly trips on holiday vs baseline (0-23 hours)

**Section 5: Top Stations Ranking**
- Two side-by-side dataframes: Top 10 increased demand, Top 10 decreased demand

**Section 6: Holiday Comparison Table**
- Sortable dataframe with all holidays and their impact metrics

---

### Logic / Algorithm

#### Baseline Period Calculation

For each holiday, identify baseline days:
1. Start with all distinct `ride_date` values from bike trips
2. Filter to dates within 15 days before OR 15 days after holiday
3. Exclude the holiday date itself
4. Exclude weekends: `dayofweek(ride_date) NOT IN (0, 6)` (Sunday=0, Saturday=6)
5. Exclude other holidays: `ride_date NOT IN (SELECT date FROM holidays)`
6. Result: ~25-30 baseline days per holiday (some days excluded)

**SQL Pattern (used in all marts):**
```sql
WITH baseline_days AS (
    SELECT h.date as holiday_date, d.ride_date
    FROM holidays h
    CROSS JOIN (SELECT DISTINCT ride_date FROM stg_bike_trips) d
    WHERE d.ride_date BETWEEN dateadd('day', -15, h.date) AND dateadd('day', 15, h.date)
      AND d.ride_date != h.date
      AND dayofweek(d.ride_date) NOT IN (0, 6)
      AND d.ride_date NOT IN (SELECT date FROM holidays)
)
```

---

#### Statistical Significance Testing ✅ Implemented

Performed in Streamlit using scipy (one-sample t-test comparing holiday trip count vs baseline daily trip distribution):
```python
from scipy import stats

# Query daily trip counts (NOT individual trips)
holiday_count = con.execute("""
    SELECT COUNT(*) as trip_count
    FROM main_staging.stg_bike_trips
    WHERE ride_date = ?
""", [holiday_date]).df()['trip_count'].values[0]

baseline_counts = con.execute("""
    SELECT ride_date, COUNT(*) as trip_count
    FROM main_staging.stg_bike_trips
    WHERE ride_date BETWEEN ? AND ?
      AND ride_date != ?
      AND dayofweek(ride_date) NOT IN (0, 6)
    GROUP BY ride_date
""", [baseline_start, baseline_end, holiday_date]).df()['trip_count'].values

# One-sample t-test: compare holiday count against baseline distribution
t_stat, p_value = stats.ttest_1samp(baseline_counts, holiday_count)

# Display
significance = "Yes" if p_value < 0.05 else "No"
st.metric("Statistical Significance", significance, delta=f"p = {p_value:.4f}",
          help="T-test comparing holiday trip count vs baseline daily trip distribution")
```

**Why one-sample t-test?** We're comparing a single holiday observation against a distribution of baseline daily counts (not comparing two independent samples).

---

## 3. Impact and Risk Analysis

### System Dependencies

**Depends On (Existing):**
- `stg_bike_trips` - Bike trip staging model (no changes needed)
- `stg_holidays` - Holiday staging model from Spec 001 (no changes needed)
- `mart_demand_daily` - Reference for understanding existing patterns (read-only)

**Affects:**
- `dim_stations` - Enhancement adds 3 columns (non-breaking, additive only)

**Consumed By:**
- New Streamlit page `Holiday_Impact.py` queries the 4 new marts

**No Impact On:**
- Existing dlt pipelines (`bike.py`, `weather.py`, `holidays.py`)
- Existing marts (`mart_demand_daily`, `mart_weather_effect`, `mart_station_stats`)
- Existing Streamlit pages (`Home.py`, `Weather.py`)
- Airflow DAG (out of scope for this feature)

---

### Potential Risks & Mitigations

#### Risk 1: Baseline Calculation Performance

**Description:** Cross join between holidays (3 rows) and ride dates (61 days) creates large intermediate result for filtering.

**Likelihood:** Low - Dataset is small (May-June 2024), DuckDB is fast on columnar data.

**Impact:** Medium - Could slow dbt build if multi-year data added later.

**Mitigation:**
- Pre-filter ride dates to relevant range before cross join (reduces rows scanned)
- Use DuckDB's optimized window functions
- Monitor dbt build time (target: <5 minutes per functional spec requirement)
- If performance degrades with more data, refactor to use intermediate model

**Code Pattern:**
```sql
-- Efficient: Filter first, then cross join
WITH relevant_dates AS (
    SELECT DISTINCT ride_date
    FROM stg_bike_trips
    WHERE ride_date BETWEEN '2024-05-01' AND '2024-06-30'  -- Narrow range
)
```

---

#### Risk 2: Station Area Classification Accuracy

**Description:** Lat/lon range-based area assignment may misclassify border stations.

**Likelihood:** Low - NYC borough boundaries are generally distinct.

**Impact:** Low - Affects grouping in area analysis, but station-level analysis unaffected.

**Mitigation:**
- Use approximate lat/lon ranges (good enough for MVP)
- Add validation query to check for 'Other' area count:
```sql
SELECT area, COUNT(*) FROM dim_stations GROUP BY area;
-- Expect minimal 'Other' count
```
- Document area boundaries in code comments
- If needed later, create manual override lookup table for edge cases

---

#### Risk 3: Missing Lat/Lon for Some Stations

**Description:** Raw bike data may have NULL `start_lat`/`start_lng` for some stations.

**Likelihood:** Low - Citi Bike data is generally complete for active stations.

**Impact:** Low - Those stations excluded from area-based analysis but still in station-level analysis (area = NULL).

**Mitigation:**
- Filter NULL lat/lon in `dim_stations` enhancement
- Log count of excluded stations during dbt build
- Add sanity check: lat/lon within NYC bounds (40.5-41.0, -74.3 to -73.7)

```sql
WHERE latitude IS NOT NULL
  AND longitude IS NOT NULL
  AND latitude BETWEEN 40.5 AND 41.0
  AND longitude BETWEEN -74.3 AND -73.7
```

---

#### Risk 4: Small Sample Size (Limited Historical Data)

**Description:** Only 2-3 holidays in May-June 2024 limits statistical power.

**Likelihood:** Certain - This is a known data constraint.

**Impact:** Medium - Statistical tests may not reach significance (p < 0.05), limiting confidence in insights.

**Mitigation:**
- Still calculate and display p-values (users can interpret with caution)
- Don't block insights on statistical significance - show trends regardless
- Design is future-proof: When more data ingested, analysis automatically improves
- No warning banner (per user decision in Q7)

**Code:**
```python
# Always show p-value, but don't require significance for insights
p_value = stats.ttest_ind(holiday_trips, baseline_trips)[1]
st.metric("P-value", f"{p_value:.3f}")
# Show all insights even if p > 0.05
```

---

#### Risk 5: Map Rendering Performance with Many Stations

**Description:** Plotly scattermapbox with 200+ station markers may render slowly.

**Likelihood:** Low - Current dataset has ~200-300 active stations, which Plotly handles well.

**Impact:** Low - Minor UI lag (1-2 seconds).

**Mitigation:**
- Use `@st.cache_data` for station data loading
- Optional: Add slider to limit displayed stations to top N by absolute change
- If needed, switch to Plotly's WebGL-based `scattergl` for better performance

---

## 4. Testing Strategy

### dbt Model Tests

Add tests to `dbt/models/marts/schema.yml`:

```yaml
models:
  - name: mart_holiday_impact_summary
    columns:
      - name: holiday_date
        tests:
          - unique
          - not_null
      - name: baseline_days_count
        tests:
          - not_null
          - dbt_utils.accepted_range:
              min_value: 1
              max_value: 30

  - name: mart_holiday_impact_by_station
    columns:
      - name: area
        tests:
          - not_null
          - accepted_values:
              values: ['Manhattan - Financial', 'Manhattan - Midtown',
                       'Manhattan - Upper West', 'Manhattan - Upper East',
                       'Manhattan - Downtown', 'Brooklyn', 'Queens',
                       'Bronx', 'Jersey City', 'Other']
    tests:
      - dbt_utils.unique_combination_of_columns:
          combination_of_columns:
            - holiday_date
            - station_id
```

---

### Integration Testing

**End-to-End Test Plan:**

1. **Data Pipeline:**
```bash
# Verify holiday data exists
uv run duckdb duckdb/warehouse.duckdb "SELECT COUNT(*) FROM raw_holidays.us_holidays"
# Expected: 14+ rows

# Build all holiday marts
cd dbt
uv run dbt run --select +mart_holiday_impact*
uv run dbt test --select +mart_holiday_impact*

# Expected: 4 models created, all tests pass
```

2. **Data Quality Verification:**
```sql
-- Verify summary mart has expected holidays
SELECT holiday_name, trips_pct_change, baseline_days_count
FROM main_marts.mart_holiday_impact_summary;
-- Expected: 2-3 rows (Memorial Day, Juneteenth, Puerto Rican Day Parade)
-- Expected: baseline_days_count ~25-30
-- Expected: trips_pct_change negative for major holidays
```

3. **Memorial Day Validation:**
```sql
-- Verify Memorial Day shows expected pattern
SELECT * FROM main_marts.mart_holiday_impact_summary
WHERE holiday_name = 'Memorial Day';
-- Expected: trips_pct_change between -20% and -40%
-- Expected: duration_pct_change between +10% and +30%

-- Verify station-level data
SELECT area, AVG(trips_pct_change) as avg_change, COUNT(*) as station_count
FROM main_marts.mart_holiday_impact_by_station
WHERE holiday_name = 'Memorial Day'
GROUP BY area
ORDER BY avg_change;
-- Expected: Financial District shows large negative change
-- Expected: Central Park area shows positive change
```

4. **Dashboard Testing:**
```bash
# Launch dashboard
cd ..
uv run streamlit run streamlit_app/pages/Holiday_Impact.py
```

**Manual Dashboard Tests:**
- Select Memorial Day → Verify KPI cards show negative trips%, positive duration%
- Check map → Financial District red markers, Central Park green markers
- Check hourly chart → 8am peak disappears, 12pm peak appears
- Check top stations tables → Correct sorting and rebalancing flags
- Test on small screen → Responsive layout

---

### Unit Testing

Optional Python unit tests for Streamlit helper functions:

**File:** `tests/test_holiday_dashboard.py`

```python
def test_rebalancing_flag():
    """Test rebalancing flag logic."""
    from streamlit_app.pages.Holiday_Impact import get_rebalancing_flag

    assert get_rebalancing_flag(50) == 'Add bikes'
    assert get_rebalancing_flag(30.1) == 'Add bikes'
    assert get_rebalancing_flag(-50) == 'Remove bikes'
    assert get_rebalancing_flag(-30.1) == 'Remove bikes'
    assert get_rebalancing_flag(0) == 'No action'
    assert get_rebalancing_flag(29.9) == 'No action'
```

Run: `PYTHONPATH=. uv run pytest tests/test_holiday_dashboard.py -v`

---

### Performance Benchmarks

**Targets:**
- dbt build for all 4 holiday marts: < 5 minutes
- Streamlit page first load: < 3 seconds
- Streamlit cached load: < 1 second
- Map rendering: < 2 seconds

**Measurement:**
```bash
cd dbt
time uv run dbt run --select mart_holiday_impact*
# Target: <5 minutes
```
