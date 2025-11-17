# Task List: Large Event API Connection

## Vertical Slices (Incremental, Runnable Tasks)

- [ ] **Slice 1: Setup dependencies and validate API connection**
  - [ ] Add `geopy>=2.4.0` to `pyproject.toml` dependencies array
  - [ ] Run `uv sync` to install geopy
  - [ ] Create test script `scripts/test_nyc_api.py` (temporary, will be deleted later)
  - [ ] Add imports: `requests`, `json`, `from datetime import datetime`
  - [ ] Test NYC Open Data Film Permits API: `https://data.cityofnewyork.us/resource/tg4x-b46p.json?$limit=5`
  - [ ] Print response status code and first event to verify connectivity
  - [ ] Test alternative NYC Parks events endpoint if Film Permits doesn't have suitable data
  - [ ] **Verification:** Run `uv run python scripts/test_nyc_api.py`, confirm 200 status code and JSON response with event data

- [ ] **Slice 2: Create minimal dlt events pipeline (hardcoded single event)**
  - [ ] Create file `dlt_pipeline/events.py`
  - [ ] Add module docstring: "DLT pipeline for NYC event data ingestion from public APIs"
  - [ ] Add imports: `import logging`, `import os`, `import time`, `from collections.abc import Iterator`, `from datetime import datetime`, `from pathlib import Path`, `from typing import Any`, `import dlt`, `import requests`, `import hashlib`
  - [ ] Set up logger: `logger = logging.getLogger(__name__)`
  - [ ] Set DLT project directory: `os.environ["DLT_PROJECT_DIR"] = str(Path(__file__).parent)`
  - [ ] Create `@dlt.resource` decorator with: `name="nyc_events"`, `write_disposition="merge"`, `primary_key="event_id"`, `table_name="nyc_events"`
  - [ ] Implement `nyc_events(start_date: str, end_date: str, api_sources: list[str] = ["nyc_open_data"]) -> Iterator[dict[str, Any]]:` function signature
  - [ ] Yield one hardcoded mock event dictionary with all required fields:
    - `event_id` = "test123"
    - `event_name` = "Test Event"
    - `event_date` = "2024-05-15"
    - `event_time` = "19:00:00"
    - `venue_name` = "Madison Square Garden"
    - `venue_address` = "4 Pennsylvania Plaza, New York, NY 10001"
    - `event_description` = "Test event for pipeline validation"
    - `event_category` = NULL
    - `expected_attendance` = NULL
    - `venue_capacity` = NULL
    - `latitude` = NULL
    - `longitude` = NULL
    - `_dlt_load_timestamp` = `datetime.now()`
    - `api_source` = "mock"
  - [ ] Implement `run_events_pipeline(start_date: str, end_date: str, api_sources: list[str] = ["nyc_open_data"], destination: str = "duckdb", dataset_name: str = "raw_events") -> dict[str, Any]:` function
  - [ ] Create pipeline: `dlt.pipeline(pipeline_name="events_ingestion", destination=destination, dataset_name=dataset_name)`
  - [ ] Run pipeline: `load_info = pipeline.run(nyc_events(start_date, end_date, api_sources))`
  - [ ] Add logging: `logger.info("Pipeline completed: %s", load_info)`
  - [ ] Return load_info
  - [ ] Add `if __name__ == "__main__":` block with logging config and example call: `run_events_pipeline("2024-05-01", "2024-05-31")`
  - [ ] **Verification:** Run `uv run python dlt_pipeline/events.py`, verify output shows "Pipeline completed", query DuckDB: `SELECT COUNT(*) FROM raw_events.nyc_events` returns 1 row

- [ ] **Slice 3: Fetch real events from NYC Open Data API**
  - [ ] Remove hardcoded mock event from `nyc_events()` function
  - [ ] Add function `def _generate_event_id(event_name: str, event_date: str, venue_name: str) -> str:` using `hashlib.md5((event_name + event_date + venue_name).encode()).hexdigest()`
  - [ ] Add function `def _map_api_fields(raw_event: dict, api_source: str) -> dict[str, Any]:` to handle flexible field mapping
  - [ ] Implement field mapping logic:
    - Try `event_name` from: raw_event.get("eventname") or raw_event.get("title") or raw_event.get("name")
    - Try `event_date` from: raw_event.get("eventdate") or raw_event.get("date") or raw_event.get("start_date") or raw_event.get("startdatetime", "")[:10]
    - Try `event_time` from: raw_event.get("eventtime") or raw_event.get("time") or raw_event.get("startdatetime", "")[11:19] or None
    - Try `venue_name` from: raw_event.get("venue") or raw_event.get("location") or raw_event.get("location_name") or raw_event.get("borough")
    - Try `venue_address` from: raw_event.get("address") or raw_event.get("location_address") or raw_event.get("full_address") or f"{venue_name}, New York, NY"
    - Try `event_description` from: raw_event.get("description") or raw_event.get("details") or raw_event.get("eventtype")
    - Try `event_category` from: raw_event.get("category") or raw_event.get("eventtype") or None
  - [ ] Return mapped dict with all fields including generated event_id, metadata fields, NULL placeholders for attendance/capacity/lat/lon
  - [ ] Update `nyc_events()` to fetch from real API:
    - URL: `https://data.cityofnewyork.us/resource/tg4x-b46p.json` (Film Permits) or suitable alternative
    - Query params: `?$limit=1000&$where=startdatetime between '{start_date}T00:00:00' and '{end_date}T23:59:59'` (adjust syntax based on API)
    - 30-second timeout
    - No retry logic (fail immediately on error)
  - [ ] Loop through API response, call `_map_api_fields()` for each event, yield transformed record
  - [ ] Add logging: `logger.info("Fetched %d events from %s API", len(data), api_source)`
  - [ ] Handle error cases:
    - If API is down: raise exception with clear message
    - If API returns empty list: log warning "No events found for date range", continue (don't fail)
  - [ ] **Verification:** Run `uv run python dlt_pipeline/events.py`, verify events are fetched and loaded, query DuckDB to see real event data with populated fields

- [ ] **Slice 4: Add data quality filtering in dlt pipeline**
  - [ ] Add counters at top of `nyc_events()`: `missing_date_count = 0`, `missing_location_count = 0`, `loaded_count = 0`, `total_fetched = 0`
  - [ ] Before yielding each record, implement quality checks:
    - Check if `event_date` is None or empty: if so, log `logger.warning("Event '%s' ignored: missing date", event_name)`, increment `missing_date_count`, continue (skip yield)
    - Check if both `venue_name` AND `venue_address` are None or empty: if so, log `logger.warning("Event '%s' ignored: missing location", event_name)`, increment `missing_location_count`, continue (skip yield)
    - If both checks pass, increment `loaded_count` and yield record
  - [ ] After loop completes, calculate `total_ignored = missing_date_count + missing_location_count`
  - [ ] Add summary logging after API fetch:
    ```python
    logger.info(
        "Events pipeline summary: Fetched %d events from API, "
        "Ignored %d events (%d missing date, %d missing location), "
        "Loaded %d events successfully",
        total_fetched, total_ignored, missing_date_count, missing_location_count, loaded_count
    )
    ```
  - [ ] **Verification:** Run pipeline, verify summary log appears, manually test with mock event missing date - confirm it's logged and skipped

- [ ] **Slice 5: Create basic dbt staging model (no geocoding yet)**
  - [ ] Create file `dbt/models/staging/stg_events.sql`
  - [ ] Add config block: `{{ config(materialized='view') }}`
  - [ ] Add CTE `raw_events`: `select * from {{ source('raw_events', 'nyc_events') }}`
  - [ ] Add final SELECT with all raw fields plus placeholder columns:
    - All columns from raw_events
    - `null as latitude` (will be geocoded later)
    - `null as longitude` (will be geocoded later)
    - `null as nearest_station_id` (will be calculated later)
    - `null as nearest_station_name` (will be calculated later)
    - `null::double as distance_to_nearest_station` (will be calculated later)
    - `null::boolean as is_large_event` (Phase 2 placeholder)
    - `null::varchar as event_size_class` (Phase 2 placeholder)
  - [ ] Update or create `dbt/models/staging/sources.yml` (or schema.yml if combined)
  - [ ] Add source definition:
    ```yaml
    sources:
      - name: raw_events
        schema: raw_events
        description: "Raw event data from external APIs"
        tables:
          - name: nyc_events
            description: "NYC public events from multiple sources"
            columns:
              - name: event_id
                tests:
                  - unique
                  - not_null
              - name: event_date
                tests:
                  - not_null
              - name: event_name
                tests:
                  - not_null
              - name: venue_name
                tests:
                  - not_null
    ```
  - [ ] **Verification:** Run `cd dbt && uv run dbt run --select stg_events`, verify model builds successfully, query `SELECT COUNT(*) FROM main_staging.stg_events` matches raw table count

- [ ] **Slice 6: Add Python geocoding logic to dbt staging model**
  - [ ] Rename `dbt/models/staging/stg_events.sql` to `dbt/models/staging/stg_events.py`
  - [ ] Convert to dbt Python model using dbt.ref() pattern
  - [ ] Add imports: `from geopy.geocoders import Nominatim`, `from geopy.exc import GeocoderTimedOut, GeocoderServiceError`, `import time`, `import pandas as pd`
  - [ ] Define function `def model(dbt, session):`
  - [ ] Inside model function, add docstring explaining geocoding approach and rate limits
  - [ ] Initialize geocoder: `geolocator = Nominatim(user_agent="citibike_demand_analytics")`
  - [ ] Define geocoding function:
    ```python
    def geocode_address(address: str) -> tuple:
        if not address or pd.isna(address):
            return None, None
        try:
            time.sleep(1)  # Respect Nominatim 1 req/sec rate limit
            location = geolocator.geocode(address, timeout=5)
            if location:
                return location.latitude, location.longitude
            else:
                return None, None
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            # Log failure but don't crash
            return None, None
    ```
  - [ ] Load raw events: `df = dbt.ref("raw_events", "nyc_events").df()`
  - [ ] Apply geocoding: `df[['latitude', 'longitude']] = df['venue_address'].apply(lambda addr: pd.Series(geocode_address(addr)))`
  - [ ] Add placeholder columns (same as before for station proximity fields)
  - [ ] Add comment: `# NOTE: Geocoding limited to 1 request/sec per Nominatim usage policy. For N events, expect ~N seconds runtime.`
  - [ ] Return df
  - [ ] **Verification:** Run `cd dbt && uv run dbt run --select stg_events` (expect longer runtime), query `SELECT COUNT(*) as total, SUM(CASE WHEN latitude IS NOT NULL THEN 1 ELSE 0 END) as geocoded FROM main_staging.stg_events`, verify >80% geocoded successfully

- [ ] **Slice 7: Filter events by station proximity (2km)**
  - [ ] Update `stg_events.py` to include proximity filtering after geocoding
  - [ ] After geocoding step, load dim_stations: `stations_df = dbt.ref("dim_stations").df()`
  - [ ] Implement cross join and distance calculation:
    - Use pandas merge with `how='cross'` to create Cartesian product of events × stations
    - Calculate Haversine distance using numpy:
      ```python
      import numpy as np
      # Convert to radians
      lat1 = np.radians(merged_df['event_latitude'])
      lon1 = np.radians(merged_df['event_longitude'])
      lat2 = np.radians(merged_df['station_latitude'])
      lon2 = np.radians(merged_df['station_longitude'])
      # Haversine formula
      dlat = lat2 - lat1
      dlon = lon2 - lon1
      a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
      c = 2 * np.arcsin(np.sqrt(a))
      distance_km = 6371 * c  # Earth radius in km
      ```
  - [ ] Group by event_id, find minimum distance: `nearest = distances_df.loc[distances_df.groupby('event_id')['distance_km'].idxmin()]`
  - [ ] Filter: keep only events where `distance_km <= 2.0`
  - [ ] Add columns: `nearest_station_id`, `nearest_station_name`, `distance_to_nearest_station`
  - [ ] Join back to original events dataframe with nearest station info
  - [ ] **Verification:** Run `cd dbt && uv run dbt run --select stg_events`, query `SELECT MAX(distance_to_nearest_station) FROM main_staging.stg_events`, verify <= 2.0 km, verify nearest_station_id is populated

- [ ] **Slice 8: Add dbt tests for staging model**
  - [ ] Update or create `dbt/models/staging/schema.yml`
  - [ ] Add model tests for `stg_events`:
    ```yaml
    models:
      - name: stg_events
        description: "Cleaned and geocoded events within 2km of Citi Bike stations"
        columns:
          - name: event_id
            description: "Unique event identifier (MD5 hash)"
            tests:
              - unique
              - not_null
          - name: event_date
            description: "Event date"
            tests:
              - not_null
          - name: event_name
            description: "Event name"
            tests:
              - not_null
          - name: latitude
            description: "Geocoded latitude"
            tests:
              - not_null
          - name: longitude
            description: "Geocoded longitude"
            tests:
              - not_null
          - name: nearest_station_id
            description: "Nearest Citi Bike station within 2km"
            tests:
              - not_null
              - relationships:
                  to: ref('dim_stations')
                  field: station_id
          - name: distance_to_nearest_station
            description: "Distance to nearest station in km"
            tests:
              - not_null
          - name: api_source
            description: "Source API identifier"
            tests:
              - accepted_values:
                  values: ['nyc_open_data', 'mock']
    ```
  - [ ] **Verification:** Run `cd dbt && uv run dbt test --select stg_events`, verify all ~8 tests pass

- [ ] **Slice 9: Create unit tests for dlt pipeline**
  - [ ] Create file `tests/test_events_pipeline.py`
  - [ ] Add imports: `import pytest`, `from unittest.mock import Mock, patch`, `from dlt_pipeline.events import nyc_events, _generate_event_id, _map_api_fields, run_events_pipeline`
  - [ ] Test 1: `test_generate_event_id_consistency()` - Call with same inputs twice, assert equal IDs; call with different inputs, assert different IDs
  - [ ] Test 2: `test_map_api_fields_flexible_mapping()` - Create mock API responses with different field names, verify mapping works for all variants
  - [ ] Test 3: `test_nyc_events_successful_ingestion(mocker)` - Mock requests.get to return 5 sample events, iterate nyc_events(), assert 5 records yielded
  - [ ] Test 4: `test_nyc_events_missing_date_ignored(mocker, caplog)` - Mock API with event missing date, assert event not yielded, assert warning logged
  - [ ] Test 5: `test_nyc_events_missing_location_ignored(mocker, caplog)` - Mock API with event missing both venue_name and venue_address, assert event not yielded
  - [ ] Test 6: `test_nyc_events_summary_logging(mocker, caplog)` - Mock API with 10 events (2 invalid), assert summary log shows correct counts
  - [ ] Test 7: `test_nyc_events_api_failure(mocker)` - Mock requests.get to raise ConnectionError, assert pipeline raises exception
  - [ ] Test 8: `test_nyc_events_zero_events_warning(mocker, caplog)` - Mock API returning empty list, assert warning logged "No events found"
  - [ ] Test 9: `test_metadata_fields_populated()` - Mock API, verify yielded records have `_dlt_load_timestamp` and `api_source` populated
  - [ ] **Verification:** Run `uv run pytest tests/test_events_pipeline.py -v`, verify all 9 tests pass

- [ ] **Slice 10: Integration test and documentation**
  - [ ] Run full pipeline for May-June 2024: `uv run python dlt_pipeline/events.py` (update main block to use these dates)
  - [ ] Query DuckDB: `SELECT COUNT(*) FROM raw_events.nyc_events`, verify >= 5 events (success criteria)
  - [ ] Test idempotency: Run pipeline again for same date range
  - [ ] Query: `SELECT COUNT(*), COUNT(DISTINCT event_id) FROM raw_events.nyc_events`, verify counts are equal (no duplicates created)
  - [ ] Run dbt: `cd dbt && uv run dbt build --select stg_events`
  - [ ] Query geocoding success:
    ```sql
    SELECT
        COUNT(*) as total_events,
        SUM(CASE WHEN latitude IS NOT NULL THEN 1 ELSE 0 END) as geocoded_events,
        SUM(CASE WHEN latitude IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate_pct
    FROM main_staging.stg_events
    ```
  - [ ] Verify success_rate_pct > 80%
  - [ ] Query final filtered events: `SELECT event_name, venue_name, distance_to_nearest_station FROM main_staging.stg_events ORDER BY distance_to_nearest_station LIMIT 10`
  - [ ] Document findings in `context/spec/003-large-event-api-connection/technical-considerations.md`:
    - Add section "Implementation Notes" with actual API endpoint used
    - Document any field mapping challenges encountered
    - Record geocoding success rate achieved
    - Note any API limitations (rate limits, date ranges, etc.)
  - [ ] Update `README.md` if significant new functionality was added (optional for Phase 1)
  - [ ] **Verification:** Full pipeline runs end-to-end without errors, at least 5 events are geocoded and filtered by proximity

- [ ] **Slice 11: Performance optimization for station proximity (Optional)**
  - [ ] Update `stg_events.py` to add bounding box filter before Haversine calculation
  - [ ] Before cross join with all stations, filter stations using approximate 2km bounding box:
    ```python
    # Approximate: 1 degree latitude ≈ 111 km, so ±0.02 degrees ≈ ±2.2 km
    # Approximate: 1 degree longitude at NYC latitude ≈ 85 km, so ±0.024 degrees ≈ ±2 km
    lat_margin = 0.02
    lon_margin = 0.024

    # For each event, filter stations to bounding box
    filtered_stations = stations_df[
        (stations_df['latitude'] >= event_lat - lat_margin) &
        (stations_df['latitude'] <= event_lat + lat_margin) &
        (stations_df['longitude'] >= event_lon - lon_margin) &
        (stations_df['longitude'] <= event_lon + lon_margin)
    ]
    ```
  - [ ] This reduces computation from (N events × 2000 stations) to (N events × ~50 stations average)
  - [ ] Run performance comparison: Time dbt run before and after optimization using `time` command
  - [ ] **Verification:** Query execution time reduces by >50%, results remain identical (same events, same nearest stations, verified with query comparing old vs new results)

---

## Expected Timeline

- Slices 1-5: ~2-3 hours (setup and basic pipeline)
- Slice 6: ~1 hour + geocoding runtime (depends on event count, expect ~N seconds for N events)
- Slices 7-9: ~2-3 hours (proximity filtering and tests)
- Slice 10: ~1 hour (integration and docs)
- Slice 11 (optional): ~30 min

**Total:** ~7-10 hours for core functionality (Slices 1-10)

---

## Notes

- **API Flexibility:** Start with NYC Open Data Film Permits API, but be prepared to try alternative endpoints (NYC Parks events, etc.) if data quality is insufficient
- **Geocoding Performance:** Nominatim rate limit (1 req/sec) means 100 events will take ~100 seconds to geocode. This is acceptable for Phase 1 datasets.
- **Future Enhancements:** Geocoding cache, multiple API sources, event classification (size/category) are deferred to future specifications
- **Testing Philosophy:** Each slice should be independently testable and leave the application in a runnable state
