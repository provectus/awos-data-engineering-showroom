# Functional Specification: Holiday Calendar Ingestion

- **Roadmap Item:** Holiday Data Integration → Holiday Calendar Ingestion
- **Status:** Draft
- **Author:** Product Team

---

## 1. Overview and Rationale (The "Why")

Maria (Operations Manager) currently cannot anticipate how holidays affect bike ridership patterns. She relies on gut feeling and yesterday's data, making it impossible to plan rebalancing operations for holiday weekends in advance. This leads to poor bike availability during holidays when demand patterns differ significantly from regular days.

**This feature enables:** The platform to ingest US federal and local NYC holiday data into the warehouse, providing the foundation for understanding holiday-driven demand patterns.

**User Value:** Maria will be able to identify which days are holidays and whether they are working days, allowing her to prepare for demand changes during Memorial Day, July 4th, Labor Day, and other holidays.

**Success Criteria:** Holiday data for any specified year is successfully ingested and available in the warehouse for analysis.

---

## 2. Functional Requirements (The "What")

### Requirement 1: Year-Based Holiday Data Ingestion

The system must ingest all US holidays for a specified year from the Nager.Date API.

**Acceptance Criteria:**
- [ ] The dlt pipeline accepts a `year` parameter (e.g., 2024)
- [ ] The pipeline calls Nager.Date API endpoint: `https://date.nager.at/api/v3/PublicHolidays/{year}/US`
- [ ] All holidays returned by the API for that year are fetched
- [ ] All fields provided by the API are captured and stored (date, name, local name, country code, fixed, global, counties, launch year, types)

### Requirement 2: Major Holiday Classification

The system must identify and tag major holidays to enable filtering and separate analysis.

**Acceptance Criteria:**
- [ ] If the API provides a classification field (e.g., "federal"), use it to tag major holidays
- [ ] If no API classification exists, all federal holidays are tagged as "major"
- [ ] Non-federal holidays are tagged as "non-major" or left untagged
- [ ] The major/non-major flag is stored in the warehouse

### Requirement 3: Working Day Determination

The system must indicate whether each holiday is a working day for businesses.

**Acceptance Criteria:**
- [ ] If the API provides a "working day" or similar flag, use it directly
- [ ] If the API does not provide this flag, apply the rule: Federal holidays = non-working day, all other holidays = working day
- [ ] Observed holidays (e.g., July 4th observed on Monday when it falls on Sunday) are ignored - only the actual holiday date is stored
- [ ] The working day flag is stored in the warehouse

### Requirement 4: Idempotent Data Loading

The system must support re-running the pipeline for the same year without creating duplicate records.

**Acceptance Criteria:**
- [ ] The holiday `date` field is used as the primary key in the warehouse
- [ ] Running the pipeline multiple times for the same year does not create duplicate records
- [ ] Existing records for the same date are updated (merge/upsert behavior)
- [ ] The data is stored in `duckdb/warehouse.duckdb` in the `raw_holidays` schema

### Requirement 5: Error Handling

The system must fail gracefully if the API is unavailable or returns an error.

**Acceptance Criteria:**
- [ ] If the Nager.Date API call fails for the specified year, the pipeline fails with a clear error message
- [ ] No partial data is written to the warehouse on failure
- [ ] Error handling follows the same pattern as the existing bike data pipeline (no special alerts or retries beyond standard dlt behavior)

### Requirement 6: NYC-Specific Holidays (dbt Layer)

Static NYC-specific holidays that occur on the same day every year must be added in the dbt transformation layer.

**Acceptance Criteria:**
- [ ] NYC-specific holidays (to be defined: e.g., NYC Marathon day, Puerto Rican Day Parade) are added as static data in a dbt model
- [ ] These holidays are unioned or joined with API-sourced holidays in the staging layer
- [ ] NYC holidays include the same fields: date, name, major flag, working day flag
- [ ] This static data lives in dbt SQL, not in the ingestion pipeline

---

## 3. Scope and Boundaries

### In-Scope

- Ingesting all US holidays for a specified year from Nager.Date API
- Capturing all fields provided by the API
- Tagging major holidays (federal holidays)
- Determining working day status (from API or derived)
- Idempotent pipeline with date as primary key
- Year parameter for pipeline execution
- Adding static NYC-specific holidays in dbt
- Storage in `duckdb/warehouse.duckdb` (`raw_holidays` schema)

### Out-of-Scope

- **Historical Holiday Analysis** - Correlating holidays with demand (separate roadmap item)
- **Special Events Data Integration** - Concerts, sports, parades (separate roadmap item)
- **Demand Forecasting Engine** - Using holiday data for predictions (Phase 2 roadmap item)
- **Enhanced Analytics Dashboards** - Holiday impact visualization (Phase 3 roadmap item)
- **Multi-year batch ingestion** - Pipeline runs for one year at a time; orchestration (Airflow) can call it multiple times if needed
- **Automatic year detection** - Year must be explicitly provided as parameter
- **User-defined custom holidays** - Only API-sourced and static NYC holidays
- **Real-time holiday updates** - Data is ingested on-demand or via scheduled pipeline, not in real-time
