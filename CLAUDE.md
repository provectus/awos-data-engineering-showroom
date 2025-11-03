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

## Code Style

Using Ruff with target Python 3.11+:
- Line length: 100 characters
- Double quotes for strings
- Imports sorted (isort)
- Type hints encouraged but not required
- Docstrings in Google style
- Per-file ignores: E402 for DAGs (sys.path modifications), T201 for notebooks (print statements)