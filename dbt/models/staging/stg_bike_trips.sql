{{
    config(
        materialized='view'
    )
}}

with source as (
    select * from {{ source('raw_bike', 'bike_trips') }}
),

cleaned as (
    select
        ride_id,
        started_at,
        ended_at,
        date_trunc('day', started_at) as ride_date,
        cast(
            (datediff('second', started_at, ended_at)) / 60.0 as double
        ) as ride_mins,
        start_station_id,
        start_station_name,
        start_lat,
        start_lng,
        end_station_id,
        end_station_name,
        end_lat,
        end_lng,
        member_casual,
        _dlt_load_timestamp,
        source_month
    from source
    where
        started_at is not null
        and ended_at is not null
        and ended_at >= started_at
)

select * from cleaned
where ride_mins between 1 and 720  -- Filter outliers (1 min to 12 hours)

