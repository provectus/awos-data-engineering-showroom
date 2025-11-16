# Product Roadmap: Citi Bike Demand Analytics Platform

_This roadmap outlines our strategic direction based on customer needs and business goals. It focuses on the "what" and "why," not the technical "how."_

---

### Phase 1: Data Foundation & Analytics (V2 - Immediate Priority)

_Build the core data infrastructure for holiday and event analysis._

- [x] **Holiday Data Integration** ✅ **COMPLETED**
  - [x] **Holiday Calendar Ingestion:** Import US federal and local NYC holidays into the data warehouse
  - [x] **Historical Holiday Analysis:** Correlate past holidays with bike demand patterns to identify trends

- [ ] **Special Events Data Integration**
  - [ ] **Large Event API Connection:** Connect to public event calendars focusing on high-attendance events (concerts, sports, parades, festivals) with 5,000+ participants
  - [ ] **Event Participant Estimation:** Capture or estimate attendance numbers for each event to classify impact size
  - [ ] **Event Classification System:** Categorize events by size - Small (5,000-15,000), Medium (15,001-30,000), Large (30,001+)
  - [ ] **Station Proximity Mapping:** Identify which Citi Bike stations are within walking distance of each event venue
  - [ ] **Historical Event Impact Database:** Build database of past large events with their participant counts and measured demand impact on nearby stations

- [ ] **Pipeline Orchestration Enhancement**
  - [ ] **Airflow DAG Integration:** Integrate holiday ingestion pipeline into Airflow orchestration workflow
  - [ ] **End-to-End Automation:** Ensure all new data sources (holidays, future events) are orchestrated with proper dependencies and monitoring

---

### Phase 2: Predictive Intelligence (V2 - High Value)

_Enable forecasting and scenario modeling for operations planning._

- [ ] **Demand Forecasting Engine**
  - [ ] **Station-Level Predictions:** Forecast future bike demand by station based on weather, holidays, and events
  - [ ] **Multi-Factor Correlation:** Combine weather + day-of-week + holiday/event data for accurate predictions

- [ ] **"What-If" Scenario Modeling**
  - [ ] **Scenario Builder Tool:** Allow users to model hypothetical situations (e.g., "Yankees game + rain + Saturday")
  - [ ] **Interactive Demand Forecasts:** Display predicted demand impact based on user-defined scenarios
  - [ ] **Rebalancing Recommendations:** Suggest which stations need bikes added/removed based on scenarios

---

### Phase 3: Visualization & User Experience (V2 - Essential)

_Make insights accessible and actionable through dashboards._

- [ ] **Enhanced Analytics Dashboards**
  - [ ] **Holiday Impact Dashboard:** Visualize demand patterns during holidays with historical comparisons
  - [ ] **Event Calendar View:** Display upcoming events overlaid with predicted demand by station
  - [ ] **What-If Scenario Dashboard:** Interactive interface for testing scenarios and viewing forecasts

- [ ] **Forecast Accuracy Tracking**
  - [ ] **Prediction vs. Actual:** Monitor and display forecast accuracy metrics over time
  - [ ] **Model Performance Dashboard:** Track which factors (weather, events, holidays) drive best predictions

---

### Phase 4: Data Quality & Orchestration Enhancement (Future)

_Strengthen data reliability and pipeline automation for production readiness._

- [ ] **Enhanced Data Quality Checks**
  - [ ] **Expanded dbt Tests:** Add comprehensive data quality tests in dbt models (schema validation, referential integrity, null checks)
  - [ ] **Great Expectations Review & Enhancement:** Review existing bike data validation setup and adopt/fix if needed; extend test suites to cover holiday and event data validation

- [ ] **Airflow Orchestration Integration**
  - [ ] **Data Quality DAGs:** Create Airflow tasks to run Great Expectations checkpoints alongside existing data pipelines
  - [ ] **dbt Test Integration:** Integrate dbt test execution into Airflow workflows with proper dependency management
  - [ ] **Quality Monitoring Dashboard:** Track data quality metrics and test results over time in Airflow UI
