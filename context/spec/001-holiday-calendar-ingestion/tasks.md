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

- [ ] **Slice 3: Add idempotency and multi-year support**
  - [ ] Update `us_holidays()` to accept and iterate through multiple years
  - [ ] Verify `primary_key="date"` enforces merge behavior
  - [ ] **Verification:** Run pipeline twice for same year, confirm no duplicate dates; run for [2024, 2025], verify both years' data exists

- [ ] **Slice 4: Implement retry logic with exponential backoff**
  - [ ] Add retry loop (max 3 attempts) around API request
  - [ ] Implement exponential backoff delays (1s, 2s, 4s) using `time.sleep()`
  - [ ] Log warnings on retry attempts
  - [ ] Raise exception after max retries to fail pipeline
  - [ ] **Verification:** Mock API timeout in test, verify 3 retry attempts before failure

- [ ] **Slice 5: Create dbt staging model with API-sourced holidays only**
  - [ ] Create `dbt/models/staging/stg_holidays.sql` with config (materialized='view')
  - [ ] Select and clean all fields from `raw_holidays.us_holidays`
  - [ ] Derive `is_major` flag: `CASE WHEN holiday_types LIKE '%Federal%' THEN true ELSE false END`
  - [ ] Derive `is_working_day` flag: `CASE WHEN is_major THEN false ELSE true END`
  - [ ] Add source definition in `dbt/models/staging/schema.yml` for `raw_holidays.us_holidays`
  - [ ] **Verification:** Run `cd dbt && uv run dbt run --select stg_holidays`, query `staging.stg_holidays` to verify flags are correct

- [ ] **Slice 6: Add NYC-specific static holidays and deduplication logic**
  - [ ] Add CTE in `stg_holidays.sql` with static VALUES for NYC holidays (NYC Marathon, Puerto Rican Day Parade with dates, names, flags)
  - [ ] Add documentation comments for each NYC holiday (source, fixed date)
  - [ ] Union API-sourced holidays with NYC static holidays
  - [ ] Implement deduplication using `ROW_NUMBER() OVER (PARTITION BY date ORDER BY is_federal DESC)`
  - [ ] Filter to keep only row_number = 1 per date
  - [ ] **Verification:** Add test NYC holiday on same date as federal holiday (e.g., July 4th), run dbt, verify only federal holiday appears

- [ ] **Slice 7: Add dbt tests for data quality**
  - [ ] Add model tests in `dbt/models/staging/schema.yml` for `stg_holidays`:
    - [ ] `unique` test on `date` column
    - [ ] `not_null` tests on `date`, `holiday_name`, `is_major`, `is_working_day`
    - [ ] `accepted_values` test on `country_code`: `['US']`
  - [ ] **Verification:** Run `cd dbt && uv run dbt test --select stg_holidays`, confirm all tests pass

- [ ] **Slice 8: Create unit tests for dlt pipeline**
  - [ ] Create `tests/test_holiday_pipeline.py`
  - [ ] Mock Nager.Date API response with sample holiday data using `pytest-mock`
  - [ ] Test successful single-year ingestion (2024)
  - [ ] Test multi-year ingestion ([2024, 2025])
  - [ ] Test retry logic: Mock API timeout, verify 3 attempts with exponential backoff
  - [ ] Test pipeline failure: Mock persistent error, verify exception raised after max retries
  - [ ] Test field transformation: Verify arrays converted to comma-separated strings
  - [ ] Test metadata: Verify `_dlt_load_timestamp` and `source_year` are added
  - [ ] **Verification:** Run `uv run pytest tests/test_holiday_pipeline.py -v`, all tests pass

- [ ] **Slice 9: Integration test and documentation**
  - [ ] Run end-to-end integration test:
    - [ ] Execute pipeline for 2024 with real API
    - [ ] Verify data in `raw_holidays.us_holidays`
    - [ ] Run dbt staging model
    - [ ] Verify `staging.stg_holidays` has no duplicate dates and correct flags
  - [ ] Update `CLAUDE.md` documentation:
    - [ ] Add holiday pipeline command under "Data Ingestion (dlt)" section: `uv run python dlt_pipeline/holidays.py`
    - [ ] Document year parameter usage and examples
  - [ ] **Verification:** Follow documentation steps, verify end-to-end workflow works

- [ ] **Slice 10: Update README.md with holiday feature documentation**
  - [ ] Add "Holiday Data Integration" section to README.md
  - [ ] Document the Nager.Date API integration
  - [ ] Explain holiday classification (major/federal vs other holidays)
  - [ ] Describe working day determination logic
  - [ ] Add example usage for running holiday pipeline
  - [ ] Update architecture diagram or data flow section if applicable
  - [ ] Add NYC-specific holidays to feature list
  - [ ] **Verification:** Review README.md to ensure it accurately reflects the new holiday ingestion capability