{{
    config(
        materialized='table'
    )
}}

-- Historical Holiday Impact Analysis (Slice 3: All Holidays with Member/Casual Breakdown)
-- Compares all available holidays bike demand to baseline weekdays
-- Includes member vs casual rider analysis

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

-- Calculate metrics for the holiday itself
holiday_metrics as (
    select
        h.date as holiday_date,
        h.holiday_name,
        h.is_major,
        h.is_working_day,
        count(*) as total_trips_holiday,
        avg(t.ride_mins) as avg_duration_holiday,
        sum(case when t.member_casual = 'member' then 1 else 0 end) as member_trips_holiday,
        sum(case when t.member_casual = 'casual' then 1 else 0 end) as casual_trips_holiday
    from holidays h
    inner join {{ ref('stg_bike_trips') }} t
        on t.ride_date = h.date
    group by h.date, h.holiday_name, h.is_major, h.is_working_day
),

-- Calculate average metrics for baseline days
baseline_metrics as (
    select
        b.holiday_date,
        count(*) / count(distinct b.ride_date) as total_trips_baseline,  -- Average trips per baseline day
        avg(t.ride_mins) as avg_duration_baseline,
        sum(case when t.member_casual = 'member' then 1 else 0 end) / count(distinct b.ride_date) as member_trips_baseline,
        sum(case when t.member_casual = 'casual' then 1 else 0 end) / count(distinct b.ride_date) as casual_trips_baseline,
        min(b.ride_date) as baseline_start_date,
        max(b.ride_date) as baseline_end_date,
        count(distinct b.ride_date) as baseline_days_count
    from baseline_days b
    inner join {{ ref('stg_bike_trips') }} t
        on t.ride_date = b.ride_date
    group by b.holiday_date
)

-- Final comparison with absolute and percentage changes
select
    hm.holiday_date,
    hm.holiday_name,
    hm.is_major,
    hm.is_working_day,

    -- Total trip metrics
    hm.total_trips_holiday,
    bm.total_trips_baseline,
    (hm.total_trips_holiday - bm.total_trips_baseline) as trips_abs_change,
    ((hm.total_trips_holiday - bm.total_trips_baseline) / nullif(bm.total_trips_baseline, 0)) * 100 as trips_pct_change,

    -- Duration metrics
    hm.avg_duration_holiday,
    bm.avg_duration_baseline,
    (hm.avg_duration_holiday - bm.avg_duration_baseline) as duration_abs_change,
    ((hm.avg_duration_holiday - bm.avg_duration_baseline) / nullif(bm.avg_duration_baseline, 0)) * 100 as duration_pct_change,

    -- Member rider metrics
    hm.member_trips_holiday,
    bm.member_trips_baseline,
    (hm.member_trips_holiday - bm.member_trips_baseline) as member_trips_abs_change,
    ((hm.member_trips_holiday - bm.member_trips_baseline) / nullif(bm.member_trips_baseline, 0)) * 100 as member_trips_pct_change,

    -- Casual rider metrics
    hm.casual_trips_holiday,
    bm.casual_trips_baseline,
    (hm.casual_trips_holiday - bm.casual_trips_baseline) as casual_trips_abs_change,
    ((hm.casual_trips_holiday - bm.casual_trips_baseline) / nullif(bm.casual_trips_baseline, 0)) * 100 as casual_trips_pct_change,

    -- Baseline metadata
    bm.baseline_start_date,
    bm.baseline_end_date,
    bm.baseline_days_count

from holiday_metrics hm
inner join baseline_metrics bm
    on hm.holiday_date = bm.holiday_date
order by hm.holiday_date
