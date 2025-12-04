# Technical Specification: Dynamic Date Ranges in dbt Models

- **Functional Specification:** `context/spec/006-dynamic-date-ranges/functional-spec.md`
- **Status:** Draft
- **Author(s):** Engineering Team

---

## 1. High-Level Technical Approach

This specification addresses removing hardcoded date filters from dbt mart models so they automatically include all available data. The key insight is simple:

**Current State:** 5 dbt models have hardcoded `where date between '2024-05-01' and '2024-06-30'` filters.

**Target State:** Remove these filters entirely. Models will process ALL data present in source tables.

**Why This Works:**
- The holiday and game models use INNER JOINs to `stg_holidays` and `stg_games`
- Only holidays/games that exist in the database AND have matching bike trip data will appear in results
- No code changes needed to dashboards - they query mart tables and display whatever data exists

**Files affected (5 dbt models):**
| Model | Location | Lines with hardcoded dates |
|-------|----------|---------------------------|
| `mart_holiday_impact_summary.sql` | Line 18 | `where date between '2024-05-01' and '2024-06-30'` |
| `mart_holiday_impact_by_station.sql` | Line 18 | `where date between '2024-05-01' and '2024-06-30'` |
| `mart_holiday_impact_by_hour.sql` | Line 18 | `where date between '2024-05-01' and '2024-06-30'` |
| `mart_holiday_impact_by_area.sql` | Line 18 | `where date between '2024-05-01' and '2024-06-30'` |
| `mart_game_day_demand.sql` | Lines 21, 111 | Two separate hardcoded date filters |

**Files NOT affected:**
- `mart_game_rebalancing.sql` - No date filters (aggregates from `mart_game_day_demand`)
- Dashboard files - No changes needed (they query mart tables dynamically)

---

## 2. Proposed Solution & Implementation Plan (The "How")

### 2.1 Holiday Impact Models (4 models)

All 4 holiday impact models follow the same pattern. The `holidays` CTE currently filters to May-June 2024:

**Current (all 4 models, line 18):**
```sql
with holidays as (
    select
        date,
        holiday_name,
        is_major,
        is_working_day
    from {{ ref('stg_holidays') }}
    where date between '2024-05-01' and '2024-06-30'  -- All May-June 2024 holidays
),
```

**Change:** Remove the `where` clause entirely:
```sql
with holidays as (
    select
        date,
        holiday_name,
        is_major,
        is_working_day
    from {{ ref('stg_holidays') }}
),
```

**Why this works:**
- The `holiday_metrics*` CTEs use `inner join {{ ref('stg_bike_trips') }} t on t.ride_date = h.date`
- Only holidays that have matching bike trip data will produce results
- If holidays exist in database but no bike data exists for those dates, they're naturally excluded

**Models to update:**
1. `dbt/models/marts/mart_holiday_impact_summary.sql` (line 18)
2. `dbt/models/marts/mart_holiday_impact_by_station.sql` (line 18)
3. `dbt/models/marts/mart_holiday_impact_by_hour.sql` (line 18)
4. `dbt/models/marts/mart_holiday_impact_by_area.sql` (line 18)

### 2.2 Game Day Demand Model

The game day demand model has TWO hardcoded date filters:

**Location 1 - Line 21 (games CTE):**
```sql
with games as (
    select
        game_id,
        game_date,
        game_datetime_rounded as game_datetime,
        estimated_end_datetime,
        stadium_name,
        home_team_name,
        away_team_name
    from {{ ref('stg_games') }}
    where game_date between '2024-05-01' and '2024-06-30'
      and stadium_name in ('Yankee Stadium', 'Citi Field')  -- Exclude London Stadium
),
```

**Change:** Remove only the date filter, keep stadium filter:
```sql
with games as (
    select
        game_id,
        game_date,
        game_datetime_rounded as game_datetime,
        estimated_end_datetime,
        stadium_name,
        home_team_name,
        away_team_name
    from {{ ref('stg_games') }}
    where stadium_name in ('Yankee Stadium', 'Citi Field')  -- Exclude London Stadium
),
```

**Location 2 - Line 111 (baseline_demand CTE):**
```sql
    inner join {{ ref('stg_bike_trips') }} t
        on dayofweek(t.ride_date) = dayofweek(g.game_date)
        and t.ride_date != g.game_date
        and t.ride_date between '2024-05-01' and '2024-06-30'
        and (t.started_at between g.game_datetime - interval '3 hours'
```

**Change:** Remove the date range filter, keep other conditions:
```sql
    inner join {{ ref('stg_bike_trips') }} t
        on dayofweek(t.ride_date) = dayofweek(g.game_date)
        and t.ride_date != g.game_date
        and (t.started_at between g.game_datetime - interval '3 hours'
```

**Why this works:**
- The `game_day_demand` CTE already uses `inner join {{ ref('stg_bike_trips') }} t on t.ride_date = g.game_date`
- Games without matching bike trip data are naturally excluded
- Baseline calculation will use all available data for the same day-of-week (not just May-June 2024)

---

## 3. Impact and Risk Analysis

### System Dependencies
- **dbt models**: 5 models modified (simple `where` clause removal)
- **DuckDB**: No schema changes
- **Dashboards**: No changes needed - automatically show available data
- **Airflow**: No changes needed

### Potential Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Performance degradation with large datasets | Low | Medium | Models already use inner joins which limit data; DuckDB handles large datasets well |
| Missing baseline data for new periods | Low | Low | Models use relative baseline logic (+/- 15 days); gracefully handles edge cases with NULLIF |
| Empty results if no matching data | Low | Low | Expected behavior - dashboards will show "no data" which is accurate |
| Inconsistent date ranges across data sources | Low | Medium | Inner joins naturally align data; only shows where all sources have data |

### Backward Compatibility

Changes are fully backward compatible:
- Same columns, same output schema
- Existing data for May-June 2024 continues to appear
- New data (when backfilled) automatically appears
- No API changes, no dashboard changes

---

## 4. Testing Strategy

### Pre-Implementation Verification
1. Document current row counts in each mart table:
   ```sql
   select 'mart_holiday_impact_summary' as model, count(*) from main_marts.mart_holiday_impact_summary
   union all
   select 'mart_holiday_impact_by_station', count(*) from main_marts.mart_holiday_impact_by_station
   union all
   select 'mart_holiday_impact_by_hour', count(*) from main_marts.mart_holiday_impact_by_hour
   union all
   select 'mart_holiday_impact_by_area', count(*) from main_marts.mart_holiday_impact_by_area
   union all
   select 'mart_game_day_demand', count(*) from main_marts.mart_game_day_demand;
   ```

### Post-Implementation Tests
1. Run `dbt build` - all models should compile and run without errors
2. Verify same row counts (since we still only have May-June 2024 data)
3. Verify dashboard pages load without errors:
   - Holiday Impact dashboard
   - Game Impact dashboard

### Future Data Test (after backfill)
1. Backfill 2023 data using Airflow DAG with custom params
2. Run `dbt build`
3. Verify mart tables now include 2023 holidays/games
4. Verify dashboards show 2023 data in selectors

### Validation Checklist
- [ ] `mart_holiday_impact_summary.sql` - date filter removed
- [ ] `mart_holiday_impact_by_station.sql` - date filter removed
- [ ] `mart_holiday_impact_by_hour.sql` - date filter removed
- [ ] `mart_holiday_impact_by_area.sql` - date filter removed
- [ ] `mart_game_day_demand.sql` - both date filters removed
- [ ] `dbt build` completes successfully
- [ ] Row counts match pre-implementation (with current data)
- [ ] Holiday Impact dashboard loads correctly
- [ ] Game Impact dashboard loads correctly

---

## 5. Implementation Slices

### Slice 1: Remove date filters from holiday impact models

**Goal:** Update all 4 holiday impact models to use all available holiday data.

**Tasks:**
- [ ] Remove `where date between...` from `mart_holiday_impact_summary.sql` (line 18)
- [ ] Remove `where date between...` from `mart_holiday_impact_by_station.sql` (line 18)
- [ ] Remove `where date between...` from `mart_holiday_impact_by_hour.sql` (line 18)
- [ ] Remove `where date between...` from `mart_holiday_impact_by_area.sql` (line 18)
- [ ] Run `dbt build --select mart_holiday_impact*`
- [ ] Verify row counts match (should be same with current data)

### Slice 2: Remove date filters from game day demand model

**Goal:** Update game day demand model to use all available game data.

**Tasks:**
- [ ] Remove `game_date between...` from games CTE (line 21)
- [ ] Remove `t.ride_date between...` from baseline_demand CTE (line 111)
- [ ] Run `dbt build --select mart_game_day_demand`
- [ ] Verify row counts match (should be same with current data)

### Slice 3: End-to-end validation

**Goal:** Full validation and dashboard testing.

**Tasks:**
- [ ] Run full `dbt build`
- [ ] Verify Holiday Impact dashboard loads
- [ ] Verify Game Impact dashboard loads
- [ ] Update roadmap.md to mark Dynamic Date Ranges as complete
