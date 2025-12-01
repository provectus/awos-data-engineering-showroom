{{
    config(
        materialized='table'
    )
}}

-- Historical Holiday Impact Analysis by Hour
-- Analyzes demand patterns by hour of day (0-23) to show peak hour shifts on holidays
-- Enables time-of-day analysis for operational rebalancing decisions

with holidays as (
    select
        date,
        holiday_name,
        is_major,
        is_working_day
    from {{ ref('stg_holidays') }}
    where date between '2024-05-01' and '2024-06-30'  -- All May-June 2024 holidays
),

-- Generate baseline days: weekdays within +/- 15 days, excluding the holiday and other holidays
baseline_days as (
    select
        h.date as holiday_date,
        h.holiday_name,
        d.ride_date
    from holidays h
    cross join (
        select distinct ride_date
        from {{ ref('stg_bike_trips') }}
    ) d
    where
        -- Within 15 days before/after the holiday
        d.ride_date between h.date - interval '15 days' and h.date + interval '15 days'
        -- Exclude the holiday itself
        and d.ride_date != h.date
        -- Exclude weekends (Sunday=0, Saturday=6)
        and dayofweek(d.ride_date) not in (0, 6)
        -- Exclude other holidays
        and d.ride_date not in (
            select date from {{ ref('stg_holidays') }}
        )
),

-- Calculate metrics for the holiday itself by hour
holiday_metrics_by_hour as (
    select
        h.date as holiday_date,
        h.holiday_name,
        h.is_major,
        h.is_working_day,
        extract(hour from t.started_at) as hour_of_day,
        count(*) as trips_holiday
    from holidays h
    inner join {{ ref('stg_bike_trips') }} t
        on t.ride_date = h.date
    group by h.date, h.holiday_name, h.is_major, h.is_working_day, extract(hour from t.started_at)
),

-- Calculate average metrics for baseline days by hour
baseline_metrics_by_hour as (
    select
        b.holiday_date,
        extract(hour from t.started_at) as hour_of_day,
        count(*) / count(distinct b.ride_date) as trips_baseline  -- Average trips per baseline day
    from baseline_days b
    inner join {{ ref('stg_bike_trips') }} t
        on t.ride_date = b.ride_date
    group by b.holiday_date, extract(hour from t.started_at)
)

-- Final comparison with absolute and percentage changes by hour
select
    hm.holiday_date,
    hm.holiday_name,
    hm.is_major,
    hm.is_working_day,
    hm.hour_of_day,
    hm.trips_holiday,
    bm.trips_baseline,
    (hm.trips_holiday - bm.trips_baseline) as trips_abs_change,
    ((hm.trips_holiday - bm.trips_baseline) / nullif(bm.trips_baseline, 0)) * 100 as trips_pct_change

from holiday_metrics_by_hour hm
inner join baseline_metrics_by_hour bm
    on hm.holiday_date = bm.holiday_date
    and hm.hour_of_day = bm.hour_of_day
order by hm.holiday_date, hm.hour_of_day
