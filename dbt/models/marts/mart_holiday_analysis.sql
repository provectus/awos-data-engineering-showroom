{{
    config(
        materialized='table'
    )
}}

-- Holiday Impact Analysis Mart
-- Joins daily demand metrics with holiday data to enable comparison of holiday vs. non-holiday demand
-- Weather normalization will be added in Slice 4 (currently trips_weather_adjusted = trips_total)

with demand_weather as (
    select
        date as ride_date,
        trips_total,
        day_type,
        tmax,
        precip
    from {{ ref('mart_weather_effect') }}
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

        -- Demand vs baseline percentage
        case
            when bc.baseline_daily_trips > 0 then
                ((dw.trips_total - bc.baseline_daily_trips) / bc.baseline_daily_trips) * 100
            else null
        end as demand_vs_baseline_pct,

        -- PLACEHOLDER: Weather-adjusted trips (Slice 4 will add actual normalization logic)
        -- For now, this equals raw trips_total
        dw.trips_total as trips_weather_adjusted

    from demand_weather dw
    left join holidays h on dw.ride_date = h.date
    cross join baseline_calc bc  -- Single row, so cross join is safe
)

select * from joined
order by ride_date
