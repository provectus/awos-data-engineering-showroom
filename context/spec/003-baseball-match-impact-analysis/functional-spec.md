# Functional Specification: Baseball Match Impact Analysis

- **Roadmap Item:** Baseball Match Impact Analysis
- **Status:** Draft
- **Author:** Product Team

---

## 1. Overview and Rationale (The "Why")

Maria (Operations Manager) currently cannot anticipate how baseball games at Yankee Stadium and Citi Field impact bike demand at nearby stations. Major League Baseball games attract 30,000-50,000 fans, creating massive demand spikes at stations near the stadiums.

**The Problem:** Without visibility into upcoming games and their historical impact patterns, Maria discovers demand spikes only after they happen, leading to:
- Empty stations near stadiums before games (fans can't get bikes to commute home)
- Overloaded stations near stadiums after games (fans can't dock bikes after riding from the game)
- Poor customer experience and lost revenue from missed trips

**Desired Outcome:** Maria can proactively rebalance bikes at stadium-adjacent stations before and after games, preventing empty/full station incidents and maximizing trip revenue during high-demand events.

**Success Metrics:**
- Maria can see upcoming Yankees and Mets home games in the system
- Maria can get hourly rebalancing recommendations (bikes to add/remove) for any upcoming game
- 30% reduction in empty/full station incidents during games
- <5 minutes to generate a rebalancing plan (vs 30+ minutes manual analysis)

---

## 2. Functional Requirements (The "What")

### Requirement 1: MLB Game Data Ingestion

The system must automatically ingest NY Yankees and NY Mets home game schedules from the MLB Stats API.

**Acceptance Criteria:**
- [ ] Pipeline connects to MLB Stats API (free public API, no authentication)
- [ ] Pipeline fetches all home games for NY Yankees (team ID 147) and NY Mets (team ID 121)
- [ ] Pipeline accepts configurable date range parameters (start_date, end_date)
- [ ] Default date range is May-June 2024 (matching bike trip data period)
- [ ] Only home games played in New York are included (not away games)
- [ ] All API fields are captured: game date/time, home team, away team, venue name, venue location, game status
- [ ] Data is stored in DuckDB warehouse in `raw_games` schema
- [ ] Pipeline supports idempotent reloads (no duplicate games)
- [ ] Pipeline is integrated into Airflow DAG alongside holiday and bike/weather ingestion

### Requirement 2: Stadium Proximity Analysis

The system must identify which Citi Bike stations are within 1km of Yankee Stadium and Citi Field.

**Acceptance Criteria:**
- [ ] Stadium addresses are geocoded to obtain lat/lon coordinates:
  - Yankee Stadium: 1 E 161st St, Bronx, NY 10451
  - Citi Field: 41 Seaver Way, Queens, NY 11368
- [ ] Distance is calculated between each Citi Bike station and each stadium using lat/lon
- [ ] Stations within 1km of either stadium are tagged as "stadium-adjacent"
- [ ] Proximity calculation is implemented in dbt transformation model
- [ ] Output table shows: station_id, stadium_name, distance_km
- [ ] Tagged stations are used to filter downstream game day analysis

### Requirement 3: Game Day vs Non-Game Day Demand Comparison

The system must analyze bike demand patterns on game days compared to non-game days at stadium-adjacent stations.

**Acceptance Criteria:**
- [ ] Game days are compared to non-game days of the same day of week (Tuesday game vs non-game Tuesdays)
- [ ] Analysis ignores weather conditions and holidays (simple game day vs non-game day average)
- [ ] Analysis covers 6-hour window: 3 hours before game start to 3 hours after game end
- [ ] Game end time is estimated as start time + 3 hours (typical game duration)
- [ ] Hourly metrics calculated for each stadium-adjacent station:
  - Trips started at station (outbound demand)
  - Trips ended at station (inbound demand)
  - Net flow (trips ended - trips started)
  - Average trip counts: game days vs non-game days
  - Percentage difference between game days and non-game days
- [ ] Analysis available at two levels:
  - Individual station level
  - Grouped station level (stations clustered within ~0.5km using H3 or k-means)
- [ ] Results stored in dbt mart tables for dashboard consumption

### Requirement 4: Demand Spike Identification

The system must identify hourly demand spikes during the 6-hour game window.

**Acceptance Criteria:**
- [ ] For each hour in the 6-hour window (-3h to +3h from game start):
  - Calculate baseline demand (average for that hour on non-game days of same day of week)
  - Calculate game day demand (actual trips for that hour on game days)
  - Calculate percentage change: (game day - baseline) / baseline × 100
- [ ] Spikes are flagged when percentage increase exceeds threshold (e.g., >50%)
- [ ] Analysis shows whether bikes are accumulating (more arrivals) or depleting (more departures)
- [ ] Results identify which hours have highest rebalancing needs

### Requirement 5: Rebalancing Recommendation Calculator

**This is the critical feature.** The system must tell Maria exactly how many bikes to add or remove from each station/area for an upcoming game.

**Acceptance Criteria:**
- [ ] User can select:
  - Venue/stadium (Yankee Stadium or Citi Field)
  - Upcoming game (from list) or manual game start time
  - Target hour (within the 6-hour game window)
- [ ] System outputs for each station or station group:
  - Number of bikes to add (+) if expected to deplete
  - Number of bikes to remove (-) if expected to overflow
  - Percentage recommendation (e.g., "+30% capacity")
  - Expected trip volume based on historical averages
- [ ] Recommendations based on simple historical average from past game days (same day of week, same hour, same stadium)
- [ ] Station grouping options available:
  - Individual stations (granular)
  - H3 hexagons (~0.5km areas)
  - K-means clusters (stations within 0.5km)
- [ ] Calculator prevents empty stations (insufficient bikes) and full stations (insufficient docks)
- [ ] Interactive interface in Streamlit dashboard

### Requirement 6: Game Impact Visualizations

The system must provide visual analytics to compare game day vs non-game day demand.

**Acceptance Criteria:**
- [ ] **Rebalancing Calculator (Priority #1):** Interactive tool as described in Requirement 5
- [ ] **Line Charts:** Trip count over time
  - X-axis: Hours relative to game start (-3h to +3h)
  - Y-axis: Trip count
  - Two lines: game day average, non-game day average
  - Filterable by stadium, station, or station group
- [ ] **Bar Charts:** Hourly demand breakdown
  - X-axis: Hour relative to game start
  - Y-axis: Trip count
  - Separate bars for trips started vs trips ended
  - Shows net flow (accumulation/depletion)
- [ ] **Station Comparison Table:**
  - Columns: station name, game day avg, non-game day avg, % difference
  - Sortable by % difference to find highest impact stations
  - Available for both individual stations and station groups
- [ ] All visualizations are interactive (filters, tooltips, drill-down)
- [ ] Accessible via Streamlit web interface

### Requirement 7: Data Quality Validation

The system must ensure data quality through dbt tests.

**Acceptance Criteria:**
- [ ] dbt tests for MLB game data:
  - Game date is not null
  - Game time is not null
  - Venue name is not null and is either "Yankee Stadium" or "Citi Field"
  - Home team is "Yankees" or "Mets"
  - Game ID is unique (no duplicates)
- [ ] dbt tests for stadium proximity model:
  - Distance values are non-negative
  - All stations have calculated distance to at least one stadium
  - Tagged stations have valid stadium references
- [ ] dbt tests for demand marts:
  - No nulls in critical fields (station_id, game_date, hour, trip_count)
  - Trip counts are non-negative
  - Date ranges match input parameters
- [ ] All tests must pass for pipeline to succeed

---

## 3. Scope and Boundaries

### In-Scope

- **MLB Game Ingestion:** Yankees and Mets home games from MLB Stats API with configurable date range (default May-June 2024)
- **Stadium Proximity:** Geocoding stadiums, identifying stations within 1km radius
- **Game Day Analysis:** Same-day-of-week comparison, ignoring weather/holidays, 6-hour window (3h before to 3h after)
- **Demand Metrics:** Trips started, trips ended, net flow, percentage differences at station and grouped levels
- **Rebalancing Calculator:** Interactive tool providing bike add/remove recommendations per station or station group
- **Spike Detection:** Percentage increase vs typical demand at same time of day
- **Station Grouping:** H3 hexagons (~0.5km) or k-means clustering
- **Visualizations:** Rebalancing calculator, line charts, bar charts, comparison tables
- **Simple Predictions:** Historical averages from past game days (same day of week, same hour)
- **Airflow Integration:** MLB ingestion added to existing DAG
- **Data Quality:** dbt schema tests (no Great Expectations or unit tests for Phase 1)

### Out-of-Scope

- **Advanced Predictions:** Weather-adjusted forecasts, opponent impact, playoff vs regular season differences
- **Real-Time Updates:** Live game data, in-game tracking, real-time alerts
- **Other Sports:** NBA, NHL, soccer, etc.
- **Other Events:** Concerts, festivals, parades at non-stadium venues
- **Great Expectations:** Comprehensive validation framework (dbt tests sufficient for Phase 1)
- **Unit Tests:** Python unit tests for dlt pipelines (not required for Phase 1)
- **Automated Execution:** System triggering truck dispatches automatically (manual execution only)
- **Optimization Algorithms:** Route optimization, multi-venue coordination, cost minimization
- **Granular Timing:** 15-minute intervals (hourly sufficient for Phase 1)
- **User Segmentation:** Member vs casual rider patterns (total demand only)
- **External Factors:** Traffic, transit disruptions, promotions
- **Multi-City:** Other cities with bike share
- **Mobile Apps:** Push notifications for operations staff
- **Multi-Year Analysis:** Seasonal trends, team performance correlation
