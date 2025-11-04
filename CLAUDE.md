# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a weather-aware bike demand platform demonstrating modern data stack with incremental data source value. The project showcases how adding new data sources (weather) incrementally enhances insights from existing sources (bike trips).

**Tech Stack**: dlt (ingestion), Great Expectations (validation), dbt (transformation), DuckDB (warehouse), Airflow (orchestration), Streamlit (visualization), Polars (analysis)

## Essential Commands

### Development Setup
```bash
# Install all dependencies (uv creates virtual environment automatically)
uv sync

# Code quality checks
uv run ruff check .
uv run ruff format .
uv run ruff check . --fix

# Run tests
uv run pytest tests/ -v
uv run pytest tests/test_bike_pipeline.py -v
uv run pytest tests/ --cov=dlt_pipeline --cov-report=html
```

### Data Pipeline Execution

**Manual execution (recommended for first run):**
```bash
# 1. Ingest bike data
uv run python dlt_pipeline/bike.py

# 2. Validate bike data
uv run python data_quality/validate_bike_data.py

# 3. Run dbt transformations
cd dbt
uv run dbt deps    # Install dbt packages (first time)
uv run dbt build   # Run models and tests
uv run dbt test    # Run only tests
uv run dbt run     # Run only models
cd ..

# 4. View dashboard
uv run streamlit run streamlit_app/Home.py

# 5. Add weather data (Part 2)
uv run python dlt_pipeline/weather.py
uv run python data_quality/validate_weather_data.py
cd dbt && uv run dbt build && cd ..

# Validate all data sources at once
uv run python data_quality/validate_all.py
```

**Airflow orchestration:**
```bash
# Initialize (first time only)
export AIRFLOW_HOME=./airflow

# Start services (use separate terminals)
uv run airflow standalone

# Trigger DAG
uv run airflow dags trigger bike_weather_pipeline
```

### dbt-Specific Commands
```bash
cd dbt

# Documentation
uv run dbt docs generate
uv run dbt docs serve

# Run specific model
uv run dbt run --select stg_bike_trips
uv run dbt run --select marts.mart_weather_effect

# Run model and downstream dependencies
uv run dbt run --select stg_bike_trips+

# Test specific model
uv run dbt test --select stg_bike_trips
```

### Data Quality Validation
```bash
# View validation results in browser
open data_quality/gx/uncommitted/data_docs/local_site/index.html
```

### Jupyter Analysis
```bash
uv run jupyter notebook  # or: uv run jupyter lab
# Open notebooks/polars_eda.ipynb
```

## Architecture Overview

### Data Flow
1. **Ingestion**: dlt pipelines extract data from APIs → Load into DuckDB raw schemas
   - `bike_ingestion.duckdb`: Raw bike trips (dlt manages)
   - `weather_ingestion.duckdb`: Raw weather data (dlt manages)

2. **Validation**: Great Expectations validates raw data quality
   - Expectation suites in `data_quality/gx/expectations/`
   - Results in `data_quality/gx/uncommitted/data_docs/`

3. **Transformation**: dbt reads from attached DuckDB files, transforms data
   - **Staging layer** (`dbt/models/staging/`): Cleans and normalizes raw data
   - **Core layer** (`dbt/models/core/`): Business logic (dimensions, facts)
   - **Marts layer** (`dbt/models/marts/`): Analytics-ready aggregations

4. **Storage**: Transformed data lands in `warehouse.duckdb`

5. **Consumption**: Streamlit dashboards query warehouse.duckdb

### Key Architectural Patterns

**DuckDB Multi-Database Pattern**:
- dbt uses `attach` in `profiles.yml` to read from multiple DuckDB files
- Raw data stays in dlt-managed databases (read-only)
- Transformed data goes to warehouse.duckdb
- Sources reference attached databases: `bike_ingestion.raw_bike.bike_trips`

**dlt Pipeline Pattern**:
- Resources use `@dlt.resource` decorator
- `write_disposition="merge"` for idempotent loads
- Primary keys prevent duplicates
- Pipelines create separate DuckDB files

**dbt Transformation Pattern**:
- Sources defined in `staging/sources.yml` reference attached databases
- Three-layer structure: staging → core → marts
- Materializations: staging=views, core/marts=tables
- Schemas configured in `dbt_project.yml`

**Data Quality Gates**:
- Validate after ingestion (raw data quality)
- Validate after transformation (business logic quality)
- dbt schema tests for referential integrity
- Great Expectations for statistical validation

## Important Implementation Details

### When Modifying dlt Pipelines
- Resources must have `primary_key` for merge operations
- Date formats should be normalized in the parse functions
- Add `_dlt_load_timestamp` for load tracking
- Handle API errors gracefully (continue on failure for individual months)
- Use Polars for efficient CSV parsing (bike pipeline)
- Batch yields for memory efficiency

### When Modifying dbt Models
- Run `dbt deps` after changing `packages.yml`
- Always add schema tests in `schema.yml` files
- Use `ref()` for model dependencies, `source()` for raw tables
- Materialized tables need explicit dependencies in DAG
- Variables in `dbt_project.yml` configure date ranges

### When Adding New Data Sources
1. Create new dlt pipeline in `dlt_pipeline/` (follow bike.py/weather.py pattern)
2. Add Great Expectations suite in `data_quality/gx/expectations/`
3. Create validation script in `data_quality/`
4. Add source definition in `dbt/models/staging/sources.yml`
5. Create staging model in `dbt/models/staging/`
6. Update Airflow DAG to include new ingestion task
7. Test end-to-end before committing

### Database Connections
- **dlt**: Automatically creates `{pipeline_name}.duckdb` in `duckdb/` directory
- **dbt**: Uses `profiles.yml` to attach multiple DuckDB files
- **Streamlit**: Connects directly to `warehouse.duckdb` (read-only)
- **Jupyter**: Can connect to any DuckDB file

### Common Pitfalls
- **DuckDB lock errors**: Only one write connection allowed; ensure processes don't overlap
- **Missing dbt packages**: Run `dbt deps` in dbt directory first
- **Source not found**: Verify attached database paths in `profiles.yml` are correct
- **Empty dashboard**: Must run dlt → dbt before viewing Streamlit
- **Validation failures**: Check `data_quality/gx/uncommitted/data_docs/` for details

## Testing Strategy

- **Unit tests** (`tests/`): Mock HTTP calls, test parsing logic
- **dbt tests**: Schema tests in YAML, data tests in SQL
- **Great Expectations**: Statistical validation, business rule checks
- **Integration**: Run full pipeline end-to-end in Airflow

## Project Variables

Configured in `dbt/dbt_project.yml`:
- `bike_start_month`: "2024-05"
- `bike_end_month`: "2024-06"
- `weather_start_date`: "2024-05-01"
- `weather_end_date`: "2024-06-30"

Update these when changing date ranges (must match across dlt and dbt).

## Cross-Cutting Standards

### Logging Format

All Python modules MUST use this standardized logging configuration for consistency across the project:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)
```

**Best Practices:**
- Use module-level logger: `logger = logging.getLogger(__name__)` to identify log source
- Default to INFO level; use DEBUG for detailed troubleshooting
- Always include timestamps for debugging time-dependent issues
- For structured logging in production, consider `structlog` (already in dependencies)

**Log Levels:**
- `DEBUG`: Detailed diagnostic information (data processing steps, API payloads)
- `INFO`: General informational messages (pipeline start/end, record counts)
- `WARNING`: Unexpected but recoverable conditions (missing optional fields)
- `ERROR`: Errors that cause operation failure but allow continuation
- `CRITICAL`: Severe errors requiring immediate attention

### Error Handling Principles

**Core Principles:**
1. **Use specific exceptions**: Prefer `requests.exceptions.RequestException` over generic `Exception`
2. **Log before raising**: Always log error context before raising exceptions
3. **Graceful degradation**: For batch operations, continue processing remaining items if one fails
4. **Timeout configuration**: Set reasonable timeouts for HTTP requests (default: 300s)
5. **Context preservation**: Include relevant identifiers (month, file, record ID) in error messages

**Example Pattern from `dlt_pipeline/bike.py`:**

```python
for month_str in months:
    logger.info("Processing %s", month_str)
    try:
        # Download and process data
        zip_file = download_bike_data(month_str, base_url)
        csv_files = unzip_bike_data(zip_file)
        yield from parse_bike_data(csv_files, month_str)

    except requests.exceptions.RequestException as e:
        # Log with context and continue
        logger.error("Failed to download data for %s: %s", month_str, e)
        continue  # Continue with next month

    except Exception as e:
        # Log unexpected errors with full traceback
        logger.exception("Unexpected error processing %s: %s", month_str, e)
        continue
```

**When to Re-raise vs. Continue:**
- **Continue**: Batch operations where one failure shouldn't stop the entire pipeline (e.g., monthly data loads)
- **Re-raise**: Critical operations where failure makes subsequent steps impossible (e.g., database connection)

### Code Style

Using Ruff with target Python 3.11+:
- **Line length**: 100 characters
- **String quotes**: Double quotes
- **Import sorting**: Enabled (isort)
- **Type hints**: Encouraged but not required
- **Docstrings**: Google style
- **Per-file ignores**:
  - `airflow/dags/*.py`: E402 (imports after sys.path modifications), I001 (import sorting)
  - `notebooks/*.py`: T201 (print statements allowed), I001 (import sorting)
  - `test_*.py`: T201 (print statements allowed)

**Ruff Configuration (from `pyproject.toml`):**
```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "A", "C4", "T20", "SIM", "ARG"]
ignore = ["E501"]
```

**Run code quality checks:**
```bash
uv run ruff check .        # Check for violations
uv run ruff check . --fix  # Auto-fix violations
uv run ruff format .       # Format code
```

## Module Execution Order

### Sequential Dependency Chain

The data pipeline must execute in this order due to data dependencies:

```
1. dlt_pipeline   → Ingest raw data to DuckDB
2. dbt            → Transform raw data in warehouse
3. data_quality   → Validate transformed data
4. streamlit_app  → Visualize warehouse data (can run in parallel)
5. notebooks      → Analyze warehouse data (can run in parallel)
```

### Airflow Orchestration DAG

The Airflow DAG (`airflow/dags/bike_weather_dag.py`) enforces these dependencies:

```
┌─────────────────┐     ┌──────────────────┐
│ ingest_bike_data │────▶│   dbt_deps       │
└─────────────────┘     │  (install pkgs)  │
                        └──────────────────┘
┌───────────────────┐            │
│ingest_weather_data│────────────┤
└───────────────────┘            ▼
                        ┌──────────────────┐
                        │    dbt_build     │
                        │ (models + tests) │
                        └──────────────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │ dbt_docs_generate│
                        └──────────────────┘
```

**Key Points:**
- Bike and weather ingestion run in parallel (no dependencies)
- dbt waits for both ingestion tasks to complete
- Data quality validation can be added after dbt_build
- Streamlit/notebooks are not orchestrated (on-demand consumption)

## Module Communication Pattern

Modules communicate exclusively via **DuckDB file paths**. No direct Python imports between data modules.

| Producer Module | Output File | Consumer Module(s) | Purpose |
|----------------|-------------|---------------------|---------|
| `dlt_pipeline` | `duckdb/bike_ingestion.duckdb` | `dbt`, `data_quality` | Raw bike trip data |
| `dlt_pipeline` | `duckdb/weather_ingestion.duckdb` | `dbt`, `data_quality` | Raw weather observations |
| `dbt` | `duckdb/warehouse.duckdb` | `data_quality`, `streamlit_app`, `notebooks` | Transformed analytics tables |

### Configuration File References

**dlt Configuration:**
- Pipeline name determines output file: `dlt.pipeline(pipeline_name="bike_ingestion")` → `duckdb/bike_ingestion.duckdb`
- Location: Hardcoded in `dlt_pipeline/bike.py` and `dlt_pipeline/weather.py`

**dbt Configuration (`dbt/profiles.yml`):**
```yaml
bike_weather:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: ../duckdb/warehouse.duckdb  # Output file
      attach:
        - path: ../duckdb/bike_ingestion.duckdb      # Input file
          alias: bike_ingestion
        - path: ../duckdb/weather_ingestion.duckdb   # Input file
          alias: weather_ingestion
```

**Consumer Configuration:**
- Streamlit (`streamlit_app/Home.py`): `duckdb.connect("duckdb/warehouse.duckdb", read_only=True)`
- Notebooks: Direct DuckDB connection to any `.duckdb` file
- Great Expectations (`data_quality/gx/`): Configured in checkpoints to reference specific DuckDB files

## DuckDB Locking Constraints

**CRITICAL: DuckDB allows only ONE write connection per database file at a time.**

### Implications

- **Development**: Run modules sequentially using Makefiles or manual execution
- **Production**: Airflow DAG enforces task dependencies to prevent concurrent writes
- **Consumers**: Always use `read_only=True` for Streamlit/notebooks to prevent accidental locks

### Symptoms of Lock Violations

```
sqlite3.OperationalError: database is locked
duckdb.IOException: Could not set lock on file
```

### Resolution Strategies

1. **Check running processes**: `ps aux | grep python` and kill stale connections
2. **Verify Airflow DAG**: Ensure task dependencies use `>>` operator correctly
3. **Use read-only connections**: For Streamlit and notebooks, always specify `read_only=True`
4. **Sequential execution**: In development, run one module at a time

**Example safe consumer connection:**
```python
import duckdb

# Safe: read-only connection
conn = duckdb.connect("duckdb/warehouse.duckdb", read_only=True)

# Unsafe: write connection (default)
# conn = duckdb.connect("duckdb/warehouse.duckdb")  # Don't do this in consumers!
```

## Module-Specific CLAUDE.md Files

Each module has its own CLAUDE.md with detailed implementation patterns and examples:

- **`dlt_pipeline/CLAUDE.md`** - Data ingestion patterns (dlt resources, API handling, Polars parsing)
- **`dbt/CLAUDE.md`** - SQL transformation patterns (staging/core/marts layers, testing, documentation)
- **`data_quality/CLAUDE.md`** - Validation patterns (Great Expectations suites, checkpoints, reporting)
- **`streamlit_app/CLAUDE.md`** - Dashboard patterns (multi-page apps, caching, visualization)
- **`airflow/CLAUDE.md`** - Orchestration patterns (TaskFlow API, DAG structure, error handling)
- **`notebooks/CLAUDE.md`** - Analysis patterns (Polars operations, statistical tests, visualization)

**Subagent Workflow:**
1. Read root `CLAUDE.md` for project overview and cross-cutting standards
2. Identify target module based on task requirements
3. Read module-specific `CLAUDE.md` for detailed patterns
4. Review example implementations in the module
5. Follow documented patterns for consistency

**When to consult module CLAUDE.md:**
- Adding new data sources → `dlt_pipeline/CLAUDE.md`
- Creating new dbt models → `dbt/CLAUDE.md`
- Adding validation checks → `data_quality/CLAUDE.md`
- Building new dashboards → `streamlit_app/CLAUDE.md`
- Modifying orchestration → `airflow/CLAUDE.md`
- Performing analysis → `notebooks/CLAUDE.md`
