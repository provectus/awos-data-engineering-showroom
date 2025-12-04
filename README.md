# 🚲 Bike Demand Analytics Platform

A data platform showcasing modern data stack with incremental value from adding new data sources. This project demonstrates a complete end-to-end data pipeline analyzing NYC bike-share demand and weather impact.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup Instructions](#setup-instructions)
- [Running the Pipeline](#running-the-pipeline)
- [Demo Walkthrough](#demo-walkthrough)
- [Holiday Data Integration](#-holiday-data-integration)
- [🎉 Historical Holiday Analysis (NEW)](#-historical-holiday-analysis-new)
- [Airflow Orchestration](#-airflow-orchestration)
- [Development](#development)
- [Testing](#testing)
- [Data Sources](#-data-sources)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

This project demonstrates a complete data pipeline that:

**Part 1 - Single Source (Bike Trips)**
- Ingests NYC Citi Bike trip data from public APIs
- Validates data quality with comprehensive checks
- Transforms raw data into business-ready analytics
- Provides interactive dashboards for demand analysis

**Part 2 - Multi-Source Enhancement (+ Weather Data)**
- Adds weather data from Open-Meteo API
- Enriches bike demand with weather context
- Enables correlation and what-if analysis
- Demonstrates incremental value of new data sources

**Part 3 - Holiday Data Integration (+ Holiday Data)** ✅ Spec 001 Completed
- Integrates US public holiday data from Nager.Date API
- Adds NYC-specific local holidays (NYC Marathon, Puerto Rican Day Parade)
- Classifies holidays as major/federal vs optional/local
- Identifies working vs non-working days for demand analysis

**Part 4 - Historical Holiday Analysis (🆕 NEW)** ✅ Spec 002 Completed
- Analyzes historical bike demand around holidays vs regular weekdays
- 4 new dbt mart models (summary, by-station, by-hour, by-area)
- Interactive dashboard with 6 comprehensive analysis sections
- K-Means clustering for neighborhood-level demand visualization (10-50 adjustable clusters)
- Statistical significance testing (t-test p-values)
- Rebalancing recommendations for operations teams

### Key Features

✅ **Idempotent Data Ingestion** - dlt ensures reliable, incremental loads
✅ **Data Quality Gates** - Great Expectations validates after data ingestion and transformation
✅ **Modular Transformations** - dbt provides testable, documented models
✅ **End-to-End Orchestration** - Airflow manages the complete workflow
✅ **Interactive Analytics** - Streamlit dashboards for self-service insights
✅ **Intelligent Holiday Handling** - Automatic merging of duplicate-date holidays, dynamic NYC event generation
✅ **Modern Development** - uv for fast dependency management, ruff for code quality

## 🏗️ Architecture

```
┌─────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│  Citi Bike API  │   │  Open-Meteo API  │   │  Nager.Date API  │
│   (Bike Trips)  │   │    (Weather)     │   │    (Holidays)    │
└────────┬────────┘   └────────┬─────────┘   └────────┬─────────┘
         │                     │                       │
         └─────────────────────┼───────────────────────┘
                               ▼
                  ┌────────────────────────────────────┐
                  │        dlt Ingestion Layer         │
                  │      (HTTP → DuckDB Raw Tables)    │
                  └────────┬───────────────────────────┘
                           │
                           ▼
                  ┌────────────────────────────────────┐
                  │   Great Expectations Validation    │
                  │    (Input data quality checks)     │
                  └────────┬───────────────────────────┘
                           │
                           ▼
                  ┌────────────────────────────────────┐
                  │      dbt Transformation Layer      │
                  │       Staging → Core → Marts       │
                  │   (+ NYC holiday generation)       │
                  └────────┬───────────────────────────┘
                           │
                           ▼
                  ┌────────────────────────────────────┐
                  │        DuckDB Warehouse            │
                  │  (Optimized Analytics Tables)      │
                  └────────┬───────────────────────────┘
                           │
                           ▼
                  ┌────────────────────────────────────┐
                  │   Great Expectations Validation    │
                  │    (Transformed Quality Checks)    │
                  └────────┬───────────────────────────┘
                           │
                    ┌──────┴──────┐
                    ▼             ▼
              ┌──────────┐  ┌──────────────┐
              │ Streamlit│  │    Jupyter   │
              │Dashboard │  │   Notebooks  │
              └──────────┘  └──────────────┘

            All orchestrated by Apache Airflow
```

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Data Ingestion** | dlt (Data Load Tool) | Extract and load data from APIs |
| **Data Validation** | Great Expectations | Data quality testing and profiling |
| **Data Transformation** | dbt (Data Build Tool) | SQL-based transformations and tests |
| **Data Warehouse** | DuckDB | Embedded analytics database |
| **Orchestration** | Apache Airflow | Workflow automation and scheduling |
| **Analytics** | Polars, Jupyter | Fast data analysis and exploration |
| **Visualization** | Streamlit, Plotly | Interactive dashboards |
| **Dependency Management** | uv | Fast Python package management |
| **Code Quality** | ruff | Linting and formatting |
| **Testing** | pytest | Unit and integration tests |

## 📁 Project Structure

```
weather-bike-demo/
├── airflow/
│   ├── dags/
│   │   └── bike_weather_dag.py      # Main orchestration DAG
│   └── airflow.cfg                  # Airflow configuration
├── dlt_pipeline/
│   ├── __init__.py
│   ├── bike.py                      # Bike data ingestion
│   ├── weather.py                   # Weather data ingestion
│   ├── games.py                     # MLB game data ingestion
│   ├── holidays.py                  # Holiday data ingestion
│   └── .dlt/
│       └── config.toml              # dlt configuration
├── data_quality/
│   ├── gx/                          # Great Expectations directory
│   │   ├── great_expectations.yml   # GE configuration
│   │   ├── expectations/            # Data validation suites
│   │   ├── checkpoints/             # Validation checkpoints
│   │   └── uncommitted/             # Validation results (git-ignored)
│   ├── validate_bike_data.py        # Bike validation script
│   ├── validate_weather_data.py     # Weather validation script
│   └── validate_all.py              # Run all validations
├── dbt/
│   ├── dbt_project.yml              # dbt project config
│   ├── profiles.yml                 # Database connections
│   ├── packages.yml                 # dbt dependencies
│   └── models/
│       ├── staging/                 # Raw data cleaning
│       │   ├── stg_bike_trips.sql
│       │   ├── stg_weather.sql
│       │   └── stg_holidays.sql
│       ├── core/                    # Business logic
│       │   ├── dim_stations.sql     # 🆕 Enhanced with lat/lon + 10 geographic areas
│       │   └── fct_trips_daily.sql
│       └── marts/                   # Analytics-ready tables
│           ├── mart_demand_daily.sql
│           ├── mart_weather_effect.sql
│           ├── 🆕 mart_holiday_impact_summary.sql       # Citywide holiday impact (4 rows)
│           ├── 🆕 mart_holiday_impact_by_station.sql    # Station-level (8,370 rows)
│           ├── 🆕 mart_holiday_impact_by_hour.sql       # Hourly patterns (96 rows)
│           └── 🆕 mart_holiday_impact_by_area.sql       # Geographic areas (36 rows)
├── streamlit_app/
│   ├── Home.py                      # Main dashboard
│   └── pages/
│       ├── Weather.py               # Weather impact page
│       └── 🆕 Holiday_Impact.py     # Historical holiday analysis (6 sections)
├── notebooks/
│   └── polars_eda.ipynb             # Exploratory analysis
├── tests/
│   ├── test_bike_pipeline.py        # Bike ingestion tests
│   ├── test_weather_pipeline.py     # Weather ingestion tests
│   ├── test_holiday_pipeline.py     # Holiday ingestion tests
│   └── __init__.py
├── duckdb/
│   └── warehouse.duckdb             # DuckDB database (generated)
├── pyproject.toml                   # Python project config
├── ruff.toml                        # Code quality config
├── env.example                      # Environment variables template
└── README.md                        # This file
```

## 🚀 Setup Instructions

### Prerequisites

- Python 3.12 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- Git

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd data-platform-ai-native
```

2. **Install dependencies with uv**
```bash
# uv will automatically create a virtual environment and install all dependencies
uv sync
```

3. **Set up environment variables**
```bash
cp env.example .env
# Edit .env if you need custom configurations
```

4. **Verify installation**
```bash
uv run ruff check .
uv run pytest tests/ -v
```

## 🏃 Running the Pipeline

### Option 1: Manual Execution (Recommended for First Run)

#### Step 1: Ingest Bike Data
```bash
uv run python dlt_pipeline/bike.py
```
This downloads May-June 2024 NYC Citi Bike data and loads it into DuckDB.

#### Step 2: Validate Bike Data
```bash
uv run python data_quality/validate_bike_data.py
```

This runs comprehensive data quality checks including:
- Column nullability and uniqueness
- Value ranges and accepted values
- Data type validations
- Row count checks

Results are saved to Data Docs for detailed inspection.

#### Step 3: Run dbt Transformations (Bike Only)
```bash
cd dbt
uv run dbt deps    # Install dbt packages
uv run dbt build   # Run models and tests
cd ..
```

#### Step 4: View Part 1 Dashboard
```bash
uv run streamlit run streamlit_app/Home.py
```
Open http://localhost:8501 to see the bike demand dashboard.

#### Step 5: Ingest Weather Data
```bash
uv run python dlt_pipeline/weather.py
```

#### Step 6: Validate Weather Data
```bash
uv run python data_quality/validate_weather_data.py
```

Or validate all data sources at once:
```bash
uv run python data_quality/validate_all.py
```

#### Step 7: Re-run dbt with Weather
```bash
cd dbt
uv run dbt build
cd ..
```

#### Step 8: View Enhanced Dashboard
```bash
uv run streamlit run streamlit_app/Home.py
```
Navigate to the "Weather" page to see weather impact analysis.

#### Step 9: Ingest Holiday Data
```bash
uv run python dlt_pipeline/holidays.py
```

This ingests US public holidays from Nager.Date API and applies intelligent merging:
- Holidays on the same date are merged (e.g., "Columbus Day and Indigenous Peoples' Day")
- Counties are merged and deduplicated
- Holiday types are prioritized (Public > Federal > Optional)

#### Step 10: Re-run dbt with Holidays
```bash
cd dbt
uv run dbt build
cd ..
```

The dbt transformation automatically adds NYC-specific holidays:
- NYC Marathon (First Sunday in November)
- Puerto Rican Day Parade (Second Sunday in June)

And derives useful flags:
- `is_major`: True for Public/Federal holidays
- `is_working_day`: False for major holidays (inverse of is_major)

#### Step 11: View Full Dashboard with Holiday Insights
```bash
uv run streamlit run streamlit_app/Home.py
```
Now you can analyze bike demand patterns around holidays and compare working vs non-working days.

### Option 2: Airflow Orchestration

See the [Airflow Orchestration](#-airflow-orchestration) section below for detailed instructions on running the pipeline with Airflow, including custom date parameters.

## 🎬 Demo Walkthrough

### Act 1: Single Source Demo

**Goal**: Show value from bike trip data alone

1. **Show Data Ingestion**
   - Run bike data ingestion
   - Point out dlt's idempotent loading (run twice to show no duplicates)

2. **Demonstrate Data Quality**
   - Run Great Expectations validation: `uv run python data_quality/validate_bike_data.py`
   - Show validation reports in `data_quality/gx/uncommitted/data_docs/local_site/`
   - Highlight key expectations: nullability, uniqueness, value ranges

3. **Explore Transformations**
   - Show dbt models structure
   - Run `dbt docs generate && dbt docs serve` to show lineage
   - Highlight tests and data quality checks

4. **View Dashboard**
   - Open Streamlit Home page
   - Show daily demand trends
   - Display member vs casual breakdown
   - Highlight top stations

**Key Message**: "We have a working pipeline with one data source providing valuable insights."

### Act 2: Add Weather Source

**Goal**: Demonstrate incremental value of adding weather data

1. **Add New Data Source**
   - Run weather ingestion: `uv run python dlt_pipeline/weather.py`
   - Validate weather data: `uv run python data_quality/validate_weather_data.py`
   - Show Great Expectations catching any quality issues (e.g., tmax >= tmin)

2. **Show Enhanced Models**
   - Display new dbt models (stg_weather, mart_weather_effect)
   - Show updated lineage graph with weather joins

3. **Demonstrate New Insights**
   - Navigate to Weather page in Streamlit
   - Show correlation between weather and demand
   - Demonstrate "what-if" temperature analysis
   - Filter by rainy vs dry days

4. **Highlight Architecture Benefits**
   - Same pipeline pattern for new sources
   - Validation at every stage
   - Tests ensure quality
   - Orchestration handles dependencies

**Key Message**: "Same architecture, new source, new insights. This is how we scale data products responsibly."

### Act 3: Add Holiday Impact Analysis

**Goal**: Show how holiday context enhances demand forecasting

1. **Ingest Holiday Data**
   - Run holiday ingestion: `uv run python dlt_pipeline/holidays.py`
   - Show intelligent merging: holidays on same date merged (e.g., "Columbus Day and Indigenous Peoples' Day")
   - Display retry logic handling network failures

2. **Dynamic Holiday Generation**
   - Show dbt model automatically generating NYC-specific holidays
   - Explain date arithmetic for dynamic events (First Sunday in November, etc.)
   - Highlight deduplication logic (Public holidays prioritized over local events)

3. **Holiday Classification**
   - Demonstrate derived flags:
     - `is_major`: Public/Federal holidays = true
     - `is_working_day`: Major holidays = false (non-working day)
   - Show how this enables working day vs holiday demand comparison

4. **Enhanced Analytics**
   - Compare bike demand on holidays vs regular days
   - Identify major holidays with different demand patterns (Memorial Day, July 4th, etc.)
   - Show NYC-specific event impact (Marathon Sunday sees different station patterns)

**Key Message**: "Holiday context is critical for demand forecasting. Our pipeline automatically enriches the data with both national and local events, classified for business use."

## 📅 Holiday Data Integration

### Overview

The holiday data integration pipeline enriches bike demand analytics with US public holidays and NYC-specific local events. This enables demand pattern analysis around holidays and improves forecasting accuracy.

### Data Source: Nager.Date API

The pipeline uses the [Nager.Date API](https://date.nager.at/) to fetch official US public holidays. The API provides:
- Federal holidays (nationwide observances)
- State-specific holidays with county-level granularity
- Holiday metadata (fixed vs floating dates, holiday types)

### Intelligent Holiday Merging

Some dates have multiple holidays (e.g., Columbus Day and Indigenous Peoples' Day on October 14th). The pipeline intelligently merges these:

**Merge Strategy**:
1. **Names**: Concatenated with " and " (e.g., "Columbus Day and Indigenous Peoples' Day")
2. **Counties**: Merged, deduplicated, and sorted (e.g., "US-AK,US-CA,US-NY,US-OR")
3. **Types**: Prioritized as Public > Federal > Optional > Local
4. **Boolean flags**: OR logic (is_global = true if ANY holiday is global)

**Example**:
```python
# API returns 2 holidays for 2024-10-14:
Holiday 1: "Columbus Day" (Public, counties: US-NY, US-CA)
Holiday 2: "Indigenous Peoples' Day" (Public, counties: US-AK, US-OR)

# Pipeline merges to single record:
{
  "date": "2024-10-14",
  "holiday_name": "Columbus Day and Indigenous Peoples' Day",
  "counties": "US-AK,US-CA,US-NY,US-OR",
  "holiday_types": "Public"
}
```

### NYC-Specific Local Holidays

The dbt staging model dynamically generates NYC-specific events using SQL date arithmetic:

**NYC Marathon**:
- **When**: First Sunday in November
- **Calculation**: November 1st + days until first Sunday
- **Impact**: Affects bike demand near Central Park, finish line stations

**Puerto Rican Day Parade**:
- **When**: Second Sunday in June
- **Calculation**: June 1st + days until first Sunday + 7 days
- **Impact**: Affects bike demand along Fifth Avenue parade route

These holidays are generated dynamically for all years present in the source data (no hardcoded dates).

### Holiday Classification

The pipeline derives two boolean flags for business use:

**is_major**:
- **True**: Public or Federal holidays (e.g., July 4th, Memorial Day, Thanksgiving)
- **False**: Optional or Local holidays (e.g., Groundhog Day, NYC Marathon)
- **Purpose**: Identify holidays with widespread business closures

**is_working_day**:
- **False**: Major holidays (most businesses closed, different commute patterns)
- **True**: Other holidays (normal work schedules)
- **Purpose**: Enable working day vs non-working day demand comparison

**Classification Logic** (in dbt/models/staging/stg_holidays.sql:128-140):
```sql
-- Derive is_major flag
case
    when holiday_types like '%Public%' then true
    when holiday_types like '%Federal%' then true
    else false
end as is_major,

-- Derive is_working_day flag (inverse of is_major)
case
    when holiday_types like '%Public%' then false
    when holiday_types like '%Federal%' then false
    else true
end as is_working_day
```

### Deduplication Strategy

When the same date has both a national holiday and an NYC local event, the pipeline prioritizes national holidays:

**Prioritization** (in dbt/models/staging/stg_holidays.sql:100-115):
```sql
row_number() over (
    partition by date
    order by
        case
            when holiday_types like '%Public%' then 1
            when holiday_types like '%Federal%' then 2
            else 3  -- Local/Optional holidays ranked lowest
        end,
        holiday_name  -- Tie-breaker: alphabetical
) as row_num
```

Only the highest-priority holiday per date is kept in the final staging table.

### Retry Logic and Reliability

The dlt pipeline includes exponential backoff retry logic for API failures:

**Retry Configuration** (in dlt_pipeline/holidays.py:51-81):
- **Max Retries**: 3 attempts
- **Backoff Delays**: 1s, 2s, 4s (exponential)
- **Failure Behavior**: Pipeline fails after all retries exhausted (prevents partial data loads)

**Example**:
```
Attempt 1: ❌ Timeout
  → Wait 1 second
Attempt 2: ❌ Connection refused
  → Wait 2 seconds
Attempt 3: ✅ Success
```

### Running the Holiday Pipeline

**Basic Usage**:
```bash
# Ingest 2024 US holidays (default)
uv run python dlt_pipeline/holidays.py
```

**Multi-Year Ingestion**:
Edit `dlt_pipeline/holidays.py` line 244:
```python
# Ingest multiple years
result = run_holiday_pipeline([2024, 2025, 2026])
```

**Verification**:
```bash
# Check raw holiday data
cd dbt
uv run dbt run --select stg_holidays

# Query results
uv run duckdb duckdb/warehouse.duckdb "SELECT * FROM staging.stg_holidays ORDER BY date LIMIT 10"
```

### Testing

**Unit Tests** (tests/test_holiday_pipeline.py):
- Mock API responses for deterministic testing
- Test retry logic (success after failures, failure after max retries)
- Test merge logic (single holiday, multiple holidays, type prioritization)
- Test field transformations (arrays to comma-separated strings)
- Test metadata enrichment (timestamps, source years)

**Run Tests**:
```bash
PYTHONPATH=. uv run pytest tests/test_holiday_pipeline.py -v
```

**dbt Tests** (dbt/models/staging/schema.yml):
- Date column uniqueness (no duplicate dates)
- Not null constraints on critical fields
- Accepted values for country_code (US only)
- Boolean flag validation (is_major, is_working_day not null)

**Run dbt Tests**:
```bash
cd dbt
uv run dbt test --select stg_holidays
```

## 🔄 Airflow Orchestration

### Overview

The Airflow DAG (`bike_weather_pipeline`) orchestrates all 4 dlt pipelines in a single workflow:

1. **Bike Data Ingestion** - NYC Citi Bike trip data from S3
2. **Weather Data Ingestion** - Daily weather from Open-Meteo API
3. **Game Data Ingestion** - MLB games from MLB Stats API
4. **Holiday Data Ingestion** - US holidays from Nager.Date API

All 4 ingestion tasks run in parallel, followed by dbt transformation and documentation generation.

### Schedule

- **Frequency**: Weekly (`@weekly`)
- **Default Date Range**: Previous month (bike data typically has ~1 month delay)
- **Trigger Rule**: dbt runs regardless of ingestion task success/failure (`trigger_rule='all_done'`)

### Starting Airflow

```bash
# Set Airflow home directory
export AIRFLOW_HOME=$PWD/airflow

# Start Airflow standalone (includes webserver + scheduler)
uv run airflow standalone
```

Access the Airflow UI at http://localhost:8080 (credentials displayed in terminal).

### Triggering the DAG

**Default Parameters (Previous Month)**:
```bash
# Trigger with default date range (previous month)
uv run airflow dags trigger bike_weather_pipeline
```

**Custom Date Parameters**:
```bash
# Trigger with specific date range
uv run airflow dags trigger bike_weather_pipeline \
  --conf '{"period_start_date": "2024-05-01", "period_end_date": "2024-06-30"}'
```

You can also trigger with custom parameters via the Airflow UI:
1. Go to DAGs → `bike_weather_pipeline`
2. Click "Trigger DAG w/ config"
3. Enter JSON: `{"period_start_date": "2024-05-01", "period_end_date": "2024-06-30"}`

### DAG Parameters

| Parameter | Format | Default | Description |
|-----------|--------|---------|-------------|
| `period_start_date` | YYYY-MM-DD | First day of previous month | Start of date range for data ingestion |
| `period_end_date` | YYYY-MM-DD | Last day of previous month | End of date range for data ingestion |

Each pipeline translates these parameters to its native format:
- **Bike**: Converts to months list (e.g., `["202405", "202406"]`)
- **Weather**: Uses dates as-is (YYYY-MM-DD)
- **Games**: Uses dates as-is (YYYY-MM-DD)
- **Holidays**: Extracts unique years (e.g., `[2024]`)

### DAG Structure

```
┌──────────────────┐  ┌────────────────────┐  ┌──────────────────┐  ┌────────────────────┐
│ ingest_bike_data │  │ ingest_weather_data│  │ ingest_game_data │  │ ingest_holiday_data│
└────────┬─────────┘  └─────────┬──────────┘  └────────┬─────────┘  └─────────┬──────────┘
         │                      │                       │                      │
         └──────────────────────┼───────────────────────┼──────────────────────┘
                                │
                                ▼
                       ┌────────────────┐
                       │   dbt_deps     │  (trigger_rule='all_done')
                       └────────┬───────┘
                                │
                                ▼
                       ┌────────────────┐
                       │   dbt_build    │
                       └────────┬───────┘
                                │
                                ▼
                       ┌────────────────────┐
                       │ dbt_docs_generate  │
                       └────────────────────┘
```

### Standalone Execution

All pipelines can still be run standalone from the project root for testing or backfill:

```bash
# Run individual pipelines (from project root)
uv run python dlt_pipeline/bike.py
uv run python dlt_pipeline/weather.py
uv run python dlt_pipeline/games.py
uv run python dlt_pipeline/holidays.py
```

**Note**: Standalone mode uses the DuckDB path from `dlt_pipeline/.dlt/secrets.toml`. Always run from the project root directory.

## 💻 Development

### Running Tests
```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_bike_pipeline.py -v

# Run with coverage
uv run pytest tests/ --cov=dlt_pipeline --cov-report=html
```

### Code Quality
```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Auto-fix issues
uv run ruff check . --fix
```

### Adding New Dependencies
```bash
# Add a new package
uv add package-name

# Add a dev dependency
uv add --dev package-name

# Update dependencies
uv sync
```

### Jupyter Notebook Analysis
```bash
# Start Jupyter
uv run jupyter notebook

# Or use JupyterLab
uv run jupyter lab

# Open notebooks/polars_eda.ipynb
```

## 🧪 Testing

### Unit Tests

- **Bike Pipeline Tests**: Mock HTTP responses, test data parsing and transformations
- **Weather Pipeline Tests**: Mock API calls, verify error handling
- **Holiday Pipeline Tests**: Mock Nager.Date API, test intelligent merging, retry logic, field transformations
- **dbt Tests**: Schema tests, data quality tests defined in YAML

### Data Quality Tests

Great Expectations validates data at every stage. The data_quality directory contains:

- **Expectation Suites**: Define data quality rules
  - `bike_trips_suite`: expectations for bike trip data
  - `weather_suite`: expectations for weather data
- **Checkpoints**: Execute validation workflows
- **Validation Scripts**: Standalone scripts for manual validation

To run validations manually:
```bash
# Validate bike trips data
uv run python data_quality/validate_bike_data.py

# Validate weather data
uv run python data_quality/validate_weather_data.py

# Validate all data sources
uv run python data_quality/validate_all.py
```

View detailed validation results in Data Docs:
```bash
# Open Data Docs in browser
open data_quality/gx/uncommitted/data_docs/local_site/index.html
```

## 🔧 Troubleshooting

### Common Issues

**Issue: dlt ingestion fails with "No module named 'dlt'"**
```bash
# Solution: Ensure you're using uv run
uv run python dlt_pipeline/bike.py
```

**Issue: DuckDB database locked**
```bash
# Solution: Close all connections, then restart
# Make sure only one process accesses the database at a time
```

**Issue: dbt cannot find profiles.yml**
```bash
# Solution: Run dbt from the dbt directory or specify profiles dir
cd dbt && uv run dbt build --profiles-dir .
```

**Issue: Streamlit shows "No data available"**
```bash
# Solution: Ensure data pipeline has been run
uv run python dlt_pipeline/bike.py
cd dbt && uv run dbt build
```

**Issue: Airflow DAG not appearing**
```bash
# Solution: Check DAG file for syntax errors
uv run python airflow/dags/bike_weather_dag.py
# Refresh Airflow UI or restart scheduler
```
If that will not help try to add this to your bashrc/zshrc file 

´´´bash
export PYTHONFAULTHANDLER=true
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
´´´

### Performance Tips

- **Large Datasets**: Adjust batch sizes in dlt pipeline configurations
- **dbt Performance**: Use `--threads` flag for parallel execution
- **DuckDB Memory**: DuckDB automatically manages memory, but for very large datasets consider using external Parquet files

## 📊 Data Sources

### Citi Bike Trip Data
- **Source**: NYC Citi Bike System Data (Amazon S3)
- **Format**: Monthly CSV files (gzipped)
- **Coverage**: May-June 2024 in demo
- **Update**: Monthly
- **License**: Public data

### Weather Data
- **Source**: Open-Meteo Historical Weather API
- **Format**: JSON API
- **Coverage**: May-June 2024 for NYC (40.73°N, 73.94°W)
- **Update**: Daily historical data
- **License**: Free for non-commercial use

### Holiday Data
- **Source**: Nager.Date Public Holiday API
- **Format**: JSON API
- **Coverage**: US federal and public holidays (2024+)
- **Special Features**:
  - Intelligent date deduplication (merges holidays on same date)
  - County-level holiday tracking
  - Holiday type classification (Public, Federal, Optional, Local)
  - NYC-specific local events (Marathon, Puerto Rican Day Parade)
- **Update**: Annual (holidays are relatively static)
- **License**: Free public API

## 🤝 Contributing

This is a demo project, but contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Run tests and linting
4. Submit a pull request

## 📝 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- NYC Citi Bike for open data
- Open-Meteo for weather API
- dlt, dbt, Great Expectations, and Streamlit communities
