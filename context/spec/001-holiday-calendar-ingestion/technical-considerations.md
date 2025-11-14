# Technical Specification: Holiday Calendar Ingestion

- **Functional Specification:** `context/spec/001-holiday-calendar-ingestion/functional-spec.md`
- **Status:** Draft
- **Author(s):** Engineering Team

---

## 1. High-Level Technical Approach

Create a new dlt pipeline (`dlt_pipeline/holidays.py`) following established patterns from existing bike and weather pipelines. The pipeline will fetch US holiday data from the Nager.Date API for specified years and load it into `duckdb/warehouse.duckdb` in the `raw_holidays` schema using merge write disposition with `date` as the primary key. A dbt staging model (`stg_holidays.sql`) will clean the data, add NYC-specific static holidays, deduplicate by date (prioritizing federal holidays), and derive major holiday and working day flags.

---

## 2. Proposed Solution & Implementation Plan

### Data Ingestion Layer (dlt Pipeline)

**New File:** `dlt_pipeline/holidays.py`

**Resource Function:**
```python
@dlt.resource(
    name="us_holidays",
    write_disposition="merge",
    primary_key="date",
    table_name="us_holidays",
)
def us_holidays(years: list[int]) -> Iterator[dict[str, Any]]:
```

**Key Implementation Details:**
- **Input Parameter:** `years: list[int]` - List of years to fetch (e.g., `[2024, 2025]`)
- **API Endpoint:** `https://date.nager.at/api/v3/PublicHolidays/{year}/US`
- **HTTP Configuration:** 30-second timeout, 3 retries with exponential backoff (1s, 2s, 4s)
- **Error Handling:** If any year fails after all retries, raise exception to fail entire pipeline (no skipping)
- **Data Yielding:** Fetch all holidays for a year, transform each to a dict, yield one record at a time
- **Field Capture:** All API fields (date, name, localName, countryCode, fixed, global, counties, launchYear, types)
- **Field Transformation:** Convert array fields (types, counties) to comma-separated strings for storage
- **Metadata:** Add `_dlt_load_timestamp` (current timestamp) and `source_year` (year parameter)

**Runner Function:**
```python
def run_holiday_pipeline(
    years: list[int],
    destination: str = "duckdb",
    dataset_name: str = "raw_holidays",
) -> dict[str, Any]:
```

**Pipeline Configuration:**
- **Pipeline Name:** `holiday_ingestion`
- **Destination:** `duckdb` with credentials pointing to `../duckdb/warehouse.duckdb` (relative from dlt_pipeline directory)
- **Dataset Name:** `raw_holidays` (creates schema in DuckDB)
- **DLT Project Directory:** Set `os.environ["DLT_PROJECT_DIR"] = str(Path(__file__).parent)` to find `.dlt/` config

### Database Schema

**Schema:** `raw_holidays`
**Table:** `us_holidays`

**Columns:**
- `date` (DATE, PRIMARY KEY) - Holiday date in YYYY-MM-DD format
- `holiday_name` (VARCHAR) - Official holiday name
- `local_name` (VARCHAR) - Local/alternative name
- `country_code` (VARCHAR) - Always "US"
- `is_fixed` (BOOLEAN) - Whether date is fixed annually
- `is_global` (BOOLEAN) - Whether holiday applies nationwide
- `holiday_types` (VARCHAR) - Comma-separated list from API's "types" array
- `counties` (VARCHAR) - Comma-separated state codes (null if nationwide)
- `launch_year` (INTEGER) - From API's "launchYear" field
- `_dlt_load_timestamp` (TIMESTAMP) - DLT ingestion timestamp
- `source_year` (INTEGER) - Year parameter used to fetch this data

### dbt Transformation Layer

**New File:** `dbt/models/staging/stg_holidays.sql`

**Transformation Logic:**
1. **Select from raw:** Clean and select all fields from `raw_holidays.us_holidays`
2. **Add NYC holidays:** CTE with static VALUES for NYC-specific holidays (NYC Marathon, Puerto Rican Day Parade, etc.)
3. **Union datasets:** Combine API-sourced and NYC static holidays
4. **Deduplicate:** Use `ROW_NUMBER() OVER (PARTITION BY date ORDER BY is_federal DESC)` to keep only one record per date, prioritizing federal holidays over NYC-specific
5. **Derive is_major:** `CASE WHEN holiday_types LIKE '%Federal%' THEN true ELSE false END`
6. **Derive is_working_day:** `CASE WHEN is_major THEN false ELSE true END` (federal holidays = non-working days)

**Materialization:** `{{ config(materialized='view') }}`

**New File:** `dbt/models/staging/schema.yml`

Add source definition:
```yaml
sources:
  - name: raw_holidays
    schema: raw_holidays
    tables:
      - name: us_holidays
        columns:
          - name: date
            tests:
              - unique
              - not_null
```

Add model tests:
```yaml
models:
  - name: stg_holidays
    columns:
      - name: date
        tests:
          - unique
          - not_null
      - name: holiday_name
        tests:
          - not_null
      - name: is_major
        tests:
          - not_null
      - name: is_working_day
        tests:
          - not_null
```

---

## 3. Impact and Risk Analysis

### System Dependencies

- **dlt framework** - Already in use for bike and weather pipelines
- **DuckDB warehouse** - `duckdb/warehouse.duckdb` must be accessible with write permissions
- **dbt models** - Downstream models can reference `staging.stg_holidays` for analysis
- **Airflow DAG** - Will need new task added to orchestrate holiday ingestion
- **No impact on existing pipelines** - Independent data source, no changes to bike/weather pipelines

### Potential Risks & Mitigations

1. **API Availability Risk**
   - **Risk:** Nager.Date API is down or rate-limited
   - **Mitigation:** Retry logic with exponential backoff; pipeline fails clearly for orchestration to retry later

2. **API Schema Changes**
   - **Risk:** Nager.Date changes response structure, breaking pipeline
   - **Mitigation:** Capture all fields generically; dbt staging handles field selection; add logging for unexpected fields

3. **Date Format Inconsistency**
   - **Risk:** API returns dates in unexpected format (not YYYY-MM-DD)
   - **Mitigation:** Use DuckDB's DATE type for automatic validation; pipeline fails on invalid dates

4. **NYC-Specific Holiday Accuracy**
   - **Risk:** Static NYC holidays hardcoded in dbt may be incorrect or change
   - **Mitigation:** Document source of NYC holiday dates in SQL comments; centralize in one CTE for easy updates

5. **Database Lock Issues**
   - **Risk:** DuckDB doesn't support concurrent writes; pipeline may fail if dbt is running simultaneously
   - **Mitigation:** Airflow DAG ensures sequential execution (ingest → dbt); SequentialExecutor prevents parallel tasks

---

## 4. Testing Strategy

### Unit Tests (`tests/test_holiday_pipeline.py`)

**Test Coverage:**
- Mock Nager.Date API response using `pytest-mock` with sample holiday data
- Test successful ingestion for single year (2024)
- Test multi-year ingestion ([2024, 2025])
- Test retry logic: Mock API timeout, verify 3 retry attempts with exponential backoff
- Test pipeline failure: Mock persistent API error, verify pipeline raises exception after max retries
- Validate all API fields are captured in yielded records
- Verify `_dlt_load_timestamp` and `source_year` metadata are added
- Test field transformation: Verify arrays (types, counties) converted to comma-separated strings

### Integration Tests

**End-to-End Validation:**
1. Run pipeline with real Nager.Date API for year 2024
2. Verify data lands in `duckdb/warehouse.duckdb` at schema `raw_holidays`, table `us_holidays`
3. Verify ~10-15 US holidays are loaded
4. Run pipeline again for same year, verify no duplicate dates (idempotency)
5. Query DuckDB to validate schema matches expected columns
6. Run dbt staging model, verify deduplication works (no duplicate dates in `stg_holidays`)
7. Test NYC static holiday union: Manually add a NYC holiday on same date as federal holiday, verify federal one is kept

### dbt Tests (`dbt/models/staging/schema.yml`)

**Data Quality Tests:**
- `unique` test on `date` column in `stg_holidays` (catches deduplication failures)
- `not_null` tests on: `date`, `holiday_name`, `is_major`, `is_working_day`
- `accepted_values` test on `country_code`: `['US']`
- `relationships` test (future): Verify holiday dates exist when joining with trip data
