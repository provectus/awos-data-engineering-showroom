{{
    config(
        materialized='table'
    )
}}

-- Holiday Impact Analysis Mart
-- Joins daily demand metrics with holiday data to enable comparison of holiday vs. non-holiday demand
-- Includes weather normalization to adjust demand as if all days had average weather conditions

with demand_weather as (
    select
        date as ride_date,
        trips_total,
        day_type,
        tmax,
        temp_avg,
        precip
    from {{ ref('mart_weather_effect') }}
),

-- Calculate overall average weather conditions (baseline for normalization)
weather_baseline as (
    select
        avg(temp_avg) as baseline_temp,
        avg(precip) as baseline_precip
    from demand_weather
    where temp_avg is not null
),

holidays as (
    select
        date,
        holiday_name,
        local_name,
        is_nationwide,
        is_fixed,
        holiday_types,
        counties
    from {{ ref('stg_holidays') }}
),

-- Calculate baseline (average trips on non-holiday days)
baseline_calc as (
    select
        avg(dw.trips_total) as baseline_daily_trips
    from demand_weather dw
    left join holidays h on dw.ride_date = h.date
    where h.date is null  -- Only non-holiday days
),

joined as (
    select
        dw.ride_date,

        -- Holiday identification
        case when h.date is not null then true else false end as is_holiday,
        h.holiday_name,

        -- Holiday category derived from holiday_types
        case
            when h.holiday_types like '%Public%' then 'Federal Holiday'
            when h.holiday_types like '%Observance%' then 'NY State Observance'
            else null
        end as holiday_category,

        -- Demand metrics from mart_demand_daily (via mart_weather_effect)
        dw.trips_total,

        -- Weather metrics
        dw.tmax,
        dw.precip,

        -- Day type (Weekday/Weekend)
        dw.day_type,

        -- Baseline comparison (cross join to get the single baseline value)
        bc.baseline_daily_trips,

        -- Weather normalization: Calculate weather impact factor and adjust trips
        -- Goal: Estimate what trips would have been under baseline weather conditions
        -- Temperature factor: Linear relationship with 1.5% change per degree C from baseline
        -- Precipitation factor: Logarithmic decay - rain has diminishing marginal impact
        case
            when dw.temp_avg is null or dw.precip is null then
                -- If weather data missing, return raw trips (no adjustment)
                dw.trips_total
            else
                -- Calculate normalized trips:
                -- trips_normalized = trips_actual * (baseline_impact / actual_impact)
                -- where impact = temp_factor * precip_factor
                dw.trips_total * (
                    -- Baseline weather impact (what we're normalizing TO)
                    (1.0 / (1.0 + 0.03 * wb.baseline_precip))  -- Baseline precip impact
                    /
                    -- Actual weather impact (what we're normalizing FROM)
                    greatest(
                        (1.0 / (1.0 + 0.03 * dw.precip)),  -- Actual precip impact
                        0.25  -- Cap minimum impact at 25% to avoid extreme adjustments
                    )
                ) * (
                    -- Temperature adjustment: 1.5% per degree from optimal (20.3°C)
                    1.0 + (dw.temp_avg - wb.baseline_temp) * 0.015
                )
        end as trips_weather_adjusted,

        -- Demand vs baseline percentage (using weather-adjusted trips)
        case
            when bc.baseline_daily_trips > 0 and dw.temp_avg is not null and dw.precip is not null then
                -- Calculate using weather-adjusted trips
                (((dw.trips_total * (
                    (1.0 / (1.0 + 0.03 * wb.baseline_precip)) /
                    greatest((1.0 / (1.0 + 0.03 * dw.precip)), 0.25)
                ) * (
                    1.0 + (dw.temp_avg - wb.baseline_temp) * 0.015
                )) - bc.baseline_daily_trips) / bc.baseline_daily_trips) * 100
            when bc.baseline_daily_trips > 0 then
                -- Fallback to raw trips if weather data missing
                ((dw.trips_total - bc.baseline_daily_trips) / bc.baseline_daily_trips) * 100
            else null
        end as demand_vs_baseline_pct

    from demand_weather dw
    left join holidays h on dw.ride_date = h.date
    cross join baseline_calc bc  -- Single row, so cross join is safe
    cross join weather_baseline wb  -- Single row with baseline weather values
)

select * from joined
order by ride_date
