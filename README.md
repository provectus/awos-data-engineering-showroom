# 🚲 Weather-Aware Bike Demand Platform

A data platform demo showcasing modern data stack with incremental value from adding new data sources. This project demonstrates a complete end-to-end data pipeline analyzing NYC bike-share demand and weather impact.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup Instructions](#setup-instructions)
- [Running the Pipeline](#running-the-pipeline)
- [Demo Walkthrough](#demo-walkthrough)
- [Development](#development)
- [Testing](#testing)
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

### Key Features

✅ **Idempotent Data Ingestion** - dlt ensures reliable, incremental loads  
✅ **Data Quality Gates** - Great Expectations validates after data ingestion and transformation
✅ **Modular Transformations** - dbt provides testable, documented models  
✅ **End-to-End Orchestration** - Airflow manages the complete workflow  
✅ **Interactive Analytics** - Streamlit dashboards for self-service insights  
✅ **Modern Development** - uv for fast dependency management, ruff for code quality

## 🏗️ Architecture

```
┌─────────────────┐         ┌──────────────────┐
│  Citi Bike API  │         │  Open-Meteo API  │
│   (Bike Trips)  │         │    (Weather)     │
└────────┬────────┘         └────────┬─────────┘
         │                           │
         ▼                           ▼
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
│       │   └── stg_weather.sql
│       ├── core/                    # Business logic
│       │   ├── dim_stations.sql
│       │   └── fct_trips_daily.sql
│       └── marts/                   # Analytics-ready tables
│           ├── mart_demand_daily.sql
│           └── mart_weather_effect.sql
├── streamlit_app/
│   ├── Home.py                      # Main dashboard
│   └── pages/
│       └── Weather.py               # Weather impact page
├── notebooks/
│   └── polars_eda.ipynb             # Exploratory analysis
├── tests/
│   ├── test_bike_pipeline.py        # Bike ingestion tests
│   ├── test_weather_pipeline.py     # Weather ingestion tests
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

#### Step 8: View Full Dashboard
```bash
uv run streamlit run streamlit_app/Home.py
```
Navigate to the "Weather" page to see weather impact analysis.

### Option 2: Airflow Orchestration

#### Initialize Airflow
```bash
export AIRFLOW_HOME=./airflow
uv run airflow db init
uv run airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin
```

#### Start Airflow
```bash
# Terminal 1: Start scheduler
uv run airflow scheduler

# Terminal 2: Start webserver
uv run airflow webserver --port 8080
```

#### Trigger the DAG
```bash
uv run airflow dags trigger bike_weather_pipeline
```

Or use the Airflow UI at http://localhost:8080 (login: admin/admin)

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
