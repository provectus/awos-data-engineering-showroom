# Functional Specification: Data Quality Framework

- **Roadmap Item:** Phase 5 - Data Quality Framework
- **Status:** Draft
- **Author:** Claude

---

## 1. Overview and Rationale (The "Why")

### Problem Statement
Maria the Operations Manager relies on accurate demand forecasts to dispatch rebalancing trucks. Bad data leads to bad predictions, which leads to empty or overfull stations and customer complaints. Currently, there is no systematic way to:
- Know if data is fresh and complete before making decisions
- Catch data quality issues before they propagate to dashboards
- Understand which data sources are healthy vs. problematic

### Desired Outcome
A comprehensive data quality framework that automatically validates all data sources, alerts when quality issues occur, and provides visibility into data health through a dedicated dashboard.

### Success Criteria
- All 4 data sources (bike trips, weather, holidays, games) have automated quality checks
- Data quality issues are detected within 24 hours (daily DAG)
- Operations team can see data health at a glance in Streamlit dashboard
- Failed quality checks are visible in Airflow UI (red tasks)

---

## 2. Functional Requirements (The "What")

### Feature 1: dbt Testing Enhancement

**As an** operations team member, **I want** comprehensive data quality tests in dbt, **so that** I can trust the transformed data in dashboards.

**Acceptance Criteria:**
- [ ] Source freshness checks configured for all 4 raw sources with 10-day threshold
  - `raw_bike.bike_trips` - warn if data older than 10 days
  - `raw_weather.daily_weather` - warn if data older than 10 days
  - `raw_holidays.us_holidays` - warn if data older than 10 days
  - `raw_games.mlb_games` - warn if data older than 10 days
- [ ] Uniqueness tests on all primary keys (no duplicate records)
- [ ] Not null tests on all critical columns (IDs, dates, required fields)
- [ ] Referential integrity tests (foreign keys reference valid parent records)
- [ ] dbt_utils and/or dbt_expectations packages installed and configured
- [ ] All tests pass when running `uv run dbt test` from `dbt/` directory

---

### Feature 2: Great Expectations Redesign

**As an** operations team member, **I want** data validation at the ingestion layer, **so that** bad data is caught before it enters the warehouse.

**Acceptance Criteria:**
- [ ] Current GX implementation reviewed and fixed (whatever issues exist)
- [ ] Validation suite for bike trips data (existing - verify working)
- [ ] Validation suite for weather data (existing - verify working)
- [ ] Validation suite for holidays data (new - not null, valid ranges, uniqueness)
- [ ] Validation suite for games data (new - not null, valid ranges, uniqueness)
- [ ] All validations runnable from repo root: `uv run python data_quality/validate_all.py`
- [ ] All validations runnable from Airflow (same logic, different entry point)
- [ ] Validation results output in consistent format for storage

---

### Feature 3: Data Quality DAG

**As an** operations team member, **I want** automated daily quality checks, **so that** I know immediately when data issues occur.

**Acceptance Criteria:**
- [ ] New DAG file `data_quality_dag.py` created in `airflow/dags/`
- [ ] DAG runs daily at a fixed time (independent of ingestion DAG)
- [ ] DAG includes task to run `dbt test`
- [ ] DAG includes task to run Great Expectations checkpoints
- [ ] Test results stored in `data_quality` schema within `warehouse.duckdb`
- [ ] Results table includes: test_name, test_type (dbt/gx), status (pass/fail), run_timestamp, failure_details
- [ ] DAG task fails (shows red in Airflow UI) when any test fails
- [ ] DAG runnable with: `uv run airflow dags trigger data_quality_dag`

---

### Feature 4: Data Quality Dashboard

**As an** operations team member, **I want** a dashboard showing data health, **so that** I can quickly assess if data is trustworthy before making decisions.

**Acceptance Criteria:**
- [ ] New Streamlit page `pages/Data_Quality.py` created
- [ ] Dashboard shows latest run summary:
  - Total tests run
  - Pass count and percentage
  - Fail count
  - Last run timestamp
- [ ] Dashboard shows data freshness per source:
  - Bike trips: last record date, freshness status (OK/STALE)
  - Weather: last record date, freshness status
  - Holidays: last record date, freshness status
  - Games: last record date, freshness status
- [ ] Dashboard shows list of failed tests (if any) with:
  - Test name
  - Test type (dbt or GX)
  - Failure details/message
- [ ] User can drill into individual test failures to see details
- [ ] Dashboard accessible from main Streamlit navigation

---

## 3. Scope and Boundaries

### In-Scope
- dbt test enhancements using dbt_utils/dbt_expectations packages
- Source freshness checks with 10-day thresholds
- Great Expectations fixes and extension to all 4 data sources
- Dedicated daily Airflow DAG for quality checks
- Results storage in `data_quality` schema
- Streamlit dashboard showing latest run and freshness indicators

### Out-of-Scope
- Historical trend analysis (tracking quality over time) - Future enhancement
- Alerting/notifications (email, Slack) on failures - Future enhancement
- Real-time quality monitoring (only daily batch) - Future enhancement
- Phase 6: Forecast Accuracy Tracking - Separate roadmap item
- Phase 7: Jersey City Bike Share Integration - Separate roadmap item