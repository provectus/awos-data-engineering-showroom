{{
    config(
        materialized='table'
    )
}}

-- Historical Holiday Impact Analysis by Geographic Area
-- Analyzes demand patterns by geographic area to show which neighborhoods need rebalancing
-- Enables area-level operational planning and resource allocation

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

-- Calculate metrics for the holiday itself by area
holiday_metrics_by_area as (
    select
        h.date as holiday_date,
        h.holiday_name,
        h.is_major,
        h.is_working_day,
        s.area,
        count(distinct t.start_station_id) as station_count,
        count(*) as trips_holiday
    from holidays h
    inner join {{ ref('stg_bike_trips') }} t
        on t.ride_date = h.date
    left join {{ ref('dim_stations') }} s
        on t.start_station_id = s.station_id
    group by h.date, h.holiday_name, h.is_major, h.is_working_day, s.area
),

-- Calculate average metrics for baseline days by area
baseline_metrics_by_area as (
    select
        b.holiday_date,
        s.area,
        count(*) / count(distinct b.ride_date) as trips_baseline  -- Average trips per baseline day
    from baseline_days b
    inner join {{ ref('stg_bike_trips') }} t
        on t.ride_date = b.ride_date
    left join {{ ref('dim_stations') }} s
        on t.start_station_id = s.station_id
    group by b.holiday_date, s.area
)

-- Final comparison with absolute and percentage changes by area
select
    hm.holiday_date,
    hm.holiday_name,
    hm.is_major,
    hm.is_working_day,
    hm.area as area_name,
    hm.station_count,
    hm.trips_holiday,
    bm.trips_baseline,
    (hm.trips_holiday - bm.trips_baseline) as trips_abs_change,
    ((hm.trips_holiday - bm.trips_baseline) / nullif(bm.trips_baseline, 0)) * 100 as trips_pct_change,
    (hm.trips_holiday / nullif(hm.station_count, 0)) as avg_station_trips_holiday,
    (bm.trips_baseline / nullif(hm.station_count, 0)) as avg_station_trips_baseline

from holiday_metrics_by_area hm
inner join baseline_metrics_by_area bm
    on hm.holiday_date = bm.holiday_date
    and hm.area = bm.area
order by hm.holiday_date, trips_pct_change desc
