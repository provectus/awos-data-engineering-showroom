# Tasks: Dynamic Date Ranges in dbt Models

**Spec:** 006-dynamic-date-ranges
**Status:** ✅ COMPLETED

---

## Slice 1: Remove date filters from holiday impact summary model ✅

**Goal:** Update the main holiday impact summary model to use all available holiday data. This is the foundational model for citywide holiday analytics.

- [x] Remove `where date between '2024-05-01' and '2024-06-30'` from `holidays` CTE in `mart_holiday_impact_summary.sql` (line 18)
- [x] Run `dbt build --select mart_holiday_impact_summary` from `dbt/` directory
- [x] Verify model builds successfully without errors
- [x] Verify Holiday Impact dashboard Summary section still loads

---

## Slice 2: Remove date filters from remaining holiday impact models ✅

**Goal:** Update the 3 supporting holiday models (station, hour, area) to match the summary model. System remains runnable after each sub-task.

- [x] Remove `where date between '2024-05-01' and '2024-06-30'` from `holidays` CTE in `mart_holiday_impact_by_station.sql` (line 18)
- [x] Run `dbt build --select mart_holiday_impact_by_station` - verify success
- [x] Remove `where date between '2024-05-01' and '2024-06-30'` from `holidays` CTE in `mart_holiday_impact_by_hour.sql` (line 18)
- [x] Run `dbt build --select mart_holiday_impact_by_hour` - verify success
- [x] Remove `where date between '2024-05-01' and '2024-06-30'` from `holidays` CTE in `mart_holiday_impact_by_area.sql` (line 18)
- [x] Run `dbt build --select mart_holiday_impact_by_area` - verify success
- [x] Verify complete Holiday Impact dashboard loads correctly (all sections)

---

## Slice 3: Remove date filters from game day demand model ✅

**Goal:** Update the game day demand model to use all available game data. This model has TWO date filters that must both be removed.

- [x] Remove `where game_date between '2024-05-01' and '2024-06-30'` from `games` CTE in `mart_game_day_demand.sql` (line 21) - keep stadium filter
- [x] Remove `and t.ride_date between '2024-05-01' and '2024-06-30'` from `baseline_demand` CTE in `mart_game_day_demand.sql` (line 111)
- [x] Run `dbt build --select mart_game_day_demand mart_game_rebalancing` - verify both models build
- [x] Verify Game Impact dashboard loads correctly

---

## Slice 4: Final validation and documentation ✅

**Goal:** End-to-end validation and roadmap update.

- [x] Run full `dbt build` to ensure all models work together
- [x] Run `dbt test` to verify data quality tests pass (PASS=169, ERROR=0)
- [x] Fix stadium name test - added 'Journey Bank Ballpark' to accepted values in schema.yml
- [x] **[MANUAL]** Verify Holiday Impact dashboard shows all expected data
- [x] **[MANUAL]** Verify Game Impact dashboard shows all expected data
- [x] Update `context/product/roadmap.md` to mark "Dynamic Date Ranges" as completed in Phase 4

---

## Success Criteria (from Functional Spec) ✅

- [x] All dbt mart models work with any date range present in the data
- [x] No code changes required when backfilling historical data
- [x] Dashboards automatically reflect all available data
