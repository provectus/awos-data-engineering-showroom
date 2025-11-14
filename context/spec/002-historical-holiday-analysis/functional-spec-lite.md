# Functional Specification: Historical Holiday Analysis (Lite Version)

**Roadmap Item:** Holiday Data Integration → Historical Holiday Analysis
**Status:** Draft

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
   - Group by area (Manhattan Financial, Brooklyn, etc.)
   - Flag rebalancing needs (>30% change = add/remove bikes)

3. **Hourly patterns**
   - Compare demand hour-by-hour (0-23)
   - Show peak hour shifts (commute peaks disappear, leisure peaks appear)

4. **Interactive dashboard**
   - Select holiday from dropdown
   - View KPI cards (trips %, duration %, significance)
   - See station heatmap (red=less demand, green=more demand)
   - View hourly comparison chart
   - See top stations tables with rebalancing recommendations

5. **Most recent data only**
   - Use most recent occurrence of each holiday
   - No year-over-year trends yet (need more data)

---

## Success Criteria

- Operations team uses dashboard weekly for pre-holiday planning
- Data model ready for Phase 2 forecasting
- Top 3 holidays with biggest impact identified

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

| Metric | Definition | Use Case |
|--------|-----------|----------|
| Total Trips | Count of trips on holiday vs baseline | Overall demand impact |
| Avg Duration | Mean trip length | Behavioral change (commute vs leisure) |
| Trips per Station | Station-level demand | Rebalancing priorities |
| Peak Hours | Trips by hour (0-23) | Staffing & operations |
| Rebalancing Need | Std dev of station demand | Operational complexity |

---

## User Personas

**Operations Manager:** "Which stations need bikes before Memorial Day?"
**Business Analyst:** "What's the revenue impact of July 4th?"
**Urban Planner:** "How does demand shift geographically on holidays?"
**ML Engineer:** "Clean foundation data for forecasting models"

---

## Example Insights (Memorial Day 2024)

**Expected Patterns:**
- Total trips: -25% to -35% (fewer commuters)
- Avg duration: +15% to +25% (leisure rides longer)
- Financial District: -60% to -80% (offices closed)
- Central Park: +40% to +80% (recreational)
- 8am commute peak: Disappears (-80%)
- 12pm leisure peak: New peak (+50%)
