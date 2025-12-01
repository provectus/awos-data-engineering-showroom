# Task List: Baseball Match Impact Analysis

## Vertical Slices (Incremental, Runnable Tasks)

- [ ] **Slice 1: Create dlt pipeline that ingests MLB game data for Yankees and Mets**
  - [ ] Create `dlt_pipeline/games.py` file with module docstring explaining MLB game data ingestion
  - [ ] Add imports: `logging`, `os`, `Path`, `Iterator`, `Any`, `datetime`, `dlt`, `requests`
  - [ ] Set up logger and `DLT_PROJECT_DIR` environment variable (follow `holidays.py` pattern)
  - [ ] Create `mlb_games(start_date, end_date, team_ids=[147, 121])` function with `@dlt.resource` decorator
    - [ ] Set `write_disposition="merge"`, `primary_key="game_id"`, `table_name="mlb_games"`
  - [ ] Implement loop through `team_ids` list (Yankees=147, Mets=121):
    - [ ] URL: `https://statsapi.mlb.com/api/v1/schedule`
    - [ ] Params: `sportId=1`, `teamId=<team_id>`, `startDate`, `endDate`, `hydrate="team,venue"`
    - [ ] Parse response: iterate through `dates[].games[]`
    - [ ] Filter home games only: `home_team_id == team_id`
  - [ ] Yield complete records with all API fields:
    - [ ] `game_id` (from gamePk), `game_date`, `game_datetime`, `official_date`
    - [ ] `season`, `game_type`, `game_status`
    - [ ] `home_team_id`, `home_team_name`, `away_team_id`, `away_team_name`
    - [ ] `venue_id`, `venue_name`
    - [ ] `_dlt_load_timestamp`, `source_api="mlb_stats_api"`
  - [ ] Add logging: `logger.info(f"Fetched {home_games} home games for team {team_id}")`
  - [ ] Create `run_game_pipeline()` function with dlt.pipeline config (destination="duckdb", dataset_name="raw_games")
  - [ ] Add `if __name__ == "__main__"` block with default dates: May-June 2024
  - [ ] **Verification:** Run `uv run python dlt_pipeline/games.py`, verify 55 total games (25 Yankees + 30 Mets) loaded in `duckdb/warehouse.duckdb` at `raw_games.mlb_games`

- [ ] **Slice 2: Test idempotency and add to Airflow DAG with retry**
  - [ ] Test merge disposition: Run pipeline twice, verify no duplicate game_ids
  - [ ] Add import to `airflow/dags/bike_weather_dag.py`: `from dlt_pipeline.games import run_game_pipeline`
  - [ ] Add @task function `ingest_game_data()` calling `run_game_pipeline("2024-05-01", "2024-06-30")`
  - [ ] Task will use default Airflow retry settings from `default_args` (2 retries with 5 min delay)
  - [ ] Update DAG dependencies: `[ingest_bike, ingest_weather, ingest_games] >> [validate_bike, validate_weather] >> dbt_transform`
  - [ ] **Verification:** Run `uv run airflow dags test bike_weather_pipeline`, verify game ingestion task executes successfully

- [ ] **Slice 3: Create dbt staging model for games**
  - [ ] Create `dbt/models/staging/stg_games.sql` with `materialized='view'`
  - [ ] Add source definition in `dbt/models/staging/schema.yml` for `raw_games.mlb_games`
  - [ ] Select all fields from source, cast types:
    - [ ] `game_date::date`, `game_datetime::timestamp`, `game_datetime::time as game_time`
  - [ ] Add derived fields:
    - [ ] `estimated_end_datetime` = `game_datetime + interval '3 hours'`
    - [ ] `is_yankees_home` = `CASE WHEN home_team_id = 147 THEN true ELSE false END`
    - [ ] `is_mets_home` = `CASE WHEN home_team_id = 121 THEN true ELSE false END`
    - [ ] `stadium_name` = `CASE WHEN venue_name LIKE '%Yankee%' THEN 'Yankee Stadium' WHEN venue_name LIKE '%Citi Field%' THEN 'Citi Field' ELSE venue_name END`
  - [ ] **Verification:** Run `cd dbt && uv run dbt run --select stg_games`, query `staging.stg_games` to verify 55 rows with correct derived fields

- [ ] **Slice 4: Create stadium dimension with geocoded coordinates**
  - [ ] Create `dbt/models/core/dim_stadiums.sql` with `materialized='table'`
  - [ ] Hardcode 2 rows with tested coordinates:
    - [ ] Yankee Stadium: stadium_id=1, address='1 E 161st St, Bronx, NY 10451', lat=40.8296, lon=-73.9265, city='Bronx', state='NY'
    - [ ] Citi Field: stadium_id=2, address='41 Seaver Way, Queens, NY 11368', lat=40.7573, lon=-73.8459, city='Queens', state='NY'
  - [ ] Add `geocoded_at = current_timestamp`
  - [ ] **Verification:** Run `cd dbt && uv run dbt run --select dim_stadiums`, verify 2 rows with exact coordinates

- [ ] **Slice 5: Create station proximity fact table using Haversine formula**
  - [ ] Create `dbt/models/core/fct_station_proximity.sql` with `materialized='table'`
  - [ ] Cross join `dim_stadiums` × `main_core.dim_stations` (2,147 stations with coordinates)
  - [ ] Calculate distance using Haversine formula in SQL:
    ```sql
    6371 * 2 * asin(sqrt(
        pow(sin((radians(stadium_lat) - radians(station_lat)) / 2), 2) +
        cos(radians(station_lat)) * cos(radians(stadium_lat)) *
        pow(sin((radians(stadium_lon) - radians(station_lon)) / 2), 2)
    )) as distance_km
    ```
  - [ ] Add `within_1km` flag: `CASE WHEN distance_km <= 1.0 THEN true ELSE false END`
  - [ ] **Verification:** Run `uv run dbt run --select fct_station_proximity`, count stations within 1km of each stadium (expect 10-30 per stadium)

- [ ] **Slice 6: Add dbt schema tests for staging and core models**
  - [ ] Add tests in `dbt/models/staging/schema.yml` for `stg_games`:
    - [ ] `unique` and `not_null` on `game_id`
    - [ ] `not_null` on `game_date`, `stadium_name`
    - [ ] `accepted_values` on `stadium_name`: `['Yankee Stadium', 'Citi Field']`
  - [ ] Add tests in `dbt/models/core/schema.yml` for `dim_stadiums`:
    - [ ] `unique` and `not_null` on `stadium_id`
    - [ ] `not_null` on `latitude`, `longitude`
  - [ ] Add tests for `fct_station_proximity`:
    - [ ] `not_null` on `distance_km`
    - [ ] `dbt_utils.expression_is_true` on `distance_km >= 0`
    - [ ] `accepted_values` on `within_1km`: `[true, false]`
  - [ ] **Verification:** Run `cd dbt && uv run dbt test --select stg_games dim_stadiums fct_station_proximity`, all tests pass

- [ ] **Slice 7: Create game day demand mart comparing game days vs non-game days**
  - [ ] Create `dbt/models/marts/mart_game_day_demand.sql` with `materialized='table'`
  - [ ] Follow pattern from `mart_holiday_impact_by_station.sql`:
    - [ ] CTE `games`: Select from `stg_games` where game_date between '2024-05-01' and '2024-06-30'
    - [ ] CTE `nearby_stations`: Select from `fct_station_proximity` where `within_1km = true`
    - [ ] CTE `game_day_demand`: JOIN games + nearby_stations + `stg_bike_trips` on game_date
      - [ ] Filter trips to 6-hour window: `start_hour >= extract(hour from game_datetime) - 3 AND start_hour <= extract(hour from estimated_end_datetime) + 3`
      - [ ] Calculate `hour_offset` = `start_hour - extract(hour from game_datetime)`
      - [ ] GROUP BY game_id, stadium, station, hour; COUNT trips_started and trips_ended
    - [ ] CTE `baseline_demand`: Same day of week, non-game days, excluding holidays
      - [ ] `dayofweek(ride_date) = dayofweek(game_date)`
      - [ ] `ride_date NOT IN (SELECT game_date FROM games)`
      - [ ] `ride_date NOT IN (SELECT date FROM stg_holidays)`
      - [ ] AVG(trips_started), AVG(trips_ended) per hour
  - [ ] Final SELECT: JOIN game_day_demand + baseline_demand, calculate:
    - [ ] `net_flow_game_day` = trips_ended - trips_started
    - [ ] `net_flow_baseline` = avg_trips_ended - avg_trips_started
    - [ ] `trips_started_pct_change` = ((game_day - baseline) / baseline) * 100
    - [ ] `trips_ended_pct_change` = similar
  - [ ] **Verification:** Run `uv run dbt run --select mart_game_day_demand`, verify rows exist for each game × station × hour combination

- [ ] **Slice 8: Create rebalancing recommendations mart**
  - [ ] Create `dbt/models/marts/mart_game_rebalancing.sql` with `materialized='table'`
  - [ ] Aggregate `mart_game_day_demand` by stadium, station, hour_offset:
    - [ ] `avg(trips_started_game_day)`, `avg(trips_ended_game_day)`, `avg(net_flow_game_day)`
  - [ ] Add rebalancing logic:
    ```sql
    bikes_to_add_or_remove = CASE
        WHEN avg_net_flow < -10 THEN -1 * round(abs(avg_net_flow))  -- Add bikes
        WHEN avg_net_flow > 10 THEN round(avg_net_flow)             -- Remove bikes
        ELSE 0
    END
    ```
  - [ ] Add text recommendation:
    ```sql
    rebalancing_recommendation = CASE
        WHEN avg_net_flow < -10 THEN 'Add ' || round(abs(avg_net_flow)) || ' bikes'
        WHEN avg_net_flow > 10 THEN 'Remove ' || round(avg_net_flow) || ' bikes'
        ELSE 'No action needed'
    END
    ```
  - [ ] JOIN with `main_core.dim_stations` to get station names
  - [ ] **Verification:** Run `uv run dbt run --select mart_game_rebalancing`, query results to verify recommendations make sense (negative net_flow → add bikes, positive → remove bikes)

- [ ] **Slice 9: Add dbt tests for mart models**
  - [ ] Add tests in `dbt/models/marts/schema.yml` for `mart_game_day_demand`:
    - [ ] `not_null` on `game_id`, `station_id`, `hour_offset`
    - [ ] `dbt_utils.expression_is_true` on `trips_started_game_day >= 0`
    - [ ] `dbt_utils.expression_is_true` on `trips_ended_game_day >= 0`
  - [ ] Add tests for `mart_game_rebalancing`:
    - [ ] `not_null` on `bikes_to_add_or_remove`, `rebalancing_recommendation`
  - [ ] **Verification:** Run `cd dbt && uv run dbt test --select mart_game_day_demand mart_game_rebalancing`, all tests pass

- [ ] **Slice 10: Create Streamlit rebalancing calculator page (Priority Feature)**
  - [ ] Create `streamlit_app/pages/Game_Impact.py`
  - [ ] Set page config: `page_title="Baseball Game Impact"`, `page_icon="⚾"`, `layout="wide"`
  - [ ] Add DuckDB connection: `@st.cache_resource` with `duckdb.connect("duckdb/warehouse.duckdb", read_only=True)`
  - [ ] Sidebar filters:
    - [ ] Stadium selector: `st.selectbox("Select Stadium", ["Yankee Stadium", "Citi Field"])`
    - [ ] Upcoming games dropdown: Query `staging.stg_games WHERE stadium_name = {stadium} AND game_date >= current_date`
    - [ ] Hour offset slider: `st.slider("Hour Relative to Game Start", -3, 3, 0)`
  - [ ] Tab 1: **Rebalancing Calculator** (CRITICAL)
    - [ ] Query `marts.mart_game_rebalancing` filtered by stadium and hour_offset
    - [ ] Display dataframe with columns: station_name, bikes_to_add_or_remove, rebalancing_recommendation, avg_trips_started/ended
    - [ ] Sort by `abs(bikes_to_add_or_remove) DESC` to show highest priority stations first
  - [ ] **Verification:** Run `uv run streamlit run streamlit_app/pages/Game_Impact.py`, test rebalancing calculator with different games and hours, verify recommendations display correctly

- [ ] **Slice 11: Add demand comparison and station map visualizations**
  - [ ] Tab 2: **Demand Analysis**
    - [ ] Query `mart_game_day_demand` aggregated by hour_offset for selected stadium
    - [ ] Create Plotly line chart: X=hour_offset, Y=trip_count, two lines (game_day vs baseline)
    - [ ] Add markers for clarity
  - [ ] Tab 3: **Station Map**
    - [ ] Query `fct_station_proximity` JOIN `main_core.dim_stations` WHERE `stadium_name = {stadium} AND within_1km = true`
    - [ ] Create Plotly scatter_mapbox with station markers
    - [ ] Hover data: station_name, distance_km
  - [ ] **Verification:** Test all 3 tabs, verify charts render correctly, interact with filters

- [ ] **Slice 12: Integration test and end-to-end validation**
  - [ ] Run complete pipeline end-to-end:
    - [ ] `uv run python dlt_pipeline/games.py` → Verify 55 games loaded
    - [ ] `cd dbt && uv run dbt build && cd ..` → Verify all models build successfully
    - [ ] Check `dim_stadiums` has 2 rows
    - [ ] Check `fct_station_proximity` has stations within 1km of each stadium
    - [ ] Check `mart_game_day_demand` has demand data for all games
    - [ ] Check `mart_game_rebalancing` has actionable recommendations
  - [ ] Test Streamlit dashboard:
    - [ ] Select Yankee Stadium, game from May 2024, hour offset = -2
    - [ ] Verify rebalancing recommendations appear
    - [ ] Check demand chart shows game day spike vs baseline
    - [ ] Verify station map shows markers near Yankee Stadium
  - [ ] Spot-check data quality:
    - [ ] Known game: Yankees vs Red Sox on 2024-05-09 appears in data
    - [ ] Stadium coordinates match expected: Yankee Stadium (40.8296, -73.9265)
    - [ ] At least 10 stations within 1km of each stadium
  - [ ] **Verification:** All acceptance criteria from functional spec are met

- [ ] **Slice 13: Update documentation (using tasks.md as ground truth)**
  - [ ] Update `context/spec/003-baseball-match-impact-analysis/functional-spec.md`:
    - [ ] Remove Requirement 8 section about retry logic (handled by Airflow)
    - [ ] Verify all other requirements match implemented slices
  - [ ] Update `context/spec/003-baseball-match-impact-analysis/technical-considerations.md`:
    - [ ] Remove retry logic section from Component 2.3.1 (dlt pipeline)
    - [ ] Update Airflow section to mention default retry behavior (2 retries, 5 min delay)
    - [ ] Verify all component descriptions match implementation
  - [ ] Update `CLAUDE.md`:
    - [ ] Add game pipeline command: `uv run python dlt_pipeline/games.py`
    - [ ] Document date range parameters
    - [ ] Add dbt model descriptions for game-related models
  - [ ] Update `README.md`:
    - [ ] Add "Baseball Game Impact Analysis" section
    - [ ] Document MLB Stats API integration
    - [ ] Explain rebalancing calculator feature
    - [ ] Add example: "Predict demand spikes at Yankee Stadium before games"
  - [ ] Update `context/product/roadmap.md`:
    - [ ] Mark all "Baseball Match Impact Analysis" sub-items as complete:
      - [x] MLB Game Data Ingestion
      - [x] Stadium Proximity Analysis
      - [x] Game Day Demand Patterns
      - [x] Pre/Post Game Rush Analysis
      - [x] Game Impact Dashboard
  - [ ] **Verification:** Review all updated docs for consistency and accuracy

---

## Notes

- **Total Expected Data:** 55 games (25 Yankees + 30 Mets) for May-June 2024 period
- **Stadium Coordinates:** Tested with geopy, hardcoded for consistency
- **Existing Stations:** 2,147 stations with coordinates available in `main_core.dim_stations`
- **Haversine Accuracy:** Formula accurate for distances <100km, 1km radius is conservative
- **Schema Naming:** DuckDB uses `main_core`, `main_marts` prefixes (not just `core`, `marts`)
- **Retry Logic:** Handled by Airflow default_args (2 retries with 5 min delay), not in dlt pipeline
- **dbt Tests Only:** No Great Expectations or Python unit tests required per functional spec
- **Airflow Integration:** Runs in parallel with bike/weather ingestion, non-blocking
