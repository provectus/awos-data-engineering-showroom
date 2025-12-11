# Technical Specification: Airflow Orchestration Integration

- **Functional Specification:** `context/spec/005-airflow-orchestration-integration/functional-spec.md`
- **Status:** Draft
- **Author(s):** Engineering Team

---

## 1. High-Level Technical Approach

This specification addresses orchestrating all 4 dlt pipelines (bike, weather, games, holidays) in Airflow with configurable date parameters. The key changes are:

1. **Standardize all dlt pipelines** - Add `credentials_path` parameter to all 4 pipelines for consistent DuckDB path resolution
2. **Fix games.py** - Currently fails in Airflow due to DuckDB path resolution issue
3. **Add holidays.py to DAG** - New task following existing pattern
4. **Add DAG parameters** - `start_date` and `end_date` with previous month defaults
5. **Update trigger rules** - Ensure dbt runs regardless of ingestion failures
6. **Change schedule** - Daily → Weekly
7. **Update documentation** - README with Airflow usage instructions

**Files affected:**
- `dlt_pipeline/bike.py` - Add credentials_path parameter (standardization)
- `dlt_pipeline/weather.py` - Add credentials_path parameter (standardization)
- `dlt_pipeline/games.py` - Add credentials_path parameter (fixes Airflow issue)
- `dlt_pipeline/holidays.py` - Add credentials_path parameter (standardization)
- `airflow/dags/bike_weather_dag.py` - Major updates (params, holidays task, trigger rules, schedule)
- `README.md` - Documentation updates

---

## 2. Proposed Solution & Implementation Plan (The "How")

### 2.1 Standardize All dlt Pipelines with credentials_path Parameter

**Root Cause of games.py failure:** dlt resolves the relative path `./duckdb/warehouse.duckdb` from secrets.toml relative to `DLT_PROJECT_DIR` (which is `dlt_pipeline/`), resulting in invalid path `dlt_pipeline/./duckdb/warehouse.duckdb`.

**Solution:** Add optional `credentials_path` parameter to all `run_*_pipeline()` functions. When provided, use `dlt.destinations.duckdb(credentials_path)` instead of relying on secrets.toml.

**Standard pattern for all pipelines:**

```python
def run_<name>_pipeline(
    # ... existing parameters ...
    destination: str = "duckdb",
    dataset_name: str = "raw_<name>",
    credentials_path: str | None = None,  # NEW PARAMETER
) -> dict[str, Any]:
    """Run the <name> data ingestion pipeline.

    Args:
        ...
        credentials_path: Optional absolute path to DuckDB file.
                         If None, uses path from secrets.toml (requires running from project root).
    """
    # Determine destination configuration
    if credentials_path:
        dest = dlt.destinations.duckdb(credentials_path)
    else:
        dest = destination

    pipeline = dlt.pipeline(
        pipeline_name="<name>_ingestion",
        destination=dest,
        dataset_name=dataset_name,
    )
    # ... rest of pipeline logic ...
```

**Apply to all 4 pipelines:**

| Pipeline | Function | Current Status | Change |
|----------|----------|----------------|--------|
| bike.py | `run_bike_pipeline()` | Works in Airflow | Add `credentials_path` for standardization |
| weather.py | `run_weather_pipeline()` | Works in Airflow | Add `credentials_path` for standardization |
| games.py | `run_game_pipeline()` | **Fails in Airflow** | Add `credentials_path` to fix issue |
| holidays.py | `run_holiday_pipeline()` | Not in Airflow | Add `credentials_path` for standardization |

**Standalone mode:** All pipelines continue to work when run from project root directory using `uv run python dlt_pipeline/<name>.py` (uses secrets.toml default).

### 2.2 Update Airflow DAG

**Changes to `airflow/dags/bike_weather_dag.py`:**

#### 2.2.1 Add imports and constants
```python
from calendar import monthrange
from datetime import datetime, timedelta

from dlt_pipeline.holidays import run_holiday_pipeline  # NEW IMPORT

# Calculate absolute DuckDB path
project_root = Path(__file__).parent.parent.parent
DUCKDB_PATH = str(project_root / "duckdb" / "warehouse.duckdb")
```

#### 2.2.2 Add helper functions
```python
def get_previous_month_range() -> tuple[str, str]:
    """Calculate first and last day of previous month.

    Returns:
        Tuple of (start_date, end_date) in YYYY-MM-DD format
    """
    today = datetime.now()
    first_of_current = today.replace(day=1)
    last_of_previous = first_of_current - timedelta(days=1)
    first_of_previous = last_of_previous.replace(day=1)
    return first_of_previous.strftime("%Y-%m-%d"), last_of_previous.strftime("%Y-%m-%d")


def get_months_from_date_range(start_date: str, end_date: str) -> list[str]:
    """Convert date range to list of months in YYYYMM format.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        List of month strings, e.g., ["202411", "202412"]
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    months = []
    current = start
    while current <= end:
        months.append(current.strftime("%Y%m"))
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    return list(dict.fromkeys(months))  # Remove duplicates, preserve order
```

#### 2.2.3 Add DAG params with previous month defaults
```python
default_start, default_end = get_previous_month_range()

with DAG(
    dag_id="bike_weather_pipeline",
    default_args=default_args,
    description="End-to-end bike and weather data pipeline",
    schedule_interval="@weekly",  # CHANGED from @daily
    start_date=pendulum.datetime(2024, 5, 1, tz="UTC"),
    catchup=False,
    tags=["data-ingestion", "analytics", "demo"],
    params={
        "start_date": default_start,
        "end_date": default_end,
    },
) as dag:
```

#### 2.2.4 Update all ingestion tasks to use params and credentials_path
```python
@task
def ingest_bike_data(**context) -> str:
    """Task to ingest bike trip data using dlt."""
    start_date = context["params"]["start_date"]
    end_date = context["params"]["end_date"]
    months = get_months_from_date_range(start_date, end_date)

    result = run_bike_pipeline(months, credentials_path=DUCKDB_PATH)
    return str(result)

@task
def ingest_weather_data(**context) -> str:
    """Task to ingest weather data using dlt."""
    start_date = context["params"]["start_date"]
    end_date = context["params"]["end_date"]
    lat, lon = 40.73, -73.94

    result = run_weather_pipeline(lat, lon, start_date, end_date, credentials_path=DUCKDB_PATH)
    return str(result)

@task
def ingest_game_data(**context) -> str:
    """Task to ingest MLB game data using dlt."""
    start_date = context["params"]["start_date"]
    end_date = context["params"]["end_date"]

    result = run_game_pipeline(start_date, end_date, credentials_path=DUCKDB_PATH)
    return str(result)

@task
def ingest_holiday_data(**context) -> str:
    """Task to ingest US holiday data using dlt."""
    start_date = context["params"]["start_date"]
    end_date = context["params"]["end_date"]

    # Extract unique years from date range
    start_year = int(start_date[:4])
    end_year = int(end_date[:4])
    years = list(range(start_year, end_year + 1))

    result = run_holiday_pipeline(years, credentials_path=DUCKDB_PATH)
    return str(result)
```

#### 2.2.5 Update dbt_deps with trigger_rule
```python
dbt_deps = BashOperator(
    task_id="dbt_deps",
    bash_command=f"cd {project_root}/dbt && dbt deps --profiles-dir .",
    trigger_rule="all_done",  # NEW - runs even if upstream fails
)
```

#### 2.2.6 Update pipeline dependencies
```python
# Task instantiation
ingest_bike = ingest_bike_data()
ingest_weather = ingest_weather_data()
ingest_games = ingest_game_data()
ingest_holidays = ingest_holiday_data()  # NEW

# Pipeline dependencies - all 4 ingestion tasks run in parallel
[ingest_bike, ingest_weather, ingest_games, ingest_holidays] >> dbt_deps >> dbt_build >> dbt_docs_generate
```

### 2.3 README Documentation Updates

Add/update sections documenting:

1. **Airflow Orchestration** - All 4 pipelines (bike, weather, games, holidays) orchestrated
2. **Schedule** - Weekly execution (changed from daily)
3. **Default date range** - Previous month (bike data has ~1 month delay)
4. **Custom parameters** - How to trigger with custom dates via Airflow UI or CLI:
   ```bash
   # Trigger with custom date range
   uv run airflow dags trigger bike_weather_pipeline \
     --conf '{"start_date": "2024-05-01", "end_date": "2024-06-30"}'
   ```
5. **Standalone execution** - Still works from project root for testing/backfill:
   ```bash
   uv run python dlt_pipeline/bike.py
   uv run python dlt_pipeline/weather.py
   uv run python dlt_pipeline/games.py
   uv run python dlt_pipeline/holidays.py
   ```

---

## 3. Impact and Risk Analysis

### System Dependencies
- **Airflow**: DAG structure changes, new task added
- **dlt pipelines**: Function signature changes (backward compatible with defaults)
- **DuckDB**: No changes to database or path
- **dbt**: No changes, trigger rule ensures it still runs
- **secrets.toml**: No changes needed

### Potential Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking standalone mode | Low | Medium | `credentials_path` defaults to None, preserving existing behavior |
| DAG import errors | Low | High | Test DAG syntax before deployment: `python airflow/dags/bike_weather_dag.py` |
| Date parsing errors | Medium | Low | Add validation and clear error messages in helper functions |
| Holiday API rate limiting | Low | Low | Existing retry logic with exponential backoff in holidays.py |
| Backward compatibility | Low | Low | All new parameters have defaults, existing calls work unchanged |

### Backward Compatibility

All changes are backward compatible:
- `credentials_path=None` (default) preserves existing behavior using secrets.toml
- Standalone scripts with hardcoded dates continue to work
- Existing Airflow runs would work but will use new defaults (previous month)

---

## 4. Testing Strategy

### Unit Tests
- Test `get_months_from_date_range()` helper function with various date ranges
- Test `get_previous_month_range()` returns correct defaults
- Test year extraction logic for holidays (date range spanning multiple years)

### Integration Tests
- Verify DAG loads without errors: `uv run python airflow/dags/bike_weather_dag.py`
- Test each pipeline standalone from project root:
  ```bash
  uv run python dlt_pipeline/bike.py
  uv run python dlt_pipeline/weather.py
  uv run python dlt_pipeline/games.py
  uv run python dlt_pipeline/holidays.py
  ```
- Test each pipeline with explicit `credentials_path` parameter

### End-to-End Test
1. Start Airflow: `export AIRFLOW_HOME=$PWD/airflow && uv run airflow standalone`
2. Trigger DAG manually with test date range via UI or CLI
3. Verify all 4 ingestion tasks complete (success or expected failure)
4. Verify dbt_deps runs with `trigger_rule='all_done'`
5. Verify dbt_build completes successfully
6. Check DuckDB has data in all raw schemas

### Validation Checklist
- [ ] bike.py runs in standalone mode from project root
- [ ] bike.py runs successfully in Airflow with credentials_path
- [ ] weather.py runs in standalone mode from project root
- [ ] weather.py runs successfully in Airflow with credentials_path
- [ ] games.py runs in standalone mode from project root
- [ ] games.py runs successfully in Airflow with credentials_path (previously failing)
- [ ] holidays.py runs in standalone mode from project root
- [ ] holidays.py runs successfully in Airflow with credentials_path
- [ ] DAG accepts custom start_date/end_date params
- [ ] DAG defaults to previous month when no params provided
- [ ] dbt runs even if one ingestion task fails (trigger_rule='all_done')
- [ ] Weekly schedule is active
- [ ] README documentation updated
