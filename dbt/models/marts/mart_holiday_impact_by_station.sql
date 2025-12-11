{{
    config(
        materialized='table'
    )
}}

-- Holiday Impact Analysis by Station (Slice 4)
-- Analyzes bike demand changes at the station level for each holiday
-- Enables operations managers to identify which specific stations need rebalancing

with holidays as (
    select
        date,
        holiday_name,
        is_major,
        is_working_day
    from {{ ref('stg_holidays') }}
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

-- Calculate metrics for the holiday itself, grouped by station
holiday_metrics_by_station as (
    select
        h.date as holiday_date,
        h.holiday_name,
        h.is_major,
        h.is_working_day,
        t.start_station_id,
        count(*) as trips_holiday
    from holidays h
    inner join {{ ref('stg_bike_trips') }} t
        on t.ride_date = h.date
    where t.start_station_id is not null
    group by h.date, h.holiday_name, h.is_major, h.is_working_day, t.start_station_id
),

-- Calculate average metrics for baseline days, grouped by station
baseline_metrics_by_station as (
    select
        b.holiday_date,
        t.start_station_id,
        count(*) / count(distinct b.ride_date) as trips_baseline  -- Average trips per baseline day
    from baseline_days b
    inner join {{ ref('stg_bike_trips') }} t
        on t.ride_date = b.ride_date
    where t.start_station_id is not null
    group by b.holiday_date, t.start_station_id
)

-- Final comparison with geographic enrichment from dim_stations
select
    hm.holiday_date,
    hm.holiday_name,
    hm.is_major,
    hm.is_working_day,
    hm.start_station_id as station_id,
    s.station_name,
    s.area,
    s.latitude,
    s.longitude,
    hm.trips_holiday,
    bm.trips_baseline,
    (hm.trips_holiday - bm.trips_baseline) as trips_abs_change,
    ((hm.trips_holiday - bm.trips_baseline) / nullif(bm.trips_baseline, 0)) * 100 as trips_pct_change

from holiday_metrics_by_station hm
left join baseline_metrics_by_station bm
    on hm.holiday_date = bm.holiday_date
    and hm.start_station_id = bm.start_station_id
left join {{ ref('dim_stations') }} s
    on hm.start_station_id = s.station_id
order by hm.holiday_date, trips_pct_change desc
