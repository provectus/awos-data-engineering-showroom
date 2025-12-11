# Product Roadmap: Citi Bike Demand Analytics Platform

_This roadmap outlines our strategic direction based on customer needs and business goals. It focuses on the "what" and "why," not the technical "how."_

---

### Phase 1: Data Foundation & Analytics ✅ **100% COMPLETE**

_Build the core data infrastructure for holiday and event analysis._

**Status**: All Phase 1 items completed! Foundation is ready for Phase 2 predictive intelligence.

- [x] **Holiday Data Integration** ✅ **COMPLETED**
  - [x] **Holiday Calendar Ingestion:** Import US federal and local NYC holidays into the data warehouse
  - [x] **Historical Holiday Analysis:** Correlate past holidays with bike demand patterns to identify trends

- [x] **Baseball Match Impact Analysis** ✅ **COMPLETED**
  - [x] **MLB Game Data Ingestion:** Ingest NY Yankees and NY Mets home game schedules from MLB public API (54 games, May-June 2024)
  - [x] **Stadium Proximity Analysis:** Identify Citi Bike stations near Yankee Stadium (Bronx) and Citi Field (Queens) using Haversine formula (37 stations within 1km)
  - [x] **Game Day Demand Patterns:** Analyze bike trip patterns on game days vs non-game days at stadium-adjacent stations with 30-minute granularity
  - [x] **Pre/Post Game Rush Analysis:** Identify demand spikes in 6-hour window (-3h to +3h) with baseline comparison
  - [x] **Game Impact Dashboard:** Interactive Streamlit dashboard with rebalancing calculator, demand analysis charts, and station map

- [x] **Pipeline Orchestration Enhancement** ✅ **COMPLETED**
  - [x] **Airflow DAG Integration:** Holiday and game data ingestion integrated into `bike_weather_dag.py` with proper task dependencies
  - [x] **End-to-End Automation:** All data sources (bike, weather, holidays, games) orchestrated with retry logic and sequential execution (ingest → dbt build → docs)

---

### Phase 2: Predictive Intelligence (V2 - High Value) ✅ **100% COMPLETE**

_Enable forecasting and scenario modeling for operations planning._

- [x] **Demand Forecasting Engine** ✅ **COMPLETED**
  - [x] **Station Clustering:** K-means clustering of 2,147 stations into 30 geographic areas for area-level demand predictions
  - [x] **Baseline Net Flow Calculation:** Historical average net flow (trips_ended - trips_started) by cluster, day-of-week, and hour (5,040 patterns)
  - [x] **Multi-Factor Correlation:** 17 adjustment factors combining temperature (4 levels), wind (2 levels), rain (2 levels), holidays (2 types), and day-of-week (7 days) for accurate predictions
  - [x] **Factor-Based Forecasting:** Multiplicative forecast model: `adjusted_net_flow = baseline × day_factor × temp_factor × wind_factor × rain_factor × holiday_factor`
  - [x] **24-Hour Prediction Dashboard:** Interactive Streamlit dashboard with forecast chart, rebalancing recommendations, cluster map, and station list
  - [x] **Rebalancing Recommendations:** Actionable hourly guidance (Add/Remove bikes) with 3-bike threshold logic matching game rebalancing patterns
  - [x] **What-If Scenario Capability:** Built into forecast dashboard via 6 input controls allowing users to model any combination of day, weather, and holiday conditions

---

### Phase 3: Visualization & User Experience (V2 - Essential) ✅ **100% COMPLETE**

_Make insights accessible and actionable through dashboards._

- [x] **Enhanced Analytics Dashboards** ✅ **COMPLETED**
  - [x] **Holiday Impact Dashboard:** Visualize demand patterns during holidays with historical comparisons (citywide summary, station-level heatmaps, hourly patterns, geographic distribution)
  - [x] **Game Impact Dashboard:** Interactive rebalancing calculator with demand analysis and station proximity maps for Yankees/Mets games
  - [x] **Demand Forecast Dashboard:** Interactive 24-hour forecast interface with 6 input controls (day, temperature, wind, rain, holiday, cluster), forecast chart, rebalancing recommendations table, cluster map visualization, and station list

---

### Phase 4: Pipeline Orchestration & Continuous Data ✅ **100% COMPLETE**

_Ensure end-to-end pipeline orchestration and enable continuous data ingestion beyond the initial dataset._

- [x] **Airflow Orchestration Integration** ✅ **COMPLETED**
  - [x] **Data Ingestion DAG:** All 4 dlt pipelines (bike, weather, holidays, games) orchestrated in Airflow with `credentials_path` parameter for reliable DuckDB access
  - [x] **Configurable Date Parameters:** DAG accepts `period_start_date` and `period_end_date` params (defaults to previous month)
  - [x] **dbt Execution DAG:** dbt build and docs integrated with `trigger_rule='all_done'` ensuring dbt runs regardless of ingestion failures
  - [x] **Weekly Schedule:** Changed from daily to weekly schedule for production-appropriate cadence
  - [x] **End-to-End Pipeline Validation:** Complete pipeline runs successfully from ingestion through transformation

- [x] **Continuous Data Pipeline** ✅ **COMPLETED**
  - [x] **Dynamic Date Ranges:** ✅ Removed hardcoded May-June 2024 dates from 5 dbt mart models (holiday impact + game day demand)
  - [x] **Automated Data Refresh:** ✅ DAG runs weekly with configurable `period_start_date`/`period_end_date` params
  - [x] **Incremental Loading:** ✅ All 4 dlt pipelines use `write_disposition="merge"` with primary keys
  - [x] **Historical Data Expansion:** ✅ Supported - Use existing DAG with custom date params to backfill (manual trigger)

---

### Phase 5: Data Quality & Testing ✅ **100% COMPLETE**

_Comprehensive data quality framework with automated validation, monitoring, and reporting._

- [x] **Data Quality Framework** ✅ **COMPLETED**
  - [x] **dbt Testing Enhancement:** Source freshness checks (10-day warn, 15-day error) on all 4 raw sources plus uniqueness/not_null tests on primary keys (138 total dbt tests)
  - [x] **Great Expectations Redesign:** Fixed DuckDB/SQLAlchemy compatibility issue using pandas DataFrames, extended validation to all 4 sources (bike_trips, weather, holidays, games) with 31 total expectations
  - [x] **Data Quality DAG:** Created `data_quality_dag.py` running daily at 6 AM UTC with all tasks as subprocesses (to avoid Airflow scheduler memory issues), results stored in `data_quality.test_results` table
  - [x] **Data Quality Dashboard:** Streamlit page (`pages/Data_Quality.py`) showing KPI cards (total/passed/failed/rate), freshness status (OK/WARN/STALE), and failed test details

---

### Phase 6: Model Performance & Analytics (Future)

_Track and improve forecasting model performance over time._

- [ ] **Forecast Accuracy Tracking**
  - [ ] **Prediction vs. Actual:** Monitor and display forecast accuracy metrics over time
  - [ ] **Model Performance Dashboard:** Track which factors (weather, events, holidays) drive best predictions

---

### Phase 7: Regional Expansion (Future)

_Expand coverage to the greater NYC metro area bike share network._

- [ ] **Jersey City Bike Share Integration**
  - [ ] **JC Data Ingestion:** Add Jersey City Citi Bike trip data from S3 (JC-prefixed files, same schema as NYC)
  - [ ] **Cross-River Analysis:** Analyze bike demand patterns between NYC and Jersey City/Hoboken
  - [ ] **Regional Station Mapping:** Integrate JC/Hoboken stations (HB*, JC* prefixes) into station dimension with geographic classification
  - [ ] **Unified Dashboard Views:** Enable NYC + Jersey City combined analytics and comparison views
  - [ ] **Ferry Connection Analysis:** Identify demand patterns at stations near Hudson River ferry terminals
