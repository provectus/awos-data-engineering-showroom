# Tasks: Dynamic Date Ranges in dbt Models

**Spec:** 006-dynamic-date-ranges
**Status:** Draft

---

## Slice 1: Remove date filters from holiday impact summary model

**Goal:** Update the main holiday impact summary model to use all available holiday data. This is the foundational model for citywide holiday analytics.

- [ ] Remove `where date between '2024-05-01' and '2024-06-30'` from `holidays` CTE in `mart_holiday_impact_summary.sql` (line 18)
- [ ] Run `dbt build --select mart_holiday_impact_summary` from `dbt/` directory
- [ ] Verify model builds successfully without errors
- [ ] Verify Holiday Impact dashboard Summary section still loads

---

## Slice 2: Remove date filters from remaining holiday impact models

**Goal:** Update the 3 supporting holiday models (station, hour, area) to match the summary model. System remains runnable after each sub-task.

- [ ] Remove `where date between '2024-05-01' and '2024-06-30'` from `holidays` CTE in `mart_holiday_impact_by_station.sql` (line 18)
- [ ] Run `dbt build --select mart_holiday_impact_by_station` - verify success
- [ ] Remove `where date between '2024-05-01' and '2024-06-30'` from `holidays` CTE in `mart_holiday_impact_by_hour.sql` (line 18)
- [ ] Run `dbt build --select mart_holiday_impact_by_hour` - verify success
- [ ] Remove `where date between '2024-05-01' and '2024-06-30'` from `holidays` CTE in `mart_holiday_impact_by_area.sql` (line 18)
- [ ] Run `dbt build --select mart_holiday_impact_by_area` - verify success
- [ ] Verify complete Holiday Impact dashboard loads correctly (all sections)

---

## Slice 3: Remove date filters from game day demand model

**Goal:** Update the game day demand model to use all available game data. This model has TWO date filters that must both be removed.

- [ ] Remove `where game_date between '2024-05-01' and '2024-06-30'` from `games` CTE in `mart_game_day_demand.sql` (line 21) - keep stadium filter
- [ ] Remove `and t.ride_date between '2024-05-01' and '2024-06-30'` from `baseline_demand` CTE in `mart_game_day_demand.sql` (line 111)
- [ ] Run `dbt build --select mart_game_day_demand mart_game_rebalancing` - verify both models build
- [ ] Verify Game Impact dashboard loads correctly

---

## Slice 4: Final validation and documentation

**Goal:** End-to-end validation and roadmap update.

- [ ] Run full `dbt build` to ensure all models work together
- [ ] Run `dbt test` to verify data quality tests pass
- [ ] **[MANUAL]** Verify Holiday Impact dashboard shows all expected data
- [ ] **[MANUAL]** Verify Game Impact dashboard shows all expected data
- [ ] Update `context/product/roadmap.md` to mark "Dynamic Date Ranges" as completed in Phase 4

---

## Success Criteria (from Functional Spec)

- [ ] All dbt mart models work with any date range present in the data
- [ ] No code changes required when backfilling historical data
- [ ] Dashboards automatically reflect all available data
