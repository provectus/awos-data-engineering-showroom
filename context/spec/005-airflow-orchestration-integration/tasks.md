# Tasks: Airflow Orchestration Integration

**Spec:** 005-airflow-orchestration-integration
**Status:** Ready for Implementation

---

## Slice 1: Fix games.py and verify it works in Airflow

**Goal:** Fix the broken games.py pipeline so it runs successfully in Airflow. This is the most critical fix.

- [ ] Add `credentials_path` parameter to `run_game_pipeline()` in `dlt_pipeline/games.py`
- [ ] Add `DUCKDB_PATH` constant to DAG file (absolute path from project_root)
- [ ] Update DAG's `ingest_game_data()` task to pass `DUCKDB_PATH` as `credentials_path`
- [ ] Test games.py standalone: `uv run python dlt_pipeline/games.py`
- [ ] Test DAG loads without errors: `uv run python airflow/dags/bike_weather_dag.py`
- [ ] **[MANUAL]** Ask user to trigger DAG in Airflow and verify games ingestion succeeds

---

## Slice 2: Standardize bike.py and weather.py with credentials_path

**Goal:** Apply the same pattern to bike.py and weather.py for consistency. System remains runnable.

- [ ] Add `credentials_path` parameter to `run_bike_pipeline()` in `dlt_pipeline/bike.py`
- [ ] Add `credentials_path` parameter to `run_weather_pipeline()` in `dlt_pipeline/weather.py`
- [ ] Update DAG's `ingest_bike_data()` task to pass `DUCKDB_PATH`
- [ ] Update DAG's `ingest_weather_data()` task to pass `DUCKDB_PATH`
- [ ] Test bike.py standalone: `uv run python dlt_pipeline/bike.py`
- [ ] Test weather.py standalone: `uv run python dlt_pipeline/weather.py`
- [ ] Test DAG loads without errors: `uv run python airflow/dags/bike_weather_dag.py`
- [ ] **[MANUAL]** Ask user to trigger DAG and verify all 3 ingestion tasks succeed

---

## Slice 3: Add holidays.py to Airflow DAG

**Goal:** Add the missing holidays pipeline to orchestration. All 4 pipelines now in DAG.

- [ ] Add `credentials_path` parameter to `run_holiday_pipeline()` in `dlt_pipeline/holidays.py`
- [ ] Add import for `run_holiday_pipeline` in DAG file
- [ ] Add `ingest_holiday_data()` task to DAG
- [ ] Update pipeline dependencies to include `ingest_holidays` in parallel group
- [ ] Test holidays.py standalone: `uv run python dlt_pipeline/holidays.py`
- [ ] Test DAG loads without errors: `uv run python airflow/dags/bike_weather_dag.py`
- [ ] **[MANUAL]** Ask user to trigger DAG and verify all 4 ingestion tasks run in parallel

---

## Slice 4: Add DAG date parameters with previous month defaults

**Goal:** Make date ranges configurable via DAG params. Enables custom date range triggers.

- [ ] Add `get_previous_month_range()` helper function to DAG
- [ ] Add `get_months_from_date_range()` helper function to DAG
- [ ] Add `params` dict with `start_date` and `end_date` defaults to DAG definition
- [ ] Update `ingest_bike_data()` to read params and convert to months list
- [ ] Update `ingest_weather_data()` to read params and pass dates
- [ ] Update `ingest_game_data()` to read params and pass dates
- [ ] Update `ingest_holiday_data()` to read params and extract years
- [ ] Test DAG loads without errors: `uv run python airflow/dags/bike_weather_dag.py`
- [ ] **[MANUAL]** Ask user to trigger DAG with default params and verify it uses previous month
- [ ] **[MANUAL]** Ask user to trigger DAG with custom params and verify: `uv run airflow dags trigger bike_weather_pipeline --conf '{"start_date": "2024-05-01", "end_date": "2024-06-30"}'`

---

## Slice 5: Update trigger rules and schedule

**Goal:** Ensure dbt runs regardless of ingestion failures and change to weekly schedule.

- [ ] Add `trigger_rule="all_done"` to `dbt_deps` BashOperator
- [ ] Change `schedule_interval` from `"@daily"` to `"@weekly"`
- [ ] Test DAG loads without errors: `uv run python airflow/dags/bike_weather_dag.py`
- [ ] **[MANUAL]** Ask user to verify in Airflow UI that schedule shows as weekly
- [ ] **[MANUAL]** Ask user to verify dbt_deps runs even when upstream task fails (optional - can skip if time constrained)

---

## Slice 6: Update README documentation

**Goal:** Document the orchestration setup for users.

- [ ] Add/update "Airflow Orchestration" section in README.md
- [ ] Document all 4 pipelines are orchestrated (bike, weather, games, holidays)
- [ ] Document weekly schedule
- [ ] Document default date range behavior (previous month)
- [ ] Document how to trigger with custom parameters via Airflow CLI
- [ ] Document standalone execution still works from project root
- [ ] Review documentation for accuracy and completeness

---

## Slice 7: Final validation and cleanup

**Goal:** Complete end-to-end validation of all requirements.

- [ ] Verify all 4 standalone pipelines work from project root
- [ ] **[MANUAL]** Ask user to start Airflow and trigger full DAG run
- [ ] **[MANUAL]** Ask user to verify all 4 ingestion tasks complete in Airflow UI
- [ ] **[MANUAL]** Ask user to verify dbt_deps and dbt_build complete
- [ ] Verify DuckDB has data in all raw schemas (raw_bike, raw_weather, raw_games, raw_holidays)
- [ ] Verify Streamlit dashboard loads: `uv run streamlit run streamlit_app/Home.py`
- [ ] Run linting: `uv run ruff check .`
- [ ] Fix any linting issues

---

## Success Criteria (from Functional Spec)

- [ ] All 4 dlt pipelines execute successfully in Airflow DAG
- [ ] DAG accepts `start_date` and `end_date` parameters (defaults to previous month)
- [ ] dbt build runs after all ingestion tasks complete (regardless of individual success/failure)
- [ ] Standalone execution continues to work for all pipelines
- [ ] README documentation updated with Airflow usage instructions
