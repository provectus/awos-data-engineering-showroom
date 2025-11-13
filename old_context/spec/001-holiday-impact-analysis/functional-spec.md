# Functional Specification: Holiday Impact Analysis

- **Roadmap Item:** Phase 1 - Holiday Impact Analysis
- **Status:** Approved
- **Author:** Product Team (via Claude Code)

---

## 1. Overview and Rationale (The "Why")

### Problem Statement
Operations managers, business analysts, and schedulers currently lack visibility into how public holidays affect NYC Citi Bike demand patterns. This blind spot leads to three critical inefficiencies:

1. **Inefficient Staffing**: Operations teams cannot accurately predict whether holidays will increase or decrease demand, leading to over-staffing (wasted costs) or under-staffing (poor service quality)
2. **Inaccurate Revenue Forecasting**: Business analysts cannot account for holiday effects when projecting monthly revenue, causing forecast errors that impact business planning
3. **Suboptimal Maintenance Scheduling**: Schedulers lack data to identify low-demand holidays that would be ideal maintenance windows, resulting in maintenance during high-demand periods

### Desired Outcome
Users will be able to:
- Quantify the demand impact of each holiday type (federal, state observance)
- Compare demand patterns on holidays vs. regular days with weather normalization
- Identify high-demand holidays requiring extra resources and low-demand holidays suitable for maintenance
- Plan staffing levels for upcoming holidays based on historical patterns and weather forecasts

### Success Metrics
- **Operational Efficiency**: 10-15% reduction in staffing costs through holiday-optimized crew sizing
- **Service Quality**: 25% improvement in bike availability on high-demand holidays
- **Planning Accuracy**: Operations team uses holiday insights for 100% of major holidays
- **User Adoption**: Holiday Impact dashboard accessed 2+ times per week by operations team

---

## 2. Functional Requirements (The "What")

### 2.1 Holiday Data Integration

**As a** data platform, **I want to** automatically ingest and maintain US holiday data, **so that** users always have current holiday information.

**Acceptance Criteria:**
- [ ] The system ingests US federal holidays from Nager.Date API (https://date.nager.at/api/v3/PublicHolidays/{year}/US)
- [ ] The system ingests New York state holidays from the same API
- [ ] Holiday data includes: date, holiday name, holiday type (Public, Observance, etc.), and whether it's nationwide or NY-specific
- [ ] The system fetches holidays for current year and next year (e.g., 2024-2025)
- [ ] Holiday data refreshes annually (manual trigger acceptable for MVP)
- [ ] When no bike trip data exists for a holiday date, that holiday still appears in the dataset but shows no demand metrics

### 2.2 Holiday Demand Analysis Dashboard

**As an** operations manager, **I want to** access a dedicated Holiday Impact dashboard page, **so that** I can analyze holiday demand patterns in one place.

**Acceptance Criteria:**
- [ ] A new "Holiday Impact" page is added to the Streamlit navigation menu
- [ ] The page is accessible from the main dashboard sidebar
- [ ] The page title is "Holiday Impact Analysis"
- [ ] When insufficient historical data exists (< 2 holidays with bike data), the page displays a banner: "Limited historical data available. Insights will strengthen as more data accumulates over time."
- [ ] The page loads in under 3 seconds with current dataset size

### 2.3 Holiday vs. Non-Holiday Demand Comparison

**As an** operations manager, **I want to** see average demand on holidays compared to non-holidays, **so that** I can understand the overall holiday impact.

**Acceptance Criteria:**
- [ ] A bar chart displays two bars: "Average Holiday Demand" and "Average Non-Holiday Demand"
- [ ] The metric displayed is total daily trips
- [ ] The chart shows weather-adjusted demand (demand normalized as if all days had average weather conditions)
- [ ] A percentage change label shows the difference (e.g., "-15%" or "+20%")
- [ ] The chart is segmented by holiday type: Federal Holidays, NY State Observances
- [ ] Each segment shows its average demand vs. non-holiday baseline
- [ ] When hovering over a bar, a tooltip shows: exact trip count, number of holidays in that category, and date range of data

### 2.4 Holiday Calendar Heatmap

**As a** business analyst, **I want to** view holidays in a calendar format with demand overlay, **so that** I can visually identify high and low demand periods.

**Acceptance Criteria:**
- [ ] A calendar view displays the current year (or selected date range)
- [ ] Each date shows as a cell in the calendar grid
- [ ] Holidays are visually highlighted with a distinct border or icon
- [ ] Cell background color intensity represents demand level (darker = higher demand)
- [ ] A color scale legend is displayed (e.g., "Low Demand" to "High Demand")
- [ ] Dates without bike trip data appear in gray with "No Data" indicator
- [ ] The calendar is view-only (no click interactions)
- [ ] Holiday names appear as text labels on holiday dates

### 2.5 Individual Holiday Analysis

**As a** scheduler, **I want to** analyze demand patterns for a specific holiday, **so that** I can plan staffing and maintenance for that holiday.

**Acceptance Criteria:**
- [ ] A dropdown menu lists all holidays in the dataset by name and date (e.g., "Memorial Day - May 27, 2024")
- [ ] When a holiday is selected, a time series line chart displays demand for ±3 days around the holiday (7 days total)
- [ ] The holiday date is visually marked on the chart (e.g., vertical line or highlighted point)
- [ ] The chart shows daily trip counts on the Y-axis and dates on the X-axis
- [ ] A summary panel displays: holiday name, date, total trips on holiday, % change vs. average day, weather on that holiday (temperature, precipitation)
- [ ] If the selected holiday has no bike trip data, the chart shows a message: "No trip data available for this holiday"
- [ ] The chart includes a baseline line showing average daily demand for reference

### 2.6 Holiday Type Performance Table

**As a** business analyst, **I want to** see demand metrics by holiday type, **so that** I can understand which holiday categories have the most impact.

**Acceptance Criteria:**
- [ ] A table displays rows for each holiday type: Federal Holidays, NY State Observances
- [ ] Columns display: Holiday Type, Number of Holidays, Average Demand (trips), % Change vs. Baseline, Sample Holidays (2-3 examples)
- [ ] The table is sortable by any column
- [ ] % Change is color-coded: green for positive, red for negative
- [ ] When a holiday type has no data, the row shows "N/A" for demand metrics
- [ ] The table includes a "Total/Average" row at the bottom summarizing all holiday types

### 2.7 What-If Holiday Planning Tool

**As an** operations manager, **I want to** predict demand for upcoming holidays, **so that** I can plan staffing levels in advance.

**Acceptance Criteria:**
- [ ] A dropdown menu lists upcoming holidays (holidays in the next 365 days from current date)
- [ ] When a holiday is selected, the system displays:
  - Predicted demand based on historical patterns for that holiday type
  - Weather forecast integration (if available): adjusted prediction based on forecasted temperature and precipitation
  - Staffing recommendation as relative guidance: "Increase staffing by X%" or "Reduce staffing by X%"
- [ ] If historical data for that specific holiday doesn't exist, the system uses the average for that holiday type (e.g., all Federal Holidays)
- [ ] If weather forecast is unavailable, the system shows prediction based on average weather conditions with a note: "Weather forecast unavailable - using average conditions"
- [ ] The staffing recommendation is displayed as: "Recommendation: [Increase/Reduce/Maintain] staffing by [X]% compared to typical day"
- [ ] The tool does NOT provide specific bike redistribution recommendations
- [ ] A confidence indicator is shown: "Confidence: [High/Medium/Low]" based on amount of historical data available

---

## 3. Scope and Boundaries

### In-Scope

- Integration with Nager.Date API for US holiday data
- Filtering to federal holidays and New York state holidays only
- Five dashboard visualizations: demand comparison bar chart, calendar heatmap, individual holiday analysis, holiday type performance table, what-if planning tool
- Weather-adjusted demand calculations (normalizing for weather effects)
- Relative staffing recommendations (percentage-based guidance)
- Annual holiday data refresh (manual trigger acceptable)
- Support for limited historical data scenarios with user disclaimers

### Out-of-Scope

- **Airflow orchestration/scheduling** - Holiday data is refreshed annually (one-time manual activity), not part of daily pipeline
- **Great Expectations data validation** - Holiday API data is simple and reliable, comprehensive validation is redundant overhead
- **Automatic daily holiday data refresh** - Annual refresh is sufficient (holidays don't change frequently)
- **State holidays for states other than New York** - NYC-focused platform doesn't need other state observances
- **Specific bike redistribution recommendations** - Phase 3 feature (Route Optimization)
- **Specific numerical staffing recommendations** - Only relative guidance (e.g., "increase by 25%", not "deploy 4 trucks")
- **Year-over-year holiday comparisons** - Requires multiple years of data (future enhancement)
- **Real-time holiday demand tracking** - Phase 2+ feature (Real-Time Analytics)
- **Multi-city holiday analysis** - Phase 4 feature
- **Custom holiday definitions** - Only public API holidays supported
- **Holiday demand forecasting with ML models** - Phase 2 feature (Predictive Forecasting)
- **Integration with HR/scheduling systems** - Manual application of staffing recommendations
- **Mobile-optimized holiday dashboard** - Desktop browser only for MVP

---
