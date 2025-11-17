# Technical Specification: Large Event API Connection

- **Functional Specification:** `context/spec/003-large-event-api-connection/functional-spec.md`
- **Status:** Draft
- **Author(s):** Engineering Team

---

## 1. High-Level Technical Approach

Create a new dlt pipeline (`dlt_pipeline/events.py`) following established patterns from existing bike and weather pipelines. The pipeline will fetch NYC event data from the NYC Parks Public Events API (free, no authentication) for a specified date range and load it into `duckdb/warehouse.duckdb` in the `raw_events` schema using merge write disposition with a composite primary key (`event_id`). A dbt staging model (`stg_events.sql`) will geocode venue addresses using Nominatim, filter events within 2km of Citi Bike stations using Haversine distance formula, and add placeholder category fields for future enrichment.

**Affected Systems:** dlt pipeline (new file), DuckDB warehouse (new schema), dbt staging layer (new model), dependencies (add geopy library).

**Note on Phase 1 Limitations:** This implementation loads all events with NULL values for attendance/capacity fields and placeholder categories. Future phases will add: (1) geocoding cache to reduce API calls, (2) retry/timeout logic for geocoding failures, (3) event participant estimation, (4) category classification.

---

## 2. Proposed Solution & Implementation Plan (The "How")

### Data Ingestion Layer (dlt Pipeline)

**New File:** `dlt_pipeline/events.py`

**Resource Function:**
```python
@dlt.resource(
    name="nyc_events",
    write_disposition="merge",
    primary_key="event_id",
    table_name="nyc_events",
)
def nyc_events(
    start_date: str,
    end_date: str,
    api_sources: list[str] = ["nyc_parks"]
) -> Iterator[dict[str, Any]]:
```

**Key Implementation Details:**

- **Input Parameters:**
  - `start_date: str` - Start date in YYYY-MM-DD format (e.g., "2024-05-01")
  - `end_date: str` - End date in YYYY-MM-DD format (e.g., "2024-06-30")
  - `api_sources: list[str]` - List of API sources to fetch from (default: `["nyc_parks"]`, extensible for future APIs)

- **API Endpoint (NYC Parks):**
  - Base URL: `https://data.cityofnewyork.us/resource/w3wp-dpdi.json`
  - Query approach: Use SODA API with query parameters or alternative NYC Open Data endpoint
  - Filter: Events between start_date and end_date
  - Pagination: Use `$limit` and `$offset` if dataset is large

- **HTTP Configuration:**
  - 30-second timeout
  - No retry logic for API failures (per functional spec - fail immediately if API is down)
  - Error handling:
    - If API returns 0 events: Log warning "No events found for date range", pipeline succeeds
    - If API is down or unreachable: Raise exception, pipeline fails with clear error message

- **Data Yielding:**
  - Fetch all events for date range from API
  - Transform each event to standardized dict format
  - Generate unique `event_id` as `md5(event_name + event_date + venue_name)` for primary key
  - Yield one record at a time

- **Field Capture & Mapping:**
  - `event_name` (required) - Map from API field "eventname", "title", or "name"
  - `event_date` (required) - Map from API field "eventdate", "date", or "start_date"
  - `event_time` (optional) - Map from API field "eventtime", "time", or "start_time"
  - `venue_name` (required) - Map from API field "venue", "location", or "location_name"
  - `venue_address` (required) - Map from API field "address", "location_address", or "full_address"
  - `event_description` (optional) - Map from API field "description" or "details"
  - `event_category` (optional) - Map from API field "category" or set to NULL (placeholder for future enrichment)
  - `expected_attendance` (optional) - Set to NULL for Phase 1 (no data available)
  - `venue_capacity` (optional) - Set to NULL for Phase 1 (no data available)
  - `latitude` (optional) - Set to NULL in raw (will be geocoded in dbt)
  - `longitude` (optional) - Set to NULL in raw (will be geocoded in dbt)

- **Data Quality Rules:**
  - **If event_date is missing:** Log "Event '{event_name}' ignored: missing date" and skip (do not yield)
  - **If venue_name AND venue_address are both missing:** Log "Event '{event_name}' ignored: missing location" and skip (do not yield)
  - **Track ignored events:** Maintain counters: `missing_date_count`, `missing_location_count`

- **Metadata Fields:**
  - `_dlt_load_timestamp` - Current timestamp (datetime.now())
  - `api_source` - Source identifier string (e.g., "nyc_parks")
  - `event_id` - Generated hash for primary key (VARCHAR)

- **Summary Logging:**
  - After processing all events, log:
    ```
    "Events pipeline summary: Fetched {total_fetched} events from API,
    Ignored {total_ignored} events ({missing_date} missing date, {missing_location} missing location),
    Loaded {total_loaded} events successfully"
    ```

**Runner Function:**
```python
def run_events_pipeline(
    start_date: str,
    end_date: str,
    api_sources: list[str] = ["nyc_parks"],
    destination: str = "duckdb",
    dataset_name: str = "raw_events",
) -> dict[str, Any]:
```

**Pipeline Configuration:**
- **Pipeline Name:** `events_ingestion`
- **Destination:** `duckdb` with credentials pointing to `../duckdb/warehouse.duckdb` (relative from dlt_pipeline directory)
- **Dataset Name:** `raw_events` (creates schema in DuckDB)
- **DLT Project Directory:** Set `os.environ["DLT_PROJECT_DIR"] = str(Path(__file__).parent)` to find `.dlt/` config

**Example Usage (in main block):**
```python
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Ingest events for May-June 2024 (matching bike data period)
    result = run_events_pipeline(
        start_date="2024-05-01",
        end_date="2024-06-30"
    )
    logger.info("Events ingestion complete. Result: %s", result)
```

---

### Data Model / Database Changes

**New Schema:** `raw_events`

**New Table:** `nyc_events`

**Columns:**
| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| `event_id` | VARCHAR | PRIMARY KEY, NOT NULL | MD5 hash of event_name + event_date + venue_name |
| `event_name` | VARCHAR | NOT NULL | Event title/name from API |
| `event_date` | DATE | NOT NULL | Event date (YYYY-MM-DD format) |
| `event_time` | TIME | NULLABLE | Event start time (HH:MM:SS format) |
| `venue_name` | VARCHAR | NOT NULL | Venue/location name |
| `venue_address` | VARCHAR | NOT NULL | Full venue address string |
| `event_description` | TEXT | NULLABLE | Event description/details |
| `event_category` | VARCHAR | NULLABLE | Event category (NULL for Phase 1) |
| `expected_attendance` | INTEGER | NULLABLE | Expected attendance count (NULL for Phase 1) |
| `venue_capacity` | INTEGER | NULLABLE | Venue capacity (NULL for Phase 1) |
| `latitude` | DOUBLE | NULLABLE | Geocoded latitude (NULL in raw, populated in dbt) |
| `longitude` | DOUBLE | NULLABLE | Geocoded longitude (NULL in raw, populated in dbt) |
| `_dlt_load_timestamp` | TIMESTAMP | NOT NULL | DLT ingestion timestamp |
| `api_source` | VARCHAR | NOT NULL | API source identifier (e.g., "nyc_parks") |

**Primary Key Strategy:** Composite key using MD5 hash ensures idempotency - re-running pipeline for same date range will update existing records via merge write disposition, not create duplicates.

---

### dbt Transformation Layer

**New File:** `dbt/models/staging/stg_events.sql`

**Transformation Logic:**

1. **Select from raw table:**
   ```sql
   with raw_events as (
       select * from {{ source('raw_events', 'nyc_events') }}
   )
   ```

2. **Geocode venue addresses:**
   - **Implementation:** Use dbt Python model with `geopy` library and Nominatim geocoder
   - **Geocoding logic:**
     ```python
     from geopy.geocoders import Nominatim
     from geopy.exc import GeocoderTimedOut, GeocoderServiceError
     import time

     geolocator = Nominatim(user_agent="citibike_demand_analytics")

     def geocode_address(address):
         try:
             time.sleep(1)  # Respect Nominatim rate limit (1 req/sec)
             location = geolocator.geocode(address, timeout=5)
             if location:
                 return location.latitude, location.longitude
             else:
                 return None, None
         except (GeocoderTimedOut, GeocoderServiceError):
             return None, None
     ```
   - **Add columns:** `latitude_geocoded`, `longitude_geocoded`
   - **Log failures:** Track events where geocoding returned NULL

3. **Filter by station proximity (2km using Haversine distance):**
   ```sql
   with events_with_distances as (
       select
           e.*,
           s.station_id,
           s.station_name,
           -- Haversine distance formula in km
           2 * 6371 * asin(
               sqrt(
                   pow(sin(radians(e.latitude_geocoded - s.latitude) / 2), 2) +
                   cos(radians(s.latitude)) *
                   cos(radians(e.latitude_geocoded)) *
                   pow(sin(radians(e.longitude_geocoded - s.longitude) / 2), 2)
               )
           ) as distance_km
       from geocoded_events e
       cross join {{ ref('dim_stations') }} s
       where e.latitude_geocoded is not null
         and e.longitude_geocoded is not null
   ),

   nearest_stations as (
       select
           event_id,
           min(distance_km) as min_distance_km,
           first(station_id) as nearest_station_id,
           first(station_name) as nearest_station_name
       from events_with_distances
       group by event_id
       having min(distance_km) <= 2.0  -- 2km threshold (configurable)
   )
   ```

4. **Add derived fields:**
   - `is_large_event` (BOOLEAN) - NULL for Phase 1 (to be estimated in future)
   - `event_size_class` (VARCHAR) - NULL for Phase 1 (Small/Medium/Large classification in future)
   - `is_within_bike_network` (BOOLEAN) - TRUE if within 2km, FALSE otherwise

5. **Final select with all fields:**
   ```sql
   select
       e.event_id,
       e.event_name,
       e.event_date,
       e.event_time,
       e.venue_name,
       e.venue_address,
       e.event_description,
       e.event_category,
       e.expected_attendance,
       e.venue_capacity,
       e.latitude_geocoded as latitude,
       e.longitude_geocoded as longitude,
       n.nearest_station_id,
       n.nearest_station_name,
       n.min_distance_km as distance_to_nearest_station,
       null as is_large_event,  -- Placeholder for Phase 2
       null as event_size_class,  -- Placeholder for Phase 2
       e._dlt_load_timestamp,
       e.api_source
   from geocoded_events e
   inner join nearest_stations n on e.event_id = n.event_id
   where n.min_distance_km <= 2.0
   ```

**Materialization:** `{{ config(materialized='view') }}`

**Configuration:**
```sql
{{
    config(
        materialized='view',
        tags=['staging', 'events']
    )
}}
```

---

**Update File:** `dbt/models/staging/schema.yml`

Add source definition:
```yaml
sources:
  - name: raw_events
    schema: raw_events
    description: "Raw event data from external APIs"
    tables:
      - name: nyc_events
        description: "NYC public events ingested from NYC Parks API and other sources"
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
            description: "Event title/name"
            tests:
              - not_null
          - name: venue_name
            description: "Venue name"
            tests:
              - not_null
          - name: venue_address
            description: "Venue address"
            tests:
              - not_null
```

Add staging model tests:
```yaml
models:
  - name: stg_events
    description: "Cleaned and geocoded events within 2km of Citi Bike stations"
    columns:
      - name: event_id
        description: "Unique event identifier"
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
        description: "Geocoded latitude coordinate"
        tests:
          - not_null
      - name: longitude
        description: "Geocoded longitude coordinate"
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
        description: "Distance in km to nearest station"
        tests:
          - not_null
      - name: api_source
        description: "Source API identifier"
        tests:
          - accepted_values:
              values: ['nyc_parks']
```

---

### Dependencies

**New Python Dependency:** Add to `pyproject.toml`:
```toml
dependencies = [
    # ... existing dependencies ...
    "geopy>=2.4.0",  # Geocoding library for address → lat/lon conversion
]
```

After adding, run: `uv sync` to install geopy

---

## 3. Impact and Risk Analysis

### System Dependencies

- **dlt framework** - Already in use for bike, weather, and holiday pipelines; no breaking changes
- **DuckDB warehouse** - `duckdb/warehouse.duckdb` must be accessible with write permissions; new `raw_events` schema will be created
- **geopy library** - New dependency for geocoding; must be added to `pyproject.toml`
- **Nominatim API (OpenStreetMap)** - Free geocoding service; rate limit: 1 request/second
- **dim_stations table** - Required for proximity filtering in dbt; must exist and have lat/lon coordinates
- **dbt models** - Downstream models can reference `{{ ref('stg_events') }}` for event analysis
- **No impact on existing pipelines** - Independent data source; no changes to bike/weather/holiday pipelines

### Potential Risks & Mitigations

1. **NYC Parks API Structure Uncertainty**
   - **Risk:** API endpoint or field names may differ from assumptions (403 error encountered during testing); actual field structure unknown until implementation
   - **Mitigation:**
     - Test API connection as first implementation step
     - Build flexible field mapper to handle varying field names (e.g., try "eventname" then "title" then "name")
     - Document actual API field mappings in code comments
     - Add comprehensive error logging for unexpected field structures

2. **Geocoding Rate Limits (Nominatim: 1 req/sec)**
   - **Risk:** Large event datasets (100+ events) will slow down dbt transformations; 100 events = 100 seconds minimum
   - **Mitigation:**
     - Add 1-second sleep delay between geocoding requests in Python model
     - Document limitation in code: "Geocoding limited to 1 request/sec per Nominatim usage policy"
     - **Future enhancement:** Create `geocoded_venues` cache table (venue_address → lat/lon) to avoid redundant API calls for recurring venues
     - Consider batch geocoding or alternative geocoding service if performance becomes critical

3. **Geocoding Failures**
   - **Risk:** Some venue addresses may not geocode successfully (invalid/ambiguous addresses, API timeouts, service unavailable)
   - **Mitigation:**
     - Set 5-second timeout per geocoding request
     - If geocoding fails or times out, set lat/lon to NULL
     - Log all failed geocoding attempts with event_id and address
     - Events with NULL coordinates are excluded by `where latitude is not null` filter in staging model
     - Track geocoding success rate in dbt test (target: >80% success rate)

4. **Station Proximity Calculation Performance**
   - **Risk:** Haversine distance calculation for ~2,000 stations × N events may be slow in SQL (CROSS JOIN creates 2,000N rows)
   - **Mitigation:**
     - Leverage DuckDB's efficient vectorized math functions
     - Optimize query: Filter stations to bounding box before Haversine calculation (reduce CROSS JOIN size)
     - Example: `where s.latitude between e.lat - 0.02 and e.lat + 0.02` (roughly ±2km)
     - If performance is still poor, consider creating spatial index or pre-computing station proximity grid

5. **Missing Attendance/Capacity Data**
   - **Risk:** All events will have NULL for `expected_attendance` and `venue_capacity` fields; cannot filter for 5,000+ participant threshold
   - **Mitigation:**
     - Accept as Phase 1 limitation
     - Document in code comments: "PHASE 1: Attendance/capacity data not available from NYC Parks API"
     - Defer estimation to separate roadmap item: "Event Participant Estimation"
     - Load all events; future feature will estimate attendance based on venue capacity or historical data

6. **Event Category Ambiguity**
   - **Risk:** NYC Parks API may not provide granular categories (concert vs sports vs parade); unable to filter by event type
   - **Mitigation:**
     - Accept all events from API
     - Set `event_category` to API-provided value or NULL (placeholder)
     - Document: "PHASE 1: Category classification not implemented"
     - Defer classification to future feature using ML or keyword matching on event names/descriptions

7. **API Date Range Limitations**
   - **Risk:** NYC Parks "Upcoming 14 Days" dataset may only provide future events (not historical); may have pagination limits
   - **Mitigation:**
     - Test actual API capabilities during implementation
     - If limited to 14 days, chunk date range into 14-day periods
     - Use pagination parameters (`$limit` and `$offset`) if available
     - Log warning if date range exceeds API capabilities

8. **No Capacity-Based Filtering in Phase 1**
   - **Risk:** Functional spec requires 5,000+ participant events, but this cannot be implemented without attendance data
   - **Mitigation:**
     - Document as known limitation: "Capacity-based filtering deferred to 'Event Classification System' roadmap item"
     - Accept all events in Phase 1
     - Future feature will estimate attendance and add size classification (Small/Medium/Large)

9. **Database Lock Issues (DuckDB Concurrency)**
   - **Risk:** DuckDB doesn't support concurrent writes; pipeline may fail if dbt is running simultaneously
   - **Mitigation:**
     - Airflow DAG ensures sequential execution: ingest → dbt
     - SequentialExecutor prevents parallel tasks
     - No manual intervention required; workflow orchestration handles locking

10. **Geocoding Cache Not Implemented (Phase 1)**
    - **Risk:** Re-running pipeline for overlapping date ranges will re-geocode same venues redundantly
    - **Mitigation:**
      - Accept as Phase 1 limitation for simplicity
      - Document future enhancement: "Create geocoded_venues table to cache address → lat/lon mappings"
      - Nominatim rate limit (1 req/sec) makes this tolerable for small datasets (<100 events)

---

## 4. Testing Strategy

### Unit Tests (`tests/test_events_pipeline.py`)

**Test Coverage:**

1. **Mock API Response:**
   - Use `pytest-mock` to mock NYC Parks API response with sample event JSON data
   - Mock successful API call returning 10 sample events

2. **Test Successful Ingestion:**
   - Test pipeline with date range (2024-05-01 to 2024-05-31)
   - Verify 10 events are yielded with correct field mappings

3. **Test Event ID Generation:**
   - Verify `event_id` hash is consistent for same event_name + event_date + venue_name
   - Verify different events produce different event_ids

4. **Test Data Quality Rules:**
   - **Missing date:** Mock event with NULL event_date, verify it's ignored and logged
   - **Missing location:** Mock event with NULL venue_name and NULL venue_address, verify it's ignored and logged
   - **Valid event:** Mock event with all required fields, verify it's yielded

5. **Test Summary Logging:**
   - Verify log message format: "Fetched X events, ignored Y events (missing_date: A, missing_location: B), loaded Z events"
   - Check counters are accurate

6. **Test API Failure:**
   - Mock persistent API error (connection timeout)
   - Verify pipeline raises exception with clear error message

7. **Test Zero Events:**
   - Mock API response with empty array `[]`
   - Verify pipeline succeeds with warning: "No events found for date range"

8. **Test Metadata Fields:**
   - Verify `_dlt_load_timestamp` is populated with current timestamp
   - Verify `api_source` is set to "nyc_parks"

### Integration Tests

**End-to-End Validation:**

1. **Run Pipeline with Real API:**
   - Execute: `uv run python dlt_pipeline/events.py` for date range 2024-05-01 to 2024-05-31
   - (If 403 error persists, use mock data for testing)

2. **Verify Data Landing:**
   - Query DuckDB: `SELECT COUNT(*) FROM raw_events.nyc_events`
   - Verify at least 5 events loaded (success criteria from functional spec)

3. **Verify Schema:**
   - Query: `DESCRIBE raw_events.nyc_events`
   - Confirm all expected columns exist with correct data types

4. **Test Idempotency:**
   - Run pipeline again for same date range
   - Query: `SELECT COUNT(DISTINCT event_id) FROM raw_events.nyc_events`
   - Verify no duplicate event_ids (merge write disposition works correctly)

5. **Run dbt Staging Model:**
   - Execute: `cd dbt && uv run dbt run --select stg_events`
   - Verify model builds successfully

6. **Verify Geocoding:**
   - Query: `SELECT COUNT(*) FROM staging.stg_events WHERE latitude IS NOT NULL`
   - Calculate geocoding success rate: (geocoded_events / total_events) × 100
   - Target: >80% success rate

7. **Verify Station Proximity Filtering:**
   - Query: `SELECT MAX(distance_to_nearest_station) FROM staging.stg_events`
   - Verify max distance ≤ 2.0 km
   - Verify `nearest_station_id` is populated for all events

8. **Test dbt Tests:**
   - Execute: `cd dbt && uv run dbt test --select stg_events`
   - Verify all tests pass (unique, not_null, relationships, accepted_values)

9. **Test Ignored Events Logging:**
   - Manually insert raw event with missing event_date in DuckDB
   - Run dlt pipeline
   - Verify event is logged as ignored and not loaded

### dbt Tests (`dbt/models/staging/schema.yml`)

**Data Quality Tests:**

1. **Uniqueness:**
   - `unique` test on `event_id` in `stg_events` (catches duplicate events)

2. **Not Null Constraints:**
   - `not_null` tests on: `event_id`, `event_date`, `event_name`, `latitude`, `longitude`, `nearest_station_id`, `distance_to_nearest_station`

3. **Referential Integrity:**
   - `relationships` test: Verify `nearest_station_id` exists in `dim_stations.station_id`

4. **Accepted Values:**
   - `accepted_values` test on `api_source`: `['nyc_parks']` (expandable for future APIs like Eventbrite, Ticketmaster)

5. **Custom Tests:**
   - Create custom dbt test: `test_station_proximity_within_threshold.sql`
   - SQL: `SELECT * FROM {{ ref('stg_events') }} WHERE distance_to_nearest_station > 2.0`
   - Expected: 0 rows (all events should be ≤ 2km from nearest station)

### Geocoding Tests

**Validation:**

1. **Test geopy/Nominatim Integration:**
   - Unit test with sample NYC addresses (e.g., "Madison Square Garden, New York, NY")
   - Verify successful geocoding returns lat/lon within NYC bounds (40.5-41.0, -74.3 to -73.7)

2. **Test Timeout Handling:**
   - Mock `GeocoderTimedOut` exception
   - Verify function returns (None, None) and logs failure

3. **Test Invalid Address:**
   - Test with invalid/ambiguous address (e.g., "XYZ123 Fake Street")
   - Verify returns (None, None) without crashing

4. **Monitor Geocoding Success Rate:**
   - After integration test, query:
     ```sql
     SELECT
         COUNT(*) as total,
         SUM(CASE WHEN latitude IS NOT NULL THEN 1 ELSE 0 END) as geocoded,
         SUM(CASE WHEN latitude IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
     FROM staging.stg_events
     ```
   - Target: >80% success rate
   - If lower, investigate common failure patterns and improve address cleaning logic
