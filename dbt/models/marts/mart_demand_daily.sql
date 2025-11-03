{{
    config(
        materialized='table'
    )
}}

with daily_totals as (
    select
        ride_date,
        sum(trips) as trips_total,
        avg(avg_duration_mins) as avg_duration_mins,
        sum(case when member_casual = 'member' then trips else 0 end) as member_trips,
        sum(case when member_casual = 'casual' then trips else 0 end) as casual_trips,
        sum(unique_start_stations) as total_start_stations,
        sum(unique_end_stations) as total_end_stations
    from {{ ref('fct_trips_daily') }}
    group by ride_date
),

enhanced as (
    select
        *,
        dayname(ride_date) as day_of_week,
        dayofweek(ride_date) as day_of_week_num,
        case
            when dayofweek(ride_date) in (0, 6) then 'Weekend'
            else 'Weekday'
        end as day_type
    from daily_totals
)

select * from enhanced
order by ride_date

