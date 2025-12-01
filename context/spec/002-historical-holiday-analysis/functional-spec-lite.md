# Functional Specification: Historical Holiday Analysis (Lite Version)

**Roadmap Item:** Holiday Data Integration → Historical Holiday Analysis
**Status:** ✅ Completed

---

## The Problem

Operations managers have holiday data but can't see how holidays affect bike demand. They need to answer: "Should I add bikes to Central Park before Memorial Day?" without data to back decisions.

---

## The Solution

Analyze historical bike demand around holidays vs regular days. Show:
- **Overall impact:** Total trips, duration, statistical significance
- **Station impact:** Which stations need more/fewer bikes
- **Time patterns:** How hourly demand shifts on holidays
- **Geographic patterns:** Which areas see demand increases/decreases

---

## Key Requirements

1. **Compare holidays to baseline**
   - Baseline = average of 15 days before + 15 days after (exclude weekends/holidays)
   - Show absolute & percentage change
   - Test statistical significance (p < 0.05)

2. **Station-level analysis**
   - Top 10 stations with increased/decreased demand
   - Group by area using 10 geographic classifications (Manhattan Financial, Manhattan Midtown, Manhattan Upper West, Manhattan Upper East, Manhattan Downtown, Brooklyn, Queens, Bronx, Jersey City, Other)
   - Flag rebalancing needs (>30% change = add/remove bikes)
   - **K-Means clustering:** Aggregate 2,000+ stations into 10-50 adjustable neighborhood clusters for visualization

3. **Hourly patterns**
   - Compare demand hour-by-hour (0-23)
   - Show peak hour shifts (commute peaks disappear, leisure peaks appear)
   - Identify baseline vs holiday peak hours

4. **Interactive dashboard** (6 sections)
   - **Section 1:** Holiday selector dropdown + 3 KPI cards (trips %, duration %, statistical significance)
   - **Section 2:** Demand comparison grouped bar chart (baseline vs holiday)
   - **Section 3:** Neighborhood-level demand map with K-Means clustering (adjustable 10-50 clusters, color-coded red/yellow/green)
   - **Section 4:** Hourly demand pattern line chart (24-hour comparison)
   - **Section 5:** Top stations ranking tables (top 10 increased/decreased with rebalancing actions)
   - **Section 6:** Holiday comparison sortable table (compare all 4 holidays side-by-side)

5. **Most recent data only**
   - Use most recent occurrence of each holiday
   - No year-over-year trends yet (need more data)

---

## Success Criteria ✅

- ✅ Operations team can use dashboard for pre-holiday planning (all 4 holidays analyzed)
- ✅ Data model ready for Phase 2 forecasting (4 mart models with 34 passing tests)
- ✅ Top 3 holidays with biggest impact identified:
  1. Memorial Day: -52.87% trips (major non-working holiday)
  2. Juneteenth: +10.99% trips (celebration effect)
  3. Puerto Rican Day Parade: Localized Manhattan impact
- ✅ Statistical significance validated (t-test p < 0.05 for all holidays)
- ✅ Dashboard accessible at http://localhost:8501

---

## Out of Scope

- ❌ Weather correlation (future)
- ❌ Predictive forecasting (Phase 2)
- ❌ Year-over-year trends (need more data)
- ❌ Special events like concerts (separate feature)
- ❌ Automated rebalancing system integration (future)
- ❌ Real-time alerts (Phase 4)

---

## Metrics Summary

| Metric | Definition | Implementation | Use Case |
|--------|-----------|----------------|----------|
| Total Trips | Count of trips on holiday vs baseline | One-sample t-test (α=0.05) | Overall demand impact with statistical validation |
| Avg Duration | Mean trip length | Percentage change calculation | Behavioral change (commute vs leisure) |
| Trips per Station | Station-level demand | 8,370 rows (4 holidays × ~2,093 stations) | Rebalancing priorities |
| Peak Hours | Trips by hour (0-23) | 96 rows (4 holidays × 24 hours) | Staffing & operations, peak hour identification |
| Geographic Clusters | K-Means neighborhood aggregation | 10-50 adjustable clusters | Visualization of geographic demand patterns |
| Statistical Significance | T-test comparing holiday vs baseline distribution | p-value < 0.05 threshold | Confidence in observed changes |

---

## User Personas

**Operations Manager:** "Which stations need bikes before Memorial Day?"
**Business Analyst:** "What's the revenue impact of July 4th?"
**Urban Planner:** "How does demand shift geographically on holidays?"
**ML Engineer:** "Clean foundation data for forecasting models"

---

## Actual Results (Memorial Day 2024)

**Validated Patterns:**
- ✅ Total trips: **-52.87%** (significant at p < 0.05) - major decline due to fewer commuters
- ✅ Avg duration: **+0.88%** (minimal change, not as expected)
- ✅ Member trips: **-56.15%** (commuters stay home)
- ✅ Casual trips: **-38.76%** (tourists/recreational riders also down)
- ✅ Financial District: **-58.84%** average (Manhattan Financial area)
- ✅ 8am commute peak: **-71.5%** (nearly disappears)
- ✅ 5pm commute peak: **-83.1%** (completely disappears)
- ✅ Peak hour shift: From **19:00 baseline** → **14:00 holiday** (midday leisure)
- ✅ Statistical significance: **p < 0.0001** (highly significant difference)
