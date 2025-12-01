# Functional Specification: Demand Forecasting Engine - Station Rebalancing Predictions

- **Roadmap Item:** Phase 2: Predictive Intelligence → Demand Forecasting Engine → Station-Level Predictions
- **Status:** Draft
- **Author:** Product Team

---

## 1. Overview and Rationale (The "Why")

Maria (Operations Manager) currently makes rebalancing decisions reactively—she waits until stations are empty or full before dispatching trucks. With historical holiday and game data in the warehouse, she needs **proactive forecasting** to plan rebalancing operations 24 hours in advance.

**The Problem:** Without predictive capabilities, Maria cannot answer questions like: "How many bikes should I add to Financial District stations tomorrow at 8am?" or "Which areas will accumulate excess bikes on Saturday afternoon?" This leads to inefficient truck routes, wasted fuel, and customer dissatisfaction (empty/full stations).

**This feature enables:** Hourly predictions of **net bike flow** (bikes to add or remove) for station clusters/areas over the next 24 hours, accounting for day-of-week patterns, weather conditions, and holidays.

**User Value:**
- **Operations Managers** can plan rebalancing routes 24 hours in advance, optimizing truck efficiency
- **Field Teams** receive actionable guidance ("Add 15 bikes to Midtown Area at 7am")
- **Business Analysts** can quantify forecast accuracy and improve operations planning over time

**Success Criteria:**
- Forecast accuracy (MAPE) < 30% for next 24 hours
- Operations team uses forecasts weekly for route planning
- 40% reduction in empty/full station incidents (Phase 1 goal)

---

## 2. Functional Requirements (The "What")

### Requirement 1: Station Clustering by Geographic Area

The system must group individual bike stations into geographic areas/clusters to predict aggregate rebalancing needs.

**Acceptance Criteria:**
- [ ] Stations are grouped using **either** 0.5km radius clusters **or** k-means clustering algorithm
- [ ] Each area has a unique identifier (e.g., "Area_1", "Midtown_Cluster")
- [ ] Each area contains at least 3 stations (minimum viable cluster size)
- [ ] The clustering model/mapping is stored and reused consistently across all predictions
- [ ] A reference table shows which stations belong to which areas

### Requirement 2: Hourly Net Flow Forecasting (24-Hour Horizon)

The system must predict **net bike flow** for each area for each hour over the next 24 hours.

**Net Flow Definition:**
- `net_flow = trips_ended - trips_started`
- **Negative net flow** = bikes are depleting (more trips started than ended) → **Add bikes**
- **Positive net flow** = bikes are accumulating (more trips ended than started) → **Remove bikes**

**Acceptance Criteria:**
- [ ] For each area and each hour (0-23) in the next 24 hours, the system predicts the net flow value
- [ ] Predictions are based on historical hourly patterns for that area
- [ ] Output includes: `area_id`, `forecast_hour` (timestamp), `predicted_net_flow` (integer), `recommendation` (text)
- [ ] Recommendations follow the pattern: "Add X bikes" (if net_flow < -3), "Remove X bikes" (if net_flow > 3), "No action needed" (if -3 ≤ net_flow ≤ 3)
- [ ] The 3-bike threshold matches the game rebalancing logic for consistency

### Requirement 3: Multi-Factor Baseline Forecasting

The system must adjust historical baseline demand using weather and holiday factors.

**Baseline Calculation:**
- Start with historical average net flow for that area, day-of-week, and hour-of-day
- Apply weather adjustment factor (rain, temperature, wind)
- Apply holiday adjustment factor (if next day is a holiday)

**Acceptance Criteria:**
- [ ] The system calculates historical average net flow grouped by: area, day_of_week, hour
- [ ] Weather adjustment uses next 24 hours of weather forecast data (temperature, precipitation, wind)
- [ ] Holiday adjustment uses the upcoming holiday flag (from stg_holidays table)
- [ ] Final forecast formula: `predicted_net_flow = baseline_net_flow × weather_factor × holiday_factor`
- [ ] Weather and holiday factors are multiplicative (e.g., rain = 0.8, holiday = 1.2)
- [ ] Simple factor ranges: weather (0.6-1.2), holiday (0.7-1.5) based on historical analysis

### Requirement 4: Forecast Storage and Retrieval

The system must store forecast results for dashboard consumption and accuracy tracking.

**Acceptance Criteria:**
- [ ] Forecasts are stored in a dbt mart table: `mart_demand_forecast`
- [ ] Table schema includes: `forecast_generated_at` (when prediction was made), `forecast_hour` (which hour is being predicted), `area_id`, `predicted_net_flow`, `bikes_to_add_or_remove`, `rebalancing_recommendation`
- [ ] **Alternative approach acceptable:** Forecasts can be generated in-memory (Python/Polars) and served directly to dashboard if performance is better
- [ ] Forecasts are regenerated daily (or on-demand via dashboard refresh)
- [ ] Historical forecasts are retained for accuracy validation

### Requirement 5: Forecast Accuracy Tracking

The system must compare predictions to actual outcomes and calculate accuracy metrics.

**Acceptance Criteria:**
- [ ] After each forecast hour passes, the system compares `predicted_net_flow` to `actual_net_flow`
- [ ] Accuracy metric used: **MAPE** (Mean Absolute Percentage Error) = `mean(|actual - predicted| / |actual|) × 100`
- [ ] Accuracy is calculated per area and overall (citywide average)
- [ ] Accuracy metrics are stored in a separate table: `mart_forecast_accuracy`
- [ ] Dashboard displays current forecast accuracy (last 7 days rolling average)

### Requirement 6: Interactive Forecast Dashboard

The system must provide an interactive dashboard where operations managers can view and act on forecasts.

**Acceptance Criteria:**
- [ ] Dashboard shows forecast for next 24 hours (hourly breakdown)
- [ ] User can filter by area or view citywide summary
- [ ] Dashboard displays forecast as a line chart (predicted net flow over time)
- [ ] Dashboard shows rebalancing recommendations table: `Area`, `Hour`, `Bikes to Add/Remove`, `Recommendation`
- [ ] Dashboard shows color-coded indicators: red (add bikes), blue (remove bikes), gray (no action)
- [ ] Dashboard displays current forecast accuracy (MAPE metric) as a KPI card
- [ ] Dashboard allows refresh/regeneration of forecasts on-demand

---

## 3. Scope and Boundaries

### In-Scope

- **Station clustering** using either 0.5km radius or k-means (whichever is simpler to implement)
- **Net flow prediction** (trips_ended - trips_started) for each area, each hour, next 24 hours
- **Multi-factor baseline model** using historical patterns + weather adjustment + holiday adjustment
- **Simple multiplicative factors** for weather and holidays (no complex ML models)
- **Forecast storage** in dbt mart table OR in-memory generation (whichever fits better)
- **Accuracy tracking** using MAPE metric, stored for historical analysis
- **Interactive Streamlit dashboard** with 24-hour forecast view, rebalancing recommendations, and accuracy KPIs
- **Working with existing data only** (May-June 2024 bike trips, weather, holidays)
- **No additional data ingestion** required
- **No model retraining** workflow (static baseline approach is acceptable for MVP)

### Out-of-Scope

- **MLB game impact integration** - Explicitly excluded per user request
- **Advanced ML models** - Random forests, XGBoost, neural networks (future Phase 2 enhancement)
- **Real-time forecasting** - Only daily batch generation for next 24 hours
- **Multi-day forecasting** - Only 24-hour horizon (not 48h, 72h, etc.)
- **Individual station forecasts** - Only area-level aggregates
- **Automated rebalancing dispatch** - System only provides recommendations, not automated truck routing
- **Weather API integration** - Use existing weather data only, no real-time forecast ingestion
- **Scenario modeling** - "What-if" analysis tool (separate roadmap item: What-If Scenario Modeling)
- **Model performance dashboard** - Detailed factor analysis and model tuning UI (future enhancement)
- **Confidence intervals** - Prediction ranges or uncertainty quantification
- **Event calendar integration** - Concerts, parades, festivals (future special events feature)
- **Member vs casual segmentation** - Unified demand model only
- **Seasonal trend analysis** - Long-term patterns beyond day-of-week/hour-of-day
