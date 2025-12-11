# Functional Specification: Airflow Orchestration Integration

- **Roadmap Item:** Phase 4 - Airflow Orchestration Integration
- **Status:** Draft
- **Author:** Product Team

---

## 1. Overview and Rationale (The "Why")

**The Problem:** Currently, not all dlt pipelines are scheduled with Airflow. The holidays pipeline is completely missing from orchestration, and the games pipeline fails due to DuckDB path configuration issues. This means:
- Operations teams must manually run holiday ingestion
- Game data ingestion fails in automated runs
- No unified way to specify date ranges for data ingestion
- Pipeline execution is inconsistent between Airflow and standalone modes

**Desired Outcome:** All 4 dlt pipelines (bike, weather, games, holidays) run successfully in Airflow with configurable date parameters, while maintaining standalone execution capability for testing. This creates a foundation for the Continuous Data Pipeline work in Phase 4.

**Success Metrics:**
- All 4 dlt pipelines execute successfully in Airflow DAG
- DAG accepts `start_date` and `end_date` parameters (defaults to previous month)
- dbt build runs after all ingestion tasks complete (regardless of individual success/failure)
- Standalone execution continues to work for all pipelines
- README documentation updated with Airflow usage instructions

---

## 2. Functional Requirements (The "What")

### Requirement 1: Add holidays.py to Airflow DAG

The holidays pipeline must be integrated into the existing Airflow DAG.

**Acceptance Criteria:**
- [ ] `ingest_holiday_data` task added to DAG
- [ ] Task extracts years from DAG `start_date` and `end_date` parameters
- [ ] Task calls `run_holiday_pipeline()` with extracted years
- [ ] Task runs in parallel with bike, weather, and games ingestion tasks
- [ ] Task failure does not block other ingestion tasks

### Requirement 2: Fix games.py DuckDB Path Issue

The games pipeline currently fails in Airflow due to DuckDB configuration. Fix without changing the DuckDB path (which works for bike and weather).

**Acceptance Criteria:**
- [ ] Identify root cause of games.py failure in Airflow (likely working directory or DLT_PROJECT_DIR issue)
- [ ] Fix games.py to use same pattern as bike.py and weather.py
- [ ] games.py continues to work in standalone mode (`uv run python dlt_pipeline/games.py`)
- [ ] games.py works in Airflow DAG execution
- [ ] No changes to `./duckdb/warehouse.duckdb` path in secrets.toml

### Requirement 3: DAG Date Parameters

The DAG must accept date range parameters with sensible defaults for previous month (since bike data has ~1 month delay).

**Acceptance Criteria:**
- [ ] DAG accepts `start_date` parameter (YYYY-MM-DD format)
- [ ] DAG accepts `end_date` parameter (YYYY-MM-DD format)
- [ ] Default `start_date`: first day of previous month
- [ ] Default `end_date`: last day of previous month
- [ ] Parameters can be overridden when triggering DAG manually via Airflow UI
- [ ] Each pipeline translates parameters to its native format:
  - bike.py: Convert date range to months list (e.g., `["202411"]`)
  - weather.py: Pass dates as-is (YYYY-MM-DD)
  - games.py: Pass dates as-is (YYYY-MM-DD)
  - holidays.py: Extract unique years from date range (e.g., `[2024]`)

### Requirement 4: DAG Schedule Change

Update DAG schedule from daily to weekly.

**Acceptance Criteria:**
- [ ] DAG `schedule_interval` changed from `@daily` to `@weekly`
- [ ] DAG continues to be triggerable manually on-demand

### Requirement 5: dbt Execution Trigger Rule

dbt build must run after all ingestion tasks complete, regardless of whether they succeeded or failed.

**Acceptance Criteria:**
- [ ] dbt_deps task has `trigger_rule='all_done'`
- [ ] dbt_build task runs after dbt_deps (maintains current dependency)
- [ ] If bike ingestion fails but weather succeeds, dbt still runs and processes available data
- [ ] If all ingestion tasks fail, dbt still attempts to run (will use existing data)

### Requirement 6: README Documentation Update

Update README.md to document Airflow orchestration with all 4 pipelines.

**Acceptance Criteria:**
- [ ] Document all 4 dlt pipelines are orchestrated by Airflow
- [ ] Document how to trigger DAG with custom date parameters via Airflow UI
- [ ] Document default date range behavior (previous month)
- [ ] Document weekly schedule
- [ ] Update architecture diagram if needed to show holidays pipeline

---

## 3. Scope and Boundaries

### In-Scope

- Adding holidays.py to Airflow DAG
- Fixing games.py DuckDB path issue for Airflow execution
- Adding DAG parameters for start_date and end_date
- Changing DAG schedule to weekly
- Setting trigger_rule='all_done' for dbt tasks
- Updating README documentation
- Ensuring all pipelines work both in Airflow and standalone mode

### Out-of-Scope

- **Continuous Data Pipeline** - Dynamic date ranges in dbt, incremental loading, historical backfill (separate roadmap item in Phase 4)
- **Data Quality DAG** - Great Expectations integration (Phase 5)
- **CLI argument parsing for standalone mode** - Hardcoded dates are acceptable for test runs
- **Changes to DuckDB path** - Must remain `./duckdb/warehouse.duckdb`
- **Changes to dlt pipeline core logic** - Only configuration/path fixes allowed
- **Forecast Accuracy Tracking** - Phase 6 item
- **Model Performance Dashboard** - Phase 6 item
