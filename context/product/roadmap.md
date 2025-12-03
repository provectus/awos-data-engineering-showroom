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

### Phase 4: Pipeline Orchestration & Continuous Data (Future)

_Ensure end-to-end pipeline orchestration and enable continuous data ingestion beyond the initial dataset._

- [ ] **Airflow Orchestration Integration**
  - [ ] **Data Ingestion DAG:** Verify and enhance Airflow tasks for all dlt pipelines (bike, weather, holidays, games) with proper error handling
  - [ ] **dbt Execution DAG:** Integrate dbt build and test execution into Airflow workflows with proper dependency management
  - [ ] **End-to-End Pipeline Validation:** Ensure complete pipeline runs successfully from ingestion through transformation to dashboard-ready data

- [ ] **Continuous Data Pipeline**
  - [ ] **Dynamic Date Ranges:** Remove hardcoded May-June 2024 dates from dbt models to support multi-year data
  - [ ] **Automated Data Refresh:** Update Airflow DAGs to fetch latest bike trip data on a scheduled basis (daily/weekly)
  - [ ] **Incremental Loading:** Configure dlt pipelines for incremental data ingestion (append new trips, avoid full reloads)
  - [ ] **Historical Data Expansion:** Backfill historical data beyond May-June 2024 for richer trend analysis

---

### Phase 5: Data Quality Enhancement (Future)

_Strengthen data reliability and quality monitoring for production readiness._

- [ ] **Enhanced Data Quality Checks**
  - [ ] **Expanded dbt Tests:** Add comprehensive data quality tests in dbt models (schema validation, referential integrity, null checks)
  - [ ] **Great Expectations Review & Enhancement:** Review existing bike data validation setup and adopt/fix if needed; extend test suites to cover holiday and event data validation
  - [ ] **Data Quality DAG:** Create Airflow tasks to run Great Expectations checkpoints alongside existing data pipelines
  - [ ] **Quality Monitoring Dashboard:** Track data quality metrics and test results over time in Streamlit or Airflow UI

---

### Phase 6: Model Performance & Analytics (Future)

_Track and improve forecasting model performance over time._

- [ ] **Forecast Accuracy Tracking**
  - [ ] **Prediction vs. Actual:** Monitor and display forecast accuracy metrics over time
  - [ ] **Model Performance Dashboard:** Track which factors (weather, events, holidays) drive best predictions
