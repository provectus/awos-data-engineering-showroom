# Technical Specification: Baseball Match Impact Analysis

- **Functional Specification:** [functional-spec.md](./functional-spec.md)
- **Status:** Draft
- **Author(s):** Engineering Team

---

## 1. High-Level Technical Approach

This feature will follow the existing v1 architecture pattern with minimal changes to working code:

**Data Ingestion:** New `dlt_pipeline/games.py` will ingest MLB game schedules from MLB Stats API (free public API, no auth required). Follows the same pattern as `holidays.py` with merge disposition, retry logic, and configurable date ranges.

**Data Transformation:** New dbt models will:
- Stage game data (`stg_games.sql`)
- Create stadium dimension with geocoded coordinates (`dim_stadiums.sql`)
- Calculate station-to-stadium proximity using Haversine formula (`fct_station_proximity.sql`)
- Analyze game day vs non-game day demand patterns (`mart_game_day_demand.sql`)
- Provide rebalancing recommendations (`mart_game_rebalancing.sql`)

**Visualization:** New Streamlit page `Game_Impact.py` with rebalancing calculator (priority feature), demand comparison charts, and station maps.

**Orchestration:** Add game ingestion task to existing Airflow DAG (`bike_weather_dag.py`).

**Affected Systems:** dlt_pipeline, dbt, streamlit_app, airflow. No changes to existing pipelines or models.

---

## 2. Proposed Solution & Implementation Plan (The "How")

### Architecture Changes

No new services. Feature integrates into existing architecture:
- dlt pipeline → DuckDB `raw_games` schema
- dbt transforms → DuckDB `staging`, `core`, `marts` schemas
- Streamlit reads from `marts` tables
- Airflow orchestrates end-to-end flow

### Data Model / Database Changes

**New Tables:**

```sql
-- Raw layer (created by dlt)
raw_games.mlb_games
- game_id (PK, from API gamePk)
- game_date, game_datetime, official_date
- season, game_type, game_status
- home_team_id, home_team_name
- away_team_id, away_team_name
- venue_id, venue_name
- _dlt_load_timestamp, source_api

-- Staging (dbt view)
staging.stg_games
- game_id, game_date, game_time, game_datetime
- estimated_end_datetime (game_datetime + 3 hours)
- home_team_name, away_team_name, venue_name
- is_yankees_home, is_mets_home
- stadium_name (standardized)

-- Core dimensions/facts (dbt tables)
core.dim_stadiums
- stadium_id, stadium_name, address
- latitude, longitude (geocoded)
- city, state, geocoded_at

core.fct_station_proximity
- station_id (FK), stadium_id (FK)
- distance_km (Haversine calculation)
- within_1km (boolean flag)

-- Analytics marts (dbt tables)
marts.mart_game_day_demand
- game_date, game_id, stadium_name, station_id
- hour_offset (-3 to +3), game_hour
- trips_started/ended_game_day vs _baseline
- net_flow_game_day vs _baseline
- pct_change metrics

marts.mart_game_rebalancing
- stadium_name, station_id, station_name, hour_offset
- avg_trips_started/ended/net_flow
- bikes_to_add_or_remove (negative=add, positive=remove)
- rebalancing_recommendation (text)
- pct_capacity_adjustment
```

**No Changes to Existing Tables**

### API Contracts

**External API: MLB Stats API**

```
GET https://statsapi.mlb.com/api/v1/schedule

Query Parameters:
- sportId: 1 (MLB)
- teamId: 147 (Yankees) or 121 (Mets)
- startDate: YYYY-MM-DD
- endDate: YYYY-MM-DD
- hydrate: "team,venue"

Response (validated via testing):
{
  "dates": [{
    "date": "2024-05-03",
    "games": [{
      "gamePk": 747048,
      "gameDate": "2024-05-03T23:05:00Z",
      "teams": {
        "home": {"team": {"id": 147, "name": "New York Yankees"}},
        "away": {"team": {"id": 141, "name": "Houston Astros"}}
      },
      "venue": {"id": 3313, "name": "Yankee Stadium"},
      "status": {"detailedState": "Final"}
    }]
  }]
}

Home Game Filtering: Only include games where teams.home.team.id in [147, 121]
Expected Volume: ~55 games for May-June 2024 (25 Yankees + 30 Mets)
```

### Component Breakdown

**1. dlt Pipeline: `dlt_pipeline/games.py`**

Pattern: Follows `holidays.py` structure exactly
- `@dlt.resource` with merge disposition, primary_key="game_id"
- `mlb_games(start_date, end_date, team_ids=[147, 121])` generator function
- Retry logic: 3 attempts with exponential backoff [1s, 2s, 4s]
- Loops through team_ids, fetches schedule, filters home games
- `run_game_pipeline()` wrapper function
- Default date range: 2024-05-01 to 2024-06-30

**2. dbt Staging: `dbt/models/staging/stg_games.sql`**

Pattern: Follows `stg_holidays.sql` structure
- Materialized as view
- Type casting (date, timestamp, time)
- Derived fields: estimated_end_datetime, is_yankees_home, is_mets_home
- Standardized stadium_name

**3. dbt Core: `dbt/models/core/dim_stadiums.sql`**

Pattern: Static dimension table
- Hardcoded 2 rows (Yankee Stadium, Citi Field)
- Geocoded coordinates (tested with geopy):
  - Yankee Stadium: 40.8296, -73.9265
  - Citi Field: 40.7573, -73.8459
- Materialized as table

**4. dbt Core: `dbt/models/core/fct_station_proximity.sql`**

Pattern: Cartesian join with distance calculation
- Cross join dim_stations × dim_stadiums
- Haversine formula in SQL for great circle distance
- Filter: within_1km flag for 1.0 km radius
- Materialized as table

**5. dbt Mart: `dbt/models/marts/mart_game_day_demand.sql`**

Pattern: Follows `mart_holiday_impact_by_station.sql` exactly
- Game day metrics: JOIN games + nearby_stations + bike_trips on game_date
- Baseline metrics: Same day of week, non-game days, excluding holidays
- 6-hour window: -3h to +3h from game start (hourly granularity)
- Calculates: trips_started/ended, net_flow, pct_change
- Materialized as table

**6. dbt Mart: `dbt/models/marts/mart_game_rebalancing.sql`**

Pattern: Aggregates hourly averages + rebalancing logic
- GROUP BY stadium, station, hour_offset
- avg(net_flow): negative = bikes depleting (ADD), positive = accumulating (REMOVE)
- Threshold: >10 trips net flow triggers recommendation
- Output: bikes_to_add_or_remove, rebalancing_recommendation text
- Materialized as table

**7. Streamlit: `streamlit_app/pages/Game_Impact.py`**

Pattern: Follows existing page structure
- Sidebar filters: stadium, upcoming game, hour_offset slider
- Tab 1: Rebalancing Calculator (dataframe with recommendations)
- Tab 2: Demand Analysis (Plotly line chart game vs baseline)
- Tab 3: Station Map (Plotly mapbox scatter)
- DuckDB connection: `@st.cache_resource`

**8. Airflow: Update `airflow/dags/bike_weather_dag.py`**

Changes:
- Add import: `from dlt_pipeline.games import run_game_pipeline`
- Add @task: `ingest_game_data()`
- Update dependencies: `[ingest_bike, ingest_weather, ingest_games] >> ...`

### Logic / Algorithm

**Haversine Distance Formula (DuckDB SQL):**

```sql
distance_km = 6371 * 2 * asin(sqrt(
    pow(sin((radians(stadium_lat) - radians(station_lat)) / 2), 2) +
    cos(radians(station_lat)) * cos(radians(stadium_lat)) *
    pow(sin((radians(stadium_lon) - radians(station_lon)) / 2), 2)
))
```

**Baseline Calculation:**
- For each game, find all days where:
  - Same day of week (e.g., Tuesday game → all Tuesdays)
  - NOT a game day
  - NOT a holiday
  - Within analysis period (May-June 2024)
- Average demand across these baseline days

**Rebalancing Logic:**
```
net_flow = trips_ended - trips_started
if net_flow < -10:  # Bikes depleting
    recommendation = "Add X bikes"
elif net_flow > 10:  # Bikes accumulating
    recommendation = "Remove X bikes"
else:
    recommendation = "No action needed"
```

---

## 3. Impact and Risk Analysis

### System Dependencies

**Dependencies (Existing Systems):**
- `dim_stations`: Provides station lat/lon for proximity calculation
- `stg_bike_trips`: Source for demand metrics
- `stg_holidays`: Used to exclude holidays from baseline
- DuckDB warehouse: All transformed data storage
- Airflow: Orchestration framework

**Impacts (New to Existing):**
- None. New models do not modify existing tables or pipelines.
- Airflow DAG adds one parallel task (no blocking dependencies).

### Potential Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **MLB API Unavailable** | Pipeline fails, no game data | - Retry logic (3 attempts, exponential backoff)<br>- API is official MLB, historically reliable<br>- Non-blocking: other pipelines continue |
| **API Schema Changes** | Parsing errors | - Defensive field access (`.get()`)<br>- Comprehensive logging<br>- dbt tests catch schema issues early |
| **No Games in Date Range** | Empty marts | - Expected behavior<br>- Dashboard shows "No upcoming games" message<br>- Not a failure condition |
| **Incorrect Stadium Coordinates** | Wrong stations identified | - Coordinates tested manually with geopy<br>- Spot-check validation: known stations near stadiums |
| **Haversine Distance Inaccuracy** | Stations included/excluded incorrectly | - Haversine accurate for <100km distances<br>- 1km radius is conservative (allows margin of error) |
| **Baseline Calculation Bias** | Inaccurate recommendations | - Excludes holidays and game days for clean comparison<br>- Same day-of-week controls for weekly patterns<br>- Historical averages smooth outliers |
| **DuckDB Query Performance** | Slow dashboard | - Marts materialized as tables (pre-computed)<br>- Limited to stadium-adjacent stations (small dataset)<br>- Add indexes if needed (future optimization) |
| **dbt Model Failures** | Broken analytics | - Schema tests on all models<br>- Expression tests on numeric ranges<br>- Comprehensive logging |

---

## 4. Testing Strategy

### dbt Tests (Primary Quality Gate)

Per functional spec, dbt tests provide sufficient coverage for Phase 1.

**Schema Tests:**

```yaml
# stg_games
- game_id: unique, not_null
- game_date: not_null
- stadium_name: not_null, accepted_values(['Yankee Stadium', 'Citi Field'])

# dim_stadiums
- stadium_id: unique, not_null
- latitude: not_null
- longitude: not_null

# fct_station_proximity
- distance_km: not_null, expression_is_true(">= 0")
- within_1km: not_null, accepted_values([true, false])

# mart_game_day_demand
- trips_started_game_day: expression_is_true(">= 0")
- trips_ended_game_day: expression_is_true(">= 0")

# mart_game_rebalancing
- bikes_to_add_or_remove: not_null
- rebalancing_recommendation: not_null
```

### Integration Testing

**Step 1: dlt Pipeline Validation**
```bash
# Run pipeline manually
uv run python dlt_pipeline/games.py

# Verify results
uv run python -c "
import duckdb
conn = duckdb.connect('duckdb/warehouse.duckdb')
count = conn.execute('SELECT COUNT(*) FROM raw_games.mlb_games').fetchone()[0]
print(f'Games loaded: {count}')  # Expected: 55+ for May-June 2024
"

# Test idempotency
uv run python dlt_pipeline/games.py  # Rerun
# Verify count unchanged (no duplicates)
```

**Step 2: dbt Model Validation**
```bash
cd dbt

# Build all models
uv run dbt build

# Verify key tables
uv run dbt show --select dim_stadiums  # Should show 2 rows
uv run dbt show --select fct_station_proximity --limit 10

# Run tests
uv run dbt test

cd ..
```

**Step 3: Streamlit Dashboard Validation**
```bash
uv run streamlit run streamlit_app/pages/Game_Impact.py

# Manual checks:
# - Select Yankee Stadium, any upcoming game
# - Set hour offset to -1 (1 hour before game)
# - Verify rebalancing calculator shows recommendations
# - Check demand chart displays game vs baseline
# - Confirm station map shows markers
```

**Step 4: Airflow DAG Validation**
```bash
# Test DAG syntax
uv run airflow dags test bike_weather_pipeline

# Trigger manual run
uv run airflow dags trigger bike_weather_pipeline

# Monitor in Airflow UI (localhost:8080)
```

### Spot-Check Validation

**Data Quality Checks:**
- [ ] Known game appears: Yankees vs Red Sox on 2024-05-09
- [ ] Yankee Stadium coordinates: 40.8296, -73.9265
- [ ] Citi Field coordinates: 40.7573, -73.8459
- [ ] At least 10 stations within 1km of each stadium
- [ ] Rebalancing recommendations align with intuition:
  - Pre-game: expect bikes to deplete (fans leaving work, going to game)
  - Post-game: expect bikes to accumulate (fans biking from game)

**Manual Test Scenarios:**

| Scenario | Expected Result |
|----------|----------------|
| Select Yankees game 2 hours before start | Recommendations to ADD bikes (outbound demand) |
| Select Mets game 1 hour after end | Recommendations to REMOVE bikes (inbound demand) |
| Compare weekday vs weekend game | Different baseline comparisons |
| Select game on holiday | Baseline excludes that holiday |

### End-to-End Test

**Full Pipeline Run:**
```bash
# 1. Ingest data
uv run python dlt_pipeline/games.py

# 2. Transform
cd dbt && uv run dbt build && cd ..

# 3. Verify dashboard
uv run streamlit run streamlit_app/pages/Game_Impact.py

# 4. Check all acceptance criteria from functional spec
```

---

## Notes

- **H3 Hexagon Grouping:** Deferred to Phase 2 (optional). Phase 1 uses individual stations.
- **Great Expectations:** Not required per functional spec. dbt tests provide sufficient coverage.
- **Unit Tests:** Not required per functional spec. Integration tests sufficient for Phase 1.
- **Geocoding:** Hardcoded coordinates (tested with geopy). No runtime geocoding to avoid rate limits.
- **Game Duration:** Fixed 3-hour assumption. No special handling for extra innings/delays in Phase 1.
