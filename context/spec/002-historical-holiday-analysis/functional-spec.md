# Functional Specification: Historical Holiday Analysis

- **Roadmap Item:** Holiday Data Integration → Historical Holiday Analysis
- **Status:** Draft
- **Author:** Product Team

---

## 1. Overview and Rationale (The "Why")

Maria (Operations Manager) now has holiday data in the warehouse (from Spec 001), but she cannot yet see how holidays actually affect bike demand. She needs to answer questions like: "Should I add bikes to Central Park stations before Memorial Day?" and "How much does July 4th reduce commuter demand in the Financial District?" Without historical analysis, she cannot make data-driven rebalancing decisions for upcoming holidays.

**This feature enables:** Analysis of historical bike demand patterns around holidays, comparing holiday demand to regular day baselines to identify trends and impacts.

**User Value:**
- **Operations Managers** can plan bike rebalancing before holidays based on historical demand patterns
- **Business Analysts** can quantify revenue impact of holidays (fewer trips vs longer rides)
- **Urban Planners** can understand geographic demand shifts (business districts down, parks up)
- **ML Engineers** get clean analytical foundation for Phase 2 demand forecasting models

**Success Criteria:**
- Operations team uses dashboard weekly to plan holiday rebalancing
- Foundation data model created for Phase 2 forecasting
- Top 3 holidays with biggest demand impact identified

---

## 2. Functional Requirements (The "What")

### Requirement 1: Holiday vs Regular Day Comparison

The system must calculate and compare demand metrics between holidays and regular non-holiday days.

**Acceptance Criteria:**
- [ ] For each holiday, the system calculates: total trips, average trip duration, trips per station
- [ ] For each holiday, the system calculates a baseline from regular non-weekend days (15 days before and 15 days after the holiday, excluding weekends and other holidays)
- [ ] The system shows absolute change (holiday - baseline) and percentage change ((holiday - baseline) / baseline * 100)
- [ ] The system indicates if the change is statistically significant (p-value < 0.05)

### Requirement 2: Major vs Minor Holiday Segmentation

The system must differentiate impact analysis between major holidays (federal/public) and minor holidays.

**Acceptance Criteria:**
- [ ] Holiday analysis respects the `is_major` flag from the holiday data
- [ ] Major holidays (Memorial Day, July 4th, etc.) are analyzed with high priority
- [ ] Minor holidays (Groundhog Day, etc.) are included but marked as lower priority
- [ ] Working day vs non-working day classification is used to explain demand patterns

### Requirement 3: Station-Level Geographic Analysis

The system must show which stations have the biggest demand changes on holidays, grouped by geographic area.

**Acceptance Criteria:**
- [ ] For each holiday, the system identifies the top 10 stations with increased demand
- [ ] For each holiday, the system identifies the top 10 stations with decreased demand
- [ ] Stations are grouped by area (Manhattan sub-areas like Financial/Midtown, Brooklyn, Queens, etc.)
- [ ] For each station, the system shows percentage change and flags for rebalancing recommendations (e.g., "Add bikes", "Remove bikes")

### Requirement 4: Peak Hour Pattern Analysis

The system must show how hourly demand patterns differ on holidays compared to regular days.

**Acceptance Criteria:**
- [ ] For each holiday, the system calculates trips for each hour of day (0-23)
- [ ] The system compares holiday hourly patterns to baseline hourly patterns
- [ ] The system identifies peak hour shifts (e.g., commute peaks disappear, midday leisure peaks appear)
- [ ] Results show which hours have the biggest percentage changes

### Requirement 5: Rebalancing Insights

The system must provide actionable rebalancing recommendations based on historical holiday patterns.

**Acceptance Criteria:**
- [ ] For stations with >30% demand increase, the system flags "Add bikes"
- [ ] For stations with >30% demand decrease, the system flags "Remove bikes"
- [ ] Recommendations are prioritized (high/medium/low) based on absolute demand change (number of bikes affected)
- [ ] System shows standard deviation of station demand as a measure of rebalancing complexity

### Requirement 6: Most Recent Holiday Occurrence

For holidays that occur multiple times historically (e.g., Memorial Day 2022, 2023, 2024), the system must focus on the most recent occurrence.

**Acceptance Criteria:**
- [ ] When multiple years of data exist for the same holiday, only the most recent occurrence is analyzed
- [ ] The system clearly labels which year's data is being shown
- [ ] Historical trend analysis (year-over-year) is explicitly marked as out-of-scope for this phase

### Requirement 7: Interactive Dashboard

The system must provide an interactive dashboard where users can explore holiday impact analysis.

**Acceptance Criteria:**
- [ ] Dashboard has a dropdown to select holidays (Memorial Day 2024, Juneteenth 2024, etc.)
- [ ] Dashboard displays key metrics as KPI cards (total trips change %, duration change %, statistical significance)
- [ ] Dashboard shows station-level heatmap color-coded by demand change (red=decrease, yellow=stable, green=increase)
- [ ] Dashboard shows hourly demand comparison chart (holiday line vs baseline line)
- [ ] Dashboard shows top 10 stations tables (increased demand and decreased demand)
- [ ] Dashboard shows holiday comparison table (sortable by impact metrics)

---

## 3. Scope and Boundaries

### In-Scope

- Calculating demand metrics (total trips, avg duration, trips per station, peak hours, rebalancing needs) for each holiday
- Comparing holidays to 15-day before/after baseline (excluding weekends and holidays)
- Statistical significance testing (t-test with p-value)
- Station-level analysis grouped by geographic area (Manhattan sub-areas, boroughs)
- Hourly demand pattern comparison (holiday vs baseline)
- Rebalancing recommendations (add/remove bikes flags)
- Most recent occurrence analysis only (no year-over-year trends yet)
- Interactive Streamlit dashboard with 6 sections (selector, comparison chart, heatmap, hourly chart, top stations, comparison table)
- Multiple data models with different granularities (citywide summary, by-station, by-hour, by-area)
- Working with current dataset (May-June 2024: Memorial Day, Juneteenth, Puerto Rican Day Parade)

### Out-of-Scope

- **Year-over-year trend analysis** - Comparing same holiday across multiple years (need more historical data)
- **Weather correlation** - Controlling for weather effects in holiday comparison (future enhancement)
- **Predictive demand forecasting** - Using holiday patterns to predict future demand (Phase 2: Demand Forecasting Engine)
- **Real-time alerts** - Automated notifications before upcoming holidays (Phase 4)
- **Special events impact** - Concerts, sports games, festivals (separate roadmap item: Special Events Data Integration)
- **Automated rebalancing** - System automatically redistributes bikes (future integration with operations system)
- **Multi-day holiday periods** - Analyzing day before/after holidays or holiday weekends (current scope: holiday day only)
- **Member vs casual segmentation** - Deep dive into rider type differences (can be added as enhancement)
- **Revenue impact modeling** - Financial analysis of holiday demand changes (business analytics team)
- **Integration with operations systems** - Pushing recommendations to bike rebalancing tools (future)
- **Great Expectations validation** - Data quality checks for holiday analysis marts (Phase 4)
- **Airflow orchestration** - Automated scheduling of analysis refresh (separate roadmap item: Pipeline Orchestration Enhancement)
