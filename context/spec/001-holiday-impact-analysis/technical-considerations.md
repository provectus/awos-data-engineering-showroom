# Technical Specification: Holiday Impact Analysis

- **Functional Specification:** [context/spec/001-holiday-impact-analysis/functional-spec.md](./functional-spec.md)
- **Status:** Draft
- **Author(s):** Engineering Team (via Claude Code)

---

## 1. High-Level Technical Approach

This feature adds holiday impact analysis capabilities to the NYC Citi Bike demand analytics platform. The implementation follows the existing data pipeline architecture:

1. **Data Ingestion**: Create a new dlt pipeline (`dlt_pipeline/holidays.py`) to fetch US holiday data from the Nager.Date API for 2024-2025
2. **Data Transformation**: Add dbt models to join holidays with bike trip data and calculate weather-adjusted demand metrics
3. **Dashboard**: Create a new Streamlit page (`streamlit_app/pages/Holiday_Impact.py`) with five required visualizations

**Key architectural decisions:**
- Follow the same pattern as `weather.py` for the dlt pipeline (API fetch → DuckDB)
- No Great Expectations validation or Airflow scheduling (per functional spec - out of scope)
- dbt will handle joining holidays to existing `mart_demand_daily` to create a new `mart_holiday_analysis` table
- Manual pipeline execution is acceptable (run `python dlt_pipeline/holidays.py` then `dbt build`)

**Systems affected:**
- New: `dlt_pipeline/holidays.py` (ingestion)
- New: `dbt/models/staging/stg_holidays.sql` (staging transformation)
- New: `dbt/models/marts/mart_holiday_analysis.sql` (analytics mart)
- New: `streamlit_app/pages/Holiday_Impact.py` (dashboard page)
- Modified: `dbt/models/staging/schema.yml` (add staging tests)
- Modified: `dbt/models/marts/schema.yml` (add mart tests)

---

## 2. Proposed Solution & Implementation Plan (The "How")

### 2.1 Data Ingestion - dlt Pipeline

**File**: `dlt_pipeline/holidays.py`

**API Integration:**
- Endpoint: `https://date.nager.at/api/v3/PublicHolidays/{year}/US`
- Method: GET requests (no authentication required)
- Years to fetch: 2024 and 2025 (two API calls)
- Timeout: 30 seconds per request
- Retry logic: Exponential backoff on failures (3 retries max)

**Data Model:**

Based on actual API response schema, the `us_holidays` table will have:

| Column Name | Data Type | Source Field | Description |
|------------|-----------|--------------|-------------|
| `date` | DATE | `date` | Primary key, format "YYYY-MM-DD" |
| `holiday_name` | TEXT | `name` | Official holiday name |
| `local_name` | TEXT | `localName` | Local/alternative name |
| `is_nationwide` | BOOLEAN | `global` | Whether holiday applies to all states |
| `is_fixed` | BOOLEAN | `fixed` | Whether holiday date is fixed annually |
| `holiday_types` | TEXT | `types` | Comma-separated list from types array (e.g., "Public, School") |
| `counties` | TEXT | `counties` | Comma-separated state codes (e.g., "US-CA, US-CT"), null if nationwide |
| `_dlt_load_timestamp` | TIMESTAMP | Generated | Ingestion metadata |

**dlt Resource Configuration:**
```python
@dlt.resource(
    name="us_holidays",
    write_disposition="merge",
    primary_key="date",
    table_name="us_holidays",
)
```

**Filtering Logic:**
Include holidays where:
- `global == true` (nationwide holidays), OR
- `counties` array contains any value starting with "US-NY" (New York-specific holidays)

**Pipeline Configuration:**
- Pipeline name: `"holiday_ingestion"`
- Destination: `"duckdb"`
- Dataset name: `"raw_holidays"`
- Output database: `duckdb/holiday_ingestion.duckdb` (following existing convention)

**Error Handling:**
- Wrap API requests in try-except blocks
- Log detailed errors with context (URL, year, response status)
- Continue processing remaining years if one year fails
- Return empty iterator for failed requests (don't crash pipeline)

**Implementation Pattern:**
Follow the same structure as `weather.py`:
- Resource function fetches and yields records
- `run_holiday_pipeline()` function orchestrates execution
- `if __name__ == "__main__"` block for manual execution
- Logging at INFO level for pipeline progress

---

### 2.2 Data Transformation - dbt Models

#### Staging Layer

**File**: `dbt/models/staging/stg_holidays.sql`

**Purpose**: Clean and standardize raw holiday data (no business logic)

**Transformations:**
- Cast `date` to DATE type
- Cast `is_nationwide` and `is_fixed` to BOOLEAN
- Trim whitespace from text fields
- Ensure consistent NULL handling for `counties` field

**Materialization**: `view` (no storage cost for simple transformations)

**Source Reference**: `{{ source('raw_holidays', 'us_holidays') }}`

#### Marts Layer

**File**: `dbt/models/marts/mart_holiday_analysis.sql`

**Purpose**: Create analytics-ready table with holiday flags, demand metrics, and weather adjustments

**Join Logic:**
```sql
-- LEFT JOIN to preserve all dates from demand_daily
FROM {{ ref('mart_demand_daily') }} AS demand
LEFT JOIN {{ ref('stg_holidays') }} AS holidays
  ON demand.ride_date = holidays.date
```

**Computed Columns:**

| Column Name | Data Type | Calculation | Description |
|------------|-----------|-------------|-------------|
| `ride_date` | DATE | From `mart_demand_daily` | Primary key |
| `is_holiday` | BOOLEAN | `holidays.date IS NOT NULL` | Flag for holiday dates |
| `holiday_name` | TEXT | From `stg_holidays` | Null for non-holidays |
| `holiday_category` | TEXT | Derived from `holiday_types` | "Federal Holiday" if contains "Public", "NY State Observance" if contains "Observance", NULL otherwise |
| `trips_total` | INTEGER | From `mart_demand_daily` | Raw trip count |
| `trips_weather_adjusted` | FLOAT | TBD - normalize using weather effect | Weather-normalized demand |
| `baseline_daily_trips` | INTEGER | AVG(trips_total) WHERE is_holiday = false | Non-holiday average for comparison |
| `demand_vs_baseline_pct` | FLOAT | `(trips_total - baseline_daily_trips) / baseline_daily_trips * 100` | Percentage change from baseline |
| `tmax` | FLOAT | From `mart_demand_daily` (via weather join) | Temperature on that date |
| `precip` | FLOAT | From `mart_demand_daily` (via weather join) | Precipitation on that date |
| `day_type` | TEXT | From `mart_demand_daily` | "Weekday" or "Weekend" |

**Weather Normalization Logic:**
- Reuse pattern from `mart_weather_effect.sql`
- Calculate expected demand as if weather was average (e.g., 70°F, no precipitation)
- Formula: `trips_weather_adjusted = trips_total * (avg_weather_factor / actual_weather_factor)`
- Include both raw and adjusted metrics for transparency

**Materialization**: `table` (for query performance in dashboard)

**Schema**: `main_marts` (following existing convention)

#### dbt Tests

**Staging Tests** (`dbt/models/staging/schema.yml`):
```yaml
models:
  - name: stg_holidays
    columns:
      - name: date
        tests:
          - unique
          - not_null
      - name: is_nationwide
        tests:
          - accepted_values:
              values: [true, false]
      - name: is_fixed
        tests:
          - accepted_values:
              values: [true, false]
```

**Marts Tests** (`dbt/models/marts/schema.yml`):
```yaml
models:
  - name: mart_holiday_analysis
    columns:
      - name: ride_date
        tests:
          - unique
          - not_null
      - name: is_holiday
        tests:
          - not_null
      - name: demand_vs_baseline_pct
        tests:
          - dbt_utils.accepted_range:
              min_value: -100
              max_value: 500
              inclusive: true
```

**Row Count Test:**
Verify `mart_holiday_analysis` has same row count as `mart_demand_daily` (LEFT JOIN preserves all dates)

---

### 2.3 Dashboard - Streamlit Visualization

**File**: `streamlit_app/pages/Holiday_Impact.py`

**Page Configuration:**
```python
st.set_page_config(
    page_title="Holiday Impact Analysis",
    page_icon="🎉",
    layout="wide",
    initial_sidebar_state="expanded",
)
```

**Database Connection:**
- Use same pattern as `Home.py`: `duckdb.connect("duckdb/warehouse.duckdb", read_only=True)`
- Cache connection with `@st.cache_resource`
- Cache data queries with `@st.cache_data(ttl=600)` (10-minute TTL)

**Data Validation & Banner:**
```python
# Query to check data sufficiency
holiday_count = df[df['is_holiday'] == True]['holiday_name'].nunique()

if holiday_count < 2:
    st.info("⚠️ Limited historical data available. Insights will strengthen as more data accumulates over time.")
```

**Visualization Components:**

#### 1. Holiday vs. Non-Holiday Demand Comparison (FR 2.3)

**Chart Type**: Grouped bar chart (Plotly `px.bar`)

**Data Query**:
```sql
SELECT
    holiday_category,
    AVG(trips_weather_adjusted) AS avg_demand,
    COUNT(DISTINCT ride_date) AS holiday_count,
    MIN(ride_date) AS date_range_start,
    MAX(ride_date) AS date_range_end
FROM main_marts.mart_holiday_analysis
WHERE is_holiday = TRUE
GROUP BY holiday_category

UNION ALL

SELECT
    'Non-Holiday Baseline' AS holiday_category,
    AVG(trips_weather_adjusted) AS avg_demand,
    COUNT(DISTINCT ride_date) AS holiday_count,
    MIN(ride_date) AS date_range_start,
    MAX(ride_date) AS date_range_end
FROM main_marts.mart_holiday_analysis
WHERE is_holiday = FALSE
```

**Display Elements**:
- X-axis: Holiday category ("Federal Holiday", "NY State Observance", "Non-Holiday Baseline")
- Y-axis: Average daily trips (weather-adjusted)
- Percentage change labels on each bar (calculated vs. baseline)
- Hover tooltip: exact trip count, number of holidays, date range

**Color Scheme**: Use distinct colors for each category (e.g., blue for federal, orange for state, gray for baseline)

#### 2. Holiday Calendar Heatmap (FR 2.4)

**Chart Type**: Custom Plotly heatmap or grid layout

**Data Query**:
```sql
SELECT
    ride_date,
    is_holiday,
    holiday_name,
    trips_total,
    CASE WHEN trips_total IS NULL THEN 'No Data' ELSE 'Data Available' END AS data_status
FROM main_marts.mart_holiday_analysis
WHERE YEAR(ride_date) = 2024  -- Default to current year
ORDER BY ride_date
```

**Display Elements**:
- Calendar grid: 12 months × ~30 days
- Cell background: Color intensity based on `trips_total` (darker = higher demand)
- Holiday markers: Distinct border or icon on holiday dates
- Holiday labels: Display `holiday_name` as text on holiday cells
- No-data indicator: Gray cells with "No Data" label where `trips_total IS NULL`
- Color scale legend: "Low Demand" → "High Demand" gradient

**Interaction**: View-only (no click interactions per functional spec)

#### 3. Individual Holiday Analysis (FR 2.5)

**UI Components**:
- Dropdown: `st.selectbox()` with list of holidays (format: "Holiday Name - Date")
- Line chart: Plotly `px.line()` showing ±3 days around selected holiday
- Summary panel: `st.metric()` components for key stats

**Data Query** (parameterized by selected holiday date):
```sql
SELECT
    ride_date,
    trips_total,
    baseline_daily_trips,
    holiday_name,
    tmax,
    precip
FROM main_marts.mart_holiday_analysis
WHERE ride_date BETWEEN DATE '{holiday_date}' - INTERVAL 3 DAY
                    AND DATE '{holiday_date}' + INTERVAL 3 DAY
ORDER BY ride_date
```

**Display Elements**:
- Line chart: Daily trip counts over 7-day window
- Vertical line: Marks the holiday date (Plotly annotation)
- Baseline reference line: Horizontal line at `baseline_daily_trips` value
- Summary panel:
  - Holiday name and date
  - Total trips on holiday
  - % change vs. baseline
  - Weather: Temperature (°F) and precipitation (mm)

**No-Data Handling**: If `trips_total IS NULL`, display message: "No trip data available for this holiday"

#### 4. Holiday Type Performance Table (FR 2.6)

**Chart Type**: Interactive Streamlit dataframe (`st.dataframe()`)

**Data Query**:
```sql
SELECT
    holiday_category AS "Holiday Type",
    COUNT(DISTINCT ride_date) AS "Number of Holidays",
    ROUND(AVG(trips_total), 0) AS "Average Demand (trips)",
    ROUND(AVG(demand_vs_baseline_pct), 1) AS "% Change vs. Baseline",
    STRING_AGG(holiday_name, ', ') AS "Sample Holidays"  -- Limit to 2-3 in code
FROM main_marts.mart_holiday_analysis
WHERE is_holiday = TRUE
GROUP BY holiday_category

UNION ALL

SELECT
    'Total/Average' AS "Holiday Type",
    COUNT(DISTINCT ride_date),
    ROUND(AVG(trips_total), 0),
    ROUND(AVG(demand_vs_baseline_pct), 1),
    'All holidays' AS "Sample Holidays"
FROM main_marts.mart_holiday_analysis
WHERE is_holiday = TRUE
```

**Display Elements**:
- Sortable columns (Streamlit default behavior)
- Color-coded % change: Use `st.dataframe()` with styling function
  - Green: Positive % change
  - Red: Negative % change
- "N/A" for null values (when holiday has no trip data)
- Total/Average row at bottom (bold styling)

**Sample Holidays**: Truncate to 2-3 examples in Python code before display

#### 5. What-If Holiday Planning Tool (FR 2.7)

**UI Components**:
- Dropdown: `st.selectbox()` with upcoming holidays (filtered to `ride_date > CURRENT_DATE` and within next 365 days)
- Prediction display: `st.metric()` or `st.info()` boxes
- Confidence indicator: Badge or colored text

**Data Query** (for historical patterns):
```sql
-- Get historical average for this holiday type
SELECT
    holiday_category,
    AVG(trips_total) AS avg_historical_demand,
    AVG(demand_vs_baseline_pct) AS avg_baseline_change_pct,
    COUNT(DISTINCT ride_date) AS data_points
FROM main_marts.mart_holiday_analysis
WHERE is_holiday = TRUE
  AND holiday_category = '{selected_holiday_category}'
GROUP BY holiday_category
```

**Prediction Logic**:
1. Look up historical data for the specific holiday (if exists)
2. If no data for specific holiday, use average for that holiday category
3. Calculate predicted demand: `baseline_daily_trips * (1 + avg_baseline_change_pct / 100)`
4. Generate staffing recommendation based on % change:
   - If < -20%: "Reduce staffing by X%"
   - If -20% to +20%: "Maintain staffing levels"
   - If > +20%: "Increase staffing by X%"

**Display Elements**:
- Predicted demand: "Estimated trips: X,XXX"
- Staffing recommendation: "Recommendation: Increase staffing by 25% compared to typical day"
- Confidence indicator:
  - High: ≥5 historical data points
  - Medium: 2-4 data points
  - Low: <2 data points
- Weather note: "Weather forecast unavailable - using average conditions" (since weather forecast integration is out of scope)

**Out of Scope** (per functional spec):
- Weather forecast API integration
- Specific numerical staffing (e.g., "deploy 4 trucks")
- Bike redistribution recommendations

---

### 2.4 Navigation Integration

**Modification**: Update Streamlit sidebar navigation in `streamlit_app/Home.py` or create `streamlit_app/pages/` structure

Since Streamlit automatically detects pages in the `pages/` directory, simply creating `streamlit_app/pages/Holiday_Impact.py` will add it to the navigation menu.

**Page Order**: Streamlit orders pages alphabetically by filename. Consider naming:
- `pages/1_Holiday_Impact.py` (if specific order desired)
- Or let Streamlit use default alphabetical ordering

---

## 3. Impact and Risk Analysis

### System Dependencies

**External Dependencies:**
- **Nager.Date API** (`https://date.nager.at`)
  - Purpose: Source of US holiday data
  - Dependency type: External HTTP API (no authentication)
  - Affected by: API downtime, rate limiting, schema changes
  - Mitigation: See risks below

**Internal Dependencies:**
- **dbt marts**: `mart_holiday_analysis` depends on:
  - `mart_demand_daily` (existing mart with trip aggregations)
  - `mart_weather_effect` (for weather normalization patterns)
  - `stg_holidays` (new staging model)

- **DuckDB databases**:
  - Input: `duckdb/bike_ingestion.duckdb`, `duckdb/weather_ingestion.duckdb`
  - Output: `duckdb/holiday_ingestion.duckdb`, `duckdb/warehouse.duckdb`

- **Streamlit dashboard**: Reads from `duckdb/warehouse.duckdb` (read-only connection)

### Potential Risks & Mitigations

#### 1. Insufficient Historical Data (High Likelihood, Medium Impact)

**Risk**: With only May-June 2024 bike trip data, very few holidays exist for meaningful analysis (Memorial Day 2024 is the primary data point).

**Impact**:
- Visualizations may show limited insights
- Statistical significance is low
- User may question feature value

**Mitigation**:
- Display prominent banner when `<2 holidays` have bike trip data: "Limited historical data available. Insights will strengthen as more data accumulates over time."
- Use "N/A" placeholders gracefully in tables and charts
- Design visualizations to handle sparse data (e.g., empty states, helpful messaging)
- Document in user-facing text that insights improve over time as more data accumulates

**Likelihood**: High (current dataset constraint)
**Severity**: Medium (feature still functional, just limited insights)

---

#### 2. Nager.Date API Availability (Medium Likelihood, Medium Impact)

**Risk**: External API may experience downtime, rate limiting, or network failures during pipeline execution.

**Impact**:
- Holiday data ingestion fails
- Dashboard shows stale or missing holiday information
- Manual re-run required

**Mitigation**:
- Implement request timeout (30 seconds) to fail fast
- Add retry logic with exponential backoff (3 attempts)
- Wrap API calls in try-except blocks with detailed error logging
- Cache API responses locally (dlt automatically handles this via DuckDB merge)
- Annual refresh cadence means temporary outages are acceptable (not real-time critical)

**Likelihood**: Medium (external dependencies always carry risk)
**Severity**: Medium (feature degraded but not broken; manual retry fixes)

---

#### 3. Holiday API Schema Changes (Low Likelihood, High Impact)

**Risk**: Nager.Date changes their API response structure, breaking our parsing logic.

**Impact**:
- Pipeline crashes during ingestion
- No new holiday data loaded
- Existing data remains functional (merge disposition preserves old data)

**Mitigation**:
- Add try-except blocks around JSON parsing
- Log full API response on errors for debugging
- Include schema version or API documentation URL in code comments
- Monitor pipeline logs for parsing errors
- Consider adding a simple schema validation check (e.g., verify required fields exist)

**Likelihood**: Low (public APIs rarely break backward compatibility)
**Severity**: High (requires code changes to fix)

---

#### 4. Weather Normalization Complexity (Medium Likelihood, Low Impact)

**Risk**: Weather-adjusted demand calculations may be complex, incorrect, or misleading to users.

**Impact**:
- Users misinterpret insights
- Operational decisions based on flawed metrics
- Requires rework of calculation logic

**Mitigation**:
- Include both raw trip counts AND weather-adjusted metrics in dashboard
- Allow users to compare raw vs. adjusted to build intuition
- Use simple, explainable normalization formulas (avoid black-box ML)
- Document calculation methodology in dashboard tooltips or help text
- Start with basic normalization (temperature/precipitation effects) and iterate based on feedback

**Likelihood**: Medium (weather normalization is inherently complex)
**Severity**: Low (users can fall back to raw metrics)

---

#### 5. Database Locking (Low Likelihood, Low Impact)

**Risk**: DuckDB warehouse is locked if dbt transformation runs while Streamlit dashboard is reading data.

**Impact**:
- Pipeline fails with "database locked" error
- User must close dashboard to run pipeline

**Mitigation**:
- All Streamlit connections use `read_only=True` (already implemented)
- DuckDB supports multiple readers simultaneously
- Write lock only occurs during `dbt build`, which is manual operation
- Document execution pattern: close dashboard before running pipeline (if needed)

**Likelihood**: Low (read-only connections prevent most locking issues)
**Severity**: Low (simple workaround: close dashboard)

---

#### 6. Performance with Large Date Ranges (Low Likelihood, Medium Impact)

**Risk**: Calendar heatmap visualization may be slow or memory-intensive with multi-year datasets.

**Impact**:
- Page load exceeds 3-second requirement (functional spec)
- Poor user experience
- Browser may hang on large datasets

**Mitigation**:
- Default calendar view to current year only (12 months max)
- Use Plotly's efficient heatmap rendering (hardware-accelerated)
- Apply `@st.cache_data(ttl=600)` to queries (avoid repeated computation)
- Consider adding year selector filter if multi-year support needed in future
- Test with projected 2-3 years of data to validate performance

**Likelihood**: Low (current dataset is small; multi-year is future concern)
**Severity**: Medium (impacts user experience)

---

#### 7. Null Handling for Missing Data (High Likelihood, Low Impact)

**Risk**: Holidays without bike trip data (future holidays, data gaps) cause NULL values in joins, potentially breaking visualizations.

**Impact**:
- Charts display errors or empty states
- Dashboard crashes on NULL calculations
- User confusion about missing data

**Mitigation**:
- Use LEFT JOIN logic in dbt to preserve all dates
- Add NULL checks in Streamlit code before rendering charts
- Display explicit "No Data" messages for holidays without trip data
- Use SQL `COALESCE()` for calculated fields with NULLs
- Test with intentionally sparse data (e.g., future holidays with no trips)

**Likelihood**: High (future holidays inherently lack trip data)
**Severity**: Low (expected behavior, not a bug)

---

### Performance Considerations

**Expected Dataset Size:**
- Holidays: ~15-20 per year × 2 years = 30-40 rows (very small)
- `mart_holiday_analysis`: Same row count as `mart_demand_daily` (~60 days currently, growing over time)
- Query performance: Subsecond response times expected (DuckDB is optimized for analytics)

**Optimization Strategies:**
- Materialize `mart_holiday_analysis` as table (not view) for dashboard query speed
- Use indexes on `ride_date` if query performance degrades (DuckDB auto-optimizes)
- Cache Streamlit queries for 10 minutes to reduce repeated database hits
- Limit calendar heatmap to single year by default

**Load Testing**: Not required for MVP (dataset is small; <100 users expected)

---

## 4. Testing Strategy

### Unit Tests

**File**: `tests/test_holidays_pipeline.py`

**Test Coverage:**

1. **API Response Parsing**
   - Mock successful API response with sample holiday data
   - Verify correct extraction of all fields (date, name, types, etc.)
   - Test filtering logic (nationwide + NY-specific holidays)

2. **Error Handling**
   - Mock API timeout → verify pipeline logs error and continues
   - Mock 404 response → verify graceful failure (no crash)
   - Mock invalid JSON → verify parsing error is caught and logged

3. **Data Type Conversions**
   - Verify date strings parsed to DATE type
   - Verify boolean fields (global, fixed) cast correctly
   - Verify array fields (types, counties) joined to comma-separated strings

4. **Primary Key Uniqueness**
   - Test with multiple years → verify no duplicate dates in output
   - Test with same holiday in multiple API calls → verify merge logic works

**Implementation Pattern:**
```python
@pytest.fixture
def mock_nager_api_response():
    return {
        "date": "2024-07-04",
        "localName": "Independence Day",
        "name": "Independence Day",
        "countryCode": "US",
        "fixed": False,
        "global": True,
        "counties": None,
        "launchYear": None,
        "types": ["Public"]
    }

def test_holiday_parsing(mock_nager_api_response, mocker):
    # Mock requests.get to return sample response
    mocker.patch('requests.get', return_value=mock_response)

    # Run pipeline and verify output
    # Assert expected fields exist and are correct types
```

**Mocking Library**: `pytest-mock` (already in project dependencies)

---

### dbt Tests

**Staging Layer Tests** (`dbt/models/staging/schema.yml`):

```yaml
version: 2

models:
  - name: stg_holidays
    description: Cleaned and standardized US holiday data from Nager.Date API
    columns:
      - name: date
        description: Holiday date (primary key)
        tests:
          - unique
          - not_null

      - name: holiday_name
        description: Official holiday name
        tests:
          - not_null

      - name: is_nationwide
        description: Whether holiday applies to all US states
        tests:
          - not_null
          - accepted_values:
              values: [true, false]

      - name: is_fixed
        description: Whether holiday date is fixed annually
        tests:
          - not_null
          - accepted_values:
              values: [true, false]

      - name: holiday_types
        description: Comma-separated holiday types (e.g., "Public, School")
        tests:
          - not_null
```

**Custom dbt Test** (row count validation):
```yaml
  - name: stg_holidays
    tests:
      - dbt_utils.expression_is_true:
          expression: "COUNT(*) > 0"
          config:
            severity: error
```

---

**Marts Layer Tests** (`dbt/models/marts/schema.yml`):

```yaml
version: 2

models:
  - name: mart_holiday_analysis
    description: Analytics-ready table combining holidays with daily bike demand metrics
    columns:
      - name: ride_date
        description: Date (primary key)
        tests:
          - unique
          - not_null

      - name: is_holiday
        description: Boolean flag for holiday dates
        tests:
          - not_null
          - accepted_values:
              values: [true, false]

      - name: demand_vs_baseline_pct
        description: Percentage change in demand vs. non-holiday baseline
        tests:
          - dbt_utils.accepted_range:
              min_value: -100
              max_value: 500
              inclusive: true
              where: "trips_total IS NOT NULL"  # Only test dates with data

      - name: holiday_category
        description: Holiday classification (Federal, State Observance, or NULL)
        tests:
          - accepted_values:
              values: ['Federal Holiday', 'NY State Observance', null]
              quote: false

    tests:
      # Verify LEFT JOIN preserved all dates from mart_demand_daily
      - dbt_utils.equal_rowcount:
          compare_model: ref('mart_demand_daily')
```

**Relationship Test** (referential integrity):
```yaml
      - name: holiday_name
        tests:
          - relationships:
              to: ref('stg_holidays')
              field: holiday_name
              where: "is_holiday = TRUE"  # Only test holiday dates
```

---

### Integration Tests

**Manual Validation Checklist** (run before merging to main branch):

#### 1. End-to-End Pipeline Execution

```bash
# Step 1: Run holiday ingestion
uv run python dlt_pipeline/holidays.py

# Verify: Check DuckDB for holiday data
uv run python -c "
import duckdb
conn = duckdb.connect('duckdb/holiday_ingestion.duckdb')
result = conn.execute('SELECT COUNT(*) FROM raw_holidays.us_holidays').fetchone()
print(f'Holidays loaded: {result[0]}')
assert result[0] > 20, 'Expected at least 20 holidays for 2024-2025'
"

# Step 2: Run dbt transformations
cd dbt
uv run dbt build --select stg_holidays mart_holiday_analysis

# Verify: Check mart table exists and has expected row count
uv run dbt test --select mart_holiday_analysis

# Step 3: Launch dashboard
cd ..
uv run streamlit run streamlit_app/Home.py

# Verify: Navigate to "Holiday Impact" page in browser
# Verify: Page loads in <3 seconds
```

#### 2. Data Quality Validation

**SQL Queries to Run** (via DuckDB CLI or Python):

```sql
-- Verify federal holidays exist
SELECT holiday_name, date
FROM main_marts.mart_holiday_analysis
WHERE is_holiday = TRUE AND holiday_category = 'Federal Holiday'
ORDER BY date;

-- Expected: New Year's Day, Memorial Day, Independence Day, Labor Day, Thanksgiving, Christmas

-- Verify NY-specific holidays (if any)
SELECT holiday_name, date
FROM main_marts.mart_holiday_analysis
WHERE is_holiday = TRUE AND holiday_category = 'NY State Observance';

-- Verify non-holiday dates have NULL holiday_name
SELECT COUNT(*)
FROM main_marts.mart_holiday_analysis
WHERE is_holiday = FALSE AND holiday_name IS NULL;

-- Verify baseline calculation
SELECT
    AVG(trips_total) AS calculated_baseline,
    AVG(baseline_daily_trips) AS stored_baseline
FROM main_marts.mart_holiday_analysis
WHERE is_holiday = FALSE;
-- Both values should match
```

#### 3. Dashboard Functionality Testing

**Test Cases:**

| Test Case | Steps | Expected Result |
|-----------|-------|-----------------|
| Page Load | Navigate to Holiday Impact page | Page loads in <3 seconds; banner displays (limited data) |
| Demand Comparison Chart | View bar chart | Shows 3 bars (Federal, Observance, Baseline); % change labels visible |
| Calendar Heatmap | View calendar | 2024 calendar displays; holidays marked; color intensity varies |
| Individual Holiday Dropdown | Select Memorial Day 2024 | Line chart shows 7 days; holiday marked; summary panel populated |
| Holiday with No Data | Select future holiday (e.g., New Year's 2025) | Chart shows "No trip data available" message |
| Performance Table | Sort by % Change column | Table re-sorts correctly; colors update |
| What-If Tool | Select upcoming holiday | Prediction displays; staffing recommendation shown; confidence = Low |

#### 4. Edge Cases

**Scenarios to Test:**

1. **Empty dataset**: Drop all bike trip data → verify dashboard shows "No data available" banner
2. **Single holiday**: Filter to only Memorial Day 2024 → verify banner shows "Limited historical data"
3. **NULL weather data**: Set `tmax` and `precip` to NULL for a holiday → verify summary panel shows "N/A"
4. **Long holiday name**: Test with holiday name >50 characters → verify text wrapping in calendar heatmap
5. **No upcoming holidays**: Mock current date to Dec 31, 2025 → verify What-If dropdown is empty or shows placeholder

---

### Performance Validation

**Acceptance Criteria** (from functional spec):
- Page load time: <3 seconds with current dataset size

**Measurement Approach:**
1. Use browser DevTools Network tab to measure time-to-interactive
2. Use Streamlit's built-in performance profiling: `st.experimental_get_query_params()` + timing logs
3. Test with projected 2-year dataset (simulate growth)

**Performance Targets:**
- Initial page load: <3 seconds
- Query execution (each visualization): <500ms
- Chart rendering (Plotly): <1 second

**Optimization Checkpoints:**
- If queries >500ms: Add DuckDB indexes or optimize SQL
- If rendering >1s: Reduce data points (e.g., limit calendar to single year)
- If total load >3s: Increase cache TTL or precompute aggregations in dbt

---

### Regression Testing

**Ensure existing functionality is not broken:**

1. Run full test suite: `uv run pytest tests/ -v`
2. Verify existing dashboard pages still load: Home, (any other existing pages)
3. Check `mart_demand_daily` row count unchanged (new mart doesn't affect upstream)
4. Verify `dbt build` completes without errors for all models

**Automated CI/CD** (if applicable):
- Add `tests/test_holidays_pipeline.py` to CI pipeline
- Run `dbt test` as part of CI checks
- Fail build if any test fails

---

## 5. Implementation Checklist

**Phase 1: Data Ingestion**
- [ ] Create `dlt_pipeline/holidays.py` with Nager.Date API integration
- [ ] Implement filtering logic (nationwide + NY-specific)
- [ ] Add error handling and retry logic
- [ ] Write unit tests in `tests/test_holidays_pipeline.py`
- [ ] Run pipeline and verify data in `duckdb/holiday_ingestion.duckdb`

**Phase 2: dbt Transformation**
- [ ] Create `dbt/models/staging/stg_holidays.sql`
- [ ] Create `dbt/models/marts/mart_holiday_analysis.sql`
- [ ] Implement weather normalization logic
- [ ] Add dbt tests to `schema.yml` files
- [ ] Run `dbt build` and verify mart table created

**Phase 3: Dashboard Development**
- [ ] Create `streamlit_app/pages/Holiday_Impact.py`
- [ ] Implement Visualization 1: Demand Comparison Bar Chart
- [ ] Implement Visualization 2: Calendar Heatmap
- [ ] Implement Visualization 3: Individual Holiday Analysis
- [ ] Implement Visualization 4: Performance Table
- [ ] Implement Visualization 5: What-If Planning Tool
- [ ] Add data validation and banner logic
- [ ] Test all visualizations with current dataset

**Phase 4: Testing & Validation**
- [ ] Run unit tests: `uv run pytest tests/test_holidays_pipeline.py -v`
- [ ] Run dbt tests: `cd dbt && uv run dbt test`
- [ ] Execute integration test checklist (manual validation)
- [ ] Test edge cases (empty data, NULL handling, etc.)
- [ ] Verify performance: page load <3 seconds

**Phase 5: Documentation & Deployment**
- [ ] Update `CLAUDE.md` with holiday pipeline commands
- [ ] Add docstrings to all new Python functions
- [ ] Update dbt model documentation (descriptions in `schema.yml`)
- [ ] Add usage instructions to README (if applicable)
- [ ] Deploy to production (manual pipeline run + dashboard deployment)

---

## 6. Future Enhancements (Out of Scope for MVP)

These items are explicitly out of scope per the functional specification but may be considered for future iterations:

1. **Airflow Orchestration**: Automate annual holiday data refresh via Airflow DAG
2. **Great Expectations Validation**: Add comprehensive data quality checks for holiday data
3. **Weather Forecast Integration**: Incorporate Open-Meteo forecast API for What-If tool predictions
4. **Year-over-Year Comparisons**: Compare holiday demand across multiple years (requires multi-year bike data)
5. **ML-Based Forecasting**: Replace heuristic predictions with ML models (Phase 2 feature)
6. **Multi-City Support**: Expand to other bike-share systems beyond NYC (Phase 4 feature)
7. **Real-Time Holiday Tracking**: Live dashboard updates during holidays (Phase 2+ feature)
8. **Custom Holiday Definitions**: Allow users to define organization-specific holidays
9. **Mobile Optimization**: Responsive design for mobile devices

---

## 7. Open Questions

- [ ] **Weather normalization formula**: Should we use the exact formula from `mart_weather_effect.sql`, or create a simplified version for holidays?
- [ ] **Holiday category naming**: Confirm "Federal Holiday" and "NY State Observance" are the preferred user-facing labels (vs. "Public Holiday", "State Holiday", etc.)
- [ ] **What-If confidence thresholds**: Are the proposed thresholds (High ≥5, Medium 2-4, Low <2 data points) appropriate for this use case?
- [ ] **Page navigation order**: Should "Holiday Impact" appear before or after existing pages in the Streamlit sidebar?

---

**End of Technical Specification**
