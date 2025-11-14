# Task List: Holiday Calendar Ingestion

## Vertical Slices (Incremental, Runnable Tasks)

- [x] **Slice 1: Create basic dlt pipeline structure that successfully connects to Nager.Date API**
  - [x] Create `dlt_pipeline/holidays.py` file with module docstring
  - [x] Add imports and logger setup (following bike.py/weather.py patterns)
  - [x] Set `DLT_PROJECT_DIR` environment variable
  - [x] Create basic `us_holidays(years: list[int])` function with `@dlt.resource` decorator (merge disposition, primary_key="date")
  - [x] Implement HTTP GET request to `https://date.nager.at/api/v3/PublicHolidays/{year}/US` for a single year
  - [x] Add basic error handling (raise on RequestException)
  - [x] Parse JSON response and yield one test record with all API fields
  - [x] Create `run_holiday_pipeline()` function with dlt.pipeline configuration pointing to `../duckdb/warehouse.duckdb`
  - [x] Add `if __name__ == "__main__"` block to test with year 2024
  - [x] **Verification:** Run `uv run python dlt_pipeline/holidays.py` and confirm data lands in `duckdb/warehouse.duckdb` at `raw_holidays.us_holidays`

- [x] **Slice 2: Implement complete field capture and metadata for all holidays**
  - [x] Update `us_holidays()` to iterate through all holidays in API response
  - [x] Transform array fields (types, counties) to comma-separated strings
  - [x] Add `_dlt_load_timestamp` metadata field with `datetime.now()`
  - [x] Add `source_year` metadata field
  - [x] Map all API fields to snake_case column names (holiday_name, local_name, etc.)
  - [x] **Verification:** Run pipeline for 2024, query DuckDB to verify all ~10-15 holidays are captured with all fields

- [x] **Slice 3: Add idempotency and multi-year support**
  - [x] Update `us_holidays()` to accept and iterate through multiple years
  - [x] Verify `primary_key="date"` enforces merge behavior
  - [x] **Verification:** Run pipeline twice for same year, confirm no duplicate dates; run for [2024, 2025], verify both years' data exists

- [x] **Slice 4: Implement retry logic with exponential backoff**
  - [x] Add retry loop (max 3 attempts) around API request
  - [x] Implement exponential backoff delays (1s, 2s, 4s) using `time.sleep()`
  - [x] Log warnings on retry attempts
  - [x] Raise exception after max retries to fail pipeline
  - [x] **Verification:** Mock API timeout in test, verify 3 retry attempts before failure

- [x] **Slice 5: Create dbt staging model with API-sourced holidays only**
  - [x] Create `dbt/models/staging/stg_holidays.sql` with config (materialized='view')
  - [x] Select and clean all fields from `raw_holidays.us_holidays`
  - [x] Derive `is_major` flag: `CASE WHEN holiday_types LIKE '%Federal%' THEN true ELSE false END`
  - [x] Derive `is_working_day` flag: `CASE WHEN is_major THEN false ELSE true END`
  - [x] Add source definition in `dbt/models/staging/schema.yml` for `raw_holidays.us_holidays`
  - [x] **Verification:** Run `cd dbt && uv run dbt run --select stg_holidays`, query `staging.stg_holidays` to verify flags are correct

- [x] **Slice 6: Add NYC-specific static holidays and deduplication logic**
  - [x] Add CTE in `stg_holidays.sql` with dynamic SQL for NYC holidays (NYC Marathon, Puerto Rican Day Parade using date arithmetic)
  - [x] Add documentation comments for each NYC holiday (source, calculation method)
  - [x] Union API-sourced holidays with NYC static holidays
  - [x] Implement deduplication using `ROW_NUMBER() OVER (PARTITION BY date ORDER BY is_federal DESC)`
  - [x] Filter to keep only row_number = 1 per date
  - [x] Cast date column to DATE type to ensure correct schema
  - [x] **Verification:** Add test NYC holiday on same date as federal holiday (e.g., July 4th), run dbt, verify only federal holiday appears

- [x] **Slice 7: Add dbt tests for data quality**
  - [x] Add model tests in `dbt/models/staging/schema.yml` for `stg_holidays`:
    - [x] `unique` test on `date` column
    - [x] `not_null` tests on `date`, `holiday_name`, `is_major`, `is_working_day`
    - [x] `accepted_values` test on `country_code`: `['US']`
  - [x] **Verification:** Run `cd dbt && uv run dbt test --select stg_holidays`, confirm all tests pass

- [x] **Slice 8: Create unit tests for dlt pipeline**
  - [x] Create `tests/test_holiday_pipeline.py`
  - [x] Mock Nager.Date API response with sample holiday data using `pytest-mock`
  - [x] Test successful single-year ingestion (2024)
  - [x] Test multi-year ingestion ([2024, 2025])
  - [x] Test retry logic: Mock API timeout, verify 3 attempts with exponential backoff
  - [x] Test pipeline failure: Mock persistent error, verify exception raised after max retries
  - [x] Test field transformation: Verify arrays converted to comma-separated strings
  - [x] Test metadata: Verify `_dlt_load_timestamp` and `source_year` are added
  - [x] Test intelligent merging: Verify holidays on same date are merged correctly
  - [x] **Verification:** Run `PYTHONPATH=. uv run pytest tests/test_holiday_pipeline.py -v`, all 11 tests pass

- [x] **Slice 9: Integration test and documentation**
  - [x] Run end-to-end integration test:
    - [x] Execute pipeline for 2024 with real API
    - [x] Verify data in `raw_holidays.us_holidays` (14 holidays, 0 duplicates)
    - [x] Run dbt staging model
    - [x] Verify `staging.stg_holidays` has no duplicate dates and correct flags (16 holidays with NYC, 12 major, 12 non-working)
  - [x] Update `CLAUDE.md` documentation:
    - [x] Add holiday pipeline command under "Data Ingestion (dlt)" section: `uv run python dlt_pipeline/holidays.py`
    - [x] Document year parameter usage and examples
  - [x] **Verification:** Follow documentation steps, verify end-to-end workflow works

- [x] **Slice 10: Update README.md with holiday feature documentation**
  - [x] Add "Holiday Data Integration" section to README.md
  - [x] Document the Nager.Date API integration
  - [x] Explain holiday classification (major/federal vs other holidays)
  - [x] Describe working day determination logic
  - [x] Add example usage for running holiday pipeline
  - [x] Update architecture diagram to include Nager.Date API as third data source
  - [x] Add NYC-specific holidays to feature list
  - [x] Add Part 3 (Holiday Impact Analysis) to Overview section
  - [x] Add Steps 9-11 to Running the Pipeline section
  - [x] Add Act 3 to Demo Walkthrough section
  - [x] Update Table of Contents with Holiday Data Integration link
  - [x] **Verification:** Review README.md to ensure it accurately reflects the new holiday ingestion capability