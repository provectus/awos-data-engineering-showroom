# Tasks: Data Quality Framework (Spec 007)

**Status:** COMPLETED

---

## Slice 1: Fix Great Expectations (bike + weather) - COMPLETED

**Goal:** Fix broken GX config to point to `warehouse.duckdb`, verify existing validations work.

**Note:** Discovered DuckDB/SQLAlchemy compatibility issue with GX. Rewrote to use pandas DataFrames instead of SQL connections.

- [x] Rewrote `validate_all.py` to use pandas DataFrames (bypasses DuckDB/SQLAlchemy issue)
- [x] Cleaned up `great_expectations.yml` - removed obsolete SQL datasources
- [x] Verified queries use correct schema paths (`raw_bike.bike_trips`, `raw_weather.daily_weather`)
- [x] Existing expectation suites work: `bike_trips_suite.json`, `weather_suite.json`
- [x] Checkpoints are created dynamically by validation script
- [x] Verify: Run `uv run python data_quality/validate_all.py` from repo root - PASSED

---

## Slice 2: Extend Great Expectations (holidays + games) - COMPLETED

**Goal:** Add expectation suites for holidays and games, update validation script.

- [x] Create `expectations/holidays_suite.json` (not_null on date/holiday_name, unique on date, row count >= 1)
- [x] Create `expectations/games_suite.json` (not_null on game_id/game_date/venue_name, unique on game_id, row count >= 1)
- [x] Add holidays and games to DATA_SOURCES dict in `validate_all.py`
- [x] Verify: Run `uv run python data_quality/validate_all.py` - all 4 sources pass

---

## Slice 3: dbt Source Definitions with Freshness - COMPLETED

**Goal:** Add source definitions with freshness checks and uniqueness/not_null tests on raw tables.

- [x] Add `raw_bike` source definition with freshness (10-day warn, 15-day error) and tests on `ride_id` (in sources.yml)
- [x] Add `raw_weather` source definition with freshness and tests on `date` (in sources.yml)
- [x] Update existing `raw_holidays` source definition with freshness checks (in schema.yml)
- [x] Update existing `raw_games` source definition with freshness checks and tests on `game_id` (in schema.yml)
- [x] Verify: `uv run dbt source freshness` - freshness checks work (stale for historical data is expected)
- [x] Verify: `uv run dbt test` - all 138 tests pass

---

## Slice 4: Data Quality DAG with Results Storage - COMPLETED

**Goal:** Create Airflow DAG that runs GX + dbt tests and stores results in DuckDB.

**Note:** All tasks run as subprocesses to isolate memory from Airflow standalone scheduler. Heavy imports (GX, pandas, duckdb) in the scheduler process caused crashes.

- [x] Create `airflow/dags/data_quality_dag.py` with DAG definition (daily at 6 AM UTC)
- [x] Add `run_gx_validations` task (subprocess: `python data_quality/validate_all.py`)
- [x] Add `run_dbt_tests` task (subprocess: `dbt test`)
- [x] Add `store_results` task (subprocess: `python data_quality/store_results.py`)
- [x] Create `data_quality/store_results.py` script for isolated results storage
- [x] Add env vars `TQDM_DISABLE=1` and `GE_USAGE_STATISTICS=FALSE` to prevent progress bar slowdowns
- [x] Wire task dependencies: `run_gx_validations` + `run_dbt_tests` → `store_results`
- [x] Verify: DAG runs successfully in Airflow standalone without crashing scheduler

---

## Slice 5: Data Quality Dashboard - COMPLETED

**Goal:** Create Streamlit page showing test results and freshness status.

- [x] Create `streamlit_app/pages/Data_Quality.py` with page config and DB connection
- [x] Add `load_latest_results()` function to query `data_quality.test_results`
- [x] Add `load_freshness_data()` function to query max dates from raw tables
- [x] Add KPI cards section (total tests, passed, failed, pass rate)
- [x] Add Data Freshness section with OK/WARN/STALE status (color-coded)
- [x] Add Failed Tests section with expandable details
- [x] Verify: Python syntax valid, queries work correctly

---

## Completion Checklist

- [x] All GX validations pass: `uv run python data_quality/validate_all.py` (4/4 sources)
- [x] All dbt tests pass: `uv run dbt test --profiles-dir . --project-dir .` (138 tests)
- [x] Source freshness works: `uv run dbt source freshness --profiles-dir . --project-dir .`
- [x] DAG created and tasks execute correctly
- [x] Dashboard displays test results and freshness status
- [x] Update roadmap.md to mark Phase 5 as complete