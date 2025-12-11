# Technical Specification: Data Quality Framework

- **Functional Specification:** `context/spec/007-data-quality-framework/functional-spec.md`
- **Status:** Approved
- **Author(s):** Claude

---

## 1. High-Level Technical Approach

This specification implements a comprehensive data quality framework with four components:

1. **dbt Testing Enhancement** - Add source freshness checks and expand test coverage using existing `dbt_utils` package
2. **Great Expectations Redesign** - Fix broken configuration (pointing to obsolete databases), add validation for all 4 raw data sources
3. **Data Quality DAG** - New daily Airflow DAG that runs validations and stores results in DuckDB
4. **Data Quality Dashboard** - New Streamlit page querying stored results

**Systems affected:**
- `dbt/` - Source definitions and tests in schema.yml
- `data_quality/` - GX configuration and validation scripts
- `airflow/dags/` - New DAG file
- `streamlit_app/pages/` - New dashboard page
- `duckdb/warehouse.duckdb` - New `data_quality` schema

---

## 2. Proposed Solution & Implementation Plan (The "How")

### Feature 1: dbt Testing Enhancement

**Files to modify:**
- `dbt/models/staging/schema.yml` - Add source definitions with freshness
- `dbt/packages.yml` - No change (dbt_utils already installed)

**Implementation:**

Add source definitions with freshness checks to `schema.yml`:

```yaml
sources:
  - name: raw_bike
    schema: raw_bike
    freshness:
      warn_after: {count: 10, period: day}
      error_after: {count: 15, period: day}
    loaded_at_field: started_at
    tables:
      - name: bike_trips
        columns:
          - name: ride_id
            tests:
              - unique
              - not_null

  - name: raw_weather
    schema: raw_weather
    freshness:
      warn_after: {count: 10, period: day}
      error_after: {count: 15, period: day}
    loaded_at_field: date
    tables:
      - name: daily_weather
        columns:
          - name: date
            tests:
              - unique
              - not_null

  - name: raw_holidays
    schema: raw_holidays
    freshness:
      warn_after: {count: 10, period: day}
      error_after: {count: 15, period: day}
    loaded_at_field: date
    tables:
      - name: us_holidays
        # Tests already exist in current schema.yml

  - name: raw_games
    schema: raw_games
    freshness:
      warn_after: {count: 10, period: day}
      error_after: {count: 15, period: day}
    loaded_at_field: game_date
    tables:
      - name: mlb_games
        columns:
          - name: game_id
            tests:
              - unique
              - not_null
```

**Referential integrity tests** (add to staging models):
```yaml
- name: stg_bike_trips
  columns:
    - name: start_station_id
      tests:
        - relationships:
            to: ref('dim_stations')
            field: station_id
            config:
              severity: warn
```

---

### Feature 2: Great Expectations Redesign

**Root cause:** GX config points to obsolete `bike_ingestion.duckdb` and `weather_ingestion.duckdb` files.

**Files to modify:**
- `data_quality/gx/great_expectations.yml` - Update datasource connection strings
- `data_quality/gx/checkpoints/` - Create checkpoint YAML files (currently missing)
- `data_quality/gx/expectations/` - Add `holidays_suite.json`, `games_suite.json`

**Implementation:**

**1. Update `great_expectations.yml` datasources:**

```yaml
fluent_datasources:
  bike_datasource:
    type: sql
    assets:
      bike_trips:
        type: query
        query: SELECT * FROM raw_bike.bike_trips
    connection_string: duckdb:///./duckdb/warehouse.duckdb

  weather_datasource:
    type: sql
    assets:
      daily_weather:
        type: query
        query: SELECT * FROM raw_weather.daily_weather
    connection_string: duckdb:///./duckdb/warehouse.duckdb

  holidays_datasource:
    type: sql
    assets:
      us_holidays:
        type: query
        query: SELECT * FROM raw_holidays.us_holidays
    connection_string: duckdb:///./duckdb/warehouse.duckdb

  games_datasource:
    type: sql
    assets:
      mlb_games:
        type: query
        query: SELECT * FROM raw_games.mlb_games
    connection_string: duckdb:///./duckdb/warehouse.duckdb
```

**2. Create checkpoint files** in `data_quality/gx/checkpoints/`:

- `bike_trips_checkpoint.yml`
- `weather_checkpoint.yml`
- `holidays_checkpoint.yml`
- `games_checkpoint.yml`

**3. Create new expectation suites:**

`holidays_suite.json`:
- `expect_column_values_to_not_be_null` on `date`, `holiday_name`
- `expect_column_values_to_be_unique` on `date`
- `expect_table_row_count_to_be_between` (min: 1)

`games_suite.json`:
- `expect_column_values_to_not_be_null` on `game_id`, `game_date`, `venue_name`
- `expect_column_values_to_be_unique` on `game_id`
- `expect_table_row_count_to_be_between` (min: 1)

**4. Update `validate_all.py`:**

```python
def main() -> dict:
    """Run all data validations and return results."""
    context = gx.get_context(mode='file', context_root_dir=Path(__file__).parent / 'gx')

    results = {}
    checkpoints = ['bike_trips_checkpoint', 'weather_checkpoint',
                   'holidays_checkpoint', 'games_checkpoint']

    for checkpoint_name in checkpoints:
        checkpoint = context.checkpoints.get(checkpoint_name)
        result = checkpoint.run()
        results[checkpoint_name] = {
            'success': result.success,
            'results': result.to_json_dict()
        }

    return results
```

---

### Feature 3: Data Quality DAG

**Files to create:**
- `airflow/dags/data_quality_dag.py`

**Implementation:**

```python
"""Airflow DAG for daily data quality checks.

This DAG runs independently of the ingestion DAG and:
1. Runs Great Expectations validations on all raw sources
2. Runs dbt tests
3. Stores results in data_quality schema
"""

from datetime import datetime, timedelta
from pathlib import Path
import json
import uuid

import pendulum
from airflow import DAG
from airflow.decorators import task
from airflow.operators.bash import BashOperator

project_root = Path(__file__).parent.parent.parent
DUCKDB_PATH = str(project_root / "duckdb" / "warehouse.duckdb")

default_args = {
    "owner": "data-team",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="data_quality_dag",
    default_args=default_args,
    description="Daily data quality validation",
    schedule_interval="0 6 * * *",  # Daily at 6 AM UTC
    start_date=pendulum.datetime(2024, 1, 1, tz="UTC"),
    catchup=False,
    tags=["data-quality"],
) as dag:

    @task
    def run_gx_validations() -> dict:
        """Run Great Expectations validations."""
        from data_quality.validate_all import main as validate_all
        return validate_all()

    @task
    def run_dbt_tests() -> dict:
        """Run dbt tests and capture results."""
        import subprocess
        result = subprocess.run(
            ["uv", "run", "dbt", "test", "--profiles-dir", ".", "-o", "json"],
            cwd=project_root / "dbt",
            capture_output=True,
            text=True
        )
        return {"returncode": result.returncode, "output": result.stdout}

    @task
    def store_results(gx_results: dict, dbt_results: dict) -> None:
        """Store validation results in DuckDB."""
        import duckdb

        conn = duckdb.connect(DUCKDB_PATH)

        # Create schema and table if not exists
        conn.execute("CREATE SCHEMA IF NOT EXISTS data_quality")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS data_quality.test_results (
                run_id VARCHAR,
                run_timestamp TIMESTAMP,
                test_type VARCHAR,
                test_name VARCHAR,
                status VARCHAR,
                failure_message VARCHAR,
                source_name VARCHAR
            )
        """)

        run_id = str(uuid.uuid4())
        run_timestamp = datetime.utcnow()

        # Store GX results
        for checkpoint_name, result in gx_results.items():
            conn.execute("""
                INSERT INTO data_quality.test_results VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [run_id, run_timestamp, 'gx', checkpoint_name,
                  'pass' if result['success'] else 'fail',
                  None if result['success'] else 'Validation failed',
                  checkpoint_name.replace('_checkpoint', '')])

        # Store dbt results (parse from output)
        status = 'pass' if dbt_results['returncode'] == 0 else 'fail'
        conn.execute("""
            INSERT INTO data_quality.test_results VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [run_id, run_timestamp, 'dbt', 'dbt_test_suite', status,
              None if status == 'pass' else 'dbt tests failed', 'all'])

        conn.close()

    # Task dependencies
    gx_results = run_gx_validations()
    dbt_results = run_dbt_tests()
    store_results(gx_results, dbt_results)
```

---

### Feature 4: Data Quality Dashboard

**Files to create:**
- `streamlit_app/pages/Data_Quality.py`

**Implementation** (following existing Streamlit patterns):

```python
"""Streamlit dashboard for data quality monitoring."""

import pandas as pd
import streamlit as st
import duckdb
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Data Quality Monitor",
    page_icon="✅",
    layout="wide",
)

FRESHNESS_THRESHOLD_DAYS = 10

@st.cache_resource
def get_db_connection():
    """Create and cache DuckDB connection."""
    return duckdb.connect("duckdb/warehouse.duckdb", read_only=True)

@st.cache_data(ttl=300)
def load_latest_results():
    """Load latest test results."""
    conn = get_db_connection()
    query = """
        WITH latest_run AS (
            SELECT MAX(run_timestamp) as max_ts
            FROM data_quality.test_results
        )
        SELECT * FROM data_quality.test_results
        WHERE run_timestamp = (SELECT max_ts FROM latest_run)
    """
    return conn.execute(query).df()

@st.cache_data(ttl=300)
def load_freshness_data():
    """Load freshness data for all sources."""
    conn = get_db_connection()
    freshness = []

    sources = [
        ('bike_trips', 'raw_bike.bike_trips', 'started_at'),
        ('weather', 'raw_weather.daily_weather', 'date'),
        ('holidays', 'raw_holidays.us_holidays', 'date'),
        ('games', 'raw_games.mlb_games', 'game_date'),
    ]

    for name, table, date_col in sources:
        result = conn.execute(f"SELECT MAX({date_col}) FROM {table}").fetchone()
        last_date = result[0] if result else None
        freshness.append({'source': name, 'last_date': last_date})

    return pd.DataFrame(freshness)

# Dashboard layout
st.title("✅ Data Quality Monitor")

# Load data
results_df = load_latest_results()
freshness_df = load_freshness_data()

if results_df.empty:
    st.warning("No test results found. Run the data quality DAG first.")
else:
    last_run = results_df['run_timestamp'].iloc[0]
    st.caption(f"Last run: {last_run}")

    # KPI Cards
    col1, col2, col3 = st.columns(3)
    total = len(results_df)
    passed = len(results_df[results_df['status'] == 'pass'])
    failed = total - passed

    col1.metric("Total Tests", total)
    col2.metric("Passed", f"{passed} ({100*passed//total}%)")
    col3.metric("Failed", failed)

    # Freshness Table
    st.subheader("Data Freshness")
    today = datetime.now().date()

    for _, row in freshness_df.iterrows():
        last_date = row['last_date']
        if last_date:
            days_old = (today - last_date.date()).days if hasattr(last_date, 'date') else (today - last_date).days
            is_stale = days_old > FRESHNESS_THRESHOLD_DAYS
            status = "🔴 STALE" if is_stale else "🟢 OK"
            st.write(f"**{row['source']}**: {last_date} ({days_old} days ago) - {status}")
        else:
            st.write(f"**{row['source']}**: No data - 🔴 STALE")

    # Failed Tests
    st.subheader("Failed Tests")
    failed_df = results_df[results_df['status'] == 'fail']
    if failed_df.empty:
        st.success("All tests passed!")
    else:
        for _, row in failed_df.iterrows():
            with st.expander(f"❌ {row['test_name']} ({row['test_type']})"):
                st.write(f"**Source:** {row['source_name']}")
                st.write(f"**Message:** {row['failure_message']}")
```

---

## 3. Impact and Risk Analysis

### System Dependencies
- **DuckDB warehouse** - All components read/write to `warehouse.duckdb`
- **dbt models** - Source freshness depends on raw tables existing
- **Airflow scheduler** - DAG requires Airflow to be running

### Potential Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| GX validation fails on first run | Add try/except handling, log errors gracefully |
| DuckDB locked during concurrent access | Use read_only=True for dashboard, separate connections for writes |
| dbt test output parsing fails | Store raw output, parse best-effort |
| Missing data_quality schema | CREATE IF NOT EXISTS in DAG |

---

## 4. Testing Strategy

1. **Manual Testing:**
   - Run `uv run python data_quality/validate_all.py` from repo root
   - Run `uv run dbt test --profiles-dir . --project-dir .` from dbt/
   - Run `uv run dbt source freshness --profiles-dir . --project-dir .` from dbt/

2. **Integration Testing:**
   - Trigger DAG manually: `uv run airflow dags trigger data_quality_dag`
   - Verify results in DuckDB: `SELECT * FROM data_quality.test_results`
   - Launch dashboard: `uv run streamlit run streamlit_app/Home.py`

3. **Validation Criteria:**
   - All GX checkpoints run without errors
   - All dbt tests pass (169 existing + new source tests)
   - Dashboard displays latest results correctly
   - Freshness shows correct OK/STALE status
