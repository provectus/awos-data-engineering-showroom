# Task List: Holiday Impact Analysis

- **Specification:** [Functional Spec](./functional-spec.md) | [Technical Considerations](./technical-considerations.md)
- **Status:** Ready for Implementation

---

## Implementation Approach

This task list follows a **vertical slicing** methodology where each main task represents a small, end-to-end, runnable increment of the feature. The application remains in a working state after each task is completed.

**Execution Order:** Complete tasks sequentially from Slice 1 → Slice 13.

---

## **Slice 1: Holiday Data Ingestion Foundation**

Set up the basic holiday data pipeline to fetch and store holiday data, verifying the data is accessible in DuckDB.

- [x] Create `dlt_pipeline/holidays.py` with basic structure:
  - [x] Sub-task: Define `@dlt.resource` function that fetches US holidays from Nager.Date API for 2024 and 2025
  - [x] Sub-task: Implement filtering logic to include only nationwide holidays OR NY-specific holidays
  - [x] Sub-task: Configure dlt pipeline with `merge` write disposition, primary key `date`, output to `duckdb/holiday_ingestion.duckdb`
  - [x] Sub-task: Add error handling (try-except blocks, retry logic with 3 attempts, timeout 30s)
  - [x] Sub-task: Add logging at INFO level for pipeline progress
  - [x] Sub-task: Create `run_holiday_pipeline()` function and `if __name__ == "__main__"` block for manual execution
- [x] Test the pipeline runs successfully:
  - [x] Sub-task: Execute `uv run python dlt_pipeline/holidays.py`
  - [x] Sub-task: Verify data exists in `duckdb/holiday_ingestion.duckdb` using DuckDB CLI or Python query (expect ~30-40 holidays)

**Validation:** Pipeline runs without errors and creates `holiday_ingestion.duckdb` with holiday data.

---

## **Slice 2: Holiday Staging Model (dbt)**

Create the dbt staging model to clean and standardize raw holiday data, making it queryable.

- [x] Create dbt staging model for holidays:
  - [x] Sub-task: Create `dbt/models/staging/stg_holidays.sql` that selects from `{{ source('raw_holidays', 'us_holidays') }}`
  - [x] Sub-task: Add transformations: cast `date` to DATE, cast booleans, trim whitespace, handle NULLs in `counties`
  - [x] Sub-task: Set materialization to `view` in model config
  - [x] Sub-task: Add source definition in `dbt/models/staging/sources.yml` (or update existing) for `raw_holidays.us_holidays`
- [x] Add dbt tests for staging model:
  - [x] Sub-task: Update `dbt/models/staging/schema.yml` with tests: `date` (unique, not_null), `is_nationwide` (not_null, accepted_values), `is_fixed` (not_null, accepted_values), `holiday_name` (not_null)
  - [x] Sub-task: Run `cd dbt && uv run dbt build --select stg_holidays`
  - [x] Sub-task: Verify staging model created and tests pass

**Validation:** `stg_holidays` view exists and passes all dbt tests. Can query holidays via dbt.

---

## **Slice 3: Basic Holiday Mart (without weather normalization)**

Create the analytics mart that joins holidays to bike trip data, enabling basic holiday analysis (raw trip counts only, no weather adjustment yet).

- [x] Create `mart_holiday_analysis` with basic functionality:
  - [x] Sub-task: Create `dbt/models/marts/mart_holiday_analysis.sql`
  - [x] Sub-task: LEFT JOIN `mart_demand_daily` with `stg_holidays` on `ride_date = date`
  - [x] Sub-task: Add computed columns: `is_holiday`, `holiday_name`, `holiday_category` (derived from `holiday_types`), `trips_total`, `tmax`, `precip`, `day_type`
  - [x] Sub-task: Calculate `baseline_daily_trips` as AVG of non-holiday trips
  - [x] Sub-task: Calculate `demand_vs_baseline_pct` using raw trip counts
  - [x] Sub-task: Set materialization to `table` for query performance
  - [x] Sub-task: Add placeholder column `trips_weather_adjusted` (initially equals `trips_total` - we'll implement normalization in next slice)
- [x] Add dbt tests for mart:
  - [x] Sub-task: Update `dbt/models/marts/schema.yml` with tests: `ride_date` (unique, not_null), `is_holiday` (not_null, accepted_values), `demand_vs_baseline_pct` (accepted_range -100 to 500)
  - [x] Sub-task: Add row count test: verify `mart_holiday_analysis` has same row count as `mart_demand_daily` (LEFT JOIN preservation)
  - [x] Sub-task: Run `cd dbt && uv run dbt build --select mart_holiday_analysis`
  - [x] Sub-task: Verify mart table created and tests pass

**Validation:** `mart_holiday_analysis` table exists, joins work correctly, basic metrics are calculated. Weather normalization is placeholder for now.

---

## **Slice 4: Weather Normalization Logic**

Enhance the mart with weather-adjusted demand calculations.

- [x] Implement weather normalization in `mart_holiday_analysis`:
  - [x] Sub-task: Review `mart_weather_effect.sql` for existing weather normalization patterns
  - [x] Sub-task: Update `mart_holiday_analysis.sql` to calculate `trips_weather_adjusted` using temperature and precipitation effects (formula: `trips_total * (avg_weather_factor / actual_weather_factor)`)
  - [x] Sub-task: Update `demand_vs_baseline_pct` to use weather-adjusted trips for comparison
  - [x] Sub-task: Run `cd dbt && uv run dbt build --select mart_holiday_analysis`
  - [x] Sub-task: Validate: Query mart to compare raw vs. adjusted trips for a known holiday (e.g., Memorial Day) - adjusted should differ based on weather

**Validation:** Weather-adjusted metrics are calculated correctly. Both raw and adjusted trip counts are available in the mart.

---

## **Slice 5: Basic Dashboard Page with Limited Data Banner**

Create the Holiday Impact page in Streamlit with basic structure, data connection, and the limited data banner.

- [ ] Create basic dashboard page structure:
  - [ ] Sub-task: Create `streamlit_app/pages/Holiday_Impact.py` with page config (title, icon 🎉, wide layout)
  - [ ] Sub-task: Add database connection using `duckdb.connect("duckdb/warehouse.duckdb", read_only=True)` with `@st.cache_resource`
  - [ ] Sub-task: Create cached query function `@st.cache_data(ttl=600)` to load `mart_holiday_analysis` data
  - [ ] Sub-task: Add data validation logic: count unique holidays with trip data
  - [ ] Sub-task: Display banner if `<2 holidays`: "⚠️ Limited historical data available. Insights will strengthen as more data accumulates over time."
  - [ ] Sub-task: Add page title: "Holiday Impact Analysis"
- [ ] Test page loads:
  - [ ] Sub-task: Run `uv run streamlit run streamlit_app/Home.py`
  - [ ] Sub-task: Navigate to "Holiday Impact" in sidebar
  - [ ] Sub-task: Verify page loads in <3 seconds and banner displays

**Validation:** Dashboard page is accessible, connects to database, displays banner, and loads quickly.

---

## **Slice 6: Visualization 1 - Holiday vs. Non-Holiday Demand Comparison**

Add the bar chart comparing average demand on holidays vs. non-holidays.

- [ ] Implement demand comparison bar chart:
  - [ ] Sub-task: Write SQL query to calculate average weather-adjusted demand by `holiday_category` (Federal, Observance, Non-Holiday Baseline)
  - [ ] Sub-task: Calculate percentage change vs. baseline for each category
  - [ ] Sub-task: Create Plotly grouped bar chart (`px.bar`) with holiday categories on X-axis, avg demand on Y-axis
  - [ ] Sub-task: Add percentage change labels on each bar
  - [ ] Sub-task: Add hover tooltips showing: exact trip count, number of holidays, date range
  - [ ] Sub-task: Use distinct colors for each category (blue for Federal, orange for State, gray for baseline)
  - [ ] Sub-task: Add chart to dashboard page with section header
- [ ] Test visualization:
  - [ ] Sub-task: Refresh dashboard and verify chart displays correctly
  - [ ] Sub-task: Hover over bars to verify tooltips show correct data

**Validation:** Bar chart displays with 3 bars, percentage labels, and interactive tooltips. Data matches expected values from mart.

---

## **Slice 7: Visualization 2 - Holiday Calendar Heatmap**

Add the calendar view with demand overlay and holiday highlighting.

- [ ] Implement calendar heatmap:
  - [ ] Sub-task: Write SQL query to get all dates for 2024 with `is_holiday`, `holiday_name`, `trips_total`, data status
  - [ ] Sub-task: Create Plotly heatmap or custom grid layout for 12-month calendar view
  - [ ] Sub-task: Set cell background color intensity based on `trips_total` (darker = higher demand)
  - [ ] Sub-task: Add distinct border or icon for holiday dates
  - [ ] Sub-task: Display holiday names as text labels on holiday cells
  - [ ] Sub-task: Show "No Data" indicator (gray cells) where `trips_total IS NULL`
  - [ ] Sub-task: Add color scale legend ("Low Demand" → "High Demand")
  - [ ] Sub-task: Add calendar to dashboard page with section header
- [ ] Test visualization:
  - [ ] Sub-task: Verify calendar displays full year 2024
  - [ ] Sub-task: Verify holidays are visually distinct and labeled
  - [ ] Sub-task: Verify color intensity varies with demand levels

**Validation:** Calendar heatmap displays 2024, highlights holidays with borders/icons, shows holiday names, color-codes demand levels, and handles no-data gracefully.

---

## **Slice 8: Visualization 3 - Individual Holiday Analysis**

Add the dropdown and line chart for analyzing a specific holiday with ±3 days context.

- [ ] Implement individual holiday analysis:
  - [ ] Sub-task: Create dropdown using `st.selectbox()` listing all holidays (format: "Holiday Name - Date")
  - [ ] Sub-task: Write parameterized SQL query to get ±3 days of data around selected holiday (7 days total)
  - [ ] Sub-task: Create Plotly line chart (`px.line`) showing daily trip counts over 7-day window
  - [ ] Sub-task: Add vertical line or annotation marking the holiday date
  - [ ] Sub-task: Add horizontal baseline reference line at `baseline_daily_trips` value
  - [ ] Sub-task: Create summary panel using `st.metric()` showing: holiday name, date, total trips on holiday, % change vs. baseline, weather (temp, precip)
  - [ ] Sub-task: Add NULL handling: if `trips_total IS NULL`, display "No trip data available for this holiday"
  - [ ] Sub-task: Add to dashboard page with section header
- [ ] Test visualization:
  - [ ] Sub-task: Select Memorial Day 2024 from dropdown
  - [ ] Sub-task: Verify line chart shows 7 days with holiday marked
  - [ ] Sub-task: Verify summary panel populates correctly
  - [ ] Sub-task: Select a future holiday and verify "No data" message displays

**Validation:** Dropdown lists all holidays, line chart displays 7-day window with holiday marker and baseline, summary panel shows metrics, NULL handling works.

---

## **Slice 9: Visualization 4 - Holiday Type Performance Table**

Add the sortable table showing demand metrics by holiday type.

- [ ] Implement performance table:
  - [ ] Sub-task: Write SQL query to aggregate by `holiday_category`: number of holidays, avg demand, % change vs. baseline, sample holidays (STRING_AGG)
  - [ ] Sub-task: Add "Total/Average" row summarizing all holidays
  - [ ] Sub-task: Truncate "Sample Holidays" to 2-3 examples in Python code
  - [ ] Sub-task: Create Streamlit dataframe using `st.dataframe()` with sortable columns
  - [ ] Sub-task: Apply styling function to color-code % change (green for positive, red for negative)
  - [ ] Sub-task: Handle NULL values by displaying "N/A"
  - [ ] Sub-task: Bold the "Total/Average" row
  - [ ] Sub-task: Add table to dashboard page with section header
- [ ] Test visualization:
  - [ ] Sub-task: Verify table displays with correct columns
  - [ ] Sub-task: Click column headers to verify sorting works
  - [ ] Sub-task: Verify % change colors are correct (green/red)

**Validation:** Table displays holiday types with metrics, is sortable, shows color-coded % change, handles NULLs with "N/A", and includes Total/Average row.

---

## **Slice 10: Visualization 5 - What-If Holiday Planning Tool**

Add the prediction tool for upcoming holidays with staffing recommendations.

- [ ] Implement what-if planning tool:
  - [ ] Sub-task: Create dropdown using `st.selectbox()` listing upcoming holidays (filter to `ride_date > CURRENT_DATE` and within next 365 days)
  - [ ] Sub-task: Write SQL query to get historical average demand for selected holiday's category
  - [ ] Sub-task: Implement prediction logic: use historical average for holiday type to estimate demand
  - [ ] Sub-task: Generate staffing recommendation based on % change: "<-20%" = Reduce, "-20% to +20%" = Maintain, ">+20%" = Increase
  - [ ] Sub-task: Calculate confidence indicator: High (≥5 data points), Medium (2-4), Low (<2)
  - [ ] Sub-task: Display predicted demand using `st.metric()` or `st.info()` boxes
  - [ ] Sub-task: Display staffing recommendation: "Recommendation: [Increase/Reduce/Maintain] staffing by X% compared to typical day"
  - [ ] Sub-task: Display confidence badge and weather note: "Weather forecast unavailable - using average conditions"
  - [ ] Sub-task: Add to dashboard page with section header
- [ ] Test tool:
  - [ ] Sub-task: Select an upcoming holiday (e.g., New Year's 2025)
  - [ ] Sub-task: Verify prediction displays with staffing recommendation
  - [ ] Sub-task: Verify confidence indicator shows (likely "Low" with limited data)
  - [ ] Sub-task: Verify weather note displays

**Validation:** Dropdown lists upcoming holidays, predictions display with staffing recommendations, confidence indicator shows, weather disclaimer is visible.

---

## **Slice 11: Unit Tests for Holiday Pipeline**

Add comprehensive unit tests for the dlt holiday pipeline.

- [ ] Create unit tests file:
  - [ ] Sub-task: Create `tests/test_holidays_pipeline.py`
  - [ ] Sub-task: Add pytest fixture with mock Nager.Date API response (sample holiday JSON)
  - [ ] Sub-task: Write test for successful API response parsing (verify all fields extracted correctly)
  - [ ] Sub-task: Write test for filtering logic (verify nationwide + NY-specific holidays are included)
  - [ ] Sub-task: Write test for error handling: mock API timeout, verify pipeline logs error and continues
  - [ ] Sub-task: Write test for error handling: mock 404 response, verify graceful failure
  - [ ] Sub-task: Write test for error handling: mock invalid JSON, verify parsing error caught
  - [ ] Sub-task: Write test for data type conversions (date strings → DATE, booleans)
  - [ ] Sub-task: Write test for primary key uniqueness (multiple years, no duplicate dates)
- [ ] Run unit tests:
  - [ ] Sub-task: Execute `uv run pytest tests/test_holidays_pipeline.py -v`
  - [ ] Sub-task: Verify all tests pass

**Validation:** Unit tests cover API parsing, filtering, error handling, and data types. All tests pass.

---

## **Slice 12: Integration Testing & Performance Validation**

Perform end-to-end testing to ensure the complete feature works correctly.

- [ ] Execute integration test checklist:
  - [ ] Sub-task: Run full pipeline: `uv run python dlt_pipeline/holidays.py && cd dbt && uv run dbt build && cd ..`
  - [ ] Sub-task: Verify holiday count in `holiday_ingestion.duckdb` (expect ~30-40 holidays)
  - [ ] Sub-task: Verify `mart_holiday_analysis` row count matches `mart_demand_daily`
  - [ ] Sub-task: Run all dbt tests: `cd dbt && uv run dbt test`
  - [ ] Sub-task: Launch dashboard and navigate to Holiday Impact page
  - [ ] Sub-task: Measure page load time using browser DevTools (<3 seconds required)
  - [ ] Sub-task: Test all 5 visualizations for correct display
  - [ ] Sub-task: Test edge cases: verify banner shows with limited data, verify NULL handling in charts
- [ ] Run regression tests:
  - [ ] Sub-task: Execute full test suite: `uv run pytest tests/ -v`
  - [ ] Sub-task: Verify existing dashboard pages still load (Home page)
  - [ ] Sub-task: Verify `mart_demand_daily` unchanged (no upstream impact)

**Validation:** Full pipeline runs successfully, all tests pass, dashboard loads in <3 seconds, all visualizations work correctly, no regressions in existing functionality.

---

## **Slice 13: Documentation & Final Polish**

Update documentation and add final touches to prepare for deployment.

- [ ] Update project documentation:
  - [ ] Sub-task: Update `CLAUDE.md` with holiday pipeline commands (ingestion, dbt, dashboard)
  - [ ] Sub-task: Add docstrings to all functions in `holidays.py` (Google-style)
  - [ ] Sub-task: Update dbt model descriptions in `schema.yml` files (staging and marts)
  - [ ] Sub-task: Add inline code comments for complex logic (weather normalization, filtering)
- [ ] Final manual validation:
  - [ ] Sub-task: Review all 5 visualizations in dashboard for polish (titles, labels, formatting)
  - [ ] Sub-task: Verify error messages are user-friendly (no technical jargon)
  - [ ] Sub-task: Check for any TODO comments left in code
  - [ ] Sub-task: Verify color scheme is consistent and accessible
- [ ] Prepare for deployment:
  - [ ] Sub-task: Run final `uv run ruff check . --fix && uv run ruff format .` to ensure code quality
  - [ ] Sub-task: Commit changes with descriptive commit message
  - [ ] Sub-task: Update CHANGELOG or release notes (if applicable)

**Validation:** All documentation updated, code is polished and formatted, no TODOs remain, ready for production deployment.

---

## Progress Tracking

**Total Slices:** 13
**Completed:** 4
**In Progress:** 0
**Remaining:** 9

---

## Notes

- **Vertical Slicing Philosophy:** Each slice delivers a small piece of end-to-end functionality. After each slice, the application remains in a runnable, working state.
- **Testing Strategy:** Unit tests (Slice 11) and integration tests (Slice 12) come after core functionality is complete, but you can run them incrementally during development.
- **Data Limitations:** With only May-June 2024 bike data, expect limited historical insights (Memorial Day 2024 is the primary holiday). The banner will warn users about this.
- **Out of Scope:** Airflow orchestration and Great Expectations validation are intentionally excluded per the functional spec.

---

## Next Steps

To begin implementation, execute:

```bash
/awos:implement
```

This will launch the implementation agent to execute tasks sequentially, delegating to specialized agents as needed.
