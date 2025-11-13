# Product Roadmap: NYC Citi Bike Demand Analytics Platform

## Overview

This roadmap outlines the evolution of the NYC Citi Bike Demand Analytics Platform from initial MVP through advanced predictive capabilities. Each phase builds upon previous functionality while adding incremental value for operations teams, business analysts, and urban planners.

---

## Current State: MVP (Q1 2025)

### Status: ✅ Completed

**Goal**: Deliver core demand analytics for NYC operations team

### Features Delivered
1. **Daily Demand Analytics Dashboard**
   - Trip volume trends with moving averages
   - Top 20 stations by demand
   - Member vs. casual ridership breakdown
   - Hourly demand patterns

2. **Weather Impact Analysis**
   - Temperature vs. demand correlation
   - Rainy day vs. dry day comparison
   - What-if temperature scenarios
   - Statistical correlation metrics

3. **Station Performance Rankings**
   - Station rankings by trip volume
   - Net flow analysis (sources vs. sinks)
   - Utilization metrics

4. **Automated Daily Pipeline**
   - dlt ingestion (bike trips, weather)
   - Great Expectations validation
   - dbt transformations
   - Airflow orchestration

5. **Data Quality Monitoring**
   - Automated validation suites
   - Data freshness checks
   - Referential integrity validation

### Data Sources
- NYC Citi Bike trip data (May-June 2024)
- Open-Meteo weather API (NYC)

### Success Metrics Achieved
- ✅ Dashboard used daily by operations team
- ✅ <3 second dashboard load times
- ✅ 95%+ data quality validation pass rate

---

## Phase 1: Holiday Analysis (Q1 2025 - Next)

### Status: 🎯 Planned

**Goal**: Understand impact of public holidays on bike demand patterns to improve operational planning

### Business Value
- **Staffing Optimization**: Adjust rebalancing crew size based on holiday demand patterns
- **Revenue Forecasting**: Accurate demand predictions including holiday effects
- **Service Planning**: Identify holidays with unusual demand patterns requiring special attention

### Feature: Holiday Impact Analysis

**Description**: Integrate public holiday data to analyze demand variations on holidays vs. regular days, enabling operations teams to plan staffing and fleet distribution accordingly.

**User Stories**:
1. As an **operations manager**, I need to see demand patterns on holidays vs. regular days, so that I can staff rebalancing teams appropriately
2. As a **business analyst**, I need to quantify revenue impact of holidays, so that I can forecast monthly revenue accurately
3. As a **scheduler**, I need to identify which holidays have high demand (Memorial Day) vs. low demand (Thanksgiving), so that I can plan maintenance windows

### Implementation Details

#### New Data Source: Nager.Date API
- **API**: https://date.nager.at/api/v3/PublicHolidays/2024/US
- **Coverage**: US federal and state holidays
- **Data Points**:
  - Date
  - Holiday name
  - Holiday type (federal, state, observance)
  - Counties affected (if applicable)
- **Update Frequency**: Annual (holidays published yearly)

#### Technical Components

**1. Data Ingestion (dlt pipeline)**
```
New file: dlt_pipeline/holidays.py
- Fetch US holidays for 2024-2025 from Nager.Date API
- Transform to DuckDB table: holidays_raw
- Fields: date, name, holiday_type, is_federal, counties
- Write disposition: replace (annual full refresh)
- Primary key: date
```

**2. Data Quality Validation (Great Expectations)**
```
New suite: holidays_suite
Expectations:
- Date is unique (no duplicate holidays)
- Date format is valid (YYYY-MM-DD)
- Holiday name is not null
- Holiday type in accepted values (Federal, State, Observance)
- Date range is reasonable (2024-2030)
```

**3. Data Transformation (dbt)**
```
New models:
- staging/stg_holidays.sql
  - Normalize holiday data
  - Add is_weekend flag
  - Add days_to/from_holiday for window analysis

- marts/mart_holiday_demand.sql
  - Join trips with holidays
  - Calculate demand metrics by holiday type
  - Compare holiday vs. non-holiday demand
  - Include weather effects on holidays

Key metrics:
- Avg trips per holiday vs. non-holiday
- Demand change by holiday type (federal, observance)
- Weekend holiday vs. weekday holiday patterns
- Pre/post holiday demand (days before/after)
```

**4. Dashboard Enhancement (Streamlit)**
```
New page: pages/Holiday_Impact.py

Visualizations:
1. Holiday Demand Comparison (bar chart)
   - Average trips: holidays vs. non-holidays
   - Segmented by holiday type
   - Weather-adjusted comparison

2. Holiday Calendar Heatmap
   - Calendar view with demand overlay
   - Holidays highlighted
   - Color intensity by demand level

3. Individual Holiday Analysis
   - Dropdown to select specific holiday
   - Time series: demand pattern around holiday (±3 days)
   - Weather impact on that holiday
   - Year-over-year comparison (future)

4. Holiday Type Performance (table)
   - Federal holidays: demand, change %
   - Observances: demand, change %
   - State holidays: demand, change %

5. What-If Holiday Planning
   - Select upcoming holiday
   - See predicted demand based on weather forecast
   - Staffing recommendation (trucks needed)
```

#### Pipeline Integration

**Airflow DAG Update**:
```python
ingest_holidays = PythonOperator(
    task_id='ingest_holidays',
    python_callable=run_holidays_pipeline,
    dag=dag
)

validate_holidays = PythonOperator(
    task_id='validate_holidays',
    python_callable=validate_holidays_data,
    dag=dag
)

# Dependencies
ingest_holidays >> validate_holidays >> dbt_build
```

### Acceptance Criteria

**Data Ingestion**:
- ✅ Holidays ingested from Nager.Date API for 2024-2025
- ✅ All US federal holidays captured (10+ per year)
- ✅ State-level holidays included (50+ per year)
- ✅ Pipeline runs successfully with idempotent behavior

**Data Quality**:
- ✅ No duplicate dates in holiday calendar
- ✅ All holiday names populated
- ✅ Holiday types validated against accepted values
- ✅ Great Expectations validation reports generated

**Data Transformation**:
- ✅ mart_holiday_demand model created with key metrics
- ✅ Holidays correctly joined to trip data by date
- ✅ Demand comparison calculations accurate
- ✅ dbt tests passing for all new models

**Dashboard**:
- ✅ Holiday Impact page added to Streamlit app
- ✅ All 5 visualizations render correctly
- ✅ Holiday calendar heatmap displays demand overlays
- ✅ Individual holiday drill-down works
- ✅ What-if planning tool provides staffing recommendations
- ✅ Page loads in <3 seconds

**Business Value**:
- ✅ Quantified demand change on federal holidays (e.g., "+25% on Memorial Day")
- ✅ Identified low-demand holidays for maintenance scheduling (e.g., "-40% on Thanksgiving")
- ✅ Staffing recommendations generated for upcoming holidays
- ✅ Operations team uses holiday insights weekly for planning

### Key Insights Expected

**Hypothesis to Validate**:
1. **Summer holidays increase demand**: Memorial Day, July 4th expected +20-30% demand
2. **Winter holidays decrease demand**: Thanksgiving, Christmas expected -30-50% demand
3. **Observances have minimal impact**: Columbus Day, Presidents Day expected ±5% demand
4. **Weather amplifies holiday effect**: Good weather on holiday → even higher demand
5. **Pre-holiday surge**: Day before 3-day weekend expected +10-15% demand

**Operational Actions**:
- **High-demand holidays**: Schedule extra rebalancing trucks, extend hours
- **Low-demand holidays**: Reduce staffing, schedule bike maintenance
- **Pre-holiday planning**: Pre-position bikes at popular destinations (parks, waterfronts)

### Implementation Timeline

**Week 1: Data Ingestion & Validation**
- Day 1-2: Implement dlt holidays pipeline (dlt_pipeline/holidays.py)
- Day 3: Create Great Expectations suite (holidays_suite)
- Day 4: Test ingestion end-to-end
- Day 5: Create validation script (validate_holidays_data.py)

**Week 2: Data Transformation**
- Day 1-2: Build stg_holidays model
- Day 3-4: Build mart_holiday_demand model with metrics
- Day 5: Write and validate dbt tests

**Week 3: Dashboard Development**
- Day 1-2: Create Holiday_Impact.py Streamlit page
- Day 3: Build 5 core visualizations
- Day 4: Implement what-if planning tool
- Day 5: Testing and refinement

**Week 4: Integration & Testing**
- Day 1-2: Update Airflow DAG with holiday tasks
- Day 3: End-to-end pipeline testing
- Day 4: User acceptance testing with operations team
- Day 5: Documentation and training

**Total Duration**: 4 weeks (1 sprint)

### Dependencies & Risks

**Dependencies**:
- ✅ Nager.Date API availability (free, no auth required)
- ✅ Existing dlt/dbt/Great Expectations infrastructure
- ✅ DuckDB storage capacity (holidays add <1MB data)

**Risks**:
- **Low**: Nager.Date API downtime → Mitigation: Cache holiday data locally, manual fallback
- **Low**: Holiday definitions change → Mitigation: Annual refresh process
- **Medium**: Insufficient historical data (only 2 months) → Mitigation: Document limitations, plan year-over-year analysis for future

### Success Metrics

**Adoption**:
- Operations team accesses Holiday Impact page 2+ times per week
- 100% of major holidays reviewed before occurrence
- Staffing decisions reference holiday predictions

**Accuracy**:
- Holiday demand predictions within ±15% of actual
- 90%+ confidence in holiday type categorization
- Weather-adjusted holiday forecasts beat baseline by 20%

**Business Impact**:
- 10-15% reduction in staffing costs through holiday optimization
- 25% improvement in bike availability on high-demand holidays
- Zero major holidays missed without proper planning

---

## Phase 2: Predictive Forecasting (Q2 2025)

### Status: 📋 Planned

**Goal**: Add ML-based demand forecasting to enable proactive rebalancing

### Features
1. **Demand Forecasting Models**
   - Next-day demand predictions by station and hour
   - Weather-adjusted forecasts (using weather API forecasts)
   - Holiday-adjusted forecasts (using Nager.Date holiday calendar)
   - Confidence intervals for predictions

2. **Member Behavior Segmentation**
   - Cohort analysis: new members vs. long-term
   - Usage frequency segmentation (daily, weekly, occasional)
   - Churn prediction for at-risk members

3. **Alert System**
   - Data quality alerts (Slack/email notifications)
   - Demand anomaly detection
   - Station imbalance warnings

4. **Expanded Weather Variables**
   - Humidity, wind speed, precipitation probability
   - UV index, visibility
   - Enhanced correlation analysis

### Data Sources Added
- Weather forecast API (7-day predictions)
- Historical member data (if available)

### Success Criteria
- >85% forecast accuracy (MAPE)
- 20% reduction in reactive rebalancing
- 5+ member segments identified
- Alert system used daily

**Duration**: Q2 2025 (12 weeks)

---

## Phase 3: Route Optimization (Q3 2025)

### Status: 📋 Planned

**Goal**: Automate rebalancing route planning to minimize operational costs

### Features
1. **Route Optimization Engine**
   - Multi-stop route generation (TSP/VRP algorithms)
   - Priority scoring (urgent vs. routine)
   - Time window constraints
   - Truck capacity optimization

2. **Fleet Management Integration**
   - API integration with truck tracking systems
   - Real-time location updates
   - Job assignment and dispatch

3. **Mobile Notifications**
   - Push notifications for drivers
   - Turn-by-turn navigation
   - Job completion tracking

4. **Rebalancing Performance Dashboards**
   - Truck utilization metrics
   - Routes completed vs. planned
   - Cost per rebalancing trip
   - Driver performance metrics

### Success Criteria
- 30% reduction in rebalancing miles
- <5 minute route generation
- 90%+ driver adoption
- 20% improvement in truck utilization

**Duration**: Q3 2025 (12 weeks)

---

## Phase 4: Multi-City Expansion (Q4 2025)

### Status: 📋 Future

**Goal**: Scale platform to support multiple bike-share markets

### Features
1. **Multi-City Data Ingestion**
   - Parameterized pipelines for different cities
   - Standardized data schemas across markets
   - City dimension table

2. **Cross-Market Benchmarking**
   - Compare demand patterns across cities
   - Weather impact by geography
   - Operational efficiency rankings

3. **Executive Dashboards**
   - Portfolio-level KPIs
   - Monthly automated reporting
   - Market performance heatmaps

### Target Cities
- Phase 1: NYC, Chicago, Boston
- Phase 2: San Francisco, Washington DC
- Phase 3: International (London, Paris)

### Success Criteria
- 3-5 cities onboarded
- Consistent data quality (>95%) across all markets
- Executive reporting automated
- Cross-market insights drive 10%+ efficiency gains

**Duration**: Q4 2025 (16 weeks)

---

## Long-Term Vision (2026+)

### Real-Time Analytics
- 5-minute data refresh
- Live bike availability tracking
- Streaming ingestion architecture
- WebSocket dashboard updates

### Advanced ML & AI
- Causal inference for interventions
- A/B testing framework
- Reinforcement learning for route optimization
- Dynamic pricing recommendations

### Predictive Maintenance
- Integration with bike IoT sensors
- Failure prediction models
- Maintenance scheduling optimization
- Parts inventory management

### Platform Expansion
- White-label SaaS product
- API for third-party integrations
- Mobile apps (iOS, Android)
- Global expansion (20+ cities)

---

## Prioritization Framework

### Priority Scoring
Features are prioritized using RICE framework:

**RICE = (Reach × Impact × Confidence) / Effort**

- **Reach**: Number of users/operations affected
- **Impact**: Business value (cost savings, revenue increase)
- **Confidence**: Data-backed estimate quality
- **Effort**: Engineering weeks required

### Current Priorities (Next 3 Months)

1. **Holiday Analysis** (RICE: 8.0)
   - Reach: 50 (operations + planning teams)
   - Impact: 3 (high - staffing optimization)
   - Confidence: 80%
   - Effort: 4 weeks
   - Score: (50 × 3 × 0.8) / 4 = 30

2. **Demand Forecasting** (RICE: 7.5)
   - Reach: 100 (all operations)
   - Impact: 3 (high - proactive rebalancing)
   - Confidence: 70%
   - Confidence: 70%
   - Effort: 12 weeks
   - Score: (100 × 3 × 0.7) / 12 = 17.5

3. **Expanded Weather Variables** (RICE: 4.5)
   - Reach: 50
   - Impact: 2 (medium - better predictions)
   - Confidence: 90%
   - Effort: 2 weeks
   - Score: (50 × 2 × 0.9) / 2 = 45

**Recommended Order**: Holiday Analysis → Expanded Weather → Demand Forecasting

---

## Release Strategy

### Versioning
- **v1.0 (MVP)**: Current state - bike + weather analysis
- **v1.1**: Holiday impact analysis + expanded weather
- **v2.0**: Predictive forecasting + member segmentation
- **v3.0**: Route optimization + fleet management
- **v4.0**: Multi-city support

### Rollout Approach
1. **Internal Alpha**: Data team testing (1 week)
2. **Beta**: Operations team pilot (2 weeks)
3. **General Availability**: Full deployment
4. **Training**: 1-hour onboarding session
5. **Monitoring**: 30-day adoption tracking

---

## Stakeholder Communication

### Monthly Updates
- Features delivered
- Adoption metrics
- Business impact (cost savings, efficiency gains)
- Next month priorities

### Quarterly Reviews
- Strategic alignment
- ROI analysis
- User feedback synthesis
- Roadmap adjustments

### Annual Planning
- Long-term vision review
- Budget allocation
- Technology evaluation
- Market expansion decisions

---

## Appendix: Feature Dependencies

```
MVP (v1.0)
├── Holiday Analysis (v1.1)
│   └── Predictive Forecasting (v2.0)
│       └── Route Optimization (v3.0)
│           └── Multi-City (v4.0)
├── Expanded Weather (v1.1)
│   └── Advanced Weather ML (v2.0)
└── Data Quality Monitoring
    └── Alert System (v2.0)
```

---

**Document Version**: 1.0
**Last Updated**: 2025-01-04
**Owner**: Product Team
**Status**: Active
