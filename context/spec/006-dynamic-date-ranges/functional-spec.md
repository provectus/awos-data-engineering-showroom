# Functional Specification: Dynamic Date Ranges in dbt Models

- **Roadmap Item:** Phase 4 - Continuous Data Pipeline (Dynamic Date Ranges)
- **Status:** Draft
- **Author:** Product Team

---

## 1. Overview and Rationale (The "Why")

**The Problem:** Currently, several dbt mart models have hardcoded date filters (`2024-05-01` to `2024-06-30`) that were added during initial development with the demo dataset. This means:
- When users backfill historical data, the marts don't include it
- Dashboards only show May-June 2024 regardless of available data
- Manual code changes are required to analyze different time periods

**Desired Outcome:** All dbt mart models should automatically include all available data without hardcoded date restrictions. When users backfill historical data (e.g., 2023), running `dbt build` should automatically make that data available in dashboards.

**User Value:** Operations teams can analyze historical trends across any time period they've ingested, enabling better seasonal planning and year-over-year comparisons.

**Success Metrics:**
- All dbt mart models work with any date range present in the data
- No code changes required when backfilling historical data
- Dashboards automatically reflect all available data

---

## 2. Functional Requirements (The "What")

### Requirement 1: Remove Hardcoded Date Filters from Holiday Impact Models

The following models should analyze ALL available holidays in the data:
- `mart_holiday_impact_summary.sql`
- `mart_holiday_impact_by_station.sql`
- `mart_holiday_impact_by_hour.sql`
- `mart_holiday_impact_by_area.sql`

**Acceptance Criteria:**
- [ ] Given holidays exist for 2023 and 2024 in the database, when `dbt build` runs, then all holiday impact marts include both years
- [ ] Given only 2024 holidays exist, then holiday impact marts show only 2024 data (no errors)
- [ ] The Holiday Impact dashboard displays all available holidays without code changes

### Requirement 2: Remove Hardcoded Date Filters from Game Day Model

The `mart_game_day_demand.sql` model should analyze ALL available games.

**Acceptance Criteria:**
- [ ] Given games exist for multiple seasons, when `dbt build` runs, then game day analysis includes all seasons
- [ ] The Game Impact dashboard displays all available game data without code changes

### Requirement 3: Dashboards Automatically Reflect Available Data

No dashboard code changes should be required. Dashboards should naturally show whatever data exists in the marts.

**Acceptance Criteria:**
- [ ] After backfilling 2023 data and running `dbt build`, Holiday Impact dashboard shows 2023 holidays in the selector
- [ ] After backfilling 2023 data and running `dbt build`, Game Impact dashboard shows 2023 games (if ingested)

---

## 3. Scope and Boundaries

### In-Scope
- Removing hardcoded date filters from dbt mart models
- Ensuring dashboards work with variable date ranges
- Verifying models handle empty/partial data gracefully

### Out-of-Scope (Separate Roadmap Items)
- **Historical Data Expansion** - User will manually backfill data using existing Airflow DAG with custom date parameters
- **Data Quality Enhancement** (Phase 5)
- **Model Performance & Analytics** (Phase 6)
- **Jersey City Integration** (Phase 7)
