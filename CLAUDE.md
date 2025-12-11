# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a data product for NYC Citi Bike demand analytics. The project ingests bike trip and weather data, validates quality, transforms into analytics-ready models, and visualizes insights through interactive dashboards.

## Tech Stack

- **Data Ingestion**: dlt (Data Load Tool) - idempotent, incremental loading from APIs/files
- **Data Warehouse**: DuckDB - embedded analytics database (no infrastructure needed)
- **Data Validation**: Great Expectations - automated data quality checks at ingestion and transformation stages
- **Data Transformation**: dbt (Data Build Tool) - SQL-based transformations with testing
- **Orchestration**: Apache Airflow - workflow scheduling and dependency management
- **Analytics**: Polars (dataframes), Jupyter (exploration)
- **Visualization**: Streamlit + Plotly - interactive dashboards
- **Package Management**: uv - fast Python dependency resolution
- **Code Quality**: ruff - linting and formatting

## Essential Commands

### Environment Setup
```bash
# Install dependencies (uv automatically creates venv)
uv sync

# Activate virtual environment (if needed manually)
source .venv/bin/activate
```

### Development Commands
```bash
# Run linting
uv run ruff check .

# Auto-fix linting issues
uv run ruff check . --fix

# Format code
uv run ruff format .

# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_bike_pipeline.py -v

# Run tests with coverage
uv run pytest tests/ --cov=dlt_pipeline --cov-report=html
```

### Data Pipeline Commands

**Data Ingestion (dlt)**:
```bash
# Ingest bike trip data (downloads May-June 2024 CSVs from S3)
uv run python dlt_pipeline/bike.py

# Ingest weather data (fetches from Open-Meteo API)
uv run python dlt_pipeline/weather.py

# Ingest holiday data (fetches US holidays from Nager.Date API)
# Default: ingests 2024 holidays
uv run python dlt_pipeline/holidays.py

# To ingest holidays for specific years, edit holidays.py main block:
# result = run_holiday_pipeline([2024, 2025, 2026])
```

**Data Quality Validation (Great Expectations)**:
```bash
# Validate all 4 data sources (bike_trips, weather, holidays, games)
uv run python data_quality/validate_all.py

# View validation reports in browser
open data_quality/gx/uncommitted/data_docs/local_site/index.html
```

**dbt Source Freshness**:
```bash
cd dbt

# Check data freshness for all sources (10-day warn, 15-day error thresholds)
uv run dbt source freshness --profiles-dir . --project-dir .

cd ..
```

**Data Transformation (dbt)**:
```bash
cd dbt

# Install dbt packages (dbt_utils, etc.)
uv run dbt deps

# Run all models and tests
uv run dbt build

# Run specific model
uv run dbt run --select stg_bike_trips

# Test data quality
uv run dbt test

# Generate and serve documentation
uv run dbt docs generate
uv run dbt docs serve  # Opens lineage graph at localhost:8080

cd ..
```

**Orchestration (Airflow)**:
```bash
# Set Airflow home directory
export AIRFLOW_HOME=./airflow

# Start Airflow standalone version
uv run airflow standalone

# Trigger DAG manually
uv run airflow dags trigger bike_weather_pipeline

# Trigger data quality DAG (runs GX validations + dbt tests)
uv run airflow dags trigger data_quality_dag

# Check DAG status
uv run airflow dags list
```

**Airflow DAGs:**
- **bike_weather_dag.py** - Main data ingestion pipeline (weekly schedule)
  - Runs 4 dlt pipelines in parallel (bike, weather, holidays, games)
  - Then runs dbt build and docs generation
- **data_quality_dag.py** - Data quality validation (daily at 6 AM UTC)
  - Runs Great Expectations validations (all 4 sources)
  - Runs dbt tests (138 tests)
  - Stores results in `data_quality.test_results` table
  - All tasks run as subprocesses to avoid Airflow scheduler memory issues

**Dashboard (Streamlit)**:
```bash
# Launch interactive dashboard
uv run streamlit run streamlit_app/Home.py
# Opens at http://localhost:8501
```

**Dashboard Pages:**
- **Home.py** - Overview and navigation
- **pages/Weather.py** - Weather impact analysis with correlation metrics, time series charts, and what-if temperature analysis
- **pages/Holiday_Impact.py** - Historical holiday analysis with 6 sections:
  1. Holiday Selector & KPI Cards (trips %, duration %, statistical significance)
  2. Demand Comparison Chart (baseline vs holiday for total/member/casual trips, duration)
  3. Neighborhood-Level Demand Map (K-Means clustering with 10-50 adjustable clusters, color-coded by % change)
  4. Hourly Demand Pattern (24-hour comparison showing peak hour shifts)
  5. Top Stations Ranking (top 10 increased/decreased demand with rebalancing recommendations)
  6. Holiday Comparison Table (sortable table comparing all 4 holidays side-by-side)
- **pages/Data_Quality.py** - Data quality monitoring dashboard with:
  - KPI cards (total tests, passed, failed, pass rate)
  - Data freshness status (OK/WARN/STALE with color coding)
  - Failed test details with expandable sections

**Jupyter Notebooks**:
```bash
# Start Jupyter for exploratory analysis
uv run jupyter notebook

# Or use JupyterLab
uv run jupyter lab
```

## Architecture & Data Flow

### Pipeline Stages

```
Data Sources → Ingestion → Validation → Transformation → Analytics
    ↓             ↓            ↓             ↓             ↓
NYC Citi Bike   dlt       Great Exp.      dbt        Streamlit
Open-Meteo API            Checkpoints    Models      Dashboards
```

**Detailed Flow**:
1. **Ingestion**: dlt pipelines fetch raw data → `bike_ingestion.duckdb`, `weather_ingestion.duckdb`
2. **Validation**: Great Expectations runs quality checks (null checks, value ranges, referential integrity)
3. **Transformation**: dbt reads raw DuckDB tables → stages → core models → marts → `warehouse.duckdb`
4. **Consumption**: Streamlit/Jupyter query `warehouse.duckdb` marts for analytics

### Key Database Locations
- `duckdb/warehouse.duckdb` - Transformed analytics tables (dbt output)

### dbt Model Layers

**Staging** (`models/staging/`):
- `stg_bike_trips.sql` - Clean raw bike trips (parse timestamps, standardize types)
- `stg_weather.sql` - Clean raw weather data (temperature conversions, date parsing)
- **Purpose**: Type casting, basic cleaning, no business logic

**Core** (`models/core/`):
- `dim_stations.sql` - Station dimension (deduplicated station info with lat/lon coordinates and area classification: Manhattan Financial, Manhattan Midtown, Brooklyn, etc.)
- `fct_trips_daily.sql` - Daily trip aggregations by station
- **Purpose**: Conformed dimensions and fact tables

**Marts** (`models/marts/`):
- `mart_demand_daily.sql` - Daily demand metrics (trips, duration, user types)
- `mart_weather_effect.sql` - Weather-enriched demand analysis
- `mart_holiday_impact_summary.sql` - Citywide holiday impact metrics (4 rows - one per holiday)
- `mart_holiday_impact_by_station.sql` - Station-level holiday impact (8,370 rows - 4 holidays × ~2,093 stations)
- `mart_holiday_impact_by_hour.sql` - Hourly holiday demand patterns (96 rows - 4 holidays × 24 hours)
- `mart_holiday_impact_by_area.sql` - Geographic area holiday impact (36 rows - 4 holidays × 9 areas)
- **Purpose**: Business-ready analytics tables for dashboards

### DuckDB Query Patterns

When working with DuckDB tables directly:
```python
import duckdb

# Read from warehouse
conn = duckdb.connect('duckdb/warehouse.duckdb', read_only=True)
df = conn.execute("SELECT * FROM main_marts.mart_demand_daily LIMIT 10").fetchdf()

# Example: View Memorial Day impact
memorial_day = conn.execute("""
    SELECT * FROM main_marts.mart_holiday_impact_summary
    WHERE holiday_name = 'Memorial Day'
""").fetchdf()

conn.close()
```

## Development Patterns

### Adding a New Data Source

Follow this sequence (see `.claude/agents/domain-experts/dlt-data-ingestion.md` for detailed guidance):

1. **Create dlt pipeline** in `dlt_pipeline/`:
   - Implement source function with `@dlt.source` decorator
   - Define resources with `@dlt.resource` for each table
   - Use `merge` write disposition for idempotency
   - Add primary keys for deduplication
   - Handle authentication via `.dlt/secrets.toml`

2. **Create Great Expectations suite** in `data_quality/`:
   - Define expectation suite in `gx/expectations/`
   - Create checkpoint in `gx/checkpoints/`
   - Write validation script (e.g., `validate_<source>_data.py`)
   - Key expectations: nullability, uniqueness, value ranges, referential integrity

3. **Create dbt models**:
   - Add staging model in `dbt/models/staging/stg_<source>.sql`
   - Optionally add core/mart models if creating new analytics
   - Join to existing marts to enrich analysis (e.g., `mart_weather_effect.sql`)
   - Add schema tests in `models/staging/schema.yml`

4. **Update Airflow DAG** in `airflow/dags/bike_weather_dag.py`:
   - Add ingestion task (PythonOperator or BashOperator)
   - Add validation task
   - Wire dependencies: `ingest → validate → dbt_build`

5. **Add dashboard visualizations** in `streamlit_app/pages/`:
   - Create new page: `pages/<Source>_Analysis.py`
   - Query mart tables from `warehouse.duckdb`
   - Use Plotly for interactive charts

### Testing Strategy

**Unit Tests** (`tests/`):
- Mock external API calls using `pytest-mock`
- Test data parsing and transformation logic
- Test error handling for network failures
- Example: `tests/test_bike_pipeline.py` mocks HTTP responses

**Data Quality Tests**:
- Great Expectations validates ingested data (input quality)
- dbt tests validate transformed data (output quality)
- Run after each pipeline stage to fail fast

**Integration Tests**:
- Run full pipeline end-to-end in test environment
- Validate row counts, schema consistency
- Check dashboard can load data without errors

### Error Handling

**dlt Pipelines**:
- Use try-except for HTTP requests with retry logic
- Log detailed errors with context (URL, params, response)
- Return empty iterators for optional sources (don't fail pipeline)
- Check `pipeline.run()` result for load errors

**Great Expectations**:
- Validation failures stop pipeline (fail fast)
- Review detailed reports in Data Docs for debugging
- Add expectations incrementally (start permissive, tighten over time)

**dbt**:
- Schema tests fail on data quality issues (nulls, uniqueness violations)
- Use `dbt test --select <model>` to test incrementally
- Set severity: `warn` vs `error` based on criticality

### Performance Optimization

**dlt**:
- Use `merge` write disposition with primary keys (avoids full table scans)
- Batch API requests (e.g., fetch multiple months in parallel)
- Cache downloaded files locally (see `bike.py` download logic)

**dbt**:
- Materialize staging as `view` (no storage cost)
- Materialize core/marts as `table` (query performance)
- Use `--threads N` for parallel model execution
- Add indexes on commonly filtered columns in DuckDB

**DuckDB**:
- DuckDB is optimized for analytics (columnar storage)
- Automatically parallelizes queries across cores
- Use `EXPLAIN` to analyze query plans
- Consider Parquet export for very large datasets

## Project-Specific Conventions

### File Organization
- `dlt_pipeline/` - All data ingestion code (one file per source)
- `data_quality/` - Great Expectations config and validation scripts
- `dbt/models/` - All dbt transformations (staging → core → marts)
- `airflow/dags/` - Orchestration workflows
- `streamlit_app/` - Dashboard code (Home.py + pages/)
- `tests/` - Unit and integration tests

### Naming Conventions
- **dlt tables**: `<source_name>_raw` (e.g., `bike_trips`, `weather_data`)
- **dbt staging**: `stg_<source>` (e.g., `stg_bike_trips`)
- **dbt core**: `dim_<entity>` (dimensions), `fct_<event>` (facts)
- **dbt marts**: `mart_<business_concept>` (e.g., `mart_demand_daily`)
- **Python modules**: snake_case
- **dbt models**: snake_case.sql

### Configuration Files
- `pyproject.toml` - Python dependencies, project metadata, ruff config
- `uv.lock` - Locked dependency versions (committed to git)
- `dbt/dbt_project.yml` - dbt configuration (materialization, schemas)
- `dbt/profiles.yml` - Database connections (DuckDB paths)
- `dlt_pipeline/.dlt/config.toml` - dlt non-sensitive config
- `dlt_pipeline/.dlt/secrets.toml` - dlt credentials (git-ignored)
- `ruff.toml` - Additional linting rules

### Code Style
- **Docstrings**: All public functions have Google-style docstrings
- **Type hints**: Use typing annotations (Python 3.11+)
- **Line length**: 100 characters (ruff enforced)
- **Imports**: Absolute imports, sorted by ruff (isort rules)
- **SQL**: Lowercase keywords, 2-space indentation in dbt models

## Troubleshooting

### Common Issues

**"No module named 'dlt'" or similar**:
- Always prefix commands with `uv run` to use the project virtualenv
- Example: `uv run python dlt_pipeline/bike.py` (not `python dlt_pipeline/bike.py`)

**DuckDB database locked**:
- Only one process can write to DuckDB at a time
- Close all connections before running pipeline
- Check for open Jupyter kernels or Streamlit sessions

**dbt cannot find profiles.yml**:
- Run dbt commands from `dbt/` directory: `cd dbt && uv run dbt build`
- Or specify profiles dir: `uv run dbt build --profiles-dir dbt`

**Streamlit shows "No data available"**:
- Ensure pipeline has been run: `uv run python dlt_pipeline/bike.py && cd dbt && uv run dbt build`
- Check that `duckdb/warehouse.duckdb` exists and contains mart tables

**Airflow DAG not appearing in UI**:
- Check for syntax errors: `uv run python airflow/dags/bike_weather_dag.py`
- Refresh Airflow UI (can take 30-60 seconds to detect new DAGs)
- Restart scheduler if needed

**Great Expectations validation fails**:
- Review detailed report in `data_quality/gx/uncommitted/data_docs/`
- Check which specific expectation failed
- Adjust expectations if source data schema changed
- Fix upstream data quality issues in dlt pipeline if needed

### Data Issues

**Duplicate records**:
- Ensure dlt uses `merge` write disposition with correct primary key
- Check dbt models use `DISTINCT` or `GROUP BY` where appropriate

**Missing weather data for some dates**:
- Weather API may have gaps - add null handling in dbt
- Use `LEFT JOIN` instead of `INNER JOIN` to preserve bike trips

**Schema evolution errors**:
- dlt auto-evolves schema by default (adds new columns)
- Check dlt schema contracts if you need strict validation
- Update dbt models to handle new columns

## Domain Expert Agents

This repository includes specialized Claude Code agents for different data platform tasks. These are automatically available when using Claude Code:

- **dlt-data-ingestion**: Design and implement data ingestion pipelines
- **eda-duckdb-analyst**: Perform exploratory data analysis on DuckDB tables
- **dbt-data-modeler**: Create and refactor dbt data transformation models
- **data-quality-engineer**: Build Great Expectations validation suites
- **streamlit-data-visualizer**: Create interactive Streamlit dashboards
- **data-orchestration-pipeline**: Set up Airflow DAGs and scheduling

See `.claude/agents/domain-experts/` for detailed agent prompts and capabilities.

## Product Context

**Current State**: Full-featured NYC bike demand analytics platform with weather, holidays, game day analysis, demand forecasting, and data quality monitoring.

**Completed Phases** (see `context/product/roadmap.md`):
- **Phase 1**: Data Foundation & Analytics (holidays, games, pipeline orchestration)
- **Phase 2**: Predictive Intelligence (station clustering, demand forecasting, what-if scenarios)
- **Phase 3**: Visualization & User Experience (holiday, game, and forecast dashboards)
- **Phase 4**: Pipeline Orchestration & Continuous Data (Airflow DAGs, incremental loading)
- **Phase 5**: Data Quality & Testing (GX + dbt testing, source freshness, quality dashboard)

**Future Roadmap**:
- **Phase 6**: Model Performance & Analytics (forecast accuracy tracking)
- **Phase 7**: Regional Expansion (Jersey City Bike Share integration)

**Key Users**:
- Bike-share operations managers (primary) - daily rebalancing decisions
- Urban transportation planners - infrastructure planning
- Business analysts - revenue and utilization optimization

**Success Metrics**:
- 40% reduction in empty/full station incidents
- 30% reduction in rebalancing operational costs
- >85% forecast accuracy for demand predictions

For detailed product requirements and user stories, see `context/product/product-definition.md`.
