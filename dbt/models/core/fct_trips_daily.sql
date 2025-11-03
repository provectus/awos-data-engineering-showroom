{{
    config(
        materialized='table'
    )
}}

with trips as (
    select
        ride_date,
        member_casual,
        count(*) as trips,
        avg(ride_mins) as avg_duration_mins,
        min(ride_mins) as min_duration_mins,
        max(ride_mins) as max_duration_mins,
        count(distinct start_station_id) as unique_start_stations,
        count(distinct end_station_id) as unique_end_stations
    from {{ ref('stg_bike_trips') }}
    group by ride_date, member_casual
)

select * from trips
order by ride_date, member_casual

