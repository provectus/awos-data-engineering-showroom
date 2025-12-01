# System Architecture Overview: Citi Bike Demand Analytics Platform

---

## 1. Data Ingestion & Pipeline

- **Data Ingestion Framework:** dlt (Data Load Tool) - Idempotent, incremental loading with merge write disposition
- **Primary Language:** Python 3.11+
- **Holiday Data Source:** Nager.Date API - Free public holiday API for US federal and NYC holidays
- **Events Data Source:** Ticketmaster Discovery API or PredictHQ API - NYC events with attendance estimates for classification (Small: 5K-15K, Medium: 15K-30K, Large: 30K+)
- **Existing Sources:** NYC Citi Bike S3 bucket (trip CSVs), Open-Meteo API (weather data)

---

## 2. Data Storage & Warehouse

- **Primary Data Warehouse:** DuckDB - Single embedded database at `duckdb/warehouse.duckdb`
- **Schema Organization:**
  - `raw_bike` - Raw bike trip data from dlt
  - `raw_weather` - Raw weather data from dlt
  - `raw_holidays` - Raw holiday data (V2 NEW)
  - `raw_events` - Raw events data with participant counts (V2 NEW)
  - `staging` - Cleaned and normalized data
  - `core` - Dimension and fact tables
  - `marts` - Business-ready analytics tables
- **File Storage:** Local filesystem for CSV downloads and cache (`.cache/bike_data`)
- **Note:** Legacy `bike_ingestion.duckdb` and `weather_ingestion.duckdb` are obsolete and should be cleaned up

---

## 3. Data Transformation & Modeling

- **Transformation Tool:** dbt (Data Build Tool) - SQL-based transformations with testing
- **Modeling Approach:** Layered architecture (Staging → Core → Marts)
- **New Models for V2:**
  - `models/staging/stg_holidays.sql` - Clean raw holiday data
  - `models/staging/stg_events.sql` - Clean raw events data with participant counts and classifications
  - `models/core/dim_events.sql` - Event dimension with size classifications (Small/Medium/Large)
  - `models/marts/mart_holiday_impact.sql` - Holiday demand analysis with historical comparisons
  - `models/marts/mart_event_impact.sql` - Event impact on nearby stations with proximity mapping
  - `models/marts/mart_demand_forecast.sql` - Predictive scenarios combining weather + events + holidays
- **Materialization:** Views for staging, tables for core and marts

---

## 4. Data Quality & Validation

- **Primary Framework:** Great Expectations - Automated data quality checks at ingestion and transformation stages
- **Validation Coverage:**
  - Existing: Bike trip and weather data validation suites
  - V2 NEW: Holiday data validation (date formats, completeness)
  - V2 NEW: Events data validation (participant counts, venue locations, date ranges)
  - V2 NEW: Cross-dataset validation (events have valid dates, stations exist)
- **dbt Testing:**
  - Schema tests for all staging models
  - Uniqueness tests on event IDs and holiday dates
  - Referential integrity between events and stations
  - Not-null tests on critical fields (participant_count, event_date, station_id)
- **Integration:** Great Expectations checkpoints run in Airflow before dbt transformations (Phase 4 of roadmap)

---

## 5. Orchestration & Workflow Management

- **Orchestration Tool:** Apache Airflow 2.10.3 - Workflow scheduling and dependency management
- **Executor:** SequentialExecutor with SQLite backend (local development)
- **Database:** SQLite at `airflow/airflow.db`
- **DAG Structure for V2:**
  - Expand existing `bike_weather_pipeline` DAG to include:
    - Holiday data ingestion task
    - Events data ingestion task
    - Great Expectations validation for new sources
    - dbt build (includes all V2 models)
- **Schedule:** Daily execution with catchup disabled
- **Future Consideration:** LocalExecutor with PostgreSQL for parallel task execution

---

## 6. Visualization & Analytics Interface

- **Dashboard Framework:** Streamlit - Interactive web-based dashboards
- **Charting Library:** Plotly - Interactive visualizations (line charts, heatmaps, maps)
- **Analytics Tools:**
  - Polars - Fast dataframe operations for data processing
  - Jupyter - Exploratory data analysis and prototyping
- **Dashboard Pages for V2:**
  - `Home.py` - Overview and navigation
  - `pages/Demand_Analysis.py` - Historical trip patterns (existing V1)
  - `pages/Weather_Impact.py` - Weather correlation analysis (existing V1)
  - `pages/Holiday_Impact_Analysis.py` - Holiday demand patterns (V2 NEW)
  - `pages/Event_Impact_Analysis.py` - Event-driven demand with station proximity maps (V2 NEW)
  - `pages/What_If_Scenarios.py` - Interactive scenario builder for forecasting (V2 NEW)
  - `pages/Forecast_Accuracy.py` - Prediction vs. actual tracking (V2 NEW)
- **Deployment:** Local development server (`streamlit run streamlit_app/Home.py`)
- **Future:** Streamlit Cloud or Docker container for production deployment

---

## 7. Development Environment & Testing

- **Programming Language:** Python 3.11+
- **Package Manager:** uv - Fast Python dependency resolution and virtual environment management
- **Dependency File:** `pyproject.toml` with locked versions in `uv.lock`
- **Testing Framework:** pytest - Unit and integration testing
- **Mocking:** pytest-mock - Mock external API calls for testing
- **Code Quality:**
  - **Linter/Formatter:** ruff - Fast Python linting and code formatting
  - **Configuration:** Line length 100 characters, Python 3.11 target
- **Testing Strategy:**
  - Unit tests for pipeline logic (data parsing, transformation functions)
  - Integration tests for end-to-end pipeline flows
  - Data quality tests via Great Expectations and dbt tests
- **Version Control:** Git with GitHub repository

---

## 8. External APIs & Data Sources

- **Bike Trip Data:** NYC Citi Bike Open Data - AWS S3 bucket at `s3.amazonaws.com/tripdata` (CSV files by month)
- **Weather Data:** Open-Meteo Archive API - Historical weather observations (temperature, precipitation, wind) - Free, no authentication
- **Holiday Data:** Nager.Date API - US public holidays endpoint `https://date.nager.at/api/v3/PublicHolidays/{year}/US` - Free, no authentication
- **Events Data:** Ticketmaster Discovery API or PredictHQ API - NYC events with attendance estimates
  - Ticketmaster: Free tier available, requires API key
  - PredictHQ: More comprehensive, requires paid plan
  - Selection based on budget and data quality needs during implementation
- **Station Locations:** Citi Bike Station Information feed - Real-time station locations for event proximity mapping
